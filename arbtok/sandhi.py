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
# demonstratives, relatives and a few particles. arbtok.waqf owns the list
# (it applies the same Wright §372 transform at the orthographic layer);
# importing it keeps the two libraries from drifting.
from arbtok.waqf import LEXICAL_FINAL_VOWEL
from arbtok.constants import ALIF, LAM, HAMZAT_AL_WASL

__all__ = ["apply_cross_word", "NUN_ASSIMILATION"]

#: The vowel graphemes an IPA word can end on, tested against its final
#: character. A trailing length mark ``ː`` counts too — it is the tail of a
#: long vowel. Used to decide whether a following word's hamzat al-waṣl elides.
_IPA_VOWELS = set("aeiouɑæəɛɔ")

def _ends_in_vowel(ipa: str) -> bool:
    """Does this **spoken** word end on a vowel? — the waṣl trigger.

    Tested on the post-pausal form, never the spelling: a word whose written
    case ending the pause has already dropped ends on a consonant *as spoken*
    and does not license the next word's elision, while the same word read in
    full (``pausal=False``) does. Elision tracks what is actually said (Wright I
    §19–20; Ryding 2005 §2.10), so this is the only signal it may read.
    """
    return bool(ipa) and (ipa[-1] in _IPA_VOWELS or ipa.endswith("ː"))


def _is_bare_wasl_alif(surface: str) -> bool:
    """True when the word opens on a bare hamzat al-**waṣl** alif that is not the
    definite article — اِشْتَرَى, اِنْتَ, اِسْم. Its onset is the connecting alif,
    written but silent in connected speech, surfacing as ``ʔV`` at an utterance
    edge (Ryding 2005 §2.4). ``أ``/``إ`` (hamzat al-qaṭʿ) and the article are
    excluded — the article is handled by :func:`_elide_article`."""
    if not surface:
        return False
    first = surface[0]
    if first not in (ALIF, HAMZAT_AL_WASL):
        return False
    # the definite article (ال) is a waṣl alif too, but it elides its *seat
    # vowel* rather than restoring a glottal onset — handled separately.
    letters = [c for c in surface if c not in "ًٌٍَُِّْٰ"]
    return not (len(letters) >= 2 and letters[0] in (ALIF, HAMZAT_AL_WASL)
                and letters[1] == LAM)


def _has_article(surface: str) -> bool:
    """True when the word opens on the definite article ``الـ`` (bare, with no
    proclitic in front — a proclitic + article is one token whose waṣl is
    already resolved inside the word lattice)."""
    letters = [c for c in surface if c not in "ًٌٍَُِّْٰ"]
    return (len(letters) >= 2 and letters[0] in (ALIF, HAMZAT_AL_WASL)
            and letters[1] == LAM)


def _restore_wasl_onset(ipa: str) -> str:
    """Give a bare hamzat al-waṣl word back its ``ʔ`` onset.

    The word lattice reads the connecting alif as the bare helper vowel it is in
    connected speech (اِنْتَ → ``inta``); standing at an utterance edge — and, in
    the varieties the gold records, wherever the word is not swallowed by a
    preceding vowel — it is realized with its glottal onset (``ʔinta``). o2i
    keeps the ``ʔ`` on these throughout; matching it here removes the onsetless
    reading arbtok alone produced.

    Restored only over an ``i``/``u`` prosthetic vowel (اِنْتَ → *ʔinta*,
    اِسْمَع → *ʔismaʕ*). A bare alif read with fatḥa — اَنَا, اَقْعُد, اَعْطِينِي —
    is, in the varieties the gold records, a plain vowel-initial word with no
    glottal onset (*ana*, not *ʔana*); the gold keeps the ``ʔ`` on every ``i``-
    onset waṣl word and on none of the ``a``-onset ones, so the vowel is the
    signal."""
    if ipa[:1] in ("i", "u"):
        return "ʔ" + ipa
    return ipa


def _elide_article(ipa: str) -> str:
    """Drop the definite article's seat vowel: ``aljawm`` → ``ljawm``.

    Applied only after a vowel-final word (waṣl): فِي الْبَيْت is *fiː lbajt*,
    عَلَى الشَّمْس is *ʕalaː ʃʃams* (Ryding 2005 §2.10, o2i ``AR_HAMZAT_WASL``).
    Only the leading short ``a``/``ɑ`` seat vowel is removed; the lām (or its
    sun-letter assimilate) stays and carries the article."""
    if ipa[:1] in ("a", "ɑ"):
        return ipa[1:]
    return ipa

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
    (:data:`arbtok.waqf.LEXICAL_FINAL_VOWEL`).

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


def _article_vowel_is_stressed(ipa: str, lang: str) -> bool:
    """Would this word's quantity-sensitive stress fall on the article's seat
    vowel — its initial syllable?

    The article's ``a`` elides across a vowel only when it is *unstressed*:
    ``ssajjaːra aldʒiˈdiːda`` → ``… ldʒiˈdiːda`` (stress deep in the word), but
    ``ˈattmnija`` and ``ˈarradʒul`` keep it, because the stem is light enough that
    weight throws the mark back onto the article syllable, and a stressed vowel
    cannot be deleted. orthography2ipa gets this for free by stressing each word
    *before* sandhi (its elision regex is anchored ``^[aɑ]`` and a leading ``ˈ``
    blocks the match); arbtok stresses last, so it asks the same question here.
    """
    from arbtok.stress import stress_ipa
    return stress_ipa(ipa, lang)[:1] == "ˈ"


def apply_cross_word(
    words: Sequence[Tuple[str, str, bool]],
    pausal: bool = True,
    lang: str = "ar",
) -> List[str]:
    """Apply the between-word rules to ``(ipa, surface, is_punct)`` words.

    Returns the rewritten IPA of each **spoken** word — punctuation is dropped
    from the result. A comma or a full stop is not a word and has no phonology;
    an IPA transcription carries none, exactly as ``orthography2ipa`` emits no
    ``.``/``،``/``؟``. What punctuation *is* is a pause, and a pause is what
    strips a case ending, so it is still read (below) to drive the pausal form
    of the word before it — it simply does not survive into the output.

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

    # The iʿrāb-driven rules are facts about the REFERENCE register only.
    # Waqf drops *case endings* (Wright I §372) and a dialect has none: its
    # final short vowels and its -an adverbs (أَهْلًا وَسَهْلًا → ahlan
    # wasahlan) are lexical, written because they are said, and the gold for
    # every dialect lect keeps them — as does orthography2ipa, which applies
    # no pausal transform. Likewise idghām/iqlāb of مِن's /n/ is Classical
    # recitation sandhi; the dialect gold reads *min baʕd*, not *mim baʕd*.
    # A dialect's own waqf-shaped vocalism is already restored at the
    # orthographic layer by the diacritizer (arbtok.waqf), so gating these
    # IPA-level rules to MSA/Classical drops nothing a dialect needs.
    reference_register = lang in ("ar", "arb")

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
            if pausal and reference_register:
                out[i] = _pausal(ipa, surface)
        elif nxt is not None and reference_register:
            out[i] = _assimilate_nun(ipa, nxt)

    # Onset realization — a second pass, because a word's onset is decided by the
    # *spoken* form of the word before it, which the first pass has only just
    # settled (a pause may have shortened it). Two cross-word onset rules:
    #
    #  * the definite article's seat vowel elides after a vowel-final word
    #    (فِي الْبَيْت → *fiː lbajt*); utterance-initial or after a consonant it
    #    stays (*aljawm*).
    #  * a bare hamzat al-waṣl word regains its glottal onset (اِنْتَ → *ʔinta*).
    #    The word lattice reads the connecting alif as a bare helper vowel — the
    #    mid-utterance connected form; here it is restored to the ʔV the varieties
    #    the gold records realize, which orthography2ipa keeps throughout. Unlike
    #    the article, a non-article waṣl does not shed its onset after a vowel in
    #    that gold (هُوَ اِنْتَ → *huwa ʔinta*), so the restoration is
    #    position-independent.
    for i, (ipa, surface, is_punct) in enumerate(words):
        if is_punct or not out[i]:
            continue
        prev_spoken: Optional[str] = None
        prev_was_pause = False
        for j in range(i - 1, -1, -1):
            _, _, jp = words[j]
            if jp:
                prev_was_pause = True
                break
            if out[j]:
                prev_spoken = out[j]
                break
        after_vowel = (prev_spoken is not None and not prev_was_pause
                       and _ends_in_vowel(prev_spoken))

        if _has_article(surface):
            if after_vowel and not _article_vowel_is_stressed(out[i], lang):
                # The article's seat vowel elides after a vowel only when it is
                # unstressed — a stressed vowel cannot be deleted. This is how
                # orthography2ipa behaves: it stresses each word before sandhi,
                # and its elision regex, anchored ``^[aɑ]``, cannot fire past a
                # leading stress mark. So aldʒiˈdiːda and ʃˈʃams (stress off the
                # article) elide after a vowel, while ˈalqalam, ˈallahu,
                # ˈaʃʃamis and ˈattmnija (stress on the article syllable) keep it.
                out[i] = _elide_article(out[i])
        elif _is_bare_wasl_alif(surface):
            out[i] = _restore_wasl_onset(out[i])

    return [out[i] for i, (_, _, is_punct) in enumerate(words) if not is_punct]
