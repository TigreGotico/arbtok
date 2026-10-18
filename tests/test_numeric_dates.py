"""A date written in digits is read as a date among the numbers the cardinals speak:
its day, its month by name and its year, rather than three numbers with the slashes
between them left in the text."""
import dataclasses

import pytest

from arbtok.textnorm import normalize_for_tts
from tests.voice_agent import VOICE_AGENT

SAID = [
    ("موعدك يوم 10/6/2026", "موعدك يوم عشرة يونيو ألفين وستة وعشرين"),
    ("موعدك يوم 10-06-2026", "موعدك يوم عشرة يونيو ألفين وستة وعشرين"),
    ("موعدك يوم 10.6.2026", "موعدك يوم عشرة يونيو ألفين وستة وعشرين"),
    ("ينتهي العرض 31/12/2026.", "ينتهي العرض واحد وثلاثين ديسمبر ألفين وستة وعشرين."),
    ("بتاريخ ١٥/٨/٢٠٢٦", "بتاريخ خمسة عشر أغسطس ألفين وستة وعشرين"),
    ("موعدك 1/3/26", "موعدك واحد مارس ألفين وستة وعشرين"),
    # a four-digit year first is year, month and day
    ("بتاريخ 2026-06-10", "بتاريخ عشرة يونيو ألفين وستة وعشرين"),
    ("بتاريخ 2026/01/05", "بتاريخ خمسة يناير ألفين وستة وعشرين"),
    # two dates in one sentence
    ("من 1/7/2026 إلى 15/7/2026", "من واحد يوليو ألفين وستة وعشرين إلى خمسة عشر يوليو ألفين وستة وعشرين"),
    # a Latin word after the date does not keep the year's digits
    ("موعد 10/6/2026 BMW", "موعد عشرة يونيو ألفين وستة وعشرين BMW"),
    # a Hijri date, by هـ or by a year only the Hijri calendar has, takes the Hijri month
    ("بتاريخ 15/9/1447هـ", "بتاريخ خمسة عشر رمضان ألف وأربع مئة وسبعة وأربعين هجري"),
    ("بتاريخ 15/9/1447 هـ", "بتاريخ خمسة عشر رمضان ألف وأربع مئة وسبعة وأربعين هجري"),
    ("بتاريخ 1/1/1446", "بتاريخ واحد محرم ألف وأربع مئة وستة وأربعين"),
    ("بتاريخ 1447-12-10هـ", "بتاريخ عشرة ذو الحجة ألف وأربع مئة وسبعة وأربعين هجري"),
    # the era written bare after the year is said, never left on the number
    ("بتاريخ 15/9/1447ه", "بتاريخ خمسة عشر رمضان ألف وأربع مئة وسبعة وأربعين هجري"),
    ("بتاريخ 5/3/2026م", "بتاريخ خمسة مارس ألفين وستة وعشرين ميلادي"),
    ("بتاريخ 5/3/2026 م.", "بتاريخ خمسة مارس ألفين وستة وعشرين ميلادي."),
    # a two-digit year is this century's
    ("ينتهي الضمان 31/12/30", "ينتهي الضمان واحد وثلاثين ديسمبر ألفين وثلاثين"),
    ("ينتهي الضمان 31/12/85", "ينتهي الضمان واحد وثلاثين ديسمبر ألفين وخمسة وثمانين"),
    # a dotted date with a Gregorian year is still a date
    ("بتاريخ 1.2.2026", "بتاريخ واحد فبراير ألفين وستة وعشرين"),
]


@pytest.mark.parametrize("written, said", SAID, ids=[w for w, _ in SAID])
def test_a_date_is_read_as_a_date(written, said):
    assert normalize_for_tts(written, "ar", VOICE_AGENT) == said


NOT_DATES = [
    "النتيجة 3-1",            # a score
    "نص 1/2 الكمية",          # a fraction
    "الطلب 10/6/2026/7",      # a longer run
    "القطعة 12-34-5678",      # a part number with no calendar month
    "يوم 31/2/2026",          # no such day
    "موعدك 10-6-26",          # a two-digit year only with slashes
    "الرقم 11-12-0001",       # no year a date is read in
    "سنة 1/1/1850",
    "بتاريخ 1/13/1447هـ",     # no thirteenth month
    "بتاريخ 31/9/1447هـ",     # no Hijri month has 31 days
    "الإصدار 2.1.1400",       # a version number
    "بتاريخ 5/3/2026ه",       # a Hijri era on a Gregorian year
    "بتاريخ 15/9/1447م",      # a Gregorian era on a Hijri year
]


@pytest.mark.parametrize("written", NOT_DATES)
def test_what_is_no_date_is_not_read_as_one(written):
    assert not any(month in normalize_for_tts(written, "ar", VOICE_AGENT)
                   for month in ("يناير", "فبراير", "مارس", "يونيو", "يوليو", "أكتوبر", "ديسمبر", "رمضان", "محرم"))


def test_spoken_forms_alone_reads_dates_as_before():
    assert normalize_for_tts("موعدك يوم 10/6/2026", "ar") == "موعدك يوم الأربعاء، العاشر من يونيو ألفان وستة وعشرون"


def test_a_date_after_an_identifier_word_is_read_as_a_date():
    """An identifier word reads the number after it digit by digit; the day of a date is no
    such number."""
    config = dataclasses.replace(VOICE_AGENT, identifier_words=("الفرع",))
    assert normalize_for_tts("الفرع يفتح 10/6/2026", "ar", config) == "الفرع يفتح عشرة يونيو ألفين وستة وعشرين"
