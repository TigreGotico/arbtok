"""``spell_out_plates`` reads a licence plate written in Arabic script by the letters'
names and digit by digit. Left bare, the letters are spoken as a word and the digits
as one cardinal."""
import pytest

from arbtok.textnorm import ARAB_PHONE_REGIONS, IDENTIFIER_WORDS, TtsNorm, normalize_for_tts

VOICE_AGENT = TtsNorm(spell_out_codes=True, speak_percent=True, keep_code_digits=True,
                      phone_regions=ARAB_PHONE_REGIONS, long_digit_runs=True,
                      identifier_words=IDENTIFIER_WORDS, cardinal_numbers=True,
                      leave_unspeakable_numbers=True, oblique_numbers=True, space_fused_hundreds=True,
                      spoken_forms=False, canonical_unicode=False)
# The rule is off by default; a voice agent turns it on. Passed as a flag, so that the
# config above is the rule turned off.
ON = dict(spell_out_plates=True)

PLATES = [
    ("أ ب ج ١٢٣٤", "ألف باء جيم واحد اثنين ثلاثة أربعة"),
    ("س ع د ٥٦٧٨", "سين عين دال خمسة ستة سبعة ثمانية"),
    ("أ ب هـ ١٢٣٤", "ألف باء هاء واحد اثنين ثلاثة أربعة"),
    ("هـ و ى ١٢٣٤", "هاء واو ألف مقصورة واحد اثنين ثلاثة أربعة"),
    ("أ ب ج 1234", "ألف باء جيم واحد اثنين ثلاثة أربعة"),
    ("أ ب ج ١٢ ٣٤", "ألف باء جيم واحد اثنين ثلاثة أربعة"),
]
PLATE_IDS = ["arabic-indic digits", "a name if read bare", "ha printed with a tatweel",
             "tatweel first, alif maqsura", "ascii digits", "spaced digits"]


@pytest.mark.parametrize("written, said", PLATES, ids=PLATE_IDS)
def test_a_plate_reads_its_letters_by_name_and_its_digits_one_by_one(written, said):
    assert normalize_for_tts(written, **ON) == said
    assert normalize_for_tts(written, "ar", VOICE_AGENT, **ON) == said


@pytest.mark.parametrize("written, said", PLATES, ids=PLATE_IDS)
def test_a_plates_reading_is_read_again_unchanged(written, said):
    assert normalize_for_tts(said, "ar", VOICE_AGENT, **ON) == said
    assert normalize_for_tts(said, **ON) == said


def test_a_plate_inside_a_sentence():
    assert normalize_for_tts("رقم اللوحة ر ك ب 530 جاهزة", "ar", VOICE_AGENT, **ON) == \
        "رقم اللوحة راء كاف باء خمسة ثلاثة صفر جاهزة"


@pytest.mark.parametrize("written, said", [
    ("(أ ب ج ١٢٣٤)", "(ألف باء جيم واحد اثنين ثلاثة أربعة)"),
    ("«أ ب ج ١٢٣٤»", "«ألف باء جيم واحد اثنين ثلاثة أربعة»"),
    ("اللوحة:أ ب ج ١٢٣٤", "اللوحة:ألف باء جيم واحد اثنين ثلاثة أربعة"),
], ids=["parentheses", "guillemets", "after a colon"])
def test_a_plate_after_opening_punctuation_is_read_whole(written, said):
    assert normalize_for_tts(written, "ar", VOICE_AGENT, **ON) == said


def test_two_plates_joined_by_waw_are_both_read():
    assert normalize_for_tts("رقمها أ ب ج ١٢٣٤ و د ر س ٥٦٧٨", "ar", VOICE_AGENT, **ON) == \
        "رقمها ألف باء جيم واحد اثنين ثلاثة أربعة و دال راء سين خمسة ستة سبعة ثمانية"


@pytest.mark.parametrize("written, said", [
    ("ص ب 1234 الرياض 11564", "ص ب ألف ومئتين وأربعة وثلاثين الرياض أحد عشر ألف وخمس مئة وأربعة وستين"),
    ("ص ب ٢٢٢٣ جدة", "ص ب ألفين ومئتين وثلاثة وعشرين جدة"),
    ("ط ق 123", "ط ق مئة وثلاثة وعشرين"),
], ids=["a post office box", "a post office box in arabic-indic digits", "two letters, ascii digits"])
def test_two_letters_before_a_number_are_no_plate(written, said):
    assert normalize_for_tts(written, "ar", VOICE_AGENT, **ON) == said


@pytest.mark.parametrize("written, said", [
    ("الباقة أ 1450 ريال", "الباقة أ ألف وأربع مئة وخمسين ريال"),
    ("السعر و 1500 ريال", "السعر و ألف وخمس مئة ريال"),
    ("ألف ١٢٣٤", "ألف ألف ومئتين وأربعة وثلاثين"),
], ids=["an option label", "the conjunction", "a letter's name"])
def test_a_single_letter_or_a_letter_name_before_a_number_is_no_plate(written, said):
    assert normalize_for_tts(written, "ar", VOICE_AGENT, **ON) == said


@pytest.mark.parametrize("written", [
    "أ  ب ج ١٢٣٤",
    "أ ب ج  ١٢٣٤",
    "أ ب  ج ١٢٣٤",
    "أ ب ج د ١٢٣٤",
    "أ ب ج 12345",
    "أ ب ج 1234.5",
    "أ ب ج 1234 5678",
    "ا ب ح ١٢",
    "أ ب ج ١٢٣٤ريال",
    "ء ب ج د ١٢٣٤",
    "ة ب ج د ١٢٣٤",
    "ـ ب ج د 1234",
    "ق م 2024",
    "بقيمة أ ب 300 ريال",
], ids=["doubled space after the first letter", "doubled space before the digits",
        "doubled space between letters", "four letters", "five digits", "a decimal",
        "two digit groups", "two digits", "digits run into a word", "hamza before three letters",
        "ta marbuta before three letters", "tatweel before three letters", "two letters before a year",
        "two letters before a price"])
def test_what_is_not_a_plate_reads_as_it_does_without_the_rule(written):
    said = normalize_for_tts(written, "ar", VOICE_AGENT, **ON)
    assert said == normalize_for_tts(written, "ar", VOICE_AGENT, spell_out_plates=False)
    assert "باء" not in said


def test_a_digit_only_lexicon_term_does_not_take_a_plates_digits():
    config = VOICE_AGENT.with_lexicon({"530": "فايف ثيرتي"})
    assert normalize_for_tts("رقم اللوحة ر ك ب 530", "ar", config, **ON) == "رقم اللوحة راء كاف باء خمسة ثلاثة صفر"
    assert normalize_for_tts("BMW 530", "ar", config, **ON) == "بِي إِمْ دَبَلْيُو فايف ثيرتي"


@pytest.mark.parametrize("term, said", [("G70", "جي سيفنتي"), ("GV80", "جي في إيتي"), ("X5", "اكس فايف")])
def test_a_digit_bearing_model_code_still_reads_through_the_lexicon(term, said):
    config = VOICE_AGENT.with_lexicon({term: said})
    assert normalize_for_tts(term, "ar", config, **ON) == said
    assert normalize_for_tts(f"سيارة {term} لوحتها أ ب ج 1234", "ar", config, **ON) == \
        f"سيارة {said} لوحتها ألف باء جيم واحد اثنين ثلاثة أربعة"


def test_a_plates_digits_take_the_callers_digit_words():
    config = VOICE_AGENT.with_number_forms({2: "اتنين"})
    assert normalize_for_tts("أ ب ج 1234", "ar", config, **ON) == "ألف باء جيم واحد اتنين ثلاثة أربعة"


def test_the_rule_is_arabic_only():
    assert normalize_for_tts("أ ب ج ١٢٣٤", "en", spoken_forms=False, **ON) == "أ ب ج ١٢٣٤"


def test_the_rule_is_off_by_default():
    assert normalize_for_tts("أ ب ج ١٢٣٤") == normalize_for_tts("أ ب ج ١٢٣٤", "ar", spell_out_plates=False)
    assert normalize_for_tts("أ ب ج ١٢٣٤").startswith("أ ب ج ")
