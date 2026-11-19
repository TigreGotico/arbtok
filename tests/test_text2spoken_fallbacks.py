"""text2spoken reads the numbers of ``spoken_forms``, and the fallbacks that read what it leaves.

text2spoken reads the dates, clock times, numbers and units of ``spoken_forms``, and the
literary clock of every config. A fallback reads only a form that text2spoken leaves as
written. Each one carries a ``TODO(text2spoken issue: <CLASS>)`` marker with the URL of the
text2spoken issue for its class, or no URL while no issue is filed. The guard test turns
red on the day text2spoken reads a fallback form: the fallback then comes out, with its
marker.
"""
import re
from pathlib import Path

import pytest
import text2spoken

from arbtok import textnorm
from arbtok.textnorm import TtsNorm, normalize_for_tts

ROOT = Path(__file__).parent.parent
ISSUE_URL = "https://github.com/TigreGotico/text2spoken/issues/"
MARKER = re.compile(r"TODO\(text2spoken issue: (\w+)\)(?: " + re.escape(ISSUE_URL) + r"(\d+))?")

# Each class a fallback reads: its text2spoken issue, or None while none is filed, a text
# with the form, and the written part that text2spoken keeps.
FALLBACKS = {
    "UNIT_DECLINED": (336, "الطول 300 pm", "pm"),
    "CLOCK_PERIOD_MARK": (333, "الساعة 10:30 ص اليوم", " ص "),
    "SPACE_GROUPED": (148, "السعر 1 500 000 ريال", "000"),
    "CLOCK_NEEDS_WORD": (None, "الموعد 7:40", "7:40"),
    "CLOCK_SPELLING_OR_DOT": (None, "الساعه 3:30", "3:30"),
    "CLOCK_DOCUMENTED_GAP": (None, "الساعة 13:15", "13:15"),
    "DATE_RANGE": (None, "العرض من 1 إلى 7 مارس", "من 1 "),
    "DATE_TWO_DIGIT_YEAR": (None, "ينتهي التسجيل 31/12/30", "31/12/30"),
    "DECIMAL_COMMA": (None, "الوزن 12,5", "12,5"),
    "DECIMAL_DECLINED": (None, "سعر المدة 12.50 ريال", "12.50"),
    "CODE_DIGIT_SUFFIX": (None, "السيارة 520i", "520i"),
    "LEADING_ZERO": (None, "رقمي 77 83 10 01", "01"),
    "FRACTION_OTHER": (None, "موديل 2099/2100", "2099/2100"),
    "NUMBER_AGAINST_WORD": (None, "كمية 100كمية", "100كمية"),
    "T2S_DECLINES_OTHER": (None, "اختار 2 أ و ب", " 2 "),
}


@pytest.mark.parametrize("cls", FALLBACKS)
def test_text2spoken_still_leaves_the_fallback_form(cls):
    # Red here means text2spoken reads the form: remove its fallback and its marker.
    _, text, kept = FALLBACKS[cls]
    assert kept in text2spoken.normalize(text, "ar")


@pytest.mark.parametrize("cls", FALLBACKS)
def test_the_fallback_reads_the_form(cls):
    _, text, kept = FALLBACKS[cls]
    said = normalize_for_tts(text, "ar")
    assert kept not in said
    assert not re.search("[0-9٠-٩]", said)


def test_every_fallback_marker_names_its_class_and_issue():
    found = sorted((m.group(1), int(m.group(2)) if m.group(2) else None)
                   for path in sorted((ROOT / "arbtok").glob("*.py"))
                   for m in MARKER.finditer(path.read_text(encoding="utf-8")))
    assert found == sorted((cls, issue) for cls, (issue, _, _) in FALLBACKS.items())


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


def test_a_latin_script_lect_takes_no_text2spoken_step():
    assert normalize_for_tts("Eftu 3 kitapya", "acy") == "Eftu 3 kitapya"


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
