"""text2spoken reads the numbers of ``spoken_forms``, and the fallbacks that read what it leaves.

text2spoken reads the dates, clock times, numbers and units of ``spoken_forms``, and the
literary clock of every config. A fallback reads only a form that text2spoken leaves as
written. Each one carries a ``TODO(text2spoken issue: <CLASS>)`` marker with the URL of the
text2spoken issue for its class, or no URL while no issue is filed. The guard test turns
red on the day text2spoken reads a fallback form: the fallback then comes out, with its
marker.

Where text2spoken reads part of a span and leaves the rest, the fallback completes the
span into a wrong reading. Those classes, and the forms the fallback itself misreads, are
strict xfails that hold the right reading.
"""
import re
from pathlib import Path

import pytest
import text2spoken

from arbtok import textnorm
from arbtok.util import normalize
from arbtok.textnorm import TtsNorm, normalize_for_tts

ROOT = Path(__file__).parent.parent
ISSUE_URL = "https://github.com/TigreGotico/text2spoken/issues/"
MARKER = re.compile(r"TODO\(text2spoken issue: (\w+)\)(?: " + re.escape(ISSUE_URL) + r"(\d+))?")

# Each class a fallback reads: its text2spoken issue, or None while none is filed, a text
# with the form, the written part that text2spoken keeps, and the reading of the text.
FALLBACKS = {
    "UNIT_DECLINED": (336, "الطول 300 pm", "pm", "الطول ثلاثمئة بيكومتر"),
    "CLOCK_PERIOD_MARK": (333, "الساعة 10:30 am اليوم", " am ", "الساعة العاشرة والنصف صباحاً اليوم"),
    "SPACE_GROUPED": (148, "السعر 1 500 000 ريال", "000", "السعر مليون وخمسمئة ألف ريال"),
    "CLOCK_NEEDS_WORD": (None, "الموعد 7:40", "7:40", "الموعد الساعة الثامنة إلا ثلثا"),
    "CLOCK_SPELLING_OR_DOT": (368, "الساعه 3:30", "3:30", "الساعه الثالثة والنصف"),
    "CLOCK_DOCUMENTED_GAP": (None, "الساعة 13:15", "13:15", "الساعة الواحدة والربع مساءً"),
    "DATE_TWO_DIGIT_YEAR": (None, "ينتهي التسجيل 31/12/30", "31/12/30",
                            "ينتهي التسجيل الحادي والثلاثون من ديسمبر ألفين وثلاثين"),
    "DECIMAL_COMMA": (370, "الوزن 12,5", "12,5", "الوزن اثنا عشر فاصلة خمسة"),
    "DECIMAL_DECLINED": (371, "سعر المدة 12.50 ريال", "12.50", "سعر المدة اثنا عشر فاصلة خمسة ريال"),
    "CODE_DIGIT_SUFFIX": (None, "السيارة 520i", "520i", "السيارة خمسمئة وعشرون آيْ"),
    "LEADING_ZERO": (366, "رقمي 77 83 10 01", "01", "رقمي سبعة وسبعون ثلاثة وثمانون عشرة صفر واحد"),
    "FRACTION_OTHER": (None, "موديل 2099/2100", "2099/2100", "موديل ألفان وتسعة وتسعون/ألفان ومئة"),
    "NUMBER_AGAINST_WORD": (367, "كمية 100كمية", "100كمية", "كمية مئة كمية"),
    "T2S_DECLINES_OTHER": (None, "اختار 2 أ و ب", " 2 ", "اختار اثنان أ و ب"),
}

# The classes read wrong. text2spoken reads part of the span and the fallback completes
# it: 77 83 10 as numbers with the zero of 01 lost. Or the fallback misreads the whole
# form: the groups of 1 500 000 as three numbers, the century and a weekday for a
# two-digit year, a slash as a fraction, a number joined to its noun.
MISREAD = {
    "SPACE_GROUPED": "TODO(text2spoken issue: SPACE_GROUPED) https://github.com/TigreGotico/text2spoken/issues/148",
    "LEADING_ZERO": "TODO(text2spoken issue: LEADING_ZERO) https://github.com/TigreGotico/text2spoken/issues/366",
    "DATE_TWO_DIGIT_YEAR": "arbtok.util misreads it: https://github.com/TigreGotico/arbtok/issues/362",
    "FRACTION_OTHER": "arbtok.util misreads it: https://github.com/TigreGotico/arbtok/issues/363",
    "NUMBER_AGAINST_WORD": "TODO(text2spoken issue: NUMBER_AGAINST_WORD) https://github.com/TigreGotico/text2spoken/issues/367",
}


@pytest.mark.parametrize("cls", FALLBACKS)
def test_text2spoken_still_leaves_the_fallback_form(cls):
    # Red here means text2spoken reads the form: remove its fallback and its marker.
    _, text, kept, _ = FALLBACKS[cls]
    assert kept in text2spoken.normalize(text, "ar")


@pytest.mark.parametrize("cls", [
    pytest.param(cls, marks=pytest.mark.xfail(strict=True, reason=MISREAD[cls])) if cls in MISREAD else cls
    for cls in FALLBACKS])
def test_the_fallback_reads_the_form(cls):
    _, text, _, reading = FALLBACKS[cls]
    assert normalize_for_tts(text, "ar") == reading


def test_a_date_range_reads_through_text2spoken():
    # The first day of a range is an ordinal, as the last is.
    assert normalize_for_tts("العرض من 1 إلى 7 مارس", "ar") == "العرض من الأول إلى السابع من مارس"


def test_every_fallback_marker_names_its_class_and_issue():
    found = sorted((m.group(1), int(m.group(2)) if m.group(2) else None)
                   for path in sorted((ROOT / "arbtok").glob("*.py"))
                   for m in MARKER.finditer(path.read_text(encoding="utf-8")))
    assert found == sorted((cls, issue) for cls, (issue, _, _, _) in FALLBACKS.items())


# The ISO 639-3 code of the lect's spec chain, with its region. The macrolanguage,
# Standard Arabic and a clade map to ar; a lect written in Latin script has no tag.
@pytest.mark.parametrize("lang, tag", [
    ("ar", "ar"), ("arb", "ar"), ("ar-x-mashriqi", "ar"), ("ar-SA-x-janubi", "ar"),
    ("arz-EG", "arz-EG"), ("ars-SA-x-qassim", "ars-SA"), ("afb-SA-x-dawasir", "afb-SA"),
    ("ar-LY", "ayl-LY"), ("ar-IQ-x-qeltu", "ayp-IQ"), ("aec-EG", "aec-EG"), ("abv-BH", "abv-BH"),
    ("mey-MR", "mey-MR"), ("acy", None), ("pga", None), ("ar-Latn-x-buckwalt", None),
])
def test_a_lect_maps_to_its_text2spoken_tag(lang, tag):
    assert textnorm._text2spoken_tag(lang) == tag


LATIN_SCRIPT_LECTS = ["acy", "pga", "ar-Latn-x-buckwalt"]


@pytest.mark.parametrize("lang", LATIN_SCRIPT_LECTS)
def test_a_latin_script_lect_has_its_digits_read_by_arbtok_util(lang):
    # text2spoken reads Arabic script only.
    assert normalize_for_tts("Eftu 3 kitapya", lang) == "Eftu ثلاثة kitapya"


@pytest.mark.parametrize("lang", LATIN_SCRIPT_LECTS)
def test_a_latin_script_lect_reads_the_clock_as_before(lang):
    # The clock pass reads a time for these lects as dev did, not digit by digit.
    assert normalize_for_tts("Eftu 3 kitapya 7:30 pm", lang) == "Eftu ثلاثة kitapya الساعة السابعة والنصف مساءً"


@pytest.mark.parametrize("config, register", [(TtsNorm(), "formal"), (TtsNorm(dialect_numbers=True), "colloquial")])
def test_dialect_numbers_asks_for_the_colloquial_register(monkeypatch, config, register):
    calls = []
    read = text2spoken.normalize

    def spy(text, tag, params=None, *args, **kwargs):
        calls.append((tag, params.register))
        return read(text, tag, params, *args, **kwargs)

    monkeypatch.setattr(text2spoken, "normalize", spy)
    normalize_for_tts("موعدك 15 يونيو الساعة 9:25", "arz-EG", config)
    assert calls and set(calls) == {("arz-EG", register)}


def test_a_lect_text2spoken_reads_no_number_of_still_has_its_numbers_read():
    # text2spoken reads no number in Hassaniya, mey; the default path still reads them.
    assert not re.search("[0-9]", normalize_for_tts("عندي 13 كتاب", "mey-MR"))


# What text2spoken leaves of a unit or a percent sign is read as before it read them.
@pytest.mark.parametrize("text, said", [
    # ² belongs to the symbol: square metres are not metres. m² is UNIT_DECLINED.
    ("المساحة 100 m²", "المساحة مئة m²"),
    # text2spoken reads km alone, not the km of km/h.
    ("سرعة 100 km/h", "سرعة مئة كيلومتر/h"),
    # A percent sign with no number left after it is read too.
    ("الرقم 5% و % فقط", "الرقم خمسة في المئة و بالمئة فقط"),
])
def test_a_unit_or_percent_sign_text2spoken_leaves(text, said):
    assert normalize_for_tts(text, "ar") == said


# A number that names a thing is said in its citation form, whatever word follows it
# (Ryding 2005, p. 335).
def test_a_number_after_raqm_keeps_its_citation_form():
    assert "اثنان وأربعون" in normalize_for_tts("الحافلة رقم 42 متأخرة", "ar")


@pytest.mark.xfail(strict=True, reason="text2spoken takes the gender of the next word: "
                   "https://github.com/TigreGotico/text2spoken/issues/535")
@pytest.mark.parametrize("text, number", [
    ("الغرفة 205 مشغولة", "مئتان وخمسة"),
    ("الحلقة 7 كاملة", "سبعة"),
    ("السيارة MG 5 متوفرة", "خمسة"),
    ("السيارة موديل 2026 متوفرة", "ألفان وستة وعشرون"),
])
def test_a_number_that_names_a_thing_keeps_its_citation_form(text, number):
    assert number in normalize_for_tts(text, "ar")
