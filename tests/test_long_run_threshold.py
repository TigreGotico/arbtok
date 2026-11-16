"""A run of ten or more unseparated digits is read digit by digit, unless it is round."""
import pytest

from arbtok.textnorm import TtsNorm, normalize_for_tts

RUNS = TtsNorm(long_digit_runs=True, cardinal_numbers=True, spoken_forms=False, canonical_unicode=False)
DIGITS = "واحد اثنين ثلاثة أربعة خمسة ستة سبعة ثمانية تسعة صفر"


@pytest.mark.parametrize("written, spoken", [
    ("رقم الطلب 1234567890", f"رقم الطلب {DIGITS}"),
    ("1234567890", DIGITS),
    ("١٢٣٤٥٦٧٨٩٠", DIGITS),
    ("+1234567890", DIGITS),
])
def test_ten_digits_are_read_one_by_one(written, spoken):
    assert normalize_for_tts(written, "ar", RUNS) == spoken


@pytest.mark.parametrize("written", ["4000000000", "٤٠٠٠٠٠٠٠٠٠", "1250000000"])
def test_a_round_run_stays_a_quantity(written):
    said = normalize_for_tts(written, "ar", RUNS)
    assert "مليار" in said and "صفر" not in said, said


@pytest.mark.parametrize("written", ["123456789", "1,234,567,890"])
def test_nine_digits_and_separated_numbers_stay_cardinals(written):
    said = normalize_for_tts(written, "ar", RUNS)
    assert "صفر" not in said and not any(c.isdigit() for c in said), said


def test_off_by_default():
    assert "مليار" in normalize_for_tts("1234567890", "ar", TtsNorm(cardinal_numbers=True, spoken_forms=False))
