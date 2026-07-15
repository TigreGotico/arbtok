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


def stress_ipa(ipa: str, lang: str = DEFAULT_LANG) -> str:
    """Mark the stressed syllable of one prosodic word of IPA.

    A stretch of IPA with no vowel in it is not a word — it is punctuation the
    assembler carried through, and it has no syllable to stress. Marking it would
    leave a bare stress mark floating next to a full stop.
    """
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
