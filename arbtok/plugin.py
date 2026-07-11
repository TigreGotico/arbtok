"""arbtok's Arabic G2P engine, on the orthography2ipa base interface.

arbtok *consumes* orthography2ipa — its ``ar`` spec data and the shared
:class:`~orthography2ipa.g2p_plugin.G2PPlugin`/``WordContext`` types —
and owns the Arabic pipeline. Use it directly:

    >>> from arbtok.plugin import ArbtokG2PPlugin
    >>> ArbtokG2PPlugin().transcribe("كتاب جميل")
    'kitaːb dʒamiːl'

The engine maps arbtok's machinery onto the shared interface:

- ``normalize`` — Unicode/diacritic reordering, number and date
  expansion, and automatic tashkeel diacritization of bare text via
  ``text2tashkeel`` (failure degrades gracefully to the undiacritized
  input).
- ``transcribe_word`` — for an isolated MSA word (no context), the
  orthography2ipa shared lattice with arbtok's rescorers (sun-letter
  assimilation, hamzat al-waṣl, gemination, mater lectionis; see
  :mod:`arbtok.lattice`). Cross-word effects use the orthographic
  neighbours carried by ``WordContext``: the word is tokenized together
  with its neighbours so the prev/next-token cross-word rules fire.
- ``transcribe`` — full-sentence path with clitic joining, identical to
  ``Sentence(text).ipa``.
"""
from typing import List, Optional, Union

from orthography2ipa.g2p_plugin import G2PPlugin, WordContext

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
from arbtok.dialects import ArabicDialect, WORD_EXCEPTIONS, dialect_for_lang
from arbtok.lattice import defers_to_cascade, word_ipa
from arbtok.tokenizer import Sentence, normalize_unicode
from arbtok.util import normalize as normalize_speech

_DIACRITICS = {
    FATHA, DAMMA, KASRA, SHADDA, SUKUN,
    TANWIN_FATH, TANWIN_DAMM, TANWIN_KASR, DAGGER_ALIF, MADD,
}

# Bare text below this diacritic-per-letter ratio gets auto-tashkeel.
_DIACRITIC_DENSITY_THRESHOLD = 0.2


def _diacritic_density(text: str) -> float:
    letters = [c for c in text if "؀" <= c <= "ۿ"]
    if not letters:
        return 1.0
    marks = sum(1 for c in letters if c in _DIACRITICS)
    return marks / len(letters)


class ArbtokG2PPlugin(G2PPlugin):
    """Arabic G2P via arbtok's rule-based token tree.

    Output defaults to Modern Standard Arabic. Pass *dialect* to realize the
    MSA orthography with a regional zone's reflexes (Egyptian, Levantine,
    Gulf, Maghrebi); see :mod:`arbtok.dialects`. The zone may also be
    inferred per call from a region-bearing language tag carried on
    ``WordContext.lang`` (``ar-EG`` → Egyptian, …), which overrides the
    instance default; bare ``ar`` or an unmapped region keeps MSA.
    """

    def __init__(
        self, dialect: Union[ArabicDialect, str, None] = None
    ) -> None:
        self._diacritizer = None
        self._diacritizer_failed = False
        self.dialect = (
            ArabicDialect(dialect) if dialect is not None else ArabicDialect.MSA
        )

    @property
    def language_codes(self) -> List[str]:
        return ["ar", "arb"]

    def _resolve_dialect(
        self, context: Optional[WordContext] = None
    ) -> ArabicDialect:
        """Pick the zone for a call: a region-bearing ``context.lang`` wins,
        otherwise the instance default (``MSA`` unless configured)."""
        if context is not None and context.lang:
            zone = dialect_for_lang(context.lang)
            if zone is not ArabicDialect.MSA:
                return zone
        return self.dialect

    # ─── lifecycle hooks ─────────────────────────────────────────────

    def normalize(self, text: str) -> str:
        text = normalize_speech(text, "ar")
        text = normalize_unicode(text)
        if _diacritic_density(text) < _DIACRITIC_DENSITY_THRESHOLD:
            text = self._diacritize(text)
        return text

    def _diacritize(self, text: str) -> str:
        if self._diacritizer_failed:
            return text
        if self._diacritizer is None:
            try:
                from arbtok.tashkeel import TashkeelDiacritizer
                self._diacritizer = TashkeelDiacritizer()
            except Exception:
                self._diacritizer_failed = True
                return text
        try:
            return self._diacritizer.diacritize(text)
        except Exception:
            return text

    # ─── transcription ───────────────────────────────────────────────

    def transcribe(self, text: str) -> str:
        return Sentence(self.normalize(text), dialect=self.dialect).ipa

    def transcribe_word(
        self, word: str, context: Optional[WordContext] = None
    ) -> str:
        dialect = self._resolve_dialect(context)
        if context is None or (context.prev_word is None
                               and context.next_word is None):
            # Isolated word: the MSA register runs on the orthography2ipa
            # shared lattice + rescorers. Regional zones still take the
            # reflex-cascade path (the lattice is MSA-only) as do lexical
            # exceptions, which the cascade hardcodes.
            if (dialect in (ArabicDialect.MSA, ArabicDialect.CLA)
                    and normalize_unicode(word) not in WORD_EXCEPTIONS
                    and not defers_to_cascade(word)):
                return word_ipa(word)
            return Sentence(word, dialect=dialect).ipa

        # Tokenize the word with its orthographic neighbours so the
        # cross-word rules (wasl elision, idgham/iqlab, clitic
        # attachment) see the same prev/next links as a full sentence.
        parts = [p for p in (context.prev_word, word, context.next_word)
                 if p is not None]
        target = 0 if context.prev_word is None else 1
        tokens = Sentence(" ".join(parts), dialect=dialect).tokens
        words = [t for t in tokens if t.surface not in ("",)]
        if target < len(words):
            return words[target].ipa
        return Sentence(word, dialect=dialect).ipa
