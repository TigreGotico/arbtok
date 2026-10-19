"""Model codes written in the shapes BMW and Mazda print them: a small letter before the
capitals, ``iX3``; a small letter after the digits, ``520i``; a hyphen, ``CX-5``; and a
lexicon reading with a digit written against its letters, ``أتش1``. Each is read the way
the plain code is, character by character with English names, and never reaches the
synthesizer as digits. A tatweel between a proclitic and a term read in Arabic is dropped."""
import pytest

from arbtok.textnorm import ARAB_PHONE_REGIONS, IDENTIFIER_WORDS, TtsNorm, bundled_tts_lexicon, normalize_for_tts

VOICE_AGENT = TtsNorm(spell_out_codes=True, speak_percent=True, keep_code_digits=True,
                      phone_regions=ARAB_PHONE_REGIONS, long_digit_runs=True,
                      identifier_words=IDENTIFIER_WORDS, cardinal_numbers=True,
                      leave_unspeakable_numbers=True, oblique_numbers=True, space_fused_hundreds=True,
                      spoken_forms=False, canonical_unicode=False)
UNSPELLED = TtsNorm(cardinal_numbers=True, oblique_numbers=True, identifier_words=IDENTIFIER_WORDS,
                    spoken_forms=False, canonical_unicode=False)


@pytest.mark.parametrize("written, said", [
    ("iX3", "آيْ إِكْسْ ثْرِي"),
    ("iX1 و iX3", "آيْ إِكْسْ وَنْ و آيْ إِكْسْ ثْرِي"),
    ("iX 3", "آيْ إِكْسْ ثْرِي"),
], ids=["joined", "two", "spaced, as it already was"])
def test_a_small_letter_before_the_capitals_is_part_of_the_code(written, said):
    assert normalize_for_tts(written, "ar", VOICE_AGENT) == said


@pytest.mark.parametrize("written", ["iPhone15", "eSIM", "iX", "abX35"], ids=["word", "no digit", "no digit, two",
                                                                         "two small letters"])
def test_a_small_letter_before_what_is_not_a_code_is_left(written):
    assert normalize_for_tts(written, "ar", VOICE_AGENT) == written


@pytest.mark.parametrize("written, said", [
    ("520i", "فَيْفْ تُو زِيرُو آيْ"),
    ("M340i", "إِمْ ثْرِي فُورْ زِيرُو آيْ"),
    ("330e", "ثْرِي ثْرِي زِيرُو إِي"),
    ("E300d", "إِي ثْرِي زِيرُو زِيرُو دِي"),
    ("عندنا 520i فل كامل", "عندنا فَيْفْ تُو زِيرُو آيْ فل كامل"),
], ids=["520i", "M340i", "330e", "E300d", "in a sentence"])
def test_a_small_suffix_letter_after_the_digits_is_spelled_with_the_code(written, said):
    assert normalize_for_tts(written, "ar", VOICE_AGENT) == said


@pytest.mark.parametrize("written", ["1990s", "5k", "100x", "2.5i", "40000i"],
                         ids=["a decade", "one digit", "another letter", "a decimal", "five digits"])
def test_what_does_not_carry_a_model_suffix_is_not_spelled(written):
    said = normalize_for_tts(written, "ar", VOICE_AGENT)
    assert "آيْ" not in said and "زِيرُو" not in said, said


def test_a_lexicon_reading_of_the_suffixed_code_still_wins():
    config = VOICE_AGENT.with_lexicon({"520i": "خمس مية وعشرين آي"})
    assert normalize_for_tts("BMW 520i", "ar", config) == "بِي إِمْ دَبَلْيُو خمس مية وعشرين آي"


@pytest.mark.parametrize("written", ["CX-5", "F-150", "GV-70", "مازدا CX-30 متوفرة"])
def test_a_hyphenated_code_left_unspelled_keeps_its_digits_whole(written):
    assert normalize_for_tts(written, "ar", UNSPELLED) == written


def test_an_amount_after_a_currency_code_and_a_hyphen_is_still_a_number():
    assert normalize_for_tts("السعر SAR-50", "ar", UNSPELLED) == "السعر SAR-خمسين"


@pytest.mark.parametrize("written, said", [
    ("هيونداي H1 للعائلة", "هيونداي أتش وَنْ للعائلة"),
    ("GRAND I10", "جراند آي وَنْ زِيرُو"),
], ids=["H1", "GRAND I10"])
def test_a_digit_in_a_lexicon_reading_takes_the_code_digit_name_apart_from_its_letters(written, said):
    config = VOICE_AGENT.with_lexicon(bundled_tts_lexicon("cars-sa"))
    out = normalize_for_tts(written, "ar", config)
    assert out == said
    assert not any(c.isdigit() for c in out)


@pytest.mark.parametrize("written, said", [
    ("خصم للـNissan", "خصم للنيسان"),
    ("بالـHyundai", "بالهيونداي"),
    ("للـــNissan", "للنيسان"),
], ids=["lil", "bil", "a long tatweel"])
def test_a_tatweel_before_a_term_read_in_arabic_is_dropped(written, said):
    config = VOICE_AGENT.with_lexicon(bundled_tts_lexicon("cars-sa"))
    assert normalize_for_tts(written, "ar", config) == said


@pytest.mark.parametrize("written, said", [
    ("بـX5", "بإِكْسْ فَيْفْ"),
    ("للـBMW", "للبِي إِمْ دَبَلْيُو"),
], ids=["X5", "BMW"])
def test_a_tatweel_before_a_spelled_code_is_dropped(written, said):
    assert normalize_for_tts(written, "ar", VOICE_AGENT) == said


@pytest.mark.parametrize("written", ["خصم للـ Nissan", "الـ السيارة", "بـ 75 ألف"],
                         ids=["a space after it", "a false start", "a number"])
def test_a_tatweel_not_written_against_a_term_stays(written):
    config = VOICE_AGENT.with_lexicon(bundled_tts_lexicon("cars-sa"))
    assert "ـ" in normalize_for_tts(written, "ar", config, drop_false_starts=False)


def test_the_default_config_is_unchanged_for_these_shapes():
    """The G2P plugin's config spells no code, so these shapes read as they always did."""
    assert normalize_for_tts("مازدا CX-5 متوفرة") == "مازدا CX خمسة متوفرة"
    assert normalize_for_tts("BMW iX3") == "BMW iX3"
