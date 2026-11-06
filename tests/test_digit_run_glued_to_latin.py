"""A digit run glued to Latin letters is never cut inside: the whole run is read as one
number, with a lone code letter read by its name and a longer word or unit left as it is."""
import re

import pytest

from arbtok.textnorm import normalize_for_tts, spelled_codes
from arbtok.util import _verbalize_residual_digits_ar

I, D = spelled_codes("ar")["I"], spelled_codes("ar")["D"]

SAID = [
    ("السيارة 520i", f"السيارة خمسمئة وعشرون {I}"),
    ("السيارة 330i", f"السيارة ثلاثمئة وثلاثون {I}"),
    ("السيارة 20i", f"السيارة عشرون {I}"),
    ("السيارة 118i", f"السيارة مئة وثمانية عشر {I}"),
    ("السيارة 520d", f"السيارة خمسمئة وعشرون {D}"),
    ("مشت 100kms", "مشت مئة kms"),
    # a lone small h or s after the number is the hour or the second
    ("خدمة 24h", "خدمة أربعة وعشرون ساعة"),
    ("خلال 90s", "خلال تسعون ثانية"),
    # a capital H or S is a code letter
    ("الفئة 20S", "الفئة 20S"),
]


@pytest.mark.parametrize("written, said", SAID, ids=[w for w, _ in SAID])
def test_a_glued_run_is_read_whole(written, said):
    assert normalize_for_tts(written, "ar") == said


@pytest.mark.parametrize("code", ["520i", "330i", "20i", "118i", "520d", "100kms", "M340i"])
def test_no_number_is_read_out_of_a_glued_digit_run(code):
    said = normalize_for_tts(f"السيارة {code}", "ar")
    assert not re.search(r"[ء-ي]\d|\d[ء-ي]", said), said


def test_the_residual_pass_reads_a_capital_led_run_whole():
    assert _verbalize_residual_digits_ar("M340i") == f"{spelled_codes('ar')['M']} ثلاثمئة وأربعون {I}"


@pytest.mark.parametrize("arabizi", ["3ala", "7abibi", "ma3a", "b2a"])
def test_arabizi_is_left_for_its_own_path(arabizi):
    assert _verbalize_residual_digits_ar(arabizi) == arabizi
