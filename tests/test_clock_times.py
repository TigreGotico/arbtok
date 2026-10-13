"""A clock time written in digits inside Arabic text is spoken as Arabic speakers say
it: the hour as a feminine ordinal after الساعة, a quarter, a third and a half of the
hour, twenty and a quarter to the next hour, and the period words. The words are the
date parser's ``nice_time``; each literal below is also checked against it."""
import datetime

import pytest
from ovos_date_parser import nice_time

from arbtok.textnorm import normalize_for_tts

CONFIGS = [{}, {"cardinal_numbers": True}]

# written text, spoken text, and the (hour, minute, use_ampm) nice_time reads the time from
SPOKEN = [
    ("الموعد 7:30 pm", "الموعد الساعة السابعة والنصف مساءً", (19, 30, True)),
    ("الموعد 7 pm", "الموعد الساعة السابعة مساءً", (19, 0, True)),
    ("الموعد 7pm", "الموعد الساعة السابعة مساءً", (19, 0, True)),
    ("الموعد 7:40", "الموعد الساعة الثامنة إلا ثلثاً", (7, 40, False)),
    ("الموعد 12:00 pm", "الموعد الساعة الثانية عشرة ظهراً", (12, 0, True)),
    ("الموعد 19:30", "الموعد الساعة السابعة والنصف مساءً", (19, 30, True)),
    ("الساعة 3", "الساعة الثالثة", (3, 0, False)),
    ("الساعة ٧:٣٠", "الساعة السابعة والنصف", (7, 30, False)),
    ("at 7:15 am", "at الساعة السابعة والربع صباحاً", (7, 15, True)),
    ("00:30", "الساعة الثانية عشرة والنصف صباحاً", (0, 30, True)),
    ("12 am", "منتصف الليل", (0, 0, True)),
    ("بالساعة 11 pm", "بالساعة الحادية عشرة مساءً", (23, 0, True)),
    ("7:30 ريال", "الساعة السابعة والنصف ريال", (7, 30, False)),
]


def _nice(hour, minute, use_ampm):
    return nice_time(datetime.datetime(2000, 1, 1, hour, minute), "ar", use_24hour=False, use_ampm=use_ampm)


@pytest.mark.parametrize("flags", CONFIGS, ids=["default", "cardinal_numbers"])
@pytest.mark.parametrize("written, spoken, time", SPOKEN, ids=[w for w, _, _ in SPOKEN])
def test_a_clock_time_is_spoken(written, spoken, time, flags):
    assert normalize_for_tts(written, "ar", **flags) == spoken


@pytest.mark.parametrize("written, spoken, time", SPOKEN, ids=[w for w, _, _ in SPOKEN])
def test_the_words_are_the_date_parsers(written, spoken, time):
    assert _nice(*time) in spoken


def test_a_written_saa_is_not_said_twice():
    assert normalize_for_tts("الساعة 3", "ar").count("الساعة") == 1


# written text, then what the default config and cardinal_numbers=True read: no clock time
NOT_A_TIME = [
    ("النتيجة 3:1", "النتيجة ثلاثة:واحد", "النتيجة ثلاثة:واحد"),
    ("الطول 300 pm", "الطول ثلاثمئة بيكومتر", "الطول ثلاثمئة pm"),
    ("13 pm", "ثلاثة عشر بيكومتر", "ثلاثة عشر pm"),
    ("05-06-2024", "الأربعاء، الخامس من يونيو ألفان وأربعة وعشرون", "خمسة-ستة-ألفان وأربعة وعشرون"),
    ("12:30:45", "اثنا عشر:ثلاثون:خمسة وأربعون", "اثنا عشر:ثلاثون:خمسة وأربعون"),
    ("الساعة 25", "الساعة خمسة وعشرون", "الساعة خمسة وعشرون"),
    ("24:00", "أربعة وعشرون:صفر", "أربعة وعشرون:صفر"),
    ("7:75", "سبعة:خمسة وسبعون", "سبعة:خمسة وسبعون"),
    ("7.5 pm", "سبعة فاصلة خمسة بيكومتر", "سبعة فاصلة خمسة pm"),
    ("الساعة 15h01", "الساعة خمسة عشر ودقيقة", "الساعة خمسة عشر ودقيقة"),
]


@pytest.mark.parametrize("written, default, cardinal", NOT_A_TIME, ids=[w for w, _, _ in NOT_A_TIME])
def test_a_number_that_is_no_clock_time_is_read_as_before(written, default, cardinal):
    assert normalize_for_tts(written, "ar") == default
    assert normalize_for_tts(written, "ar", cardinal_numbers=True) == cardinal


def test_seven_pm_is_a_time_and_three_hundred_pm_a_length():
    assert "بيكومتر" not in normalize_for_tts("الموعد 7 pm", "ar")
    assert "بيكومتر" in normalize_for_tts("الطول 300 pm", "ar")


def test_no_time_is_spoken_for_a_language_that_is_not_arabic():
    assert "الساعة" not in normalize_for_tts("7:30 pm", "en")


def test_no_time_is_spoken_without_spoken_forms():
    assert normalize_for_tts("الموعد 7:30 pm", "ar", spoken_forms=False) == "الموعد 7:30 pm"


def test_the_date_parser_floor_reads_the_hour_as_the_sources_give_it():
    """0.31.5a1 is the release whose Arabic ``nice_time`` reads twenty to the hour as
    إلا ثلثاً and noon with ظهراً; the words of every time above come from it."""
    from tests.test_dependency_floors import _as_tuple, _floors
    assert _as_tuple(_floors()["ovos-date-parser"]) >= _as_tuple("0.31.5a1")
