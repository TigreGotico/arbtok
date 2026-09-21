"""Text normalization for the two directions speech work needs.

:func:`normalize_asr` prepares a transcript for comparison against another
transcript. What counts as "the same text" is a judgment call that differs by
purpose, so every rule is a boolean that is off unless asked for, and a bundle of
rules in production use has a name (:data:`TRUTH_CHECK`, :data:`CER_STRIP`, ...).
Two error rates are comparable only when the same bundle produced both, which is
why :meth:`AsrNorm.describe` exists: write its string beside the number.

A recognizer writes what it hears in the script it was trained on, so a Latin-
script term comes back spelled in Arabic letters and a number comes back as
words. A lexicon on the config maps such spellings back to the terms they are, and
``spoken_numbers_to_digits`` writes number words as digits: the inverse of what
:func:`normalize_for_tts` does to a number.

:func:`normalize_for_tts` prepares text to be spoken: numbers, dates and units
become words, and the string takes the canonical Unicode form the tokenizer
reads.

This module imports nothing beyond the standard library at import time; the number
parser is imported when ``spoken_numbers_to_digits`` first runs.
"""
import dataclasses
import functools
import hashlib
import re
import unicodedata
from pathlib import Path
from typing import Dict, Mapping, Optional, Tuple

__all__ = ["AsrNorm", "TtsNorm", "normalize_asr", "normalize_for_tts",
           "TRUTH_CHECK", "CER_STRIP", "CER_NORM", "CER_MARKS_FIRST", "CER_NORM_MARKS_FIRST",
           "INTELLIGIBILITY_GATE", "KSA_VOICE_AGENT", "KSA_PHONE_SHAPES", "KSA_PHONE_PREFIXES",
           "IDENTIFIER_WORDS", "ASR_NORM_VERSION", "TTS_NORM_VERSION", "spelled_codes",
           "bundled_asr_lexicon", "bundled_tts_lexicon", "cldr_units"]

_HARAKAT = "\u064B-\u0652"
_EXTENDED_MARKS = "\u0653-\u065F\u0670"
_QURANIC_MARKS = "\u0610-\u061A\u06D6-\u06DC\u06DF-\u06E8\u06EA-\u06ED"
_TATWEEL = "\u0640"
_CONTROLS = re.compile("[\u200B-\u200F\u202A-\u202E\u2060-\u2064\u2066-\u2069\uFEFF\u061C]")

_ALEF = {"آ": "ا", "أ": "ا", "إ": "ا", "ٱ": "ا"}
_TA_MARBUTA = {"ة": "ه"}
_ALEF_MAQSURA = {"ى": "ي"}
_HAMZA_CARRIERS = {"ئ": "ي", "ؤ": "و"}
_DIGITS = {chr(base + i): str(i) for base in (0x0660, 0x06F0) for i in range(10)}

_PUNCTUATION = re.compile(r"[^\w\s]")
_NOT_ARABIC_BLOCK = re.compile("[^\u0600-\u06FF\\s]")
_WORD_FINAL_HAMZA = re.compile(r"ء(?!\S)")
_WHITESPACE = re.compile(r"\s+")
_WORDS_AND_GAPS = re.compile(r"(\s+)")
_DICTATED_DIGITS = re.compile(r"(?<!\S)\d(?:\s+\d){6,}(?!\S)")
# What may stand at the edge of a word without being part of it. A combining mark is
# not a word character to ``re`` and is very much part of the word it sits on.
_NOT_EDGE = r"\w\s\u0300-\u036F\u0610-\u061A\u064B-\u065F\u0670\u06D6-\u06ED"
_EDGE_PUNCTUATION = re.compile(rf"^([^{_NOT_EDGE}]*)(.*?)([^{_NOT_EDGE}]*)$", re.DOTALL)

# Markup a transcriber wrote and no recognizer can produce. Closed lists: a label
# or a wrapper belongs here once it has been seen in a reference, because a rule
# keyed on bracket shape or on script would also delete bracketed speech.
_EVENT_LABELS = ("exhale", "inhale", "laughter", "laugh", "laughs", "mumble",
                 "noise", "sigh", "clear_throat", "clear throat", "cough",
                 "cry", "gasp", "sound effect", "sound", "alert",
                 "notification", "emotion:angry", "?",
                 "موسيقى", "تصفيق", "آه", "بكاء", "ضحك", "آآ", "صوت_تنهد")
_LANGUAGE_DELIMITERS = ("foreign word", "foreign language", "code-switching",
                        "/code-switching", "/foreign", "/english", "foreign",
                        "fr", "en")
_LANGUAGE_NAMES = ("french", "fr", "english", "en", "arabic", "ar", "spanish",
                   "italian")
_SPAN_TAG = r"/?(?:foreign|english|french|arabic|lang)(?:\s+[^<>\]]*)?"
_OPEN, _CLOSE = r"[\[<(]+\s*", r"\s*[\]>)]"
_TIMESTAMP = r"\d{1,2}:\d{2}(?::\d{2})?"


def _alt(words):
    return "|".join(re.escape(w) for w in words)


_EVENT = re.compile(
    _OPEN + r"(?:" + _alt(_EVENT_LABELS) + r"|" + _TIMESTAMP + r"|"
    + _alt(_LANGUAGE_DELIMITERS) + r"|" + _SPAN_TAG + r")" + _CLOSE,
    re.IGNORECASE)
# The label is markup; the words after the colon were spoken and stay.
_LANGUAGE_WRAPPER = re.compile(
    _OPEN + r"(?:" + _alt(_LANGUAGE_NAMES) + r")\s*:\s*([^\]>)]*)" + _CLOSE,
    re.IGNORECASE)


def _as_lexicon(lexicon) -> Tuple[Tuple[str, str], ...]:
    """A mapping, or pairs, as the sorted tuple a frozen config holds."""
    entries = tuple(sorted(lexicon.items() if isinstance(lexicon, Mapping) else lexicon))
    for entry in entries:
        if len(entry) != 2 or not all(isinstance(part, str) for part in entry) or not entry[0].strip():
            raise ValueError(f"a lexicon entry is a non-empty string and the string it stands for, got {entry!r}")
    return entries


def _as_number_forms(forms) -> Tuple[Tuple[int, str], ...]:
    """A mapping from a value to a word, as sorted pairs; a bool is not a value."""
    pairs = forms.items() if isinstance(forms, Mapping) else forms
    out = {}
    for value, word in pairs:
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise TypeError(f"a number form is keyed by a non-negative int, not {value!r}")
        if not isinstance(word, str) or not word.strip():
            raise TypeError(f"the form for {value} is {word!r}; it must be a word")
        out[value] = word.strip()
    return tuple(sorted(out.items()))


def _as_text(text, function: str) -> str:
    if not isinstance(text, str):
        raise TypeError(f"{function} takes a str, got {type(text).__name__}: a missing text is the "
                        "caller's to decide about, not to normalize")
    return text


def _describe_lexicon(entries: Tuple[Tuple[str, str], ...]) -> str:
    if not entries:
        return ""
    body = "\n".join(f"{k}\t{v}" for k, v in entries)
    return f"; lexicon {len(entries)} entries sha256:{hashlib.sha256(body.encode('utf-8')).hexdigest()[:16]}"


def _describe_parser() -> str:
    # A description is written beside a result after the work is done; it names what it
    # can and never costs the caller that result.
    from importlib.metadata import PackageNotFoundError, version
    try:
        return f"; ovos-number-parser {version('ovos-number-parser')}"
    except PackageNotFoundError:
        return "; ovos-number-parser unknown"


def _rule_set(*definitions) -> str:
    """A name for a set of rules, computed from the rules: their flags in order, their
    patterns and their tables. It moves when any of them moves and at no other time."""
    parts = [d.pattern if hasattr(d, "pattern") else repr(sorted(d.items())) if isinstance(d, dict) else repr(d)
             for d in definitions]
    return hashlib.sha256("\x1f".join(parts).encode("utf-8")).hexdigest()[:12]


@dataclasses.dataclass(frozen=True)
class AsrNorm:
    """Which rules :func:`normalize_asr` applies. Every rule is off by default.

    The rules run in the order the fields are listed, with one exception that is
    itself a flag: ``punctuation_before_marks`` moves ``blank_punctuation`` ahead
    of the mark rules. A lexicon, when one is passed, is applied after the mark
    rules and before ``spoken_numbers_to_digits``.
    """
    #: Unicode NFC, so a composed and a decomposed spelling compare equal.
    nfc: bool = False
    #: Drop bracketed non-speech labels, timestamps and language tags; unwrap
    #: ``[french: ...]`` to the speech it carries.
    strip_event_markup: bool = False
    #: Drop zero-width and bidirectional control characters.
    strip_controls: bool = False
    #: Run ``blank_punctuation`` before the mark rules. ``\w`` does not match a
    #: combining mark, so in this order each mark is blanked to a space and a
    #: pointed word breaks into letters. Instruments with numbers on record run
    #: in this order; it is here so those numbers can be reproduced.
    punctuation_before_marks: bool = False
    #: Drop fathatan to sukun, U+064B-U+0652.
    strip_harakat: bool = False
    #: Drop maddah to wavy hamza below and the dagger alif, U+0653-U+065F, U+0670.
    strip_extended_marks: bool = False
    #: Drop honorific and Quranic annotation marks, U+0610-U+061A, U+06D6-U+06ED.
    strip_quranic_marks: bool = False
    #: Drop tatweel, U+0640.
    strip_tatweel: bool = False
    #: Write number words as digits: ``خمسة وأربعون ألف`` becomes ``45000``. Runs after
    #: the lexicon, so a term spelled with a number word is a term first. Arabic-Indic
    #: digits the parser meets come back as ASCII, and the words of a text it changed
    #: come back single-spaced.
    spoken_numbers_to_digits: bool = False
    #: Seven or more single digits standing one by one become one run: a phone number
    #: read aloud arrives as ``0 5 5 3 1 7 9 2 4 5``. Shorter runs are left apart,
    #: because two small numbers side by side are two numbers.
    join_dictated_digits: bool = False
    #: Alef with madda, with hamza above or below, and alef wasla become bare alef.
    unify_alef: bool = False
    #: Ta marbuta becomes ha.
    unify_ta_marbuta: bool = False
    #: Alef maqsura becomes ya.
    unify_alef_maqsura: bool = False
    #: Ya with hamza becomes ya; waw with hamza becomes waw.
    unify_hamza_carriers: bool = False
    #: Arabic-Indic and Extended Arabic-Indic digits become ASCII digits.
    fold_digits: bool = False
    #: ``str.lower()``, for Latin-script terms.
    fold_case: bool = False
    #: Blank every character outside U+0600-U+06FF: punctuation, ASCII digits and
    #: Latin-script words go; Arabic-Indic digits stay.
    arabic_block_only: bool = False
    #: Blank every character that is neither a word character nor whitespace.
    blank_punctuation: bool = False
    #: Drop a bare hamza that ends a word.
    drop_word_final_hamza: bool = False
    #: Runs of whitespace become one space, and the ends are trimmed.
    collapse_whitespace: bool = False
    #: Spellings and the terms they stand for, set with :meth:`with_lexicon`. It lives
    #: here, and nowhere else, so that the config a text was normalized under says
    #: everything that was done to it.
    lexicon: Tuple[Tuple[str, str], ...] = ()

    def __post_init__(self):
        object.__setattr__(self, "lexicon", _as_lexicon(self.lexicon))

    def with_lexicon(self, lexicon: Mapping[str, str]) -> "AsrNorm":
        """This config with ``lexicon``, a mapping from a spelling to its term."""
        return dataclasses.replace(self, lexicon=_as_lexicon(lexicon))

    def describe(self) -> str:
        """A stable string naming the rule set, the rules that are on, and the lexicon.

        A lexicon is named by its entry count and a digest of its sorted entries, so two
        runs that used different term lists do not describe themselves alike. When
        numbers are read, the parser that reads them is named with its version.
        """
        on = [f.name for f in dataclasses.fields(self) if getattr(self, f.name) is True]
        return (f"arbtok-asr-norm {ASR_NORM_VERSION}: {','.join(on) or 'none'}"
                + _describe_lexicon(self.lexicon)
                + (_describe_parser() if self.spoken_numbers_to_digits else ""))


_NOTHING = AsrNorm()

#: Names the rule set of :func:`normalize_asr`. It is a digest of the flags in their
#: order and of every pattern and table the rules use, so it changes when a rule or
#: the order changes and cannot be left behind by an edit. It does not cover what a
#: config carries as values: a lexicon is named by :meth:`AsrNorm.describe`, not here.
ASR_NORM_VERSION = _rule_set([f.name for f in dataclasses.fields(AsrNorm)], _HARAKAT, _EXTENDED_MARKS,
                             _QURANIC_MARKS, _TATWEEL, _CONTROLS, _ALEF, _TA_MARBUTA, _ALEF_MAQSURA,
                             _HAMZA_CARRIERS, _DIGITS, _PUNCTUATION, _NOT_ARABIC_BLOCK, _WORD_FINAL_HAMZA,
                             _WHITESPACE, _DICTATED_DIGITS, _EDGE_PUNCTUATION, _EVENT, _LANGUAGE_WRAPPER)


@functools.lru_cache(maxsize=None)
def _compiled(config: AsrNorm):
    ranges = "".join(r for on, r in ((config.strip_harakat, _HARAKAT),
                                     (config.strip_extended_marks, _EXTENDED_MARKS),
                                     (config.strip_quranic_marks, _QURANIC_MARKS),
                                     (config.strip_tatweel, _TATWEEL)) if on)
    table = {}
    for on, mapping in ((config.unify_alef, _ALEF),
                        (config.unify_ta_marbuta, _TA_MARBUTA),
                        (config.unify_alef_maqsura, _ALEF_MAQSURA),
                        (config.unify_hamza_carriers, _HAMZA_CARRIERS),
                        (config.fold_digits, _DIGITS)):
        if on:
            table.update(mapping)
    return (re.compile(f"[{ranges}]") if ranges else None,
            str.maketrans(table) if table else None)


@functools.lru_cache(maxsize=None)
def _character_rules(config: AsrNorm) -> AsrNorm:
    """The rules a spelling and a word are both read under before they are compared."""
    return dataclasses.replace(config, spoken_numbers_to_digits=False, strip_event_markup=False,
                               collapse_whitespace=True, lexicon=())


@functools.lru_cache(maxsize=64)
def _lexicon_index(config: AsrNorm):
    """Spellings as word tuples, read under the same character rules as the text."""
    rules = _character_rules(config)
    index = {}
    for spelling, term in config.lexicon:
        words = tuple(normalize_asr(spelling, rules).split())
        if words:
            index[words] = term
    return index, max((len(w) for w in index), default=0)


@functools.lru_cache(maxsize=1 << 16)
def _word_form(rules: AsrNorm, word: str) -> str:
    return normalize_asr(word, rules)


def _apply_lexicon(text: str, config: AsrNorm) -> str:
    index, longest = _lexicon_index(config)
    parts = _WORDS_AND_GAPS.split(text)  # words at even positions, the gaps between them at odd
    rules = _character_rules(config)
    edges = [_EDGE_PUNCTUATION.match(w).groups() for w in parts[::2]]
    forms = [_word_form(rules, core) for _, core, _ in edges]
    out, i = [], 0
    while i < len(edges):
        for n in range(min(longest, len(edges) - i), 0, -1):
            # Punctuation may open the first word and close the last; inside a spelling it
            # separates two things that were not said together.
            inside_clean = all(not edges[j][2] for j in range(i, i + n - 1)) and \
                all(not edges[j][0] for j in range(i + 1, i + n))
            term = index.get(tuple(forms[i:i + n])) if inside_clean and all(forms[i:i + n]) else None
            if term is not None:
                out.append(edges[i][0] + term + edges[i + n - 1][2])
                out.append(parts[2 * (i + n) - 1] if 2 * (i + n) - 1 < len(parts) else "")
                i += n
                break
        else:
            out.append(parts[2 * i])
            out.append(parts[2 * i + 1] if 2 * i + 1 < len(parts) else "")
            i += 1
    return "".join(out)


def _numbers_to_digits(text: str, lang: str) -> str:
    """The parser reads words and hands back words joined by single spaces, whether or
    not it found a number. Text it found nothing in is returned as it came; text it
    changed keeps its leading and trailing whitespace."""
    from ovos_number_parser import numbers_to_digits
    words = text.split()
    if not words:
        return text
    read = numbers_to_digits(" ".join(words), lang=lang)
    if read.split() == words:
        return text
    return text[:len(text) - len(text.lstrip())] + read + text[len(text.rstrip()):]


def normalize_asr(text: str, config: Optional[AsrNorm] = None, *, lang: str = "ar",
                  **flags: bool) -> str:
    """Normalize a transcript for comparison.

    Pass a named bundle, flags, or a bundle with flags that override it::

        normalize_asr(text, CER_NORM)
        normalize_asr(text, strip_harakat=True, collapse_whitespace=True)
        normalize_asr(text, TRUTH_CHECK, fold_digits=True)
        normalize_asr(text, CER_NORM.with_lexicon({"بي ام دبليو": "BMW"}))

    With nothing on, the text comes back unchanged. For tokens, split the result.

    A lexicon maps a spelling to the term it stands for and is part of the config, so
    that ``config.describe()`` names it; it cannot be passed beside the config.
    A spelling matches whole words only, the longest spelling first, and both it and
    the text are read under the character rules that are on: with ``unify_alef`` a
    spelling written with ``إ`` finds the word written with ``ا``, and without it
    does not. A prefixed form such as ``والبي ام دبليو`` is a different spelling and
    needs its own entry. ``lang`` is the language whose number words
    ``spoken_numbers_to_digits`` reads.
    """
    config = config or _NOTHING
    if "lexicon" in flags:
        raise TypeError("a lexicon is part of the config: normalize_asr(text, config.with_lexicon(lexicon))")
    if flags:
        config = dataclasses.replace(config, **flags)
    marks, table = _compiled(dataclasses.replace(config, lexicon=()) if config.lexicon else config)
    text = _as_text(text, "normalize_asr")
    if config.nfc:
        text = unicodedata.normalize("NFC", text)
    if config.strip_event_markup:
        text = _LANGUAGE_WRAPPER.sub(r" \1 ", _EVENT.sub(" ", text))
    if config.strip_controls:
        text = _CONTROLS.sub("", text)
    if config.blank_punctuation and config.punctuation_before_marks:
        text = _PUNCTUATION.sub(" ", text)
    if marks:
        text = marks.sub("", text)
    if config.lexicon:
        text = _apply_lexicon(text, config)
    if config.spoken_numbers_to_digits:
        text = _numbers_to_digits(text, lang)
    if config.join_dictated_digits:
        text = _DICTATED_DIGITS.sub(lambda m: _WHITESPACE.sub("", m.group(0)), text)
    if table:
        text = text.translate(table)
    if config.fold_case:
        text = text.lower()
    if config.arabic_block_only:
        text = _NOT_ARABIC_BLOCK.sub(" ", text)
    if config.blank_punctuation and not config.punctuation_before_marks:
        text = _PUNCTUATION.sub(" ", text)
    if config.drop_word_final_hamza:
        text = _WORD_FINAL_HAMZA.sub("", text)
    if config.collapse_whitespace:
        text = _WHITESPACE.sub(" ", text).strip()
    return text


_ALL_MARKS = dict(strip_harakat=True, strip_extended_marks=True,
                  strip_quranic_marks=True, strip_tatweel=True)
_ALL_LETTER_FORMS = dict(unify_alef=True, unify_ta_marbuta=True,
                         unify_alef_maqsura=True, unify_hamza_carriers=True)

#: Letter forms and marks only; digits and punctuation pass through. For checking
#: a transcript against a re-transcription and for code-switch detection.
TRUTH_CHECK = AsrNorm(nfc=True, collapse_whitespace=True, **_ALL_MARKS, **_ALL_LETTER_FORMS)

#: The TTS bake-off CER instrument: punctuation blanked first, then harakat and
#: tatweel dropped. No letter form is unified.
CER_STRIP = AsrNorm(blank_punctuation=True, punctuation_before_marks=True,
                    strip_harakat=True, strip_tatweel=True, collapse_whitespace=True)

#: :data:`CER_STRIP` with letter forms unified and a word-final bare hamza dropped.
CER_NORM = dataclasses.replace(CER_STRIP, drop_word_final_hamza=True, **_ALL_LETTER_FORMS)

#: Transcriber markup dropped, then every mark, then punctuation: a pointed word
#: stays one token. For references that carry diacritics or event labels.
CER_MARKS_FIRST = AsrNorm(strip_event_markup=True, blank_punctuation=True,
                          collapse_whitespace=True, **_ALL_MARKS)

#: :data:`CER_MARKS_FIRST` with letter forms unified and a word-final bare hamza dropped.
CER_NORM_MARKS_FIRST = dataclasses.replace(CER_MARKS_FIRST, drop_word_final_hamza=True,
                                           **_ALL_LETTER_FORMS)

#: Intelligibility gate for synthetic speech: marks dropped, letter forms unified,
#: and everything outside the Arabic block blanked, Latin code-switch included.
INTELLIGIBILITY_GATE = AsrNorm(strip_harakat=True, strip_extended_marks=True,
                               strip_tatweel=True, arabic_block_only=True,
                               collapse_whitespace=True, **_ALL_LETTER_FORMS)


_LATIN_RUN_EDGE = r"(?<![A-Za-z0-9])", r"(?![A-Za-z0-9])"
_CODE = re.compile(_LATIN_RUN_EDGE[0] + r"(?=[A-Z0-9]*[A-Z])[A-Z0-9]+" + _LATIN_RUN_EDGE[1])


@functools.lru_cache(maxsize=None)
def spelled_codes(lang: str = "ar") -> Dict[str, str]:
    """The bundled table: each Latin capital and ASCII digit to its spoken name, pointed.

    The names are the English ones as a speaker of ``lang`` says them. A pointed
    spelling is one the diacritizer leaves alone, so the reading is the table's and
    not a guess from the sentence around it.
    """
    path = Path(__file__).parent / "data" / "tts_lexicons" / f"en-codes.{lang.split('-')[0]}.tsv"
    if not path.is_file():
        raise ValueError(f"no bundled code spellings for {lang!r}; put the terms in the config's lexicon")
    rows = (line.rstrip("\n").split("\t") for line in path.read_text(encoding="utf-8").splitlines()
            if line and not line.startswith("#"))
    return {character: pointed for character, _, pointed in rows}


#: How far a page speaks for a name, nearest first: the maker's own site, its
#: distributor's, then a marketplace.
_PUBLISHED_BY = ("brand-site", "distributor-site", "marketplace")


@functools.lru_cache(maxsize=None)
def _term_rows(name: str):
    path = Path(__file__).parent / "data" / "term_lexicons" / f"{name}.tsv"
    if not path.is_file():
        have = sorted(p.stem for p in path.parent.glob("*.tsv"))
        raise ValueError(f"no bundled term lexicon {name!r}; bundled: {have}")
    lines = path.read_text(encoding="utf-8").splitlines()
    # The header names the columns, as a comment line or as the first row of the table.
    header = [line for line in lines if line.startswith(("# latin\t", "latin\t"))][0]
    columns = header.lstrip("# ").split("\t")
    return tuple(dict(zip(columns, line.split("\t"))) for line in lines
                 if line and not line.startswith("#") and line != header)


# A CLDR display name that a voice can say: Arabic letters, their marks, spaces. Some are
# a symbol, a Latin abbreviation, or carry a slash or digits, and are names only on paper.
_SPEAKABLE = re.compile("[\u0621-\u064A\u064B-\u0652\u0670\u0671 ]+")
# Codes CLDR names for its own use: the two pseudo-locales and the unknown region.
_NOT_A_PLACE = ("XA", "XB", "ZZ")


def _cldr_rows(name: str):
    """The rows of a CLDR table worth saying: a speakable Arabic name for a real thing, the
    long form where CLDR gives several widths, one row per Latin name."""
    rows = [r for r in _term_rows(name) if _SPEAKABLE.fullmatch(r["arabic_form"])
            and r["cldr_key"].split("/")[-1] not in _NOT_A_PLACE
            and (not r["cldr_key"].startswith("units/") or r["cldr_key"].startswith("units/long/"))]
    return sorted(rows, key=lambda r: (len(r["cldr_key"]), r["cldr_key"]))


@functools.lru_cache(maxsize=None)
def cldr_units(lang: str = "ar") -> Dict[str, str]:
    """Unit symbols as English writes them, ``km`` ``kg`` ``hp``, each mapped to the unit's
    name in ``lang`` from Unicode CLDR. For reading a unit that follows a number; a bare
    ``in`` or ``m`` in running text is not a unit, which is why this is not a lexicon."""
    if lang.split("-")[0] != "ar":
        raise ValueError(f"no bundled CLDR unit names for {lang!r}")
    rows = _term_rows("units-cldr")
    names = {r["cldr_key"].split("/")[2]: r["arabic_form"] for r in rows
             if r["cldr_key"].startswith("units/long/") and _SPEAKABLE.fullmatch(r["arabic_form"])}
    symbols: Dict[str, str] = {}
    for r in rows:
        width, unit = r["cldr_key"].split("/")[1:3]
        symbol = r["latin"]
        # One Latin letter after a number is as often a model or a grade as a unit
        # (`15 S`, `Class 5 C`); only the metre is common enough to read.
        if len(symbol) == 1 and symbol.isascii() and symbol.isalpha() and symbol != "m":
            continue
        # A percentage is already spoken, in this package's settled spelling of مئة.
        if symbol in ("%", "\u066A"):
            continue
        if width != "long" and unit in names and not any(c.isdigit() for c in symbol):
            symbols.setdefault(symbol, names[unit])
    return symbols


def bundled_asr_lexicon(name: str = "cars-sa") -> Dict[str, str]:
    """Arabic spellings of a name, each mapped to the name: for ``normalize_asr``.

    ``cars-sa`` holds car makes and models as Saudi maker, distributor and marketplace
    sites spell them; every row carries the page it was read from and the day. A name
    has as many entries as it has published spellings, since a recognizer may write
    any of them. ``common-en`` holds English terms in everyday use in their
    conventional Arabic spelling.
    """
    if name.endswith("-cldr"):
        raise ValueError(f"{name!r} holds Arabic names of things, not spellings of Latin-script terms: "
                         "read backwards it would translate Arabic words into English")
    return {row["arabic_form"]: row["latin"] for row in _term_rows(name)}


def bundled_tts_lexicon(name: str = "cars-sa", pointed: bool = True) -> Dict[str, str]:
    """Each name mapped to one Arabic spelling: for ``normalize_for_tts``.

    ``cars-sa``: where pages disagree the maker's own site wins, then its
    distributor's, then a marketplace. The maker publishes the name it wants said; a
    marketplace publishes the one buyers search for. These spellings are as published,
    which is unpointed, so their short vowels are still the diacritizer's to supply.

    ``common-en`` carries a pointed spelling beside the conventional one, and
    ``pointed`` chooses between them. Its pointing is authored by this package and
    cites no source; the file says so on every row.
    """
    if name.endswith("-cldr"):
        lexicon: Dict[str, str] = {}
        for row in _cldr_rows(name):
            lexicon.setdefault(row["latin"], row["arabic_form"])
            if row["cldr_key"].startswith("numbers/currencies/"):
                lexicon.setdefault(row["cldr_key"].split("/")[2], row["arabic_form"])  # SAR, USD
        return lexicon
    chosen: Dict[str, Tuple[int, str]] = {}
    for row in _term_rows(name):
        rank = _PUBLISHED_BY.index(row["form_kind"]) if "form_kind" in row else 0
        spelling = row["pointed"] if pointed and "pointed" in row else row["arabic_form"]
        if row["latin"] not in chosen or rank < chosen[row["latin"]][0]:
            chosen[row["latin"]] = (rank, spelling)
    return {latin: spelling for latin, (_, spelling) in chosen.items()}


@functools.lru_cache(maxsize=64)
def _term_pattern(lexicon: Tuple[Tuple[str, str], ...]):
    said = {term.lower(): spoken for term, spoken in lexicon}
    longest_first = sorted(said, key=len, reverse=True)
    return re.compile(_LATIN_RUN_EDGE[0] + "(" + "|".join(re.escape(t) for t in longest_first) + ")"
                      + _LATIN_RUN_EDGE[1], re.IGNORECASE), said


#: Saudi mobile numbers as they are written in running text, grouped or not: ``05`` or
#: ``966 5`` and then exactly eight digits, with a space, a hyphen or a spaced hyphen
#: between any two of them. No separator may follow the ``5`` itself, which splits the
#: operator code (``50``, ``55``); a date on the fifth of a month, ``05-06-2024 12:30``,
#: is the text that starts that way. The digits are ASCII by name: ``\d`` also matches
#: Arabic-Indic digits, and a phone number would then take its last digits from an
#: Arabic-Indic number written after it.
KSA_PHONE_SHAPES = (r"(?:(?:\+|00)?966[\s\-]*5|05)(?![\s\-])[0-9](?:(?:\s*-\s*|\s+)?[0-9]){7}(?![0-9])",)
#: What a bare digit run starts with when it is a Saudi number: country code, local
#: mobile, toll-free and unified numbers, landline area codes. A price and a phone
#: number cannot be told apart by length, so each of these names a real prefix.
KSA_PHONE_PREFIXES = (r"(?:00)?966\d{4,}", r"05\d{5,}", r"(?:800|920)\d{5,}", r"01[1-7]\d{6,}")
#: Words after which a number is a reference to be read out, not a quantity.
IDENTIFIER_WORDS = ("كود", "الكود", "رمز", "الرمز",
                    "رقم", "الرقم", "رقمك", "رقمه", "رقمي",
                    "جوال", "جوالك", "جوالي", "هاتف", "موبايل", "تلفون",
                    "فرع", "الفرع", "شاسيه", "الطلب", "الحجز",
                    "code", "number", "no", "phone", "mobile", "branch", "ref", "pin", "otp")

_DIGIT_WORDS = dict(zip("0123456789", ("صفر", "واحد", "اثنين", "ثلاثة", "أربعة", "خمسة",
                                       "ستة", "سبعة", "ثمانية", "تسعة")))
_EASTERN_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")
_FUSED_HUNDREDS = {fused + spelling: spaced + " مئة"
                   for fused, spaced in (("ثلاث", "ثلاث"), ("أربع", "أربع"), ("خمس", "خمس"), ("ست", "ست"),
                                         ("سبع", "سبع"), ("ثمان", "ثمان"), ("تسع", "تسع"))
                   for spelling in ("مئة", "مائة")}
# The colloquial hundreds a lect's number table writes, spaced the same way and for the same reason.
_FUSED_HUNDREDS.update({stem + "مية": stem + " مية"
                        for stem in ("ثلاث", "ثلث", "تلت", "تلات", "اربع", "أربع", "خمس", "ست", "سبع", "ثمن",
                                     "ثمان", "تمن", "تمان", "تسع")})
_FUSED_HUNDREDS_RE = re.compile("|".join(map(re.escape, sorted(_FUSED_HUNDREDS, key=len, reverse=True))))
_PERCENT = re.compile(r"(\d+(?:\.\d+)?)\s*[%٪]")
_LONG_RUN = re.compile(r"(?<![0-9٠-٩])\+?\d{11,}(?![0-9])")
_CODE_DIGITS = re.compile(r"(?<![0-9A-Za-z])(?:(?<=[A-Za-z] )\d{1,4}|\d{1,4}(?= [A-Za-z]))(?![0-9A-Za-z])")
_DIGIT_RUN = re.compile(r"(?<![0-9A-Za-z٠-٩])(\+?\d+)(?![0-9A-Za-z])")
_WESTERN_NUMBER = re.compile(r"(?<![0-9A-Za-z])(\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?)(?![0-9A-Za-z])")
_EASTERN_NUMBER = re.compile(r"(?<![0-9٠-٩A-Za-z])([٠-٩]{1,3}(?:[،٬][٠-٩]{3})+(?:[.٫][٠-٩]+)?"
                             r"|[٠-٩]+(?:[.٫][٠-٩]+)?)(?![0-9٠-٩A-Za-z])")
_PROCLITIC = r"[بولك]?ا?ل?"
_HELD_DIGITS = 0xE000  # private-use characters stand in for digits a rule must not read
#: ISO 639-3 codes for the individual Arabic languages. They are listed because they
#: cannot be recognized by shape: they sort beside ``arc`` (Aramaic) and ``arn``
#: (Mapudungun), which are unrelated languages. Source: ISO 639-3 code table,
#: https://iso639-3.sil.org/code_tables/639/data, read for the macrolanguage ``ara``.
ARABIC_LANGUAGE_CODES = frozenset({
    "arb",  # Standard Arabic
    "aao", "abh", "abv", "acm", "acq", "acw", "acx", "acy", "adf", "aeb",
    "aec", "afb", "ajp", "apc", "apd", "arq", "ars", "ary", "arz", "auz",
    "avl", "ayh", "ayl", "ayn", "ayp", "bbz", "pga", "shu", "ssh",
})


def is_arabic_lang(lang: str) -> bool:
    """Whether ``lang`` names an Arabic variety: ``ar`` and every ``ar-…`` tag, plus the
    ISO 639-3 code of an individual Arabic language (``arb``, ``arz``, ``ary``, ``ars``).
    Case does not matter, as it does not in BCP-47, and neither does an underscore
    written where a hyphen belongs (``ar_SA``), the same normalization
    :func:`arbtok.spec_for_lang` applies before it resolves a tag.

    ``ara``, the ISO 639-3 code of the Arabic macrolanguage, is deliberately not in
    :data:`ARABIC_LANGUAGE_CODES`: that set holds individual-language codes, and the
    macrolanguage is already named by ``ar``.

    This asks what the caller wrote. :func:`arbtok.spec_for_lang` cannot answer it: it
    resolves an unknown tag to MSA, so it calls every language on earth Arabic.
    """
    lang = lang.lower().replace("_", "-")
    return lang == "ar" or lang.startswith("ar-") or lang in ARABIC_LANGUAGE_CODES


#: Rules whose output is Arabic words whatever ``lang`` says.
_ARABIC_ONLY = ("speak_percent", "phone_shapes", "long_digit_runs", "phone_prefixes", "identifier_words",
                "dialect_numbers", "number_forms")


@dataclasses.dataclass(frozen=True)
class TtsNorm:
    """Which rules :func:`normalize_for_tts` applies, in the order they run.

    ``spoken_forms`` and ``canonical_unicode`` are on by default, which is what the
    G2P plugin runs. The rest are off. Those from ``speak_percent`` to
    ``space_fused_hundreds`` are rules a voice agent needs when it reads out prices,
    phone numbers and booking references; :data:`KSA_VOICE_AGENT` turns them on with
    Saudi phone shapes.
    """
    #: Drop zero-width and bidirectional control characters.
    strip_controls: bool = False
    #: Read ``X5``-shaped codes character by character from :func:`spelled_codes`.
    spell_out_codes: bool = False
    #: ``4.5%`` becomes ``4.5 في المئة``, and the number is then spoken like any other.
    speak_percent: bool = False
    #: A number of up to four digits beside a Latin word, ``MG 5`` or ``7 Series``,
    #: belongs to the name and is kept from every number rule below.
    keep_code_digits: bool = False
    #: Patterns of a phone number in running text; a match is read digit by digit.
    phone_shapes: Tuple[str, ...] = ()
    #: A run of eleven or more digits is a reference and is read digit by digit, with
    #: a leading ``+`` dropped as :func:`_digit_by_digit` says.
    long_digit_runs: bool = False
    #: Patterns a bare digit run matches whole when it is a phone number. When any is
    #: given, a run written with a leading ``+`` is one too.
    phone_prefixes: Tuple[str, ...] = ()
    #: Words after which a digit run is a reference and is read digit by digit:
    #: ``الكود 4729``, ``برقم الحجز 3401``. One other word may stand between.
    identifier_words: Tuple[str, ...] = ()
    #: Speak Arabic-Indic and ASCII numbers as cardinals here, ahead of
    #: ``spoken_forms``, so that the three flags below apply to them.
    cardinal_numbers: bool = False
    #: A number ``cardinal_numbers`` cannot speak is left as written and the rest of
    #: the text is still read, where otherwise the error is raised. For a caller that
    #: must say something: one odd number should not cost the whole sentence.
    leave_unspeakable_numbers: bool = False
    #: Cardinals in the oblique case, the one connected speech uses.
    oblique_numbers: bool = False
    #: In the cardinals ``cardinal_numbers`` speaks, ``ثلاثمئة`` becomes ``ثلاث مئة``: a
    #: synthesizer keeps the spaced form and garbles the fused one. Number words the
    #: author wrote are left as written.
    space_fused_hundreds: bool = False
    #: The cardinals and the digit-by-digit readings take the words of the lect ``lang``
    #: names, asked of the number parser under that lect's ISO 639-3 code: Jidda and
    #: Cairo do not say 15 alike. With no lect in the tag, or none the parser has
    #: cited words for, the words are the literary ones. Runs before
    #: ``space_fused_hundreds``.
    dialect_numbers: bool = False
    #: Your own words for values, ``{100: "مية"}``, laid over the lect's, or used
    #: alone when ``dialect_numbers`` is off. Set with :meth:`with_number_forms`.
    number_forms: Tuple[Tuple[int, str], ...] = ()
    #: Dates, times, numbers and units as words in ``lang``.
    spoken_forms: bool = True
    #: Tatweel dropped, NFC, shadda ordered before its vowel, the spellings of مائة settled.
    canonical_unicode: bool = True
    #: Terms and the way each is said, set with :meth:`with_lexicon`; applied first.
    lexicon: Tuple[Tuple[str, str], ...] = ()

    def __post_init__(self):
        object.__setattr__(self, "lexicon", _as_lexicon(self.lexicon))
        object.__setattr__(self, "number_forms", _as_number_forms(self.number_forms))
        for name in ("phone_shapes", "phone_prefixes", "identifier_words"):
            object.__setattr__(self, name, tuple(getattr(self, name)))

    def with_lexicon(self, lexicon: Mapping[str, str]) -> "TtsNorm":
        """This config with ``lexicon``, a mapping from a term to its spoken form."""
        return dataclasses.replace(self, lexicon=_as_lexicon(lexicon))

    def with_number_forms(self, forms: Mapping[int, str]) -> "TtsNorm":
        """This config with ``forms``, a mapping from a value to the word said for it."""
        return dataclasses.replace(self, number_forms=_as_number_forms(forms))

    def describe(self) -> str:
        """A stable string naming the rule set, what is on, and the lexicon by content."""
        on = [f.name if getattr(self, f.name) is True
              else f"{f.name}={hashlib.sha256(repr(getattr(self, f.name)).encode()).hexdigest()[:8]}"
              for f in dataclasses.fields(self) if getattr(self, f.name) and f.name != "lexicon"]
        # ``dialect_numbers`` takes its words from the parser as the cardinals do, so
        # the parser is named for it too: it is what identifies the words a run used.
        speaks = self.cardinal_numbers or self.spoken_forms or self.dialect_numbers
        return (f"arbtok-tts-norm {TTS_NORM_VERSION}: {','.join(on) or 'none'}"
                + _describe_lexicon(self.lexicon) + (_describe_parser() if speaks else ""))


#: Names the rule set of :func:`normalize_for_tts`, computed the way
#: :data:`ASR_NORM_VERSION` is. It covers the rules and their patterns. What a config
#: carries as values is configuration and is outside it: :data:`KSA_PHONE_SHAPES`,
#: :data:`KSA_PHONE_PREFIXES`, :data:`IDENTIFIER_WORDS` and a lexicon are named by
#: :meth:`TtsNorm.describe`, each by a digest. A record that must distinguish two runs
#: keeps the ``describe()`` string, not the version alone.
TTS_NORM_VERSION = _rule_set([f.name for f in dataclasses.fields(TtsNorm)], _CONTROLS, _CODE, _DIGIT_WORDS,
                             _FUSED_HUNDREDS, _PERCENT, _LONG_RUN, _CODE_DIGITS, _DIGIT_RUN, _WESTERN_NUMBER,
                             _EASTERN_NUMBER, _PROCLITIC, _LATIN_RUN_EDGE)
_PLUGIN_DEFAULT = TtsNorm()

#: What a Saudi voice agent's replies need before synthesis: percentages spoken, the
#: digits of a model name kept, phone numbers, long references and numbers after a
#: word such as رقم or كود read digit by digit, and every other number a cardinal in
#: the oblique case with its hundreds spaced.
KSA_VOICE_AGENT = TtsNorm(speak_percent=True, keep_code_digits=True, phone_shapes=KSA_PHONE_SHAPES,
                          long_digit_runs=True, phone_prefixes=KSA_PHONE_PREFIXES,
                          identifier_words=IDENTIFIER_WORDS, cardinal_numbers=True,
                          leave_unspeakable_numbers=True, oblique_numbers=True, space_fused_hundreds=True,
                          spoken_forms=False, canonical_unicode=False)


@functools.lru_cache(maxsize=None)
def _tts_patterns(config: TtsNorm):
    phones = re.compile(r"(?<![0-9])(?:" + "|".join(config.phone_shapes) + ")") if config.phone_shapes else None
    prefixes = re.compile("|".join(f"(?:{p})" for p in config.phone_prefixes)) if config.phone_prefixes else None
    context = re.compile(r"(?:^|[\s\W])" + _PROCLITIC + r"(?:"
                         + "|".join(re.escape(w) for w in config.identifier_words)
                         + r")(?:\s+[^\s\d]+)?\s*$", re.IGNORECASE) if config.identifier_words else None
    return phones, prefixes, context


def _number_case(config: TtsNorm) -> str:
    """The register the parser speaks a number in. It is always stated: a lect's own
    default register is the oblique, and the register here is ``oblique_numbers``'s
    to decide whatever ``lang`` says."""
    return "oblique" if config.oblique_numbers else "nominative"


@functools.lru_cache(maxsize=64)
def _number_lang(lang: str, config: TtsNorm) -> str:
    """The code the parser is asked to speak a number under: the ISO 639-3 code of the
    lect ``lang`` names, when a lect's own words are wanted, and ``lang`` otherwise. A
    lect the parser has no cited words for keeps the literary ones, Najdi among them."""
    if not config.dialect_numbers:
        return lang
    from arbtok.dialects import lect_code
    return lect_code(lang) or lang


@functools.lru_cache(maxsize=64)
def _lect_forms(lang: str, config: TtsNorm):
    """The caller's own words for values, and the pattern that finds the word the parser
    said for each inside a cardinal it composed. That word is asked of the parser, in the
    code and the case this call speaks, so a form is keyed by value and never by a
    spelling."""
    forms = dict(config.number_forms)
    if not forms:
        return forms, None, {}
    from ovos_number_parser import pronounce_number
    said = {pronounce_number(value, lang=_number_lang(lang, config), case=_number_case(config)): word
            for value, word in forms.items()}
    pattern = re.compile(r"(?<!\S)(و?)(" + "|".join(re.escape(w) for w in sorted(said, key=len, reverse=True))
                         + r")(?!\S)")
    return forms, pattern, said


@functools.lru_cache(maxsize=64)
def _digit_forms(lang: str, config: TtsNorm) -> Dict[int, str]:
    """The word a digit read on its own takes where it is not :data:`_DIGIT_WORDS`: the
    lect's own, where the lect says that digit differently from the literary reading,
    and the caller's over it. ``ar`` is the macrolanguage and reads the literary words,
    which is the comparison."""
    forms: Dict[int, str] = {}
    if config.dialect_numbers:
        from ovos_number_parser import pronounce_number
        spoken, case = _number_lang(lang, config), _number_case(config)
        for digit in range(10):
            word = pronounce_number(digit, lang=spoken, case=case)
            if word != pronounce_number(digit, lang="ar", case=case):
                forms[digit] = word
    forms.update(config.number_forms)
    return forms


def _digit_by_digit(run: str, forms: Mapping[int, str] = {}) -> str:
    """``run`` read one digit at a time, in the lect's words where ``forms`` has them.

    Everything that is not a digit is dropped: the spaces and hyphens of a grouped
    number, and a leading ``+``. The ``+`` is not spoken because the country code after
    it already says the number is international, and a word for it would differ by lect
    (زائد, بلس) where the digits do not. Every rule that reads a number this way takes a
    leading ``+`` into its match, so that no rule leaves the sign in the text.
    """
    return " ".join(forms.get(int(d), _DIGIT_WORDS[d]) for d in run.translate(_EASTERN_DIGITS) if d in _DIGIT_WORDS)


def _cardinal(number: str, lang: str, config: TtsNorm) -> str:
    from ovos_number_parser import pronounce_number
    value = float(number) if "." in number else int(number)
    words = pronounce_number(value, lang=_number_lang(lang, config), case=_number_case(config))
    forms, pattern, said = _lect_forms(lang, config)
    if isinstance(value, int) and value in forms:
        words = forms[value]
    elif pattern:
        words = pattern.sub(lambda m: m.group(1) + said[m.group(2)], words)
    if config.space_fused_hundreds:
        words = _FUSED_HUNDREDS_RE.sub(lambda m: _FUSED_HUNDREDS[m.group(0)], words)
    return words


def _speak_numbers(text: str, lang: str, config: TtsNorm) -> str:
    def speak(written: str, number: str) -> str:
        try:
            return _cardinal(number, lang, config)
        except Exception:
            if config.leave_unspeakable_numbers:
                return written
            raise

    def eastern(m):
        number = m.group(0).translate(_EASTERN_DIGITS).replace("٬", "").replace("،", "").replace("٫", ".")
        return speak(m.group(0), number)
    text = _EASTERN_NUMBER.sub(eastern, text)
    return _WESTERN_NUMBER.sub(lambda m: speak(m.group(0), m.group(0).replace(",", "")), text)


def normalize_for_tts(text: str, lang: str = "ar", config: Optional[TtsNorm] = None, **flags) -> str:
    """Prepare text to be spoken.

    ``config`` is a :class:`TtsNorm`; with none given it is what the G2P plugin runs,
    ``spoken_forms`` and ``canonical_unicode``. Flags override it:
    ``normalize_for_tts(text, KSA_VOICE_AGENT, spell_out_codes=True)``.

    ``lexicon`` maps a Latin-script term to the way it is said, ``{"BMW": "بِي إِمْ
    دَبَلْيُو"}``. It is applied first, the longest term first and without regard to
    case. A term ends where a Latin letter or digit ends, so an Arabic prefix written
    against it stays attached: ``بالBMW`` becomes ``بالبِي إِمْ دَبَلْيُو``. Give the
    spoken form fully pointed; an unpointed one leaves its vowels to the diacritizer.

    ``spell_out_codes`` reads what the lexicon did not claim and is written in
    capitals and digits with at least one capital, ``X5`` or ``GV70``, character by
    character from :func:`spelled_codes`. A number on its own is not a code.

    ``spoken_forms`` writes dates, times, numbers and units as words in ``lang``.
    ``canonical_unicode`` drops tatweel, applies NFC, orders shadda before its
    vowel and settles the spellings of مائة: the form the tokenizer reads.
    ``strip_controls`` drops zero-width and bidirectional control characters,
    which otherwise reach the tokenizer as characters it has no reading for.

    Diacritization is not part of this: it is a model, and it lives in
    :func:`arbtok.vocalize`.
    """
    config = config or _PLUGIN_DEFAULT
    if "lexicon" in flags:
        raise TypeError("a lexicon is part of the config: normalize_for_tts(text, lang, config.with_lexicon(lexicon))")
    if flags:
        config = dataclasses.replace(config, **flags)
    text = _as_text(text, "normalize_for_tts")
    speaks_arabic = [name for name in _ARABIC_ONLY if getattr(config, name)]
    if speaks_arabic and not is_arabic_lang(lang):
        raise ValueError(f"{', '.join(speaks_arabic)} speak Arabic and lang is {lang!r}")
    digit_forms = _digit_forms(lang, dataclasses.replace(config, lexicon=()))
    phones, prefixes, context = _tts_patterns(dataclasses.replace(config, lexicon=()) if config.lexicon else config)
    if config.strip_controls:
        text = _CONTROLS.sub("", text)
    if config.lexicon:
        pattern, said = _term_pattern(config.lexicon)
        text = pattern.sub(lambda m: said[m.group(1).lower()], text)
    if config.spell_out_codes:
        names = spelled_codes(lang)
        text = _CODE.sub(lambda m: " ".join(names[c] for c in m.group(0)), text)
    if config.speak_percent:
        text = _PERCENT.sub(lambda m: f"{m.group(1)} في المئة", text)
    held: Dict[str, str] = {}
    if config.keep_code_digits:
        # A private-use character stands in for each kept number; one the text already
        # holds is never used, so nothing of the text's own is rewritten on the way back.
        free = (chr(c) for c in range(_HELD_DIGITS, 0xF900) if chr(c) not in text)
        def hold(m):
            placeholder = next(free)
            held[placeholder] = m.group(0)
            return placeholder
        text = _CODE_DIGITS.sub(hold, text)
    if phones:
        text = phones.sub(lambda m: _digit_by_digit(m.group(0), digit_forms), text)
    if config.long_digit_runs:
        text = _LONG_RUN.sub(lambda m: _digit_by_digit(m.group(0), digit_forms), text)
    if prefixes or context:
        whole = text
        def reference(m):
            run = m.group(0)
            if prefixes and (run.startswith("+") or prefixes.fullmatch(run)):
                return _digit_by_digit(run, digit_forms)
            if context and context.search(whole[:m.start()]):
                return _digit_by_digit(run, digit_forms)
            return run
        text = _DIGIT_RUN.sub(reference, text)
    if config.cardinal_numbers:
        text = _speak_numbers(text, lang, config)
    if config.spoken_forms:
        from arbtok.util import normalize as spoken
        text = spoken(text, lang)
    for placeholder, digits in held.items():
        text = text.replace(placeholder, digits)
    if config.canonical_unicode:
        from arbtok.tokenizer import normalize_unicode
        text = normalize_unicode(text)
    return text
