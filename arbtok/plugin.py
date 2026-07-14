"""arbtok's Arabic G2P engine.

arbtok *consumes* orthography2ipa — its spec data, its lattice and its
``WordContext`` type — and owns the Arabic pipeline. It is not a plugin TO
orthography2ipa: nothing there discovers or calls it. It is an engine built ON
it, which is the opposite direction, and the ``G2PPlugin`` base class that once
suggested otherwise is gone. Use it directly:

    >>> from arbtok.plugin import ArbtokG2PPlugin
    >>> ArbtokG2PPlugin().transcribe("كتاب جميل")
    'kitaːb dʒamiːl'

The engine maps arbtok's machinery onto the shared interface:

- ``normalize`` — Unicode/diacritic reordering, number and date
  expansion, and automatic tashkeel diacritization of bare text via
  ``text2tashkeel`` (failure degrades gracefully to the undiacritized
  input).
- ``transcribe_word`` — for an isolated word (no context), the
  orthography2ipa shared lattice: the variety's grapheme table, arbtok's
  structural rescorers (sun-letter assimilation, hamzat al-waṣl, hamza
  carriers, accusative alif; see :mod:`arbtok.lattice`), then the rescorer
  compiled from the variety's own ``allophone_rules``. Cross-word effects
  use the orthographic neighbours carried by ``WordContext``: the word is
  tokenized together with its neighbours so the prev/next-token cross-word
  rules fire.
- ``transcribe`` — full-sentence path with clitic joining, identical to
  ``Sentence(text).ipa``.
"""
from typing import List, Optional

from orthography2ipa import WordContext

from arbtok.constants import (
    DAGGER_ALIF,
    DAMMA,
    FATHA,
    KASRA,
    MADD,
    SHADDA,
    SUKUN,
    TANWIN_DAMM,
    TANWIN_FATH,
    TANWIN_KASR,
)
from arbtok.dialects import DEFAULT_LANG, WORD_EXCEPTIONS, spec_for_lang
from arbtok.lattice import defers_to_cascade, word_ipa
from arbtok.lexicon import DEFAULT_LEXICON
from arbtok.tokenizer import Sentence, normalize_unicode
from arbtok.translit import is_latin, transliterate

PUNCT_STRIP = ".,;:!?()[]\"'،؛؟"
from arbtok.util import normalize as normalize_speech

class ArbtokG2PPlugin:
    """Arabic G2P via the orthography2ipa shared lattice.

    Output defaults to Modern Standard Arabic. Pass *lang* — any
    orthography2ipa Arabic spec code — to transcribe a variety, which reads
    the variety's own grapheme table *and* its declared ``allophone_rules``::

        >>> ArbtokG2PPlugin(lang="ar-SA-x-najd").transcribe_word("قَهْوَة")
        'ɡahawa'
        >>> ArbtokG2PPlugin(lang="ar-SA-x-hejaz").transcribe_word("بَيْت")
        'beːt'

    The variety may also be carried per call on ``WordContext.lang``, which
    overrides the instance default. A tag naming no Arabic spec narrows a
    subtag at a time and ultimately falls back to the ``ar`` leaf.
    """

    def __init__(self, lang: str = DEFAULT_LANG, diacritize: bool = True,
                 stress: bool = True,
                 lexicon: Optional[str] = DEFAULT_LEXICON) -> None:
        self._diacritizer = None
        self._diacritizer_failed = False
        #: The variety: any orthography2ipa Arabic spec code.
        self.lang = spec_for_lang(lang)
        #: Restore the marks the writing omits before transcribing. The engine's
        #: input contract is diacritized text; without this, an unmarked word is
        #: transcribed from a default reading, which is a guess.
        self.diacritize = diacritize
        #: Mark the stressed syllable. Arabic stress is quantity-sensitive, so it
        #: is read off the transcription rather than the spelling — and it drives
        #: vowel duration and prominence, which a TTS voice needs. Turn it off to
        #: score against stress-free gold.
        self.stress = stress
        #: The diacritized-stem lexicon consulted before the diacritizer model —
        #: a path, a URL, an ``hf://`` id, or ``None`` to ask the model about
        #: every word. See :mod:`arbtok.lexicon`.
        self.lexicon = lexicon

    @property
    def language_codes(self) -> List[str]:
        return ["ar", "arb"]

    def _resolve_lang(self, context: Optional[WordContext] = None) -> str:
        """Pick the variety for a call: ``context.lang`` wins when it names one,
        otherwise the instance default."""
        if context is not None and context.lang:
            code = spec_for_lang(context.lang)
            if code != DEFAULT_LANG:
                return code
        return self.lang

    # ─── lifecycle hooks ─────────────────────────────────────────────

    def normalize(self, text: str) -> str:
        text = normalize_speech(text, "ar")
        text = normalize_unicode(text)
        if self.diacritize:
            text = self._diacritize(text)
        return text

    def _diacritize(self, text: str) -> str:
        """Restore the omitted marks, word by word, under the lattice's guard.

        Each word is diacritized only if the writing leaves it underdetermined,
        and the model's proposal is kept only if it preserves the skeleton and
        the variety's grapheme table licenses it — see
        :mod:`arbtok.diacritize`. A word whose proposal is refused is left as
        written, which orthography2ipa will then report as underdetermined,
        rather than transcribed from a confident hallucination.

        Diacritization is a model, and a model can be absent (no onnxruntime, no
        weights). That is a degraded mode, not an error: the text passes through
        and the reading is a guess.
        """
        if self._diacritizer_failed:
            return text
        if self._diacritizer is None:
            try:
                from arbtok.diacritize import LatticeDiacritizer
                self._diacritizer = LatticeDiacritizer(lang=self.lang,
                                                      lexicon=self.lexicon)
            except Exception:
                self._diacritizer_failed = True
                return text
        try:
            return self._diacritizer.diacritize(text)
        except Exception:
            return text

    # ─── transcription ───────────────────────────────────────────────

    def transcribe(self, text: str) -> str:
        """Transcribe *text*, reading any Latin-script word as a loanword.

        The Arabic runs are transcribed together, so the cross-word rules still see
        their neighbours. A Latin word is a guest: it is nativised on its own (see
        :mod:`arbtok.translit`) and spliced back in its place.
        """
        parts, buffer = [], []

        def flush_arabic():
            if buffer:
                parts.append(Sentence(self.normalize(" ".join(buffer)),
                                      lang=self.lang, stress=self.stress).ipa)
                buffer.clear()

        for token in text.split():
            if is_latin(token):
                flush_arabic()
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
            # A Latin-script word has no Arabic graphemes and no reading. Left to
            # the engine its letters come back as themselves — `meeting` as
            # `meeˈting` — which is not IPA at all.
            return transliterate(word, lang) or ""
        if context is None or (context.prev_word is None
                               and context.next_word is None):
            # Isolated word: every variety runs on the orthography2ipa shared
            # lattice, which reads the grapheme table and allophone rules of
            # the variety's own spec. Only the two things the word lattice
            # genuinely cannot do fall back to the cascade — lexical
            # exceptions, which it hardcodes, and the words needing cross-word
            # or lexical context (see `defers_to_cascade`).
            if (normalize_unicode(word) not in WORD_EXCEPTIONS
                    and not defers_to_cascade(word)):
                return word_ipa(word, lang, stress=self.stress)
            return Sentence(word, lang=lang, stress=self.stress).ipa

        # Tokenize the word with its orthographic neighbours so the
        # cross-word rules (wasl elision, idgham/iqlab, clitic
        # attachment) see the same prev/next links as a full sentence.
        parts = [p for p in (context.prev_word, word, context.next_word)
                 if p is not None]
        target = 0 if context.prev_word is None else 1
        tokens = Sentence(" ".join(parts), lang=lang, stress=self.stress).tokens
        words = [t for t in tokens if t.surface not in ("",)]
        if target < len(words):
            return words[target].ipa
        return Sentence(word, lang=lang, stress=self.stress).ipa
