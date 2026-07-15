"""Where the stress falls.

Arabic stress is **quantity-sensitive**: it lands on a syllable because that
syllable is *heavy*, and weight is a property of the transcription — a long
vowel, a coda — not of the spelling. So it cannot be placed from the orthography,
only from the IPA, which is why it happens here and not in the tokenizer.

Given diacritized input the placement is exact (Ryding 2005 §2.3; Watson 2002
ch.3): superheavy final ``kiˈtaːb`` > heavy penult ``muˈdarris`` > antepenult
``ˈmadrasa``. The rules themselves live in the variety's orthography2ipa spec;
this module only decides *what a prosodic word is* and applies them to it.

It matters for TTS: stress drives vowel duration and prominence, and getting it
wrong is one of the loudest cues of a non-native-sounding voice.
"""

from __future__ import annotations

from orthography2ipa import get
from orthography2ipa.vowels import is_ipa_vowel
from orthography2ipa.stress import (
    apply_stress_mark, detect_stress, detect_stress_by_weight, syllabify_ipa,
)

from arbtok.dialects import DEFAULT_LANG

__all__ = ["stress_ipa", "stress_words"]


#: The superscript / diacritic modifiers that ride on a consonant's base letter
#: (emphatic ˤ, labialized ʷ, palatalized ʲ, aspirated ʰ, …). They are part of
#: the segment, so a proclitic-onset length must not split them off.
_SEGMENT_MODIFIERS = set("ˤʷʲʰˠˀʼ̪̬̥̠̃ː")


def _first_segment_len(ipa: str) -> int:
    """Length in characters of the first phoneme segment of *ipa* — a base
    character plus any modifiers riding on it (``ðˤ`` is two chars, one segment).
    """
    if not ipa:
        return 0
    n = 1
    while n < len(ipa) and ipa[n] in _SEGMENT_MODIFIERS:
        n += 1
    return n


def stress_ipa(
    ipa: str, lang: str = DEFAULT_LANG, proclitic_onset: int = 0,
) -> str:
    """Mark the stressed syllable of one prosodic word of IPA.

    A stretch of IPA with no vowel in it is not a word — it is punctuation the
    assembler carried through, and it has no syllable to stress. Marking it would
    leave a bare stress mark floating next to a full stop.

    ``proclitic_onset`` holds this many leading characters out of the stress
    computation and re-prepends them unmarked. It carries the waṣl-elided
    definite article, which is proclitic: unstressed and outside its host's
    stress domain, so الْيَوم after a vowel is *lˈjawm*, not *ˈljawm*, and
    السُّوق is *sˈsuːɡ* — the stress lands by the host word's weight, exactly as
    orthography2ipa places it (Ryding 2005 §2.10; Watson 2002 ch.3).
    """
    if proclitic_onset:
        head, rest = ipa[:proclitic_onset], ipa[proclitic_onset:]
        return head + stress_ipa(rest, lang)
    if not ipa or not any(is_ipa_vowel(ch) for ch in ipa):
        return ipa
    rules = get(lang).stress
    if rules is None:
        return ipa
    if rules.quantity_sensitive:
        idx = detect_stress_by_weight(ipa, rules)
        # Mark against the SAME phonological division the weights were read off
        # (see orthography2ipa.g2p). The naive ``syllabify`` cuts ``saːliq`` as
        # ``sa|ːliq``, dropping the mark inside the long vowel — ``saˈːliq`` —
        # which is the Vˈː artifact. ``syllabify_ipa`` keeps the length mark on
        # its vowel segment, so the mark lands on the syllable onset.
        return apply_stress_mark(
            ipa, rules, idx,
            ipa_syllables=syllabify_ipa(ipa, rules.max_onset),
        )
    idx = detect_stress(ipa, rules)
    return apply_stress_mark(ipa, rules, idx)


def stress_words(ipa: str, lang: str = DEFAULT_LANG) -> str:
    """Stress each prosodic word of an assembled utterance.

    Applied *after* the sentence is assembled, so a proclitic and its host — which
    connected speech joins into one unit — take one mark between them. That is
    what they are: one phonological word, and one phonological word carries one
    primary stress.
    """
    return " ".join(stress_ipa(w, lang) for w in ipa.split(" "))
