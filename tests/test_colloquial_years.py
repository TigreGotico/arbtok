"""``colloquial_years`` reads a year from 2020 on the way Saudi speech says it: عشرين and
the number past two thousand, where the cardinal says ألفين and the rest."""
import pytest

from arbtok.textnorm import TtsNorm, normalize_for_tts
from tests.voice_agent import VOICE_AGENT

SAID = [
    ("السيارة موديل 2026 متوفرة", "السيارة موديل عشرين ستة وعشرين متوفرة"),
    ("موديلها 2024", "موديلها عشرين أربعة وعشرين"),
    ("العرض على موديل 2020", "العرض على موديل عشرين عشرين"),
    ("ينتهي الضمان سنة 2027", "ينتهي الضمان سنة عشرين سبعة وعشرين"),
    ("في عام 2030", "في عام عشرين ثلاثين"),
    ("لعام 2025", "لعام عشرين خمسة وعشرين"),
    ("موعدك 15 يونيو 2026", "موعدك خمسة عشر يونيو عشرين ستة وعشرين"),
    ("حتى 3 اغسطس ٢٠٢٥", "حتى ثلاثة اغسطس عشرين خمسة وعشرين"),
    ("من 10 جون 2026", "من عشرة جون عشرين ستة وعشرين"),
    # a range or a choice of years is read in one register
    ("موديل 2026/2027", "موديل عشرين ستة وعشرين/عشرين سبعة وعشرين"),
    # a range that crosses 2020 or 2099 keeps the cardinal for both years
    ("موديل 2019/2020", "موديل ألفين وتسعة عشر/ألفين وعشرين"),
    ("موديل 2099/2100", "موديل ألفين وتسعة وتسعين/ألفين ومئة"),
    ("موديل 2019-2020", "موديل ألفين وتسعة عشر-ألفين وعشرين"),
    # a date with its era keeps the era after the colloquial year
    ("بتاريخ 5/3/2026م", "بتاريخ خمسة مارس عشرين ستة وعشرين ميلادي"),
    ("موديلات 2025 و موديل 2025-2026", "موديلات عشرين خمسة وعشرين و موديل عشرين خمسة وعشرين-عشرين ستة وعشرين"),
    # a proclitic on the month name, and عام as a definite noun or after a preposition
    ("حتى نهاية ويونيو 2026", "حتى نهاية ويونيو عشرين ستة وعشرين"),
    ("خلال العام 2026", "خلال العام عشرين ستة وعشرين"),
    ("منذ عام 2021", "منذ عام عشرين واحد وعشرين"),
    # a date in digits takes the same year
    ("موعدك 10/6/2026", "موعدك عشرة يونيو عشرين ستة وعشرين"),
    ("موعدك 10/6/2015", "موعدك عشرة يونيو ألفين وخمسة عشر"),
    # a bare عام after a noun is "general", and the number after it no year
    ("المدير عام 2026 موظف", "المدير عام ألفين وستة وعشرين موظف"),
    ("مدير عام 2026", "مدير عام ألفين وستة وعشرين"),
    # before 2020 the year is the cardinal, as it is said
    ("موديل 2015", "موديل ألفين وخمسة عشر"),
    ("موديل 2019", "موديل ألفين وتسعة عشر"),
    # a four-digit number with no year word before it is a quantity
    ("السعر 2026 ريال", "السعر ألفين وستة وعشرين ريال"),
    ("مشت 2025 كيلو", "مشت ألفين وخمسة وعشرين كيلو"),
    # nor is a year word before a longer or a grouped number
    ("موديل 20260", "موديل عشرين ألف ومئتين وستين"),
    ("موديل 2,026", "موديل ألفين وستة وعشرين"),
]


@pytest.mark.parametrize("written, said", SAID, ids=[w for w, _ in SAID])
def test_a_year_is_read_as_it_is_said(written, said):
    assert normalize_for_tts(written, "ar", VOICE_AGENT, colloquial_years=True) == said


def test_off_the_cardinal_reads_it():
    assert normalize_for_tts("موديل 2026", "ar", VOICE_AGENT) == "موديل ألفين وستة وعشرين"


def test_the_register_is_the_cardinals():
    assert normalize_for_tts("موديل 2026", "ar", VOICE_AGENT, colloquial_years=True, oblique_numbers=False) \
        == "موديل عشرون ستة وعشرون"


def test_it_is_named_by_describe():
    assert "colloquial_years" in TtsNorm(colloquial_years=True).describe()
