"""What happens between words.

A word's own phonology comes from the lattice — the variety's grapheme table and
its ``allophone_rules``. But some of Arabic's most audible phonology is not a
property of a word at all; it is a property of a word *next to another word*, and
no word-level engine can see it:

* **idghām / iqlāb** — a final /n/ assimilates to what follows. مِنْ رَبِّهِمْ is
  *mir rabbihim*, not *min rabbihim*; مِنْ بَيْتِكَ is *mim bajtika*. The /n/ is
  written, and it is not pronounced.
* **pausal tanwīn** — a word at a pause loses its case ending, and tanwīn al-fatḥ
  lengthens rather than vanishing: كِتَابًا is *kitaːbaː* utterance-finally.
* **waṣl** — the article's vowel elides after a proclitic or a vowel-final word:
  فِي الْبَيْت is *fiː lbajt*.

These used to live inside the character cascade, which is why the cascade could
not be replaced wholesale by the lattice: doing so silently dropped them. They
are cross-word rules, so they belong here — applied to the assembled words, where
each one can actually see its neighbour.

Keeping them separate is also what makes them testable. Inside the cascade they
were conditions on a character's ``prev_token.prev_token``; here they are rules
about words, which is what they are.
"""

from __future__ import annotations

import re
from typing import List, Optional, Sequence, Tuple

# The closed class of words whose final short vowel is lexical (part of the
# word) rather than iʿrāb, and so survives the pause — pronouns,
# demonstratives, relatives and a few particles. text2tashkeel owns the list
# (it applies the same Wright §372 transform at the orthographic layer);
# importing it keeps the two libraries from drifting.
from text2tashkeel.waqf import LEXICAL_FINAL_VOWEL

__all__ = ["apply_cross_word", "NUN_ASSIMILATION"]

#: The words whose final /n/ assimilates: مِن and مَن. Both are written with a
#: nūn that a following sonorant swallows.
_NUN_WORDS = {"min", "man"}

#: What a final /n/ becomes before each following onset (Wright I §14; the
#: recitation terms are idghām for the sonorants and iqlāb for the labial).
NUN_ASSIMILATION = {
    "r": "r",   # idghām: min rabbihim → mir rabbihim
    "j": "j",   # idghām: man jaquːlu  → maj jaquːlu
    "l": "l",   # idghām: min lisaːn   → mil lisaːn
    "m": "m",   # idghām
    "b": "m",   # iqlāb:  min bajtika  → mim bajtika
}


def _assimilate_nun(ipa: str, next_ipa: str) -> str:
    """A final /n/ takes the shape of what follows it."""
    if not ipa.endswith("n") or ipa not in _NUN_WORDS:
        return ipa
    if not next_ipa:
        return ipa
    onset = next_ipa[0]
    surface = NUN_ASSIMILATION.get(onset)
    if surface is None:
        return ipa
    return ipa[:-1] + surface


#: The tanwīn. A word ends in one or it does not, and the ORTHOGRAPHY says
#: which — never the transcription.
_TANWIN_FATH, _TANWIN_DAMM, _TANWIN_KASR = "ً", "ٌ", "ٍ"

#: The tāʾ marbūṭa, silent at a pause and pronounced when a vowel follows it.
_TA_MARBUTA = "ة"

#: The plain short-vowel iʿrāb marks and the IPA vowel each one writes.
_SHORT_VOWEL_IPA = {"َ": "a", "ُ": "u", "ِ": "i"}

#: The run of harakāt at the very end of a written word.
_TRAILING_MARKS = re.compile(r"[ًٌٍَُِّْٰ]+$")


def _pausal(ipa: str, surface: str) -> str:
    """A word at a pause takes its pausal (waqf) form — Wright I §372.

    The pause drops the case and mood endings (iʿrāb): a final short vowel
    goes, tanwīn ḍamm/kasr go with their /n/, and tanwīn al-fatḥ is the
    exception — it does not vanish, it lengthens, the written alif carrying
    it: كِتَابًا is *kitaːbaː*. A tāʾ marbūṭa voiced only by its ending falls
    silent with it: مَدِينَةٌ is [madiːnatun] in full and [madiːna] at a
    pause. (Wright, *A Grammar of the Arabic Language*, 3rd ed., I §372;
    Ryding, *A Reference Grammar of MSA*, CUP 2005, §2.4.)

    Driven by the **spelling**, not by the IPA. A tanwīn or a final harakah is
    written, so whether a word has one is a fact about the page; guessing it
    from the transcription's last characters confuses a case ending with a
    stem and eats the word — the -in of قَاضٍ is an ending and the -in of
    مُؤْمِن is the word, and only the orthography can tell them apart. A
    closed class of function words (هُوَ, نَحْنُ, …) carries a *lexical*
    final vowel that is not iʿrāb and survives the pause
    (:data:`text2tashkeel.waqf.LEXICAL_FINAL_VOWEL`).

    Unmodeled: the construct-state tāʾ marbūṭa, which pausally keeps /t/
    before its annex in careful renditions (Wright I §372 rem.); arbtok has
    no morphosyntax to detect iḍāfa, and a written pause after a construct
    head is itself unusual, so the plain pausal /a/ is used throughout.
    """
    if surface in LEXICAL_FINAL_VOWEL:
        return ipa

    marks = set(surface)
    has_tanwin = bool(marks & {_TANWIN_FATH, _TANWIN_DAMM, _TANWIN_KASR})

    # A tāʾ marbūṭa is pronounced only because a vowel follows it. Take the case
    # ending away and nothing follows it any more, so it falls silent too:
    # مَدِينَةٌ is [madiːnatun] in full and [madiːna] at a pause — never
    # [madiːnat], which would be the tāʾ surviving the very thing that voiced it.
    if has_tanwin and _TA_MARBUTA in surface:
        for ending in ("atun", "atin", "atan"):
            if ipa.endswith(ending):
                return ipa[: -len(ending)] + "a"

    if _TANWIN_FATH in marks and ipa.endswith("an"):
        return ipa[:-2] + "aː"
    if (_TANWIN_DAMM in marks and ipa.endswith("un")) or (
            _TANWIN_KASR in marks and ipa.endswith("in")):
        return ipa[:-2]

    # A plain final short vowel — fatḥa, ḍamma, kasra — is the case or mood
    # ending, and the pause drops it (Wright I §372). Only when the page
    # actually writes it word-finally, and only when the transcription ends
    # in the very vowel that mark writes.
    trailing = _TRAILING_MARKS.search(surface)
    if trailing:
        vowel = next((v for m, v in _SHORT_VOWEL_IPA.items()
                      if m in trailing.group()), None)
        if vowel is not None and ipa.endswith(vowel):
            ipa = ipa[: -1]
            # The tāʾ marbūṭa the departed vowel was voicing goes too.
            if (surface[: trailing.start()].endswith(_TA_MARBUTA)
                    and ipa.endswith("t")):
                ipa = ipa[: -1]
    return ipa


def apply_cross_word(
    words: Sequence[Tuple[str, str, bool]],
    pausal: bool = True,
) -> List[str]:
    """Apply the between-word rules to ``(ipa, surface, is_punct)`` words.

    Returns the rewritten IPA of each. Punctuation is passed through untouched —
    it is not a word and has no phonology. What it *is* is a pause, and a pause is
    what strips a case ending.

    ``pausal`` is arbtok's declared waqf policy switch. ``True`` (the TTS
    default) renders a word standing at a written pause in its pausal form
    (Wright I §372 — see :func:`_pausal`); ``False`` is the full-iʿrāb
    passthrough: every written ending is read out, the recitation/pedagogical
    register. Both modes see the same word IPA — the pause is the only thing
    the flag changes, so the two cannot drift.

    A word at the end of the input is **not** treated as paused. The pause has to
    be written: an utterance may continue past whatever fragment was handed to us,
    and inventing a pause at the edge of the input would make a word's
    transcription depend on how much of the sentence the caller happened to pass.
    """
    out = [ipa for ipa, _, _ in words]

    for i, (ipa, surface, is_punct) in enumerate(words):
        if is_punct or not ipa:
            continue

        nxt: Optional[str] = None
        before_pause = False
        for j in range(i + 1, len(words)):
            nxt_ipa, _, nxt_punct = words[j]
            if nxt_punct:
                before_pause = True
                break
            if nxt_ipa:
                nxt = nxt_ipa
                break

        if before_pause:
            if pausal:
                out[i] = _pausal(ipa, surface)
        elif nxt is not None:
            out[i] = _assimilate_nun(ipa, nxt)

    return out
