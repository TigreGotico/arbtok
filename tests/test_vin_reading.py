"""``spell_out_codes`` reads a vehicle identification number as an identifier: letters
by their English names from the bundled table, digits by the Arabic words of a
digit-by-digit reading. A model code keeps the English names for its digits."""
import pytest

from arbtok import textnorm
from arbtok.textnorm import TtsNorm, cldr_units, normalize_for_tts, spelled_codes
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
    ("WBA7F2C51JG1234567", "دَبَلْيُو بِي إِي سِفَنْ إِفْ تُو سِي فَيْفْ وَنْ جِيْ جِي"
                           " وَنْ تُو ثْرِي فُورْ فَيْفْ سِكْسْ سِفَنْ"),
], ids=["X5", "GLE450", "seven", "BMW", "eighteen"])
def test_what_is_not_a_vin_keeps_the_code_reading(written, read):
    assert normalize_for_tts(written, spell_out_codes=True, **AS_WRITTEN) == read


# A run of capitals with no vowel in it is an initialism and is read letter by letter.
# A run of capitals that spells a word is a word. Neither list carries a digit.
INITIALISMS = ["BMW", "GMC", "MG", "GT", "RS"]
WORDS = ["تويوتا TOYOTA", "FORD", "KIA", "AUDI", "GENESIS",
         "LAND ROVER DEFENDER", "HYUNDAI TUCSON", "MINI COOPER S"]
# One published reading of a whole model name, as a consumer carries it.
SERIES = {"BMW 7 Series": "بِي إِمْ دَبَلْيُو سِفَنْ سِيرِيزْ"}


@pytest.mark.parametrize("written", WORDS)
def test_a_run_of_capitals_that_spells_a_word_is_not_a_code(written):
    assert normalize_for_tts(written, spell_out_codes=True, **AS_WRITTEN) == written


@pytest.mark.parametrize("written", INITIALISMS)
def test_a_vowelless_run_of_capitals_is_read_letter_by_letter(written):
    names = spelled_codes("ar")
    assert normalize_for_tts(written, spell_out_codes=True, **AS_WRITTEN) == \
        " ".join(names[c] for c in written)


@pytest.mark.parametrize("written, read", [
    ("GENESIS G80", "GENESIS جِي إِيتْ زِيرُو"),
    ("X5", "إِكْسْ فَيْفْ"),
    ("L809UPZ3V361", "إِلْ ثمانية صفر تسعة يُو بِي زِدْ ثلاثة فِي ثلاثة ستة واحد"),
], ids=["G80", "X5", "L809UPZ3V361"])
def test_a_run_with_a_digit_is_still_read_character_by_character(written, read):
    assert normalize_for_tts(written, spell_out_codes=True, **AS_WRITTEN) == read


def test_a_lexicon_entry_claims_a_model_name_before_the_code_reading():
    config = TtsNorm(spell_out_codes=True).with_lexicon(SERIES)
    assert normalize_for_tts("سيارة BMW 7 SERIES", "ar", config, **AS_WRITTEN) == \
        "سيارة " + SERIES["BMW 7 Series"]


# An initialism that carries a vowel spells a word as far as this rule can tell, so it
# is left whole. The lexicon is how a consumer has it spelled.
VOWEL_INITIALISMS = ["SUV", "VIN", "ABS"]


@pytest.mark.parametrize("written", VOWEL_INITIALISMS)
def test_an_initialism_that_carries_a_vowel_is_left_whole(written):
    assert normalize_for_tts(written, spell_out_codes=True, **AS_WRITTEN) == written


def test_a_lexicon_entry_spells_what_the_vowel_leaves_whole():
    names = spelled_codes("ar")
    said = " ".join(names[c] for c in "SUV")
    config = TtsNorm(spell_out_codes=True).with_lexicon({"SUV": said})
    assert normalize_for_tts("سيارة SUV", "ar", config, **AS_WRITTEN) == "سيارة " + said


@pytest.mark.parametrize("written, read", [
    ("المسافة 50 KM", "المسافة خمسون كيلومتر"),
    ("الوزن 5 KG", "الوزن خمسة كيلوغرام"),
], ids=["KM", "KG"])
def test_a_unit_symbol_in_capitals_after_a_number_is_a_unit(written, read):
    assert normalize_for_tts(written, "ar", spell_out_codes=True) == read


# MG spells no word, so it is the make and is read letter by letter. EV carries a
# vowel, so it is a word and is left as written for the lexicon to claim; what neither
# is, is the milligram or the electronvolt its letters also spell.
@pytest.mark.parametrize("written, read", [
    ("عندنا 3 MG متوفرة", "عندنا ثلاثة إِمْ جِي متوفرة"),
    ("عندنا 2 EV متوفرة", "عندنا اثنان EV متوفرة"),
], ids=["MG", "EV"])
def test_a_make_is_not_a_unit_because_a_unit_shares_its_letters(written, read):
    assert normalize_for_tts(written, "ar", spell_out_codes=True) == read


def test_a_symbol_the_table_writes_in_capitals_is_still_a_unit():
    assert normalize_for_tts("الذاكرة 2 GB", "ar", spell_out_codes=True) == "الذاكرة اثنان غيغابايت"


@pytest.mark.parametrize("written, read", [
    ("عندنا 3 mg متوفرة", "عندنا ثلاثة مليغرام متوفرة"),
    ("عندنا 2 ev متوفرة", "عندنا اثنان إلكترون فولت متوفرة"),
], ids=["mg", "ev"])
def test_the_same_symbol_in_lowercase_is_the_unit(written, read):
    assert normalize_for_tts(written, "ar", spell_out_codes=True) == read


def test_every_capitalised_unit_symbol_is_one_the_unit_table_reads():
    units = {symbol.lower() for symbol in cldr_units("ar")}
    assert set(textnorm._CAPITALISED_UNITS) <= units


@pytest.mark.parametrize("written", ["530i", "1234567890", "wba7f2c51jg", "service",
                                     "ABCDEFGHJKLMN"])
def test_what_is_not_a_code_is_left_as_written(written):
    assert normalize_for_tts(written, spell_out_codes=True, **AS_WRITTEN) == written
