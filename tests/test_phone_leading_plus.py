"""A leading + goes with the digits it belongs to, on every rule that reads a phone number."""
import pytest

from arbtok import textnorm
from arbtok.textnorm import KSA_VOICE_AGENT, TtsNorm, normalize_for_tts

ALGERIA = "اثنين واحد ثلاثة ستة ستة واحد اثنين ثلاثة أربعة خمسة ستة سبعة"
SAUDI = "تسعة ستة ستة خمسة صفر واحد اثنين ثلاثة أربعة خمسة ستة سبعة"
ALONE = dict(spoken_forms=False, canonical_unicode=False)


@pytest.mark.parametrize("config", [
    KSA_VOICE_AGENT,
    TtsNorm(long_digit_runs=True, **ALONE),
    TtsNorm(phone_prefixes=textnorm.KSA_PHONE_PREFIXES, **ALONE),
], ids=["voice-agent", "long_digit_runs", "phone_prefixes"])
@pytest.mark.parametrize("written, said", [
    ("اتصل على +213661234567", f"اتصل على {ALGERIA}"),
    ("اتصل على +966501234567", f"اتصل على {SAUDI}"),
], ids=["algeria", "saudi"])
def test_a_leading_plus_is_dropped_with_the_digits_read(config, written, said):
    assert normalize_for_tts(written, "ar", config) == said


def test_a_plus_is_dropped_by_the_shape_and_the_identifier_word_too():
    assert normalize_for_tts("+966 50 123 4567", "ar", TtsNorm(phone_shapes=textnorm.KSA_PHONE_SHAPES, **ALONE)) == SAUDI
    assert normalize_for_tts("رقمي +2136612", "ar", TtsNorm(identifier_words=textnorm.IDENTIFIER_WORDS, **ALONE)) \
        == "رقمي اثنين واحد ثلاثة ستة ستة واحد اثنين"


def test_a_plus_that_is_not_before_a_phone_number_stays():
    assert "+" in normalize_for_tts("2+2", "ar", KSA_VOICE_AGENT)


def test_a_digit_run_after_an_eastern_digit_is_read_as_after_a_western_one():
    """The run's lookbehind sees Arabic-Indic digits too, so the plus between them
    is not taken as the run's own and the two readings stay apart."""
    eastern = normalize_for_tts("الرقم ٥+12345678901", "ar", KSA_VOICE_AGENT)
    western = normalize_for_tts("الرقم 5+12345678901", "ar", KSA_VOICE_AGENT)
    assert eastern == western
    assert "خمسةواحد" not in eastern
