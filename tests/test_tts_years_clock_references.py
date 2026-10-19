"""Numbers the voice-agent configuration reads by what the words around them say: a year
after موديلات or after و and another year, a time written with a dot after الساعة, and a
reference after an identifier word and a colon."""
import pytest

from arbtok.textnorm import normalize_for_tts
from tests.voice_agent import VOICE_AGENT


@pytest.mark.parametrize("written, said", [
    ("عندنا موديلات 2025 بخصم", "عندنا موديلات عشرين خمسة وعشرين بخصم"),
    ("الموديلات 2026 وصلت", "الموديلات عشرين ستة وعشرين وصلت"),
    ("بموديلات 2024", "بموديلات عشرين أربعة وعشرين"),
    ("عندنا موديل 2026 و 2025", "عندنا موديل عشرين ستة وعشرين و عشرين خمسة وعشرين"),
    ("عندنا موديل 2026 و2025", "عندنا موديل عشرين ستة وعشرين وعشرين خمسة وعشرين"),
    ("موديلات 2025 و 2026 متوفرة", "موديلات عشرين خمسة وعشرين و عشرين ستة وعشرين متوفرة"),
    # each year after و is read on its own: before 2020 a year keeps the cardinal
    ("موديل 2026 و 2019", "موديل عشرين ستة وعشرين و ألفين وتسعة عشر"),
    # a number before ريال is a price, not a second year
    ("موديل 2026 و 2050 ريال خصم", "موديل عشرين ستة وعشرين و ألفين وخمسين ريال خصم"),
    # a range is still read in one register
    ("موديل 2019/2020", "موديل ألفين وتسعة عشر/ألفين وعشرين"),
])
def test_a_year_is_known_by_the_words_before_it(written, said):
    assert normalize_for_tts(written, "ar", VOICE_AGENT, colloquial_years=True) == said


@pytest.mark.parametrize("written, colloquial", [
    ("الموعد الساعة 9.30", "الموعد الساعة تسعة ونص"),
    ("الموعد الساعة 10.15 الصبح", "الموعد الساعة عشرة وربع الصبح"),
    ("الموعد الساعه 4.20", "الموعد الساعه أربعة وثلث"),
    ("الموعد الساعة ٩.٣٠", "الموعد الساعة تسعة ونص"),
])
def test_a_time_written_with_a_dot_after_alsaa_is_a_time(written, colloquial):
    assert normalize_for_tts(written, "ar", VOICE_AGENT, colloquial_clock=True) == colloquial
    # the literary reading is the one the same time written h:mm takes
    with_colon = written.replace(".", ":")
    assert normalize_for_tts(written, "ar", VOICE_AGENT) == normalize_for_tts(with_colon, "ar", VOICE_AGENT)


@pytest.mark.parametrize("written", [
    # money after it: the price of an hour
    "سعر الساعة 12.50 ريال",
    "سعر الساعة 12.50 ر.س",
    "سعر الساعة 12.50 SAR",
    # minutes past 59, and one digit after the dot
    "الساعة 9.75",
    "الساعة 9.5",
])
def test_other_dotted_numbers_after_alsaa_stay_decimals(written):
    # the decimal reading is the one the number takes after another word
    other = normalize_for_tts(written.replace("الساعة", "المدة"), "ar", VOICE_AGENT, colloquial_clock=True)
    assert normalize_for_tts(written, "ar", VOICE_AGENT, colloquial_clock=True) == other.replace("المدة", "الساعة")
    assert "فاصلة" in other


@pytest.mark.parametrize("written, said", [
    ("الكود: 4471", "الكود: أربعة أربعة سبعة واحد"),
    ("الكود : 4471", "الكود : أربعة أربعة سبعة واحد"),
    ("رقم الحجز: 3401", "رقم الحجز: ثلاثة أربعة صفر واحد"),
    ("رقمك:7731", "رقمك:سبعة سبعة ثلاثة واحد"),
    ("كود العرض: 4471 صالح", "كود العرض: أربعة أربعة سبعة واحد صالح"),
])
def test_a_colon_after_an_identifier_word_keeps_the_reference(written, said):
    assert normalize_for_tts(written, "ar", VOICE_AGENT) == said


@pytest.mark.parametrize("written, said", [
    # a colon after another word is no identifier
    ("السعر: 4471 ريال", "السعر: أربعة آلاف وأربع مئة وواحد وسبعين ريال"),
])
def test_a_colon_after_another_word_leaves_a_quantity(written, said):
    assert normalize_for_tts(written, "ar", VOICE_AGENT) == said
