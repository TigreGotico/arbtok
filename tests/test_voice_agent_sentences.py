"""Whole sentences through the voice-agent configuration, several rules in each.

Every rule has its own tests; these hold the rules together, in the order they run,
on text shaped like what an agent says. A sentence here must come out with no digit
left for the synthesizer, and a clock time must come out as a time.
"""
import pytest

from arbtok.textnorm import normalize_for_tts
from tests.voice_agent import VOICE_AGENT


def said(text):
    return normalize_for_tts(text, "ar", VOICE_AGENT)


@pytest.mark.parametrize("written, spoken", [
    ("الموعد 7:30 pm", "الموعد الساعة السابعة والنصف مساءً"),
    ("الموعد 7 pm", "الموعد الساعة السابعة مساءً"),
    ("الموعد 7pm", "الموعد الساعة السابعة مساءً"),
    ("الموعد 10:05", "الموعد الساعة العاشرة وخمس دقائق"),
    ("الموعد الساعة 12:00 pm", "الموعد الساعة الثانية عشرة ظهراً"),
    ("موعدك 19:30", "موعدك الساعة السابعة والنصف مساءً"),
    ("الساعة ٧:٣٠", "الساعة السابعة والنصف"),
])
def test_a_clock_time_is_spoken_as_a_time(written, spoken):
    assert said(written) == spoken


@pytest.mark.parametrize("written", [
    "الموعد 7:30 pm ورقمي 0501234567",
    "اتصل على +20 10 01234567 بعد الساعة 5 pm",
    "بتاريخ 05-06-2024 الساعة 12:00 pm",
    "00:30 و 23:59 و 12 am",
    "عندي ١٢ سيارة و ٧:٣٠ موعد",
    "المبلغ 1,250.50 ريال و 4.5%",
    "الموعد الساعة 10:05 والسعر 99,999 ريال",
    "٠٥٠١٢٣٤٥٦٧",
])
def test_no_digit_reaches_the_synthesizer(written):
    out = said(written)
    assert not any(c.isdigit() for c in out), out


@pytest.mark.parametrize("written, spoken", [
    ("النتيجة 3:1", "النتيجة ثلاثة:واحد"),
    ("MG 5 بسعر 70,000", "MG 5 بسعر سبعين ألف"),
])
def test_what_is_not_a_time_is_left_to_its_own_rule(written, spoken):
    assert said(written) == spoken
