"""A clock time a recognizer writes in words after الساعة is read back to the digits
:func:`normalize_for_tts` speaks: the hour as an ordinal or a cardinal, the minutes as a
number, after دقيقة, or as a quarter, third or half of the hour, and a period word that
places the hour in the day. An ordinal anywhere else stays a word."""
import datetime

import pytest
from ovos_date_parser import nice_time

from arbtok.textnorm import AsrNorm, normalize_asr

FLAGS = dict(fix_asr_errors=True, spoken_numbers_to_digits=True)

HEARD = [
    # an ordinal hour, as Arabic says the hour, with the minutes after دقيقة
    ("الساعة الثامنة ودقيقة خمسة عشر", "الساعة 8:15"),
    ("موعدك الساعة الثامنة ودقيقة خمسة عشر بكرة", "موعدك الساعة 8:15 بكرة"),
    ("الساعه الحادية عشرة والنصف", "الساعه 11:30"),
    ("الساعة الثامنة", "الساعة 8"),
    # مساء and ليلا put an hour of the 12-hour clock after noon; صباحا leaves it
    ("الساعة السادسة مساء ودقيقة خمسة واربعين", "الساعة 18:45"),
    ("الساعة السادسة مساء", "الساعة 18:00"),
    ("الساعة العاشرة ليلا", "الساعة 22:00"),
    ("الساعة الثامنة صباحا", "الساعة 8:00"),
    ("الساعة الثامنة صباحاً والربع", "الساعة 8:15"),
    ("الساعة الثانية عشرة ظهرا", "الساعة 12:00"),
    # a cardinal hour means what it meant
    ("الساعة ستة مساء", "الساعة 18:00"),
    ("الساعة ثمانية وخمسة عشر", "الساعة 8:15"),
    ("الساعة ثمانية وخمسة عشر دقيقة", "الساعة 8:15"),
    # the fractions of the hour
    ("الساعة ثمانية وربع", "الساعة 8:15"),
    ("الساعة الثامنة ونص", "الساعة 8:30"),
    ("الساعة الثامنة و نص", "الساعة 8:30"),
    ("الساعة الثامنة والثلث", "الساعة 8:20"),
    ("الساعة التاسعة الا ربع", "الساعة 8:45"),
    ("الساعة الثانية عشرة إلا ربعاً مساءً", "الساعة 23:45"),
    # إلا and a number of minutes counts back from the hour, as إلا ربع does
    ("الساعة الثامنة الا خمس دقائق", "الساعة 7:55"),
    ("الساعة الثامنة إلا دقيقة", "الساعة 7:59"),
    ("الساعة الثامنة الا دقيقتين", "الساعة 7:58"),
    ("الساعة الثامنة الا عشرة", "الساعة 7:50"),
    # counting back from one stays on the 12-hour clock unless a period word moves it
    ("الساعة الواحدة الا ربع", "الساعة 12:45"),
    ("الساعة الواحدة الا ربع ظهرا", "الساعة 12:45"),
    # twelve at night is midnight
    ("الساعة الثانية عشرة ليلا", "الساعة 0:00"),
    ("الساعة الثانية عشرة الا ربع ليلا", "الساعة 23:45"),
    ("الساعة الواحدة الا ربع ليلا", "الساعة 0:45"),
    # a bare ordinal hour where the phrase ends
    ("الساعة الثامنة.", "الساعة 8."),
    ("الساعة الثامنة، شكرا", "الساعة 8، شكرا"),
    ("الساعة الثامنة تماماً", "الساعة 8 تماماً"),
    ("الساعة الثامنة غدا", "الساعة 8 غدا"),
    ("الساعة الثامنة يوم الخميس", "الساعة 8 يوم الخميس"),
]


@pytest.mark.parametrize("heard, read", HEARD, ids=[h for h, _ in HEARD])
def test_a_spoken_clock_time_is_written_in_digits(heard, read):
    assert normalize_asr(heard, **FLAGS) == read


@pytest.mark.parametrize("hour", range(24))
def test_every_time_the_date_parser_speaks_reads_back_to_its_digits(hour):
    """``nice_time`` is what :func:`normalize_for_tts` says for ``الساعة h:mm``; the
    recognizer side reads every minute of every hour of it back, period word included."""
    for minute in range(60):
        if hour == minute == 0:
            continue  # منتصف الليل, said without الساعة
        spoken = nice_time(datetime.datetime(2000, 1, 1, hour, minute), "ar", use_24hour=False, use_ampm=True)
        assert normalize_asr(spoken, **FLAGS) == f"الساعة {hour}:{minute:02d}", spoken


UNCHANGED_ORDINALS = ["الطابق الثامن", "في الطابق الثامن ودقيقة", "الدرس الثامن ونص",
                      "المرة السادسة مساء", "الثامنة مساء"]


@pytest.mark.parametrize("text", UNCHANGED_ORDINALS)
def test_an_ordinal_is_a_digit_only_as_the_hour_after_al_saa(text):
    assert normalize_asr(text, **FLAGS) == text


@pytest.mark.parametrize("text", ["الساعة الثانية اللي اشتريتها", "الساعة الأولى من العلاج",
                                  "الساعة الثامنة الا شوي"])
def test_a_bare_ordinal_that_continues_a_noun_phrase_is_the_nth_hour_or_watch(text):
    """"the second watch I bought", "the first hour of treatment": no time is said, and
    an إلا the reader cannot count back leaves the hour a word too."""
    assert normalize_asr(text, **FLAGS) == text


@pytest.mark.parametrize("text, read", [
    # الساعة is also "the watch", and a number after it with nothing more is its number
    ("الساعة ثمانية الاف ريال", "الساعة 8000 ريال"),
    # one number, fifty-eight, not eight and fifty minutes
    ("الساعة ثمانية وخمسين", "الساعة 58"),
    # ساعة without the article is a duration
    ("ساعة ونص", "ساعة ونص"),
])
def test_a_number_after_al_saa_that_is_no_clock_time_is_left_to_the_number_pass(text, read):
    assert normalize_asr(text, **FLAGS) == read


def test_the_clock_is_read_only_with_spoken_numbers_to_digits_and_only_in_arabic():
    assert normalize_asr("الساعة الثامنة ونص", fix_asr_errors=True) == "الساعة الثامنة ونص"
    assert normalize_asr("الساعة الثامنة ونص", spoken_numbers_to_digits=True, lang="fa") == "الساعة الثامنة ونص"


def test_the_description_names_the_date_parser_that_reads_the_period_words():
    assert "; ovos-date-parser " in AsrNorm(spoken_numbers_to_digits=True).describe()
    assert "ovos-date-parser" not in AsrNorm(fix_asr_errors=True).describe()
