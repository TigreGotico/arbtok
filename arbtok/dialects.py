"""Arabic lexical exceptions and the variety→spec bridge for the cascade.

A variety is not a hardcoded bucket of consonant swaps: it is an
orthography2ipa **spec** (``ar``, ``ar-SA-x-najd``, ``ar-EG``, …) that declares
its own grapheme table and ``allophone_rules``. :func:`spec_for_lang` resolves a
language tag to one, and :func:`consonant_ipa` reads a consonant's realization
straight out of that spec — so the qāf reflex, the interdental treatment and the
jīm all come from cited spec data rather than a table in this file.

The word lattice (:mod:`arbtok.lattice`) additionally compiles the spec's
``allophone_rules``, so context-conditioned phonology — Najdi affrication and
gahawa epenthesis, Hejazi monophthongization, emphatic spreading — fires there.
The sentence cascade below reads the spec's grapheme layer only; it has no
allophone pass yet.
"""

import functools
import warnings
from enum import Enum
from typing import Dict, List, NamedTuple, Optional, Sequence, Tuple

from arbtok.textnorm import is_arabic_lang
from arbtok.constants import (B, T, DJ, X, D, R, Z, S, F, Q, K, M, N, H, LAM, WAW, YA,
                              FATHA, DAMMA, KASRA, DAGGER_ALIF, MADD,
                              HAMZA, ALEF_HAMZA_ABOVE, ALEF_HAMZA_BELOW, WAW_HAMZA, YA_HAMZA,
                              TANWIN_FATH, TANWIN_KASR, TANWIN_DAMM,
                              ALIF_MAKSURA)

# Interdental graphemes referenced by the zone overrides.
THEH = 'ث'   # ث
THAL = 'ذ'   # ذ
ZAH = 'ظ'    # ظ (emphatic interdental)


ARABIC_TO_IPA_CONSONANTS = {
    HAMZA: "ʔ", ALEF_HAMZA_ABOVE: "ʔ", ALEF_HAMZA_BELOW: "ʔ", WAW_HAMZA: "ʔ", YA_HAMZA: "ʔ",
    B: 'b',
    T: 't',
    '\u062B': 'θ',
    DJ: 'dʒ',  # DJ: 'ʤ',
    '\u062D': 'ħ',
    X: 'x',
    D: 'd',
    '\u0630': 'ð',
    R: 'r',
    Z: 'z',
    S: 's',
    '\u0634': 'ʃ',
    '\u0635': 'sˤ',
    '\u0636': 'dˤ',
    '\u0637': 'tˤ',
    '\u0638': 'ðˤ',
    '\u0639': 'ʕ',
    '\u063A': 'ɣ',
    F: 'f',
    Q: 'q',
    K: 'k',
    M: 'm',
    N: 'n',
    H: 'h',
    LAM: 'l',
    WAW: 'w',
    YA: 'j',
    # Non-standard Perso-Arabic letters used in loanwords and colloquial
    # spelling (چ tʃ, گ ɡ, پ p, ڤ v, ژ ʒ). They are real graphemes the cascade
    # must transcribe, not drop: without them ⟨بَاچِر⟩ /baːtʃir/ loses its
    # affricate. The word lattice already reads them; the cascade must too, so
    # the two paths agree.
    "چ": 'tʃ',  # چ
    "گ": 'ɡ',   # گ
    "پ": 'p',   # پ
    "ڤ": 'v',   # ڤ
    "ژ": 'ʒ',   # ژ
    # Other unicode variations
    "ﻻ": "laː"
}

DIACRITIC_TO_IPA = {
    FATHA: 'a',
    DAMMA: 'u',
    KASRA: 'i',
    DAGGER_ALIF: 'aː',
    MADD: 'aː'
}
TANWIN_TO_IPA = {
    TANWIN_FATH: "an",
    TANWIN_DAMM: "un",
    TANWIN_KASR: "in"
}

VOWEL_MAP = {**DIACRITIC_TO_IPA,
             **TANWIN_TO_IPA,
             MADD: ":",
             ALIF_MAKSURA: 'aː'}

# ---------------------------------------------------------------------------
# Variety resolution: consonants come from the spec, not from a table here
# ---------------------------------------------------------------------------

_CONSONANT_MAPS: Dict[str, Dict[str, str]] = {}

#: Vowel segments. A spec reading containing one is not a bare consonant.
_VOWEL_CHARS = set("aiueoɑæəː")


def consonant_map(lang: str) -> Dict[str, str]:
    """The consonant realizations *lang*'s spec declares, keyed by grapheme.

    Only the graphemes the cascade treats as consonants are taken, and only
    their first (highest-ranked) reading — the cascade is a single-path engine
    and cannot carry candidates. A grapheme the spec does not override keeps
    the reference realization in :data:`ARABIC_TO_IPA_CONSONANTS`.

    A reading carrying a vowel is skipped. Some spec graphemes bake a default
    vowel into the consonant — the hamza carriers read ⟨أ⟩ as ``ʔa``, which is
    the right *lattice* candidate (a rescorer strips the vowel when an explicit
    harakah follows) but the wrong thing to hand a cascade that appends the
    harakah itself: it would yield ``ʔaa``. The cascade wants the bare
    consonant, so it keeps its own ``ʔ``.
    """
    cached = _CONSONANT_MAPS.get(lang)
    if cached is None:
        from orthography2ipa import get
        cached = {
            grapheme: readings[0]
            for grapheme, readings in get(lang).graphemes.items()
            if grapheme in ARABIC_TO_IPA_CONSONANTS and readings
            and not (_VOWEL_CHARS & set(readings[0]))
        }
        _CONSONANT_MAPS[lang] = cached
    return cached


def consonant_ipa(grapheme: str, lang: str, default: str) -> str:
    """Resolve a consonant grapheme to IPA under the variety *lang*.

    Consults the variety's spec first, falling back to *default* (the reference
    realization the caller already computed).
    """
    return consonant_map(lang).get(grapheme, default)


#: The spec code used when a caller names no variety.
DEFAULT_LANG = "ar"

#: When a region carries several sibling specs, the one a bare region tag
#: resolves to. Saudi Arabia has six varieties in the data set; Najdi is the
#: most widely spoken, so ``ar-SA`` (and ``ar-SA-najdi``, ``ar-x-najdi``, …)
#: land on it rather than on whichever sibling happens to sort first.
#:
#: Every lect key in this module is a tag that orthography2ipa resolves exactly:
#: a spec key or one of its permanent aliases. orthography2ipa may key a lect by
#: its ISO 639-3 code (``ars-SA`` for ``ar-SA-x-najd``) and keep the older key as
#: an alias, so a key is compared only after ``orthography2ipa.resolve`` turns it
#: into the installed spec key.
_REGION_DEFAULTS = ("ar-SA-x-najd",)

#: Dialect names that a caller may write in a subtag, and the lect each one names.
#: langcodes ignores private-use content when it measures tag distance, so
#: ``ar-x-najd`` would otherwise fall through to MSA. The private-use tokens of the
#: installed spec keys are found without this table. It holds the spoken
#: adjectives, and the tokens of the keys that orthography2ipa spells with an
#: ISO 639-3 code (``ar-EG-x-saidi`` is ``aec-EG``).
_DIALECT_NAME_ALIASES = {
    "najd": "ar-SA-x-najd",
    "najdi": "ar-SA-x-najd",
    "hejaz": "ar-SA-x-hejaz",
    "hejazi": "ar-SA-x-hejaz",
    "hijazi": "ar-SA-x-hejaz",
    "hijaz": "ar-SA-x-hejaz",
    "qassimi": "ar-SA-x-qassim",
    "sharqiyya": "ar-SA-x-sharqiyya",
    "gulf": "ar-x-gulf",
    "gulfi": "ar-x-gulf",
    "khaleeji": "ar-x-gulf",
    "levantine": "ar-x-levantine",
    "levant": "ar-x-levantine",
    "shami": "ar-x-levantine",
    "maghrebi": "ar-x-maghrebi",
    "maghribi": "ar-x-maghrebi",
    "saidi": "ar-EG-x-saidi",
    "bedawi": "ar-EG-x-bedawi",
    "dhofari": "ar-OM-x-dhofari",
    "baharna": "ar-BH-x-baharna",
}


@functools.lru_cache(maxsize=None)
def _arabic_codes() -> Tuple[str, ...]:
    """Available Arabic spec codes, ordered to steer ``closest_match`` ties.

    :func:`langcodes.closest_match` breaks equal-distance ties by list order, so
    the order encodes two preferences: MSA (:data:`DEFAULT_LANG`) leads, so an
    unmatched region (``ar-ZZ`` — equidistant from MSA and every regional spec)
    settles on MSA rather than an arbitrary dialect; then the
    :data:`_REGION_DEFAULTS`, so a bare region matching several private-use
    siblings at distance zero (``ar-SA``) settles on the declared default
    (Najdi) rather than whichever sibling sorts first; then the rest, by code.

    Built once: orthography2ipa enumerates its whole registry on every
    ``available_codes`` call, which costs more than the rest of
    :func:`spec_for_lang` together, and the registry does not change after it
    loads.
    """
    from orthography2ipa import available_codes, resolve

    codes = [c for c in available_codes() if _is_arabic_code(c)]
    defaults = {resolve(c) for c in _REGION_DEFAULTS}
    return tuple(sorted(
        codes,
        key=lambda c: (c != DEFAULT_LANG, c not in defaults, c),
    ))


def _dialect_index(codes: Sequence[str]) -> Dict[str, str]:
    """Map a dialect token (spec private-use tokens + aliases) to its spec code."""
    from orthography2ipa import resolve

    index: Dict[str, str] = {}
    for code in codes:
        if "-x-" in code:
            index.setdefault(code.split("-x-")[-1].lower(), code)
    for alias, tag in _DIALECT_NAME_ALIASES.items():
        target = resolve(tag)
        if target in codes:
            index[alias] = target
    return index


def _exact_spec(tag: str, codes: Sequence[str]) -> Optional[str]:
    """The Arabic spec *tag* names exactly: a spec key in any case, or a tag
    orthography2ipa resolves exactly.

    orthography2ipa answers a spec key, an alias, a case variant, a BCP-47
    standardization and its curated bare-tag defaults exactly; only its
    nearest-language guess is refused here. So the key and every alias of a lect
    land on the same spec, whichever key the installed orthography2ipa uses. A
    spec key wins over orthography2ipa's answer, because BCP-47 standardization
    reads ``ARB`` as ``ar`` where the caller named the ``arb`` spec.

    A tag that orthography2ipa names exactly but that is not an Arabic lect
    arbtok carries is read as MSA (:data:`DEFAULT_LANG`). The heuristics below
    never see such a tag: they would match it to some other dialect, which is
    worse than MSA because nothing says it happened. An Arabic tag read this way
    raises a warning.
    """
    from orthography2ipa import resolve, resolves_exactly

    for code in codes:
        if code.lower() == tag.lower():
            return code
    if not resolves_exactly(tag):
        return None
    spec = resolve(tag)
    if spec in codes:
        return spec
    if is_arabic_lang(tag):
        warnings.warn(
            f"{tag!r} names the orthography2ipa spec {spec!r}, which arbtok has no "
            f"lect for; reading it as {DEFAULT_LANG!r} (Modern Standard Arabic)",
            UserWarning, stacklevel=3)
    return DEFAULT_LANG


def _core_subtags(tag: str) -> List[str]:
    """The language, extlang, script and region subtags that open *tag*.

    These are the subtags BCP-47 tag distance measures; whatever follows them —
    variants, extensions, private use — it ignores.
    """
    subtags = tag.split("-")
    core, rest = subtags[:1], subtags[1:]
    while rest and len(core) < 4 and len(rest[0]) == 3 and rest[0].isalpha():
        core.append(rest.pop(0))
    if rest and len(rest[0]) == 4 and rest[0].isalpha():
        core.append(rest.pop(0))
    if rest and ((len(rest[0]) == 2 and rest[0].isalpha())
                 or (len(rest[0]) == 3 and rest[0].isdigit())):
        core.append(rest.pop(0))
    return core


def spec_for_lang(lang: Optional[str]) -> str:
    """Resolve a language tag to an orthography2ipa Arabic spec code.

    A tag that orthography2ipa resolves exactly wins: a spec key, an alias, a
    case or underscore variant (``ar-SA-x-najd``, ``ars-SA``, ``ar-EG``,
    ``arz-EG``, ``ar-x-gulf``, ``afb``). So a caller can name any variety the
    data set carries, by its ISO 639-3 key or by an older private-use key, and
    both name the same spec. An exact tag for a spec that is not an Arabic lect
    reads as MSA, with a warning when the tag is an Arabic one. Otherwise the tag
    is matched to the closest available spec:

    * a dialect named in a subtag — private-use or not — resolves to that
      variety's spec (``ar-x-najdi`` and ``ar-SA-najdi`` → ``ar-SA-x-najd``),
      even though BCP-47 tag distance ignores private-use content;
    * a region resolves to that region's spec, defaulting to the most widely
      spoken variety when the region carries several (``ar-SA`` → Najdi,
      ``ar-EG`` → Egyptian) via subtag-aware BCP-47 matching;
    * a subtag that names no spec and no dialect is ignored, so a tag never
      resolves to something less specific than its parent tag does
      (``ar-EG-x-cairo`` → ``ar-EG``, ``ar-SA-x-riyadh`` → ``ar-SA-x-najd``);
    * anything with no Arabic match — an unknown region, a non-Arabic tag —
      falls back to the ``ar`` (MSA) leaf rather than raising.
    """
    if not lang:
        return DEFAULT_LANG

    from orthography2ipa import resolve

    codes = _arabic_codes()
    normalized = lang.replace("_", "-")

    # 1. A tag orthography2ipa resolves exactly — a caller naming a variety directly.
    exact = _exact_spec(normalized, codes)
    if exact:
        return exact

    # 2. A dialect named in a subtag. Private-use content is invisible to tag
    #    distance, so it has to be matched by name here.
    dialects = _dialect_index(codes)
    for token in normalized.lower().split("-"):
        if token in ("ar", "x"):
            continue
        match = dialects.get(token)
        if match:
            return match

    # 3. Variants, extensions and private-use subtags that name no spec are
    #    invisible to tag distance, so left in they make the tag tie at zero
    #    with ``ar`` (``ar`` maximizes to ``ar-Arab-EG``) or, over eight
    #    characters, abort the match. They are dropped one at a time from the
    #    end, stopping at a spec code, so the tag resolves as its parent does:
    #    ``ar-EG-x-cairo`` as ``ar-EG``, ``ar-SA-x-riyadh`` as ``ar-SA``.
    core = _core_subtags(normalized)
    subtags = normalized.split("-")
    while len(subtags) > len(core):
        subtags.pop()
        if len(subtags) > len(core) and len(subtags[-1]) == 1:
            subtags.pop()
        exact = _exact_spec("-".join(subtags), codes)
        if exact:
            return exact
    normalized = "-".join(core)

    # 4. An ISO 639-3 code this module gives a lect resolves back to that lect, so
    #    a tag built from :func:`lect_code` names the variety it came from. A
    #    sub-lect named in a subtag, and a spec reached by dropping subtags
    #    (``afb-AE-x-cairo`` is ``afb-AE``), have already won above.
    spec = _LANGUAGE_CODE_SPECS.get(normalized.lower().split("-")[0])
    if spec:
        return resolve(spec)

    # 5. The dialect orthography2ipa's nearest-language match names: it carries
    #    curated region defaults (``ar-TR`` is Çukurova, ``ar-EH`` is Algerian)
    #    and it matches regions whatever language subtag the spec keys carry,
    #    where BCP-47 distance from ``ar-EH`` to ``arq-DZ`` is that of two
    #    languages. An answer of MSA is left to the match below, which reads
    #    ``ary-MA`` as Moroccan where an orthography2ipa without ISO 639-3 keys
    #    gives MSA.
    nearest = resolve(normalized)
    if nearest in codes and nearest != DEFAULT_LANG:
        return nearest

    # 6. Closest region-bearing spec via subtag-aware BCP-47 matching. Codes
    #    with a subtag langcodes cannot parse (a private-use token over eight
    #    characters) are dropped from the pool — they are only ever reached by
    #    the exact-code path above, and one of them would abort the whole match.
    from langcodes import closest_match

    matchable = [c for c in codes
                 if all(len(sub) <= 8 for sub in c.split("-"))]
    try:
        best, _ = closest_match(normalized, matchable)
    except Exception:
        best = "und"
    if best in codes:
        return best

    return DEFAULT_LANG


#: The ISO 639-3 code of the individual Arabic language a spec names, for the
#: consumers that key their data by 639-3 rather than by a BCP-47 tag — the number
#: parser's cardinals among them. Only the specs that name a language of their own
#: are listed; every other spec is answered through its parent, so the Gulf states
#: take the Gulf code from ``ar-x-gulf`` without being named here. Source: ISO 639-3
#: code table, https://iso639-3.sil.org/code_tables/639/data, read for the
#: macrolanguage ``ara``.
_SPEC_LANGUAGE_CODES = {
    "ar-EG": "arz",          # Egyptian Arabic
    "ar-SA-x-hejaz": "acw",  # Hijazi Arabic
    "ar-SA-x-najd": "ars",   # Najdi Arabic
    "ar-x-gulf": "afb",      # Gulf Arabic
}
_LANGUAGE_CODE_SPECS = {code: spec for spec, code in _SPEC_LANGUAGE_CODES.items()}


@functools.lru_cache(maxsize=None)
def lect_code(lang: str) -> Optional[str]:
    """The ISO 639-3 code of the lect *lang* names, or ``None`` when it names none.

    The spec *lang* resolves to is tried first, then that spec's parents, so which
    leaves carry which code comes from orthography2ipa's genealogy rather than a list
    here: Kuwaiti has no code of its own and takes the Gulf one because its spec
    declares ``ar-x-gulf`` as its parent. ``ar`` is the macrolanguage and names no
    lect; a tag that resolves to it, or to any spec whose chain names none, is
    ``None``.

    The code is the tag translated and nothing more. Whether anything is said
    differently under it is the answer of whoever holds the data — the number parser
    speaks a lect's cardinals only for the lects it has read a source for.
    """
    from orthography2ipa import get, resolve

    languages = {resolve(spec): code for spec, code in _SPEC_LANGUAGE_CODES.items()}
    code, seen = spec_for_lang(lang), set()
    while code and code not in seen:
        if code in languages:
            return languages[code]
        seen.add(code)
        code = get(code).parent
    return None


class Lect(NamedTuple):
    """A resolvable Arabic variety and the maturity of its spec.

    :attr:`code` is an orthography2ipa spec code accepted by :func:`spec_for_lang`
    and by ``lang=`` on the plugin. :attr:`tier` is that spec's
    ``QualityTier`` value as declared upstream (``research``, ``skeleton``,
    ``stub``, ``production``) — how far its cited rule set has been taken, not a
    promise about arbtok's cascade.
    """

    code: str
    tier: str


@functools.lru_cache(maxsize=None)
def _is_arabic_code(code: str) -> bool:
    """Whether the registry key *code* names an Arabic spec.

    The answer comes from the language the spec declares, not from the shape of
    its key, so a lect keyed by its ISO 639-3 code (``arz-EG``, ``ars-SA``,
    ``afb``) counts as one keyed ``ar-…`` does. The spec's ``iso639_3`` must be
    ``ara``, a member of the macrolanguage, or Hassaniya ``mey``: the codes
    :func:`arbtok.textnorm.is_arabic_lang` accepts. A spec that declares no code
    is the language of its ``parent``, so a dialect child with no code of its own
    and the Buckwalter romanization of ``ar`` count.

    The lookalikes ``arc`` (Aramaic) and ``arn`` (Mapudungun) sort next to the
    Arabic keys and declare their own languages. So does Maltese (``mlt``),
    although orthography2ipa files it under ``ar``. A tag that is not itself a
    registry key (``arz``, an alias of ``arz-EG``) is not a registry code, and is
    ``False`` here.
    """
    from orthography2ipa import get, resolve

    if resolve(code) != code:
        return False
    language, seen = None, set()
    node: Optional[str] = code
    while node and node not in seen and language is None:
        seen.add(node)
        spec = get(node)
        language, node = spec.iso639_3, spec.parent
    return language is not None and (language == "ara" or is_arabic_lang(language))


def supported_lects() -> List[Lect]:
    """Every Arabic variety arbtok can phonemize, with its o2i quality tier.

    Enumerated from the orthography2ipa registry, so it tracks the data set
    rather than a table here: whatever Arabic specs are installed are what
    ``lang=`` resolves to, under their ``ar-…`` or ISO 639-3 keys. Sorted by
    code.

    >>> from orthography2ipa import resolve
    >>> lects = supported_lects()
    >>> wanted = {resolve(c) for c in ("ar", "ar-EG", "ar-SA-x-najd")}
    >>> sorted(l.code for l in lects if l.code in wanted) == sorted(wanted)
    True
    >>> next(l.tier for l in lects if l.code == "ar")
    'research'
    """
    from orthography2ipa import available_codes, get

    return sorted(
        (Lect(code, get(code).quality.value)
         for code in available_codes() if _is_arabic_code(code)),
        key=lambda lect: lect.code,
    )


# --- Word Exceptions ---
# Words whose spelling does not determine their reading: a letter is written and
# not pronounced, or a vowel is pronounced and not written.
#
# Every entry has to beat the grapheme rules at something. An entry the rules
# already agree with cannot be told from a live one by reading the table, and it
# hides the ones that matter; a test holds each entry to producing a reading the
# rules do not.
#
# One spelling of a word can be here and another not, and they then read
# differently: ⟨اللّٰه⟩ is an entry and reads *allaːh*, while ⟨الله⟩ and ⟨اللَّه⟩
# are not and read *ɑɫɫɑːh*, the rules' velarized lām.
#
# The readings are this package's own and cite no grammar. They were checked
# against espeak-ng, an independent Arabic phonemizer sharing no data with this
# one, which agreed on 16 of the 21 readings the table then held. Every one of
# the five it disputed is a word where it reads the deficient spelling
# literally: it gives *lakin* for لَكِن, and hears a long vowel in the silent waw
# of أُولِي and أُولَٰئِكَ. Those are the readings this table exists to prevent,
# so the disagreement corroborates the entries rather than questioning them.
WORD_EXCEPTIONS = {
    # === Unicode / orthographic variants ===

    # Demonstratives with "Dagger Alif" (pronounced long /a:/ but written short or omitted)
    "أُولَٰئِكَ": "ʔulaːʔika",  # u-la-i-ka (those) - note medial hamza logic is complex, hardcoded here

    # Particles

    # Divine Names
    "اللّٰه": "allaːh",  # Allah - heavy L, unwritten alif

    # Irregular pronunciations
    # NOTE: ⟨مِائَة⟩ "hundred" used to need an entry here for its silent alif,
    # but arbtok.tokenizer.normalize_unicode now collapses that spelling onto
    # ⟨مئة⟩ before any lexicon lookup runs (see elide_silent_alif), so the
    # normal grapheme-to-IPA path already reads it correctly. This exception
    # would never fire.
    "عَمْرٌو": "ʕamrun",  # 'Amr - final Waw is silent (differentiates from 'Umar)
    "أُولِي": "ʔuliː",  # 'uli (owners of) - silent Waw
    "أُولُو": "ʔuluː",  # 'ulu - silent Waw

    # Particles carrying hamzat al-qaṭʿ on ALEF_HAMZA_BELOW. Keys are stored in
    # _reorder_diacritics-normalized form (shadda precedes vowel):
}

