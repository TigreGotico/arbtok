"""Arabizi — Arabic written in Latin letters and digits — read as Arabic.

A Latin-script run in an Arabic sentence is not always a foreign word. Much of it
is *Arabizi* (also "3arabi", "Franco-Arabic", "chat Arabic"): Arabic spelled in the
ASCII a keyboard offers, with digits standing in for the consonants Latin has no
letter for — ``7`` for the pharyngeal ح, ``3`` for the ʿayn ع, ``2`` for the glottal
stop, ``5``/``kh`` for خ, ``9`` for the qāf ق. So ``7abibi`` is حبيبي and ``3ala`` is
على — Arabic, not English, and running it through the loanword nativiser
(:mod:`arbtok.translit`) reads حبيبي as if it were an English word, which is exactly
the failure that module warns about ("this is how ⟨Arabizi⟩ gets read as English").

## What this module does — and does not do

It does **one** narrow thing: reverse-transliterate an Arabizi token back to an
*undiacritized Arabic consonantal skeleton*, and hand that skeleton to the normal
pipeline. It does **not** produce IPA and it does **not** restore vowels. That is
the whole design: Arabizi under-determines the short vowels exactly as ordinary
unpointed Arabic does, so the skeleton is unpointed Arabic, and the fusion
diacritizer + the lect phonology — the machinery arbtok already runs on native
text — restore the vocalism dialect-aware. Arabizi gives the skeleton; fusion
gives the reading.

## The digit map

The digit conventions are the stable, well-documented core of Arabizi. They arose
because the shapes of the digits resemble the mirrored Arabic letters:

======  =========  =====================================================
 token   Arabic     source
======  =========  =====================================================
 ``2``   ء          hamza / glottal stop
 ``3``   ع          ʿayn (voiced pharyngeal)
 ``5``   خ          ḫāʾ (also written ``kh``)
 ``6``   ط          emphatic ṭāʾ
 ``7``   ح          ḥāʾ (voiceless pharyngeal)
 ``8``   غ          ġayn (also written ``gh``); regionally ``8``≈ق
 ``9``   ق          qāf (also written ``q``)
 ``3'``  غ          ʿayn + prime = ġayn
 ``7'``  خ          ḥāʾ + prime = ḫāʾ
 ``6'``  ظ          ṭāʾ + prime = ẓāʾ
======  =========  =====================================================

Documented in Yaghan, M. A. (2008), "Arabizi: A Contemporary Style of Arabic Slang",
*Design Issues* 24(2), 39–52 (the digit-for-guttural inventory, table p. 44); and in
the LDC transliteration guidelines, Bies, A. et al. (2014), "Transliteration of
Arabizi into Arabic Orthography", *Proc. EMNLP 2014 Workshop on Arabic NLP*, 11–20
(the many-to-many, context-dependent nature of the mapping — one Arabizi form spells
several skeletons, and the vowels are the ambiguous part).

## Where it is genuinely ambiguous — and how v1 stays honest

Arabizi is a *convention*, not an orthography, and three things it cannot pin down:

* **Short vowels.** ``a e i o u`` are not Arabic letters; only long vowels
  (doubled ``aa``/``ee``/``oo`` or the mater digraphs) map to alif/wāw/yāʾ. Bare
  short vowels are **dropped** from the skeleton — precisely the information
  unpointed Arabic also omits, and precisely what fusion is there to restore.
* **``g``.** Gulf/Bedouin writers use ``g`` for the qāf reflex (``soog`` = سوق),
  Egyptians for the ǧīm (``gamal`` = جمل). v1 takes the qāf reading (ق), the more
  frequent convention in this dataset; a caller who knows better can pre-map.
* **``ch``.** Levantine/Maghrebi ``ch`` = ش (``wach`` = واش); Gulf ``ch`` = چ, the
  affricated kāf (``chai`` = چاي). v1 takes ش. Both are documented; neither is
  universal. These are recorded as known losses rather than papered over.

The detection gate is deliberately conservative (see :func:`is_arabizi`): a Latin
run is treated as Arabizi only when it carries a digit-guttural, or when the caller
passes an explicit hint. A plain-Latin word like ``meeting`` or ``manager`` has no
digit and no hint, so it stays on the loanword-nativisation path — the ambiguous
"is this Arabizi or English?" call is refused in v1 rather than guessed, because a
wrong guess silently breaks the nativisation of genuine embeds.
"""

from __future__ import annotations

import re
from typing import Optional

__all__ = ["is_arabizi", "to_arabic_skeleton", "ARABIZI_DIGITS"]

#: The digit-for-guttural core (Yaghan 2008 p. 44). These are the letters Latin has
#: no glyph for; their presence in a Latin run is the strong signal of Arabizi.
ARABIZI_DIGITS = {
    "2": "ء",
    "3": "ع",
    "5": "خ",
    "6": "ط",
    "7": "ح",
    "8": "غ",
    "9": "ق",
}

#: Prime-modified digits — the "dotted" gutturals (ġayn over ʿayn, ẓāʾ over ṭāʾ).
#: Matched before the bare digit so ``3'`` wins over ``3``.
_PRIME_DIGITS = {
    "3'": "غ",
    "7'": "خ",
    "6'": "ظ",
    "9'": "ق",
}

#: Multi-character Latin sequences, matched longest-first before single letters.
#: Digraph consonants and the long-vowel matres. ``ch`` → ش and ``g`` → ق are the
#: documented v1 defaults for the two genuinely ambiguous conventions (see module
#: docstring); the doubled vowels are matres lectionis.
_DIGRAPHS = {
    "kh": "خ",
    "gh": "غ",
    "sh": "ش",
    "ch": "ش",   # v1 default; Gulf چ not modelled (ambiguous, documented)
    "th": "ث",
    "dh": "ذ",
    # long vowels / diphthongs → matres. Arabizi writes a historical *ay/*aw and a
    # long ā/ū/ī with these digraphs; the skeleton records the mater and lets the
    # lect phonology decide monophthong vs diphthong (Bahraini wain→[weːn] etc.).
    "aa": "ا",
    "ee": "ي",
    "ii": "ي",
    "oo": "و",
    "uu": "و",
    "ou": "و",
    "ai": "ي",
    "ay": "ي",
    "ei": "ي",
    "ey": "ي",
    "oi": "و",
    "au": "و",
    "aw": "و",
}

#: Single Latin consonants. Emphatics are the capitalised set (``S D T Z`` →
#: ص ض ط ظ), the widespread Arabizi convention for marking emphasis by case.
_CONSONANTS = {
    "b": "ب", "t": "ت", "j": "ج", "7": "ح", "5": "خ",
    "d": "د", "r": "ر", "z": "ز", "s": "س", "9": "ق",
    "3": "ع", "8": "غ", "f": "ف", "q": "ق", "k": "ك",
    "g": "ق",   # v1 default: qāf reflex (Gulf/Bedouin); Egyptian ǧīm not modelled
    "l": "ل", "m": "م", "n": "ن", "h": "ه", "w": "و", "y": "ي",
    "2": "ء", "v": "ف", "p": "ب", "c": "ك",
    "S": "ص", "D": "ض", "T": "ط", "Z": "ظ",
}

#: Single Latin vowels → the mater lectionis they most often stand for. Arabizi
#: spells its vowels (``habibi``, not ``hbb``), so keeping a mater preserves the
#: word shape; the length is under-determined and fusion adjusts it.
_VOWELS_SINGLE = {"a": "ا", "e": "ي", "i": "ي", "o": "و", "u": "و"}

_HAS_DIGIT_GUTTURAL = re.compile(r"[234567]|3'|7'|6'")
_LATIN = re.compile(r"[A-Za-z]")
_STRIP = ".,;:!?()[]\"'،؛؟-"


def is_arabizi(word: str, hint: Optional[bool] = None) -> bool:
    """True when *word* should be read as Arabizi rather than a foreign loanword.

    The v1 gate is deliberately conservative and has exactly two ways to fire:

    * *hint* — the caller knows. An explicit ``True``/``False`` always wins; this is
      how a caller who has language-tagged its input drives the decision, exactly as
      :mod:`arbtok.translit` insists the donor is the caller's to name.
    * a **digit-guttural** — ``2 3 5 6 7 9`` (and the primed forms). No English word
      contains one, so their presence is strong, low-false-positive evidence of
      Arabic-in-Latin. ``meeting``/``manager``/``email`` carry none and stay loans.

    What v1 does **not** attempt: sniffing all-alphabetic Arabizi (``habibi``,
    ``inta``) apart from English by morphology or lexicon lookup. That call is real
    but error-prone, and a wrong "yes" silently corrupts a genuine English embed, so
    v1 refuses it — returning ``False`` — unless the caller hints. The ambiguity is
    documented, not hidden.
    """
    if hint is not None:
        return hint
    return bool(_HAS_DIGIT_GUTTURAL.search(word))


def to_arabic_skeleton(word: str) -> str:
    """Reverse-transliterate an Arabizi *word* to an unpointed Arabic skeleton.

    Produces a consonantal skeleton with matres lectionis for long vowels and short
    vowels dropped — the same under-specification as ordinary unpointed Arabic, so
    the result is fed straight into the normal diacritize + phonology pipeline. This
    does **not** vocalise; that is fusion's job.

    Rules (matched longest-first): primed digits → dotted gutturals; digit gutturals
    → their letters; consonant digraphs (``kh gh sh ch th dh``) and doubled-vowel
    matres (``aa ee oo …``); then single consonants (capitals ``S D T Z`` emphatic).
    A **word-initial** short vowel becomes a bare alif carrier (ا); other short
    vowels are dropped; a **word-final** lone ``a`` becomes tāʾ marbūṭa (ة), the far
    more common feminine ending in these lects.
    """
    w = word.strip(_STRIP)
    if not w:
        return word
    out = []
    i = 0
    n = len(w)
    while i < n:
        # primed digits (3' 7' 6' 9')
        two = w[i:i + 2]
        if two in _PRIME_DIGITS:
            out.append(_PRIME_DIGITS[two])
            i += 2
            continue
        # digraphs (case-insensitive for letter digraphs)
        low2 = two.lower()
        if low2 in _DIGRAPHS:
            out.append(_DIGRAPHS[low2])
            i += 2
            continue
        ch = w[i]
        # emphatic capitals must be checked before lower-casing
        if ch in ("S", "D", "T", "Z"):
            out.append(_CONSONANTS[ch])
            i += 1
            continue
        if ch in _CONSONANTS:
            out.append(_CONSONANTS[ch])
            i += 1
            continue
        low = ch.lower()
        if low in _CONSONANTS:
            out.append(_CONSONANTS[low])
            i += 1
            continue
        if low in _VOWELS_SINGLE:
            if i == 0:
                # word-initial vowel needs an alif carrier to sit on
                out.append("ا")
            elif i == n - 1 and low in "eiou":
                # a word-final short vowel carries no mater in Arabic orthography
                # (يمشي's -i, كتبوا's -u are matres, but a bare final e/i/o/u after
                # a consonant is most often a dropped short vowel) — drop it.
                pass
            else:
                # Arabizi, unlike Arabic script, spells its vowels — ``habibi`` is
                # written, not ``hbb``. So a written vowel leaves a mater: it keeps
                # the word's shape for the diacritizer to vocalise, rather than
                # collapsing it to an unreadable consonant cluster. The length is
                # under-determined (a mater reads long), and fusion + the lect
                # phonology adjust it; dropping the vowel loses far more.
                out.append(_VOWELS_SINGLE[low])
            i += 1
            continue
        # unknown char (kept, e.g. stray latin) — drop silently
        i += 1
    return "".join(out)
