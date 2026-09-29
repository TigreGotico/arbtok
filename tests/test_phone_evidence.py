"""A digit run that says it is a phone number is read digit by digit under VOICE_AGENT
even when its length is outside the numbering plan; a run with no such evidence keeps
the plan's rule, and a price or a count stays a cardinal."""
import dataclasses

import pytest

from arbtok import textnorm
from arbtok.textnorm import normalize_for_tts
from tests.voice_agent import VOICE_AGENT

# The same config with every phone rule off: the reading a quantity gets.
CARDINALS = dataclasses.replace(VOICE_AGENT, phone_regions=(), long_digit_runs=False, identifier_words=())


@pytest.mark.parametrize("written, said", [
    ("+9665012345", "تسعة ستة ستة خمسة صفر واحد اثنين ثلاثة أربعة خمسة"),
    ("966501234", "تسعة ستة ستة خمسة صفر واحد اثنين ثلاثة أربعة"),
    ("الموحد 9200012345", "الموحد تسعة اثنين صفر صفر صفر واحد اثنين ثلاثة أربعة خمسة"),
    ("الرقم الموحد 9200012345", "الرقم الموحد تسعة اثنين صفر صفر صفر واحد اثنين ثلاثة أربعة خمسة"),
    ("+20123", "اثنين صفر واحد اثنين ثلاثة"),
    ("00966501234", "صفر صفر تسعة ستة ستة خمسة صفر واحد اثنين ثلاثة أربعة"),
    ("رقمي 12345678", "رقمي واحد اثنين ثلاثة أربعة خمسة ستة سبعة ثمانية"),
], ids=["plus-short-saudi", "966-short-saudi", "unified-after-word", "unified-after-two-words",
        "plus-short-egypt", "00-short-saudi", "after-identifier-word"])
def test_a_run_that_says_it_is_a_phone_number_is_read_digit_by_digit(written, said):
    assert normalize_for_tts(written, "ar", VOICE_AGENT) == said


@pytest.mark.parametrize("written", [
    "السعر 92000123 ريال",
    "عندي 966 سيارة",
    "12345678",
    "السعر 800 ريال",
])
def test_a_quantity_stays_a_cardinal(written):
    # 92000123 starts with 920, but a Saudi unified number has nine digits and this run
    # has eight, so with no word before it the run is a price.
    assert normalize_for_tts(written, "ar", VOICE_AGENT) == normalize_for_tts(written, "ar", CARDINALS)


def test_a_date_stays_a_date():
    assert "صفر" not in normalize_for_tts("05-06-2024", "ar", VOICE_AGENT)


def test_a_count_after_a_valid_number_is_not_read_with_it():
    assert normalize_for_tts("+966501234567 15", "ar", VOICE_AGENT) \
        == "تسعة ستة ستة خمسة صفر واحد اثنين ثلاثة أربعة خمسة ستة سبعة خمسة عشر"


def test_the_leading_digits_come_from_the_plan():
    assert textnorm._mobile_leads("SA") == {"5"}
    assert textnorm._marked_leads("SA") == {"800": {10}, "920": {9}}
