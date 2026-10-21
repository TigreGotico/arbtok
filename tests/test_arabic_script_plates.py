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
    ("هـ و ى ١٢٣٤", "هاء واو ياء واحد اثنين ثلاثة أربعة"),
    ("أ ب ج 1234", "ألف باء جيم واحد اثنين ثلاثة أربعة"),
    ("أ ب ج ١٢ ٣٤", "ألف باء جيم واحد اثنين ثلاثة أربعة"),
]
PLATE_IDS = ["arabic-indic digits", "a name if read bare", "ha printed with a tatweel",
             "tatweel first, the dotless ya", "ascii digits", "spaced digits"]


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
    ("ص ب 1234 الرياض 11564", "صندوق بريد ألف ومئتين وأربعة وثلاثين الرياض أحد عشر ألف وخمس مئة وأربعة وستين"),
    ("ص ب ٢٢٢٣ جدة", "صندوق بريد ألفين ومئتين وثلاثة وعشرين جدة"),
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
    "أ ب ج ١٢٣٤ريال",
    "ء ب ج د ١٢٣٤",
    "ة ب ج د ١٢٣٤",
    "ـ ب ج د 1234",
    "ق م 2024",
    "بقيمة أ ب 300 ريال",
], ids=["doubled space after the first letter", "doubled space before the digits",
        "doubled space between letters", "four letters", "five digits", "a decimal",
        "two digit groups", "digits run into a word", "hamza before three letters",
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


@pytest.mark.parametrize("written, said", [
    ("ن ى ى ٤٢٦٦", "نون ياء ياء أربعة اثنين ستة ستة"),
    ("ى ى ى 1111", "ياء ياء ياء واحد واحد واحد واحد"),
], ids=["two of them", "all three"])
def test_the_dotless_ya_of_a_plate_is_named_ya(written, said):
    """The plate prints ي without its dots; ألف مقصورة names a different letter."""
    said_now = normalize_for_tts(written, "ar", VOICE_AGENT, **ON)
    assert said_now == said
    assert "مقصورة" not in said_now


@pytest.mark.parametrize("written, said", [
    ("أ ب ج 12", "ألف باء جيم واحد اثنين"),
    ("ا ب ح ١٢", "ألف باء حاء واحد اثنين"),
    ("هـ و ى 7", "هاء واو ياء سبعة"),
    ("رقم اللوحة ر س ع ٥٦٧", "رقم اللوحة راء سين عين خمسة ستة سبعة"),
], ids=["two digits", "two arabic-indic digits", "one digit", "three digits"])
def test_a_plate_of_fewer_than_four_digits_is_read_digit_by_digit(written, said):
    assert normalize_for_tts(written, "ar", VOICE_AGENT, **ON) == said


@pytest.mark.parametrize("written, said", [
    ("أ ب ج - 1234", "ألف باء جيم واحد اثنين ثلاثة أربعة"),
    ("أ ب ج-1234", "ألف باء جيم واحد اثنين ثلاثة أربعة"),
    ("أ ب ج – ١٢٣٤", "ألف باء جيم واحد اثنين ثلاثة أربعة"),
], ids=["spaced hyphen", "hyphen", "en dash"])
def test_a_dash_between_the_letters_and_the_digits_is_not_read(written, said):
    assert normalize_for_tts(written, "ar", VOICE_AGENT, **ON) == said


@pytest.mark.parametrize("written, said", [
    ("اللوحة ١٢٣٤ أ ب ج", "اللوحة واحد اثنين ثلاثة أربعة ألف باء جيم"),
    ("اللوحة 6477 ص هـ ر، صح؟", "اللوحة ستة أربعة سبعة سبعة صاد هاء راء، صح؟"),
    ("اللوحة 1234-د ر س جاهزة", "اللوحة واحد اثنين ثلاثة أربعة دال راء سين جاهزة"),
], ids=["arabic-indic digits", "before a comma", "a hyphen and a word after"])
def test_a_plate_written_digits_first_is_read_as_written(written, said):
    assert normalize_for_tts(written, "ar", VOICE_AGENT, **ON) == said


@pytest.mark.parametrize("written", [
    "اختار 2 أ و ب",
    "1234 أ ب ج د",
    "12 أ ب ج",
    "1234 أ ب جملة",
], ids=["a count before options", "four letters", "two digits first", "a word after two letters"])
def test_digits_before_letters_that_are_not_a_plate_read_as_without_the_rule(written):
    said = normalize_for_tts(written, "ar", VOICE_AGENT, **ON)
    assert said == normalize_for_tts(written, "ar", VOICE_AGENT, spell_out_plates=False)


@pytest.mark.parametrize("written, said", [
    ("اللوحة XTR 6477", "اللوحة إِكْسْ تِي آرْ ستة أربعة سبعة سبعة"),
    ("لوحة سيارتك KSA 1234", "لوحة سيارتك كَيْ إِسْ إِيهْ واحد اثنين ثلاثة أربعة"),
    ("اللوحة 1234 ABJ", "اللوحة واحد اثنين ثلاثة أربعة إِيهْ بِي جَيْ"),
    ("رقم لوحتها: DRS-٥٦٧٨.", "رقم لوحتها: دِي آرْ إِسْ خمسة ستة سبعة ثمانية."),
    ("واللوحة ABJ 12", "واللوحة إِيهْ بِي جَيْ واحد اثنين"),
], ids=["consonants", "a word between", "digits first", "a colon and a hyphen", "two digits"])
def test_the_plates_latin_row_after_a_plate_word_is_spelled_and_read_digit_by_digit(written, said):
    assert normalize_for_tts(written, "ar", VOICE_AGENT, **ON) == said


@pytest.mark.parametrize("written", [
    "عندنا SUV 2024",
    "مرسيدس GLE 450 متوفرة",
    "اللوحة BMW 1234",
    "اللوحة ABJ 12345",
    "اللوحة ABJD 1234",
], ids=["no plate word", "a model with no plate word", "letters off the plate", "five digits", "four letters"])
def test_capitals_and_a_number_that_are_not_a_latin_plate_read_as_without_the_rule(written):
    said = normalize_for_tts(written, "ar", VOICE_AGENT, **ON)
    assert said == normalize_for_tts(written, "ar", VOICE_AGENT, spell_out_plates=False)


@pytest.mark.parametrize("written", ["أ ب ج 12", "أ ب ج - 1234", "اللوحة ١٢٣٤ أ ب ج", "اللوحة XTR 6477",
                                     "ن ى ى ٤٢٦٦"])
def test_every_new_plate_reading_is_read_again_unchanged(written):
    said = normalize_for_tts(written, "ar", VOICE_AGENT, **ON)
    assert normalize_for_tts(said, "ar", VOICE_AGENT, **ON) == said
    assert not any(c.isdigit() or c.isascii() and c.isalpha() for c in said), said


@pytest.mark.parametrize("written, said", [
    ("أ ب ج1234", "ألف باء جيم واحد اثنين ثلاثة أربعة"),
    ("اللوحة أ ب هـ١٢٣٤", "اللوحة ألف باء هاء واحد اثنين ثلاثة أربعة"),
], ids=["ascii digits", "ha with its tatweel, arabic-indic digits"])
def test_digits_written_against_the_last_letter_are_still_a_plate(written, said):
    assert normalize_for_tts(written, "ar", VOICE_AGENT, **ON) == said


@pytest.mark.parametrize("written, said", [
    ("اللوحة xtr 6477", "اللوحة إِكْسْ تِي آرْ ستة أربعة سبعة سبعة"),
    ("لوحتها 1234 Abj", "لوحتها واحد اثنين ثلاثة أربعة إِيهْ بِي جَيْ"),
], ids=["small letters", "mixed case, digits first"])
def test_the_latin_row_in_small_letters_is_read_as_in_capitals(written, said):
    assert normalize_for_tts(written, "ar", VOICE_AGENT, **ON) == said


def test_a_latin_word_after_a_plate_word_is_not_a_plate():
    said = normalize_for_tts("اللوحة bmw 1234", "ar", VOICE_AGENT, **ON)
    assert said == normalize_for_tts("اللوحة bmw 1234", "ar", VOICE_AGENT, spell_out_plates=False)
