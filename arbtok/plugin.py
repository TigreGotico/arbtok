"""arbtok's Arabic G2P engine, built on orthography2ipa's spec data and lattice.

    >>> from arbtok.plugin import ArbtokG2PPlugin
    >>> ArbtokG2PPlugin().transcribe("كتاب جميل")
    'kiˈtaːb dʒaˈmiːl'

- ``normalize``: Unicode and diacritic order, numbers and dates as words, and
  tashkeel restored on bare text by the bundled rawi ensemble (on failure the
  text passes through undiacritized).
- ``transcribe_word``: an isolated word goes through the shared lattice, arbtok's
  rescorers (:mod:`arbtok.lattice`) and the variety's ``allophone_rules``. A word
  with ``WordContext`` neighbours is read in a sentence with them, so the
  cross-word rules fire.
- ``transcribe``: the full-sentence path, ``Sentence(text).ipa``, with Latin-script
  words read as Arabizi or as loanwords.
"""
import re
from typing import List, Optional

from orthography2ipa import WordContext

from arbtok.arabizi import arabizi_covers, is_arabizi, to_arabic_skeleton
from arbtok.dialects import DEFAULT_LANG, WORD_EXCEPTIONS, spec_for_lang
from arbtok.donor_lexicon import donor_engine
from arbtok.lattice import defers_to_cascade, word_ipa
from arbtok.lexicon import DEFAULT_LEXICON, LexiconUnavailable
from arbtok.textnorm import normalize_for_tts
from arbtok.tokenizer import Sentence, normalize_unicode
from arbtok.translit import DONOR_LANG, is_latin, transliterate

#: Script runs inside one whitespace token. The Arabic range holds tatweel, so the
#: connector in الـcharger stays with the Arabic run.
_ARABIC_RUN = re.compile(r"[\u0600-\u06FF\u0750-\u077F\uFB50-\uFDFF\uFE70-\uFEFF]")
#: IPA symbols that are their ASCII letter wearing a different codepoint.
_LOOKALIKE = {"\u0261": "g", "\u0279": "r", "\u026a": "i", "\u028a": "u"}
_SCRIPT_RUN = re.compile(
    r"[\u0600-\u06FF\u0750-\u077F\uFB50-\uFDFF\uFE70-\uFEFF]+"
    r"|[^\s\u0600-\u06FF\u0750-\u077F\uFB50-\uFDFF\uFE70-\uFEFF]+")
_MIXED_RUN = re.compile(
    r"[\u0600-\u06FF\u0750-\u077F\uFB50-\uFDFF\uFE70-\uFEFF]+"
    r"|[A-Za-z][A-Za-z'\u2019-]*"
    r"|[^\s\u0600-\u06FF\u0750-\u077F\uFB50-\uFDFF\uFE70-\uFEFFA-Za-z]+")

PUNCT_STRIP = ".,;:!?()[]\"'،؛؟"


def _donor_knows(tok: str) -> bool:
    """Whether the donor lexicon reads *tok*, rather than handing its letters back:
    `ok` comes out ˌəʊkˈeɪ and `bmw` comes out ˈbmw."""
    try:
        got = donor_engine(DONOR_LANG).transcribe_word(tok.lower()) or ""
        # Fold the IPA symbols that only look like their ASCII letter: `gps` comes
        # back as ɡps with a script g (U+0261).
        bare = "".join(_LOOKALIKE.get(c, c) for c in got if c not in "ˈˌ")
        return bool(got) and bare != tok.lower()
    except Exception:
        return False


def _spelled_out(tok: str) -> bool:
    """An all-caps Latin run the donor does not know is a spelling, BMW."""
    return (tok.isascii() and tok.isalpha() and tok.isupper() and len(tok) > 1
            and not _donor_knows(tok))


def _runs(tok: str) -> list[str]:
    """*tok* split into the parts that take different paths.

    First at the script boundary: a mixed token such as الـcharger must not reach
    `transliterate` whole. Then each non-Arabic run splits at the letter/digit
    boundary, except Arabizi the mapper can write whole: `7abibi` carries its
    guttural as a digit, and splitting it reads the seven as a number.
    """
    out = []
    for run in (m.group(0) for m in _SCRIPT_RUN.finditer(tok)):
        if _ARABIC_RUN.search(run) or (is_arabizi(run) and arabizi_covers(run)):
            out.append(run)
        else:
            pieces = [m.group(0) for m in _MIXED_RUN.finditer(run)] or [run]
            for piece in pieces:
                out.extend(list(piece) if _spelled_out(piece) else [piece])
    return out or [tok]


class ArbtokG2PPlugin:
    """Arabic G2P via the orthography2ipa shared lattice.

    Output defaults to Modern Standard Arabic. Pass *lang* — any
    orthography2ipa Arabic spec code — to transcribe a variety, which reads
    the variety's own grapheme table *and* its declared ``allophone_rules``::

        >>> ArbtokG2PPlugin(lang="ar-SA-x-najd").transcribe_word("قَهْوَة")
        'ˈɡahawa'
        >>> ArbtokG2PPlugin(lang="ar-SA-x-hejaz").transcribe_word("بَيْت")
        'ˈbeːt'

    The variety may also be carried per call on ``WordContext.lang``, which
    overrides the instance default. A tag naming no Arabic spec narrows a
    subtag at a time and ultimately falls back to the ``ar`` leaf.
    """

    def __init__(self, lang: str = DEFAULT_LANG, diacritize: bool = True,
                 stress: bool = True,
                 lexicon: Optional[str] = DEFAULT_LEXICON,
                 dialect_lexicon: bool = True,
                 nativize: bool = True,
                 arabizi: bool = True,
                 pausal: Optional[bool] = None,
                 register: str = "pausal",
                 fusion: bool = True) -> None:
        self._diacritizer = None
        self._diacritizer_failed = False
        #: Restore tashkeel by scoring the ensemble's licensed readings
        #: (:mod:`arbtok.fusion`) rather than taking one model guess. Mean bare-input
        #: PER 0.189 against 0.193; see docs/rawi-fusion.md.
        self.fusion = fusion
        #: The variety: any orthography2ipa Arabic spec code.
        self.lang = spec_for_lang(lang)
        #: Restore the marks the writing omits before transcribing; an unmarked word
        #: is otherwise read from a default reading.
        self.diacritize = diacritize
        #: Mark the stressed syllable. Turn it off to score against stress-free gold.
        self.stress = stress
        #: The diacritized-stem lexicon consulted before the model: a path, a URL, an
        #: ``hf://`` id, or ``None`` (see :mod:`arbtok.lexicon`).
        self.lexicon = lexicon
        #: Consult the lect's closed-class lexicon, the function words a dialect
        #: writes in MSA orthography and vocalizes its own way, ahead of the stem
        #: lexicon and the model (see :mod:`arbtok.dialect_lexicon`).
        self.dialect_lexicon = dialect_lexicon
        #: Read a Latin-script run as a loanword nativised into the lect's phonology
        #: (:mod:`arbtok.translit`). ``False`` leaves the run untranscribed.
        self.nativize = nativize
        #: Read a Latin-script run written in Arabizi (``7abibi`` = حبيبي) as Arabic,
        #: through an unpointed skeleton (:mod:`arbtok.arabizi`). A run counts as
        #: Arabizi only when it carries a digit-guttural or the caller says so, so
        #: ``meeting`` and ``email`` stay loanwords.
        self.arabizi = arabizi
        #: The waqf policy (Wright, *A Grammar of the Arabic Language*, 3rd ed.,
        #: I §372; Ryding, *A Reference Grammar of MSA*, CUP 2005, §2.4).
        #: ``True``, the TTS register: a word at a written phrase boundary takes its
        #: pausal form, and the diacritizer restores no iʿrāb. ``False``: every
        #: written ending is read and the diacritizer restores the case and mood
        #: endings, for recitation and iʿrāb-keeping gold. The flag is read by the
        #: sandhi pause rule and the diacritizer only. ``register`` names the same
        #: switch, ``"pausal"`` or ``"full"``; an explicit ``pausal=`` wins.
        if register not in ("pausal", "full"):
            raise ValueError(
                f"register must be 'pausal' or 'full', got {register!r}")
        if pausal is None:
            pausal = register == "pausal"
        self.pausal = pausal

    @property
    def language_codes(self) -> List[str]:
        return ["ar", "arb"]

    def _resolve_lang(self, context: Optional[WordContext] = None) -> str:
        """Pick the variety for a call: ``context.lang`` wins when it names one,
        otherwise the instance default. A ``context.lang`` that is not Arabic
        keeps the instance default."""
        if context is not None and context.lang:
            try:
                code = spec_for_lang(context.lang)
            except ValueError:
                return self.lang
            if code != DEFAULT_LANG:
                return code
        return self.lang

    def normalize(self, text: str) -> str:
        text = normalize_for_tts(text, self.lang)
        if self.diacritize:
            text = self._diacritize(text)
        return text

    def _diacritize(self, text: str) -> str:
        """Restore the omitted marks, word by word, under the lattice's guard
        (:mod:`arbtok.diacritize`).

        A missing model (no onnxruntime, no weights) is a degraded mode and the text
        passes through. A lexicon that was asked for and cannot be read raises
        :class:`LexiconUnavailable`.
        """
        if self._diacritizer_failed:
            return text
        if self._diacritizer is None:
            try:
                if self.fusion:
                    from arbtok.fusion import FusionDiacritizer
                    self._diacritizer = FusionDiacritizer(lang=self.lang,
                                                          waqf=self.pausal,
                                                          lexicon=self.lexicon,
                                                          dialect_lexicon=self.dialect_lexicon)
                else:
                    from arbtok.diacritize import LatticeDiacritizer
                    self._diacritizer = LatticeDiacritizer(lang=self.lang,
                                                          waqf=self.pausal,
                                                          lexicon=self.lexicon,
                                                          dialect_lexicon=self.dialect_lexicon)
            except Exception:
                self._diacritizer_failed = True
                return text
        try:
            return self._diacritizer.diacritize(text)
        except LexiconUnavailable:
            raise
        except Exception:
            return text

    def transcribe(self, text: str, arabizi: Optional[bool] = None) -> str:
        """Transcribe *text*, reading any Latin-script word as a loanword.

        The Arabic runs are transcribed together, so the cross-word rules still see
        their neighbours. A Latin word is a guest, and there are two kinds:

        * **Arabizi** — Arabic written in Latin letters (``3ala``, ``7abibi``). When
          the Arabizi path is on (the default) and the run is detected as Arabizi
          (any token carries a digit-guttural, or *arabizi* is passed ``True``),
          every Latin token is reverse-transliterated to an Arabic skeleton
          (:mod:`arbtok.arabizi`) and folded into the Arabic buffer, so it runs
          through the same diacritize + phonology stack as native text and fusion
          restores the vocalism. This is why ``7abibi`` reads as حبيبي and not as an
          English word.
        * **foreign loanword** — everything else. With ``nativize`` on (the TTS
          default) it is nativised on its own (see :mod:`arbtok.translit`) and
          spliced back in its place; with it off the Latin run is left untouched.

        *arabizi* is a per-call hint: ``True`` forces the Arabizi reading of the
        Latin runs, ``False`` forbids it, and ``None`` leaves it to the
        digit-guttural gate.
        """
        parts, buffer = [], []
        if not self.arabizi:
            arabizi_mode = False
        elif arabizi is not None:
            arabizi_mode = arabizi
        else:
            # Over the script runs, not the tokens: the Arabizi word in a glued
            # الـ7abibi is a run, and the mapper must be able to write it whole.
            arabizi_mode = any(is_arabizi(r) and arabizi_covers(r)
                               for t in text.split() for r in _SCRIPT_RUN.findall(t))

        def flush_arabic():
            if buffer:
                parts.append(Sentence(self.normalize(" ".join(buffer)),
                                      lang=self.lang, stress=self.stress,
                                      pausal=self.pausal).ipa)
                buffer.clear()

        for token in [r for t in text.split() for r in _runs(t)]:
            if is_latin(token):
                if arabizi_mode:
                    buffer.append(to_arabic_skeleton(token))
                    continue
                flush_arabic()
                if not self.nativize:
                    parts.append(token)
                    continue
                guest = transliterate(token.strip(PUNCT_STRIP), self.lang)
                if guest:
                    parts.append(guest)
            else:
                buffer.append(token)
        flush_arabic()
        return " ".join(p for p in parts if p)

    def transcribe_word(
        self, word: str, context: Optional[WordContext] = None
    ) -> str:
        lang = self._resolve_lang(context)
        if is_latin(word):
            if not self.nativize:
                return word
            return transliterate(word, lang) or ""
        if context is None or (context.prev_word is None
                               and context.next_word is None):
            # The lattice reads an isolated word, except a lexical exception and a
            # word that needs cross-word context (`defers_to_cascade`).
            if (normalize_unicode(word) not in WORD_EXCEPTIONS
                    and not defers_to_cascade(word)):
                return word_ipa(word, lang, stress=self.stress)
            return Sentence(word, lang=lang, stress=self.stress,
                            pausal=self.pausal).ipa

        # Read with its neighbours, so the cross-word rules see them.
        parts = [p for p in (context.prev_word, word, context.next_word)
                 if p is not None]
        target = 0 if context.prev_word is None else 1
        words = Sentence(" ".join(parts), lang=lang, stress=self.stress,
                         pausal=self.pausal).tokens
        if target < len(words):
            return words[target].ipa
        return Sentence(word, lang=lang, stress=self.stress,
                        pausal=self.pausal).ipa
