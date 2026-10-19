"""``month_names`` says each month in the caller's word for it wherever a month name is
written, so a voice can say the names its speakers use rather than the literary ones."""
import dataclasses

import pytest

from arbtok.textnorm import TtsNorm, normalize_for_tts
from tests.voice_agent import VOICE_AGENT

GULF = ("يناير", "فبراير", "مارتش", "أبريل", "مي", "جون", "جولاي", "أوقست", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر")


def agent():
    return dataclasses.replace(VOICE_AGENT, month_names=GULF)


SAID = [
    ("موعدك 15 يونيو", "موعدك خمسة عشر جون"),
    ("اقرب موعد 3 أغسطس", "اقرب موعد ثلاثة أوقست"),
    ("اقرب موعد 3 اغسطس", "اقرب موعد ثلاثة أوقست"),
    ("العرض ساري حتى نهاية يوليو", "العرض ساري حتى نهاية جولاي"),
    ("في مايو ويونيه", "في مي وجون"),
    ("بيوليو", "بجولاي"),
    ("يوم 2 مارس", "يوم اثنين مارتش"),
    ("مارس 2026", "مارتش ألفين وستة وعشرين"),
    ("نهاية شهر مارس", "نهاية شهر مارتش"),
    # a month whose name the caller keeps is said as before
    ("موعدك 10 فبراير", "موعدك عشرة فبراير"),
    # مارس in a range of months
    ("العرض من مارس إلى مايو", "العرض من مارتش إلى مي"),
    ("بين يناير ومارس", "بين يناير ومارتش"),
    ("مارس أو أبريل", "مارتش أو أبريل"),
    # a date in digits names its month after the date rule has run, so it is renamed too
    ("موعدك 15/6/2026", "موعدك خمسة عشر جون ألفين وستة وعشرين"),
    # مارس in a date in digits stands beside the date's day and year, which the date rule holds
    ("موعدك 15/3/2026", "موعدك خمسة عشر مارتش ألفين وستة وعشرين"),
    # مارس with no number, شهر or month beside it is the verb
    ("مارس الرياضة يوميا", "مارس الرياضة يوميا"),
    ("ومارس الرياضة", "ومارس الرياضة"),
    ("فمارس الرياضة في مايو", "فمارس الرياضة في مي"),
    # a word that only contains a month name is no month
    ("مايوه", "مايوه"),
]


@pytest.mark.parametrize("written, said", SAID, ids=[w for w, _ in SAID])
def test_a_month_takes_the_callers_word(written, said):
    assert normalize_for_tts(written, "ar", agent()) == said


def test_off_the_month_is_written_as_it_was():
    assert normalize_for_tts("موعدك 15 يونيو", "ar", VOICE_AGENT) == "موعدك خمسة عشر يونيو"


@pytest.mark.parametrize("names", [("جون",), GULF + ("x",), GULF[:11] + ("",)])
def test_twelve_words_are_required(names):
    with pytest.raises(ValueError):
        TtsNorm(month_names=names)


def test_arabic_only():
    with pytest.raises(ValueError):
        normalize_for_tts("June 15", "en", month_names=GULF)


def test_it_is_named_by_describe():
    assert TtsNorm(month_names=GULF).describe() != TtsNorm().describe()


def test_a_date_read_by_spoken_forms_alone_keeps_the_parsers_month():
    """What the docs say: only a date the cardinals read takes the caller's word."""
    said = normalize_for_tts("موعدك 15/6/2026", "ar", month_names=GULF)
    assert "يونيو" in said and "جون" not in said, said
