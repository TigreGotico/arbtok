"""A Saudi mobile number is read digit by digit under KSA_VOICE_AGENT, and a date that
begins like one is not."""
import pytest

from arbtok.textnorm import KSA_VOICE_AGENT, normalize_for_tts

MOBILE = "صفر خمسة صفر واحد اثنين ثلاثة أربعة خمسة ستة سبعة"
INTERNATIONAL = "تسعة ستة ستة خمسة صفر واحد اثنين ثلاثة أربعة خمسة ستة سبعة"


@pytest.mark.parametrize("written", [
    "بتاريخ 05-06-2024",
    "بتاريخ 05 06 2024",
    "بتاريخ 05-21-2024",
    "بتاريخ 05-06-2024 12:30",
    "بتاريخ 05 06 2024 10 30",
])
def test_a_date_on_the_fifth_is_not_read_digit_by_digit(written):
    # A digit-by-digit reading says the leading zero; the date's numbers never do.
    assert "صفر" not in normalize_for_tts(written, "ar", KSA_VOICE_AGENT)


@pytest.mark.parametrize("written, said", [
    ("0501234567", MOBILE),
    ("050 123 4567", MOBILE),
    ("050-123-4567", MOBILE),
    ("050 - 123 - 4567", MOBILE),
    ("اتصل على 0501234567.", f"اتصل على {MOBILE}."),
    ("+966501234567", INTERNATIONAL),
    ("+966 50 123 4567", INTERNATIONAL),
    ("+966-50-123-4567", INTERNATIONAL),
    ("966 50 123 4567", INTERNATIONAL),
    ("00966 50 123 4567", "صفر صفر " + INTERNATIONAL),
])
def test_a_saudi_mobile_number_is_read_digit_by_digit(written, said):
    assert normalize_for_tts(written, "ar", KSA_VOICE_AGENT) == said


def test_a_mobile_number_ends_at_its_tenth_digit():
    said = normalize_for_tts("0501234567 12 ريال", "ar", KSA_VOICE_AGENT)
    assert said.startswith(MOBILE + " ") and "واحد اثنين ريال" not in said
