"""Diacritization as a *guarded* step, not a free generation.

Restoring tashkeel is a statistical problem — which vowel follows a letter is
morphological and syntactic, and the letters say none of it — so it belongs to a
model, and arbtok delegates it to ``text2tashkeel``. But a model asked to write
into a word can write *anything*, including a reading the orthography does not
license and a consonant that was never there. Downstream, that is indetectable:
the phonemizer will faithfully transcribe the hallucination.

arbtok is the one library that knows about both the diacritizer and the
orthography2ipa lattice, so it is where the two meet. The model **proposes**; the
lattice **disposes**.

Two of the three guards this once carried have **moved upstream**, where they
belong. text2tashkeel now decodes under an orthographic constraint of its own
(:mod:`text2tashkeel.orthography`): it cannot rewrite a letter the writing spells,
and it cannot overwrite a mark a human wrote, because the classes that would do so
are masked out before the argmax. Those are facts about Arabic and about the
model's class space — no lattice is needed to know them, so no lattice should have
to.

What is left here is the part that genuinely needs a lattice:

1. **Only act where the writing is actually silent.** orthography2ipa reports
   which letters are underdetermined (:func:`~orthography2ipa.is_underdetermined`),
   so a fully-marked word is never handed to a model at all.
2. **The result must be licensed.** The diacritized word is tokenized against the
   *variety's own* grapheme table. A mark sequence the orthography does not admit
   is not an answer, and only the spec knows which those are.

A refused proposal falls back to the word as written — an underdetermined reading,
which orthography2ipa reports as such, rather than a confident wrong one. The
skeleton check stays as a cheap backstop: it should now never fire, and if it does,
something upstream has regressed.
"""

from __future__ import annotations

from typing import List, Optional

from orthography2ipa import get, is_underdetermined
from orthography2ipa.phonetok import PhonetokTokenizer, TokenKind

from arbtok.nisba import restore_nisba
from arbtok.dialects import DEFAULT_LANG
from arbtok.tokenizer import normalize_unicode

__all__ = ["LatticeDiacritizer", "strip_marks", "repair_skeleton"]

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


def repair_skeleton(original: str, proposed: str) -> Optional[str]:
    """Keep the model's **marks**, restore the original **letters**.

    A diacritizer's job is to mark a word, so when it also swaps a letter the
    marks are usually still right and only the letter is wrong. Rejecting the
    whole proposal throws away good marks with the bad letter; repairing keeps
    them and puts our letter back.

    This is not hypothetical. The rawi models systematically rewrite the alef
    madda ⟨آ⟩ to a plain hamza carrier ⟨أ⟩ — destroying the long /aː/ it stands
    for (آبد /ʔaːbid/ came back as أَبْد /ʔabd/) — on about 6.5% of a WikiPron
    Arabic sweep. Repairing those words rather than dropping them is worth
    ~0.7 PER and ~0.5 WER points on that set, and it is strictly better than
    rejecting on every metric measured.

    Returns ``None`` when the skeletons do not align one-to-one, in which case
    the proposal cannot be repaired and must be refused.
    """
    original_letters = strip_marks(original)
    if len(original_letters) != len(strip_marks(proposed)):
        return None
    out: List[str] = []
    i = 0
    for ch in proposed:
        if ch in _MARKS:
            out.append(ch)
        else:
            out.append(original_letters[i])
            i += 1
    return "".join(out)


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
        #: Words the model proposed and the lattice refused outright, in order.
        self.rejected: List[str] = []
        #: Words whose letters the model rewrote and we put back, keeping its
        #: marks. Chiefly the alef-madda class — see :func:`repair_skeleton`.
        self.repaired: List[str] = []

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

        # (2) A diacritizer marks; it does not rewrite. When it did rewrite a
        # letter, the marks are usually still right — so keep them and put our
        # letter back, rather than throwing the whole proposal away. Only a
        # proposal that cannot be repaired (the skeletons do not align) is
        # refused.
        if not _skeleton_is_preserved(normalized, proposed):
            repaired = repair_skeleton(normalized, proposed)
            if repaired is None:
                self.rejected.append(word)
                return word
            self.repaired.append(word)
            proposed = repaired

        # (3) The nisba's shadda is not printed, and the model does not restore
        # it: عربي comes back as a bare yāʾ and reads /ʕarbiː/, not /ʕarabijj/.
        # Put the mark back before licensing, so the result is held to the
        # grapheme table like any other proposal.
        proposed = restore_nisba(proposed)

        # (4) The orthography must license the result.
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
