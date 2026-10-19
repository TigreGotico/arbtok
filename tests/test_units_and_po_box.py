"""``colloquial_units`` says a kilometre after a number the way Saudi speech says it,
``كيلو``, whether it is written ``km`` or ``كم``; and the post office box, ``ص ب``, is
read as ``صندوق بريد`` wherever the cardinals speak its number."""
import dataclasses

import pytest

from arbtok.textnorm import ARAB_PHONE_REGIONS, IDENTIFIER_WORDS, TtsNorm, normalize_for_tts

VOICE_AGENT = TtsNorm(spell_out_codes=True, speak_percent=True, keep_code_digits=True,
                      phone_regions=ARAB_PHONE_REGIONS, long_digit_runs=True,
                      identifier_words=IDENTIFIER_WORDS, cardinal_numbers=True,
                      leave_unspeakable_numbers=True, oblique_numbers=True, space_fused_hundreds=True,
                      spoken_forms=False, canonical_unicode=False)
UNITS = dataclasses.replace(VOICE_AGENT, colloquial_units=True)


@pytest.mark.parametrize("written, said", [
    ("الصيانة كل 10000 كم", "الصيانة كل عشرة آلاف كيلو"),
    ("الصيانة كل 10000 km", "الصيانة كل عشرة آلاف كيلو"),
    ("الصيانة كل 10000km", "الصيانة كل عشرة آلاف كيلو"),
    ("ماشية 45,000 KM", "ماشية خمسة وأربعين ألف كيلو"),
    ("المسافة ٢٥ كم", "المسافة خمسة وعشرين كيلو"),
    ("100كم", "مئة كيلو"),
    ("السرعة 120 km/h", "السرعة مئة وعشرين كيلو بالساعة"),
    ("السرعة 120km/h", "السرعة مئة وعشرين كيلو بالساعة"),
], ids=["arabic", "latin", "latin glued", "capitals", "arabic-indic digits", "arabic glued", "per hour",
        "per hour glued"])
def test_a_kilometre_after_a_number_is_said_kilo(written, said):
    assert normalize_for_tts(written, "ar", UNITS) == said


@pytest.mark.parametrize("written", ["كم سعرها؟", "بكم السيارة", "كم عمرك 30", "عندي كمية 5", "5 كمية",
                                     "عندنا kmart", "5 kms", "MG5 كم صافي بعد الخصم؟", "سعر HS 2026 كم؟",
                                     "MG RX5 كم تعطوني اياها؟", "X5 2024 كم سعرها", "كامري 2024 كم؟",
                                     "موديل 2024 كم سعرها؟", "السيارة 2024 كم ممشاها؟", "عندي 3 كم سؤال",
                                     "سعرها 90 كم؟", "عندنا ٥ كم لون"],
                         ids=["a question", "a clitic", "before a number", "a word", "a word after a number",
                              "a latin word", "a plural", "after a code", "after a model and its year",
                              "after a spaced code", "after a code and a year", "after a year, a question mark",
                              "after a year, a price question", "after a year, a mileage question",
                              "before a noun", "before a question mark", "arabic-indic digits before a noun"])
def test_kam_and_km_that_are_not_a_kilometre_after_a_number_are_left(written):
    assert normalize_for_tts(written, "ar", UNITS) == normalize_for_tts(written, "ar", VOICE_AGENT)


@pytest.mark.parametrize("written, said", [
    ("المسافة 50 كم من الفرع", "المسافة خمسين كيلو من الفرع"),
    ("ماشية 30 كم بس", "ماشية ثلاثين كيلو بس"),
    ("بين 100 كم و 200 كم.", "بين مئة كيلو و مئتين كيلو."),
    ("الصيانة كل 5000 كم، والزيت كل 10000 كم", "الصيانة كل خمسة آلاف كيلو، والزيت كل عشرة آلاف كيلو"),
], ids=["a preposition after it", "بس after it", "و and a full stop", "a comma"])
def test_kam_before_what_follows_a_distance_is_a_kilometre(written, said):
    assert normalize_for_tts(written, "ar", UNITS) == said


def test_the_rule_is_off_by_default():
    assert normalize_for_tts("10000 كم", "ar", VOICE_AGENT) == "عشرة آلاف كم"
    assert normalize_for_tts("10000 كم") == normalize_for_tts("10000 كم", colloquial_units=False)


def test_a_lexicon_reading_of_the_symbol_wins():
    config = UNITS.with_lexicon({"km": "كيلومتر"})
    assert normalize_for_tts("50 km", "ar", config) == "خمسين كيلومتر"


def test_the_rule_is_arabic_only():
    with pytest.raises(ValueError):
        normalize_for_tts("50 km", "en", colloquial_units=True)


def test_a_kilometre_reading_is_read_again_unchanged():
    said = normalize_for_tts("الصيانة كل 10000 كم", "ar", UNITS)
    assert normalize_for_tts(said, "ar", UNITS) == said


@pytest.mark.parametrize("written, said", [
    ("ص ب 1234", "صندوق بريد ألف ومئتين وأربعة وثلاثين"),
    ("ص.ب 1234", "صندوق بريد ألف ومئتين وأربعة وثلاثين"),
    ("ص. ب. 1234", "صندوق بريد ألف ومئتين وأربعة وثلاثين"),
    ("ص.ب: 1234", "صندوق بريد: ألف ومئتين وأربعة وثلاثين"),
    ("العنوان (ص ب ٧٧)", "العنوان (صندوق بريد سبعة وسبعين)"),
], ids=["spaced", "dotted", "dotted and spaced", "a colon", "in parentheses"])
def test_the_post_office_box_is_read_before_its_number(written, said):
    assert normalize_for_tts(written, "ar", VOICE_AGENT) == said


@pytest.mark.parametrize("written", ["ص ب", "ص بس 5", "الساعة 10 ص بالضبط", "نص ب 5", "ص ب ج 1234",
                                     "ح ص ب 1234", "رقم اللوحة أ ص ب ٥٦٧٨", "ح ص ب1234", "الساعة 9 ص ب 50 ريال"],
                         ids=["no number", "a word", "the morning", "inside a word", "a plate",
                              "the end of a plate", "the end of a plate after its word", "an unspaced plate",
                              "the morning before a price"])
def test_what_is_not_a_post_office_box_before_a_number_is_left(written):
    assert "صندوق" not in normalize_for_tts(written, "ar", VOICE_AGENT)


def test_the_post_office_box_needs_the_numbers_spoken():
    assert normalize_for_tts("ص ب 1234", "ar", spoken_forms=False, canonical_unicode=False) == "ص ب 1234"


def test_the_post_office_box_after_the_conjunction_is_read():
    assert normalize_for_tts("العنوان الرياض و ص ب 77", "ar", VOICE_AGENT) == "العنوان الرياض و صندوق بريد سبعة وسبعين"
