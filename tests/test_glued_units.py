"""A number written against a unit symbol, ``100km`` or ``100كم``, is read as the number
and the unit written apart are: the digits as a number, the symbol as a unit."""
import dataclasses

import pytest

from arbtok.textnorm import normalize_for_tts
from tests.voice_agent import VOICE_AGENT

# The voice-agent profile as it runs, and with codes spelled as well.
SPOKEN = VOICE_AGENT
CODES = dataclasses.replace(VOICE_AGENT, spell_out_codes=True)

SAID = [
    ("مشت السيارة 100km", "مشت السيارة مئة km"),
    ("مشت السيارة 100KM", "مشت السيارة مئة KM"),
    ("مشت السيارة 60,000km", "مشت السيارة ستين ألف km"),
    ("السرعة 120km/h", "السرعة مئة وعشرين km/h"),
    ("الوزن 2.5kg", "الوزن اثنين فاصلة خمسة kg"),
    ("الوزن 5kg", "الوزن خمسة kg"),
    ("قوة المحرك 300hp", "قوة المحرك ثلاث مئة hp"),
    ("مشت 100كم", "مشت مئة كم"),
    ("مشت ١٠٠كم", "مشت مئة كم"),
    ("الوزن 100kg", "الوزن مئة kg"),
    ("مشت ١٠٠km", "مشت مئة km"),
    # written apart, a number before a unit symbol is a quantity, not a name's
    ("مشت 100 km", "مشت مئة km"),
    ("الوزن 5 KG", "الوزن خمسة KG"),
]


@pytest.mark.parametrize("config", [SPOKEN, CODES], ids=["cardinal_numbers", "spell_out_codes"])
@pytest.mark.parametrize("glued, said", SAID, ids=[g for g, _ in SAID])
def test_a_glued_unit_is_read_as_the_number_and_the_unit(glued, said, config):
    assert normalize_for_tts(glued, "ar", config) == said


@pytest.mark.parametrize("written", ["مشت السيارة 100km", "مشت 100كم", "السرعة 120km/h"])
def test_no_digit_is_left(written):
    assert not any(c.isdigit() for c in normalize_for_tts(written, "ar", SPOKEN))


@pytest.mark.parametrize("written", ["السيارة X5", "الكود A100KMX", "جهاز 5G", "الفئة 330kmh", "100kms", "كمية 100كمية"])
def test_what_is_no_glued_unit_reads_as_before(written):
    split = normalize_for_tts(written, "ar", CODES)
    assert " km" not in split and " كم" not in split.replace("كمية", "")
