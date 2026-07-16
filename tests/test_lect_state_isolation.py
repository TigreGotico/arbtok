"""A variety's output must not depend on which varieties ran before it.

arbtok caches its compiled per-lect machinery at module scope — the tokenizer +
rescorer chain (``lattice._ENGINES``), the consonant realisations pulled from a
spec (``dialects._CONSONANT_MAPS``), the loanword nativisation tables
(``translit`` LRU caches). Every one of those is keyed by the spec code, so a
call for one lect must never see, reuse, or mutate another lect's entry. If any
of them were keyed too coarsely — or if a rescorer mutated a spec object shared
down an inheritance chain — then transcribing lect B after lect A in the same
process would drift from transcribing it first. That drift is invisible in a
per-lect-isolated run and only shows up in a shared batch, so it needs its own
gate.

The canonical trap is qāf. Rijāl Almaʿ (``ar-SA-x-rijal-alma``) realises
historical *q as VOICED [ɡ] (o2i spec, Alfaifi 2024:177-178 quoting Asiri
2008:72-73); its peninsular parent keeps the conservative [q]. Running the
[q]-retaining and the [ɡ]-shifting lects before it must leave its [ɡ] untouched.
"""
import pytest

from arbtok.lattice import word_ipa
from arbtok.plugin import ArbtokG2PPlugin

RIJAL = "ar-SA-x-rijal-alma"
# A spread of qāf reflexes: MSA/peninsular keep [q]; Najd/Qassim/Gulf shift to
# [ɡ]; qeltu keeps [q]. Whichever ran last must not colour Rijāl Almaʿ.
OTHER_LECTS = ["ar", "ar-x-peninsular", "ar-SA-x-najd", "ar-SA-x-qassim",
               "ar-x-gulf", "ar-IQ-x-qeltu", "ar-EG", "ar-SA-x-hejaz"]

QAF_WORDS = ["قَلَم", "قَال", "حَقِّي", "السُّوق"]


def test_rijal_alma_qaf_is_voiced_g_from_spec():
    """arbtok tracks the o2i spec: Rijāl Almaʿ qāf is [ɡ], not [q]."""
    from orthography2ipa import get

    assert get(RIJAL).graphemes["ق"][0] == "ɡ"
    for w in QAF_WORDS:
        out = word_ipa(w, RIJAL, stress=False)
        assert "ɡ" in out and "q" not in out, f"{w!r} → {out!r}"


@pytest.mark.parametrize("word", QAF_WORDS)
def test_word_ipa_no_cross_lect_state_leak(word):
    """A word's Rijāl Almaʿ transcription is byte-identical before and after a
    mixed-lect batch runs in the same process."""
    fresh = word_ipa(word, RIJAL, stress=False)
    for other in OTHER_LECTS:
        word_ipa(word, other, stress=False)
    after = word_ipa(word, RIJAL, stress=False)
    assert after == fresh, f"{word!r}: {fresh!r} (fresh) != {after!r} (post-batch)"


def test_plugin_transcribe_no_cross_lect_state_leak():
    """The full plugin pipeline is order-independent too: transcribing a
    Rijāl Almaʿ sentence after other lects reproduces the isolated output."""
    sentence = "حَقِّي قَال السُّوق قَلَم"
    rijal = ArbtokG2PPlugin(lang=RIJAL, diacritize=True, nativize=True,
                            pausal=True)
    fresh = rijal.transcribe(sentence)
    for other in OTHER_LECTS:
        ArbtokG2PPlugin(lang=other, diacritize=True, nativize=True,
                        pausal=True).transcribe(sentence)
    after = rijal.transcribe(sentence)
    assert after == fresh, f"{fresh!r} (fresh) != {after!r} (post-batch)"
    assert "q" not in after and "ɡ" in after
