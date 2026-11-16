"""A number the cardinal pass speaks agrees with the word after it.

A number from 3 to 10 before a plural whose singular is feminine takes its short form.
Ryding, "A Reference Grammar of Modern Standard Arabic", ch. 15 section 1.3.1.1: "With an
indefinite counted item, the numeral shows reverse gender agreement and precedes the
counted noun", with "thamaanii saacaat-in", eight hours, and "tisc-a sayyaaraat-in", nine
cars. The plurals and their sources are in arbtok/data/feminine_counted_nouns.tsv.

Two hundred before ألف is in construct and drops its nun. Ryding ch. 15 section 1.7: "The
dual suffix here obeys the law of nuun-drop when it goes into an 'iDaafa with a following
counted noun"; section 1.9 gives 200,000 as "mi'at-aa 'alf-in".

A number written against the Arabic word after it is two words, and its last word does not
fuse to that word."""
import pytest

from arbtok.textnorm import TtsNorm, normalize_for_tts
from tests.voice_agent import VOICE_AGENT

PLAIN = TtsNorm(cardinal_numbers=True, spoken_forms=False, canonical_unicode=False)


@pytest.mark.parametrize("text, said", [
    ("الضمان 5 سنوات", "الضمان خمس سنوات"),
    ("خلال 3 ساعات", "خلال ثلاث ساعات"),
    ("انتظر 10 دقائق", "انتظر عشر دقائق"),
    ("في 6 ثواني", "في ست ثواني"),
    ("في 6 ثوان", "في ست ثوان"),
    ("عندنا 8 سيارات", "عندنا ثماني سيارات"),
    ("تمشي على ٤ عجلات", "تمشي على أربع عجلات"),
    ("الإقامة 7 ليال", "الإقامة سبع ليال"),
    ("الإقامة 7 ليالي", "الإقامة سبع ليالي"),
    ("كررها 9 مرات", "كررها تسع مرات"),
    ("فيها 6 وسائد هوائية", "فيها ست وسائد هوائية"),
    ("ناقل حركة 8 سرعات", "ناقل حركة ثماني سرعات"),
    ("محرك 6 أسطوانات", "محرك ست أسطوانات"),
    ("محرك 6 اسطوانات", "محرك ست اسطوانات"),
    ("على 4 دفعات", "على أربع دفعات"),
    ("الضمان 5 سنوات.", "الضمان خمس سنوات."),
    ("الضمان 3 سنين، والصيانة 4 مرات", "الضمان ثلاث سنين، والصيانة أربع مرات"),
])
def test_three_to_ten_before_a_feminine_plural_take_the_short_form(text, said):
    assert normalize_for_tts(text, "ar", VOICE_AGENT) == said
    assert normalize_for_tts(text, "ar", PLAIN) == said


@pytest.mark.parametrize("text, said", [
    # يوم, خيار and مقعد are masculine: the plural's shape does not decide it
    ("خلال 3 أيام", "خلال ثلاثة أيام"),
    ("عندنا 5 خيارات", "عندنا خمسة خيارات"),
    ("فيها 7 مقاعد", "فيها سبعة مقاعد"),
    # the noun must follow the number directly
    ("بعنا 5 من السيارات", "بعنا خمسة من السيارات"),
    ("السيارات 5", "السيارات خمسة"),
    # a fraction is not a count
    ("خلال 1.5 ساعات", "خلال واحد فاصلة خمسة ساعات"),
    # a number the author wrote in words is the author's
    ("خمسة سنوات", "خمسة سنوات"),
])
def test_other_numbers_keep_the_long_form(text, said):
    assert normalize_for_tts(text, "ar", VOICE_AGENT) == said


def test_a_word_of_your_own_for_the_value_is_kept():
    config = PLAIN.with_number_forms({5: "خمسه"})
    assert normalize_for_tts("الضمان 5 سنوات", "ar", config) == "الضمان خمسه سنوات"


def test_the_lect_says_the_short_form_too():
    config = TtsNorm(dialect_numbers=True, spoken_forms=False, canonical_unicode=False)
    assert normalize_for_tts("الضمان 5 سنوات", "ar-SA", config) == "الضمان خمس سنوات"


@pytest.mark.parametrize("text, oblique, nominative", [
    ("سعرها 200,000 ريال", "سعرها مئتي ألف ريال", "سعرها مئتا ألف ريال"),
    ("سعرها 200000 ريال", "سعرها مئتي ألف ريال", "سعرها مئتا ألف ريال"),
    ("ميزانية 200,000,000 ريال", "ميزانية مئتي مليون ريال", "ميزانية مئتا مليون ريال"),
    ("سعرها ٢٠٠٬٠٠٠ ريال", "سعرها مئتي ألف ريال", "سعرها مئتا ألف ريال"),
])
def test_two_hundred_before_a_thousand_is_in_construct(text, oblique, nominative):
    assert normalize_for_tts(text, "ar", VOICE_AGENT) == oblique
    assert normalize_for_tts(text, "ar", PLAIN) == nominative


@pytest.mark.parametrize("text, said", [
    ("السعر 200 ريال", "السعر مئتين ريال"),
    ("السعر 250,000 ريال", "السعر مئتين وخمسين ألف ريال"),
])
def test_two_hundred_not_before_a_thousand_keeps_its_nun(text, said):
    assert normalize_for_tts(text, "ar", VOICE_AGENT) == said


def test_a_word_of_your_own_for_two_hundred_is_kept():
    config = VOICE_AGENT.with_number_forms({200: "ميتين", 1000: "الف"})
    assert normalize_for_tts("سعرها 200,000 ريال", "ar", config) == "سعرها ميتين الف ريال"


@pytest.mark.parametrize("text, said", [
    ("السعر 45,000ريال", "السعر خمسة وأربعين ألف ريال"),
    ("القسط 1,850ريال شهريا", "القسط ألف وثمان مئة وخمسين ريال شهريا"),
    ("السعر ٤٥٬٠٠٠ريال", "السعر خمسة وأربعين ألف ريال"),
    ("الضمان 5سنوات", "الضمان خمس سنوات"),
])
def test_a_number_against_the_word_after_it_is_read_apart(text, said):
    assert normalize_for_tts(text, "ar", VOICE_AGENT) == said


@pytest.mark.parametrize("text", ["الضمان 5 سنوات", "سعرها 200,000 ريال", "السعر 45,000ريال"])
def test_without_the_cardinal_pass_nothing_changes(text):
    off = TtsNorm(cardinal_numbers=False, spoken_forms=False, canonical_unicode=False)
    assert normalize_for_tts(text, "ar", off) == text
