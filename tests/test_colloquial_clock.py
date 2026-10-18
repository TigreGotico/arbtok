"""``colloquial_clock`` reads a clock time the way Saudi speech says it: the hour as a
cardinal, a quarter and a half as وربع and ونص, and the part of the day by its common
word where the text gives the period."""
import pytest

from arbtok.textnorm import TtsNorm, normalize_asr, normalize_for_tts
from tests.voice_agent import VOICE_AGENT

SAID = [
    ("موعدك بكرة الساعة 9:30", "موعدك بكرة الساعة تسعة ونص"),
    ("نستقبلك الساعة 10:15 في الفرع", "نستقبلك الساعة عشرة وربع في الفرع"),
    ("الساعه 1:30", "الساعه واحدة ونص"),
    ("الساعة 8:45", "الساعة ثمانية وخمسة وأربعين دقيقة"),
    ("الساعة 7:05", "الساعة سبعة وخمسة"),
    # twenty past is a third; forty and fifty count back, since "أربعة وأربعين" is 44
    ("الساعة 4:20", "الساعة أربعة وثلث"),
    ("الساعة 4:40", "الساعة خمسة إلا ثلث"),
    ("الساعة 5:50", "الساعة ستة إلا عشرة"),
    ("الساعة 12:40", "الساعة واحدة إلا ثلث"),
    ("الساعة 4:25", "الساعة أربعة وخمسة وعشرين دقيقة"),
    ("الساعة 16:40", "الساعة خمسة إلا ثلث العصر"),
    ("الساعة 11", "الساعة أحد عشر"),
    ("الساعة 12:00", "الساعة اثني عشر"),
    ("الموعد 9:00", "الموعد الساعة تسعة"),
    # the 24-hour clock and am/pm give the period, said by the part of the day
    ("الموعد 14:00", "الموعد الساعة اثنين الظهر"),
    ("الموعد الساعة 16:30", "الموعد الساعة أربعة ونص العصر"),
    ("نفتح 8 am", "نفتح الساعة ثمانية الصباح"),
    ("الساعة 10:30 am", "الساعة عشرة ونص الصباح"),
    ("الساعة 12 pm", "الساعة اثني عشر الظهر"),
    ("الساعة 18:15", "الساعة ستة وربع المغرب"),
    ("الساعة 21:00", "الساعة تسعة بالليل"),
    ("الساعة 0:30", "الساعة اثني عشر ونص بالليل"),
]


@pytest.mark.parametrize("written, said", SAID, ids=[w for w, _ in SAID])
def test_a_clock_time_is_read_as_it_is_said(written, said):
    assert normalize_for_tts(written, "ar", VOICE_AGENT, colloquial_clock=True) == said


def test_off_the_date_parser_reads_it():
    assert normalize_for_tts("الساعة 9:30", "ar", VOICE_AGENT) == "الساعة التاسعة والنصف"
    assert normalize_for_tts("الساعة 9:30", "ar") == "الساعة التاسعة والنصف"


def test_spoken_forms_alone_takes_the_option_too():
    assert normalize_for_tts("الساعة 9:30", "ar", colloquial_clock=True) == "الساعة تسعة ونص"


def test_a_number_that_is_no_time_is_untouched():
    assert normalize_for_tts("السعر 930 ريال", "ar", VOICE_AGENT, colloquial_clock=True) == \
        normalize_for_tts("السعر 930 ريال", "ar", VOICE_AGENT)


# normalize_asr reads a bare compound hour, "الساعة أحد عشر" with nothing after it, as
# "الساعة أحد 10"; the same hour with minutes after it reads back.
_BARE_COMPOUND_HOUR = pytest.mark.xfail(strict=True, reason="normalize_asr misreads a bare compound hour")


@pytest.mark.parametrize("hour", range(1, 13))
@pytest.mark.parametrize("minute", range(60))
def test_the_recognizer_side_reads_every_minute_back(request, hour, minute):
    """What the option says for every minute of every hour is what normalize_asr reads back to
    the same time, so no reading is also another time: a time with no minutes reads back as
    the hour alone, as the literary reading does."""
    if minute == 0 and hour >= 11:
        request.applymarker(_BARE_COMPOUND_HOUR)
    said = normalize_for_tts(f"الساعة {hour}:{minute:02d}", "ar", VOICE_AGENT, colloquial_clock=True)
    read = f"الساعة {hour}:{minute:02d}" if minute else f"الساعة {hour}"
    assert normalize_asr(said, fix_asr_errors=True, spoken_numbers_to_digits=True) == read, said


def test_it_is_named_by_describe():
    assert "colloquial_clock" in TtsNorm(colloquial_clock=True).describe()
