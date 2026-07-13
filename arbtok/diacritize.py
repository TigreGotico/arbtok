"""Diacritization as a *guarded* step, not a free generation.

Restoring tashkeel is a statistical problem — which vowel follows a letter is
morphological and syntactic, and the letters say none of it — so it belongs to a
model, and arbtok delegates it to ``text2tashkeel``. But a model asked to write
into a word can write *anything*, including a reading the orthography does not
license and a consonant that was never there. Downstream, that is indetectable:
the phonemizer will faithfully transcribe the hallucination.

arbtok is the one library that knows about both the diacritizer and the
orthography2ipa lattice, so it is where the two meet. The model **proposes**; the
lattice **disposes**:

1. **Only act where the writing is actually silent.** orthography2ipa reports
   which letters are underdetermined (:func:`~orthography2ipa.is_underdetermined`).
   A word that already carries its marks is left exactly as written — a human's
   tashkeel is evidence, and a model must never overwrite it.
2. **The skeleton is inviolable.** Strip the marks back off the model's output
   and it must be the word we handed it. A diacritizer may add marks; it may not
   add, drop or change a *letter*. (The rawi models also restore a hamza and the
   dagger-alef — a documented widening of the task — so those specific letter
   restorations are allowed, and nothing else is.)
3. **The result must be licensed.** The diacritized word is tokenized against the
   variety's own grapheme table. If any part of it does not map — if the model
   produced a mark sequence the orthography does not admit — the word is rejected.

A rejected proposal falls back to the word as written. That is the honest
outcome: an underdetermined reading, which orthography2ipa will report as such,
rather than a confident wrong one.
"""

from __future__ import annotations

from typing import List, Optional

from orthography2ipa import get, is_underdetermined
from orthography2ipa.phonetok import PhonetokTokenizer, TokenKind

from arbtok.dialects import DEFAULT_LANG
from arbtok.tokenizer import normalize_unicode

__all__ = ["LatticeDiacritizer", "strip_marks"]

#: Every Arabic mark a diacritizer may add. Anything else it emits is a letter.
_MARKS = set("ًٌٍَُِّْٰٓ")

#: Letters the rawi models legitimately RESTORE rather than merely mark: a bare
#: alif typed for a hamza carrier, and the silent dagger-alef. This is a
#: documented widening of the task (text2tashkeel's models fix real,
#: inconsistently-spelled input), so a change confined to these is not a
#: hallucination. Keyed by what may replace what.
_RESTORABLE = {
    "ا": {"أ", "إ", "آ", "ٱ"},   # bare alif → a hamza carrier
    "ه": {"ة"},                   # hāʾ → tāʾ marbūṭa
    "ي": {"ى"},                   # yāʾ → alif maqṣūra
}


def strip_marks(text: str) -> str:
    """The consonantal skeleton: *text* with every diacritic removed."""
    return "".join(ch for ch in text if ch not in _MARKS)


def _skeleton_is_preserved(original: str, diacritized: str) -> bool:
    """True when the model only *marked* the word, or restored a licensed letter.

    A diacritizer's contract is to add marks. If the letters come back different,
    the model rewrote the word — and the phonemizer downstream has no way to
    know. The one sanctioned exception is the restoration a rawi model is
    explicitly built to do (a bare alif that should carry a hamza, a hāʾ that
    should be a tāʾ marbūṭa).
    """
    before, after = strip_marks(original), strip_marks(diacritized)
    if before == after:
        return True
    if len(before) != len(after):
        return False
    for a, b in zip(before, after):
        if a == b:
            continue
        if b not in _RESTORABLE.get(a, ()):
            return False
    return True


class LatticeDiacritizer:
    """Diacritize a word only where the writing is silent, and only if licensed.

    ``lang`` names the orthography2ipa variety whose grapheme table licenses the
    result. ``waqf`` drops the case endings from the model's output, giving the
    pausal form that is actually spoken rather than the fully-parsed form the
    models restore (see :mod:`text2tashkeel.waqf`).
    """

    def __init__(
        self,
        lang: str = DEFAULT_LANG,
        model: Optional[str] = None,
        waqf: bool = True,
    ) -> None:
        self.lang = lang
        self.waqf = waqf
        self._model = model
        self._diacritizer = None
        self._spec = get(lang)
        self._tokenizer = PhonetokTokenizer(self._spec)
        #: Words the model proposed and the lattice refused, in order.
        self.rejected: List[str] = []

    @property
    def diacritizer(self):
        if self._diacritizer is None:
            from text2tashkeel import Diacritizer
            self._diacritizer = (
                Diacritizer(self._model, waqf=self.waqf) if self._model
                else Diacritizer(waqf=self.waqf)
            )
        return self._diacritizer

    def _is_licensed(self, word: str) -> bool:
        """True when every part of *word* maps to a grapheme the spec declares."""
        try:
            tokens = self._tokenizer.tokenize(normalize_unicode(word))
        except Exception:
            return False
        return all(t.kind is not TokenKind.UNKNOWN for t in tokens)

    def diacritize_word(self, word: str) -> str:
        """Return *word* diacritized, or unchanged if it needs nothing or the
        proposal is refused."""
        normalized = normalize_unicode(word)
        # (1) The writing already says it — never overwrite a human's marks.
        if not is_underdetermined(normalized, self._spec):
            return word

        proposed = self.diacritizer.diacritize(normalized)

        # (2) A diacritizer marks; it does not rewrite.
        if not _skeleton_is_preserved(normalized, proposed):
            self.rejected.append(word)
            return word

        # (3) The orthography must license the result.
        if not self._is_licensed(proposed):
            self.rejected.append(word)
            return word

        return proposed

    def diacritize(self, text: str) -> str:
        """Diacritize each word of *text*, guarding every one of them."""
        return " ".join(
            self.diacritize_word(w) if w.strip() else w
            for w in text.split(" ")
        )

    __call__ = diacritize
