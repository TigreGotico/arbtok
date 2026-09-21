"""``spell_out_codes`` reads a vehicle identification number as an identifier: letters
by their English names from the bundled table, digits by the Arabic words of a
digit-by-digit reading. A model code keeps the English names for its digits."""
import pytest

from arbtok.textnorm import TtsNorm, normalize_for_tts
from arbtok.tokenizer import normalize_unicode

AS_WRITTEN = dict(spoken_forms=False, canonical_unicode=False)

# The VIN of the salesteq-cs-webrtc parity fixture row parity-token_canonicalization-079.
PARITY_ROW = "رقم الهيكل WBA7F2C51JG على X5 موديل 2026."
PARITY_VIN = "دَبَلْيُو بِي إِي سبعة إِفْ اثنين سِي خمسة واحد جِيْ جِي"


def test_the_parity_fixture_vin_reads_its_digits_as_arabic_words():
    said = normalize_for_tts(PARITY_ROW, spell_out_codes=True)
    assert normalize_unicode(PARITY_VIN) in said
    assert "WBA7F2C51JG" not in said


def test_the_parity_fixture_vin_as_written():
    assert normalize_for_tts("رقم الهيكل WBA7F2C51JG", spell_out_codes=True, **AS_WRITTEN) == \
        "رقم الهيكل " + PARITY_VIN


def test_a_seventeen_character_vin():
    said = normalize_for_tts("الشاسيه 1M8GDM9AXKP042788 جاهز", spell_out_codes=True, **AS_WRITTEN)
    assert said == ("الشاسيه واحد إِمْ ثمانية جِي دِي إِمْ تسعة إِي إِكْسْ كِيْ بِي"
                    " صفر أربعة اثنين سبعة ثمانية ثمانية جاهز")


def test_an_eight_character_fragment():
    said = normalize_for_tts("آخر ثمانية L457L680", spell_out_codes=True, **AS_WRITTEN)
    assert said == "آخر ثمانية إِلْ أربعة خمسة سبعة إِلْ ستة ثمانية صفر"


def test_a_vin_takes_the_callers_digit_words():
    config = TtsNorm(spell_out_codes=True).with_number_forms({2: "اتنين"})
    said = normalize_for_tts("L457L682", "ar", config, **AS_WRITTEN)
    assert said == "إِلْ أربعة خمسة سبعة إِلْ ستة ثمانية اتنين"


@pytest.mark.parametrize("written, read", [
    ("X5", "إِكْسْ فَيْفْ"),
    ("GLE450", "جِي إِلْ إِي فُورْ فَيْفْ زِيرُو"),
    ("ABC1234", "إِي بِي سِي وَنْ تُو ثْرِي فُورْ"),
    ("BMW", "بِي إِمْ دَبَلْيُو"),
    ("ABCDEFGHJKLMN", "إِي بِي سِي دِي إِي إِفْ جِي إِيشْ جِيْ كِيْ إِلْ إِمْ إِنْ"),
    ("WBA7F2C51JG1234567", "دَبَلْيُو بِي إِي سِفَنْ إِفْ تُو سِي فَيْفْ وَنْ جِيْ جِي"
                           " وَنْ تُو ثْرِي فُورْ فَيْفْ سِكْسْ سِفَنْ"),
], ids=["X5", "GLE450", "seven", "BMW", "letters-only", "eighteen"])
def test_what_is_not_a_vin_keeps_the_code_reading(written, read):
    assert normalize_for_tts(written, spell_out_codes=True, **AS_WRITTEN) == read


@pytest.mark.parametrize("written", ["530i", "1234567890", "wba7f2c51jg", "service"])
def test_what_is_not_a_code_is_left_as_written(written):
    assert normalize_for_tts(written, spell_out_codes=True, **AS_WRITTEN) == written
