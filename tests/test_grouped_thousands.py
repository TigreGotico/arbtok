"""A number written with more than one thousands separator reads as its value.

`1,500` has always worked and `14,000,000` has not, which is the shape of a guard
that strips one separator and a body that strips all of them. The failure is
silent and expensive: the digits disappear, so a leak test sees clean text, and
what replaces them is a different number.
"""
import pytest

from arbtok.util import normalize

MILLION = "مليون"
ZERO = "صفر"


@pytest.mark.parametrize("text,must_contain", [
    ("14,000,000", MILLION),
    ("1,234,567", "مليون"),
    ("1,500", "ألف"),
    ("14000000", MILLION),
])
def test_a_grouped_number_reads_as_its_value(text, must_contain):
    out = normalize(text, "ar")
    assert must_contain in out, f"{text} -> {out}"


@pytest.mark.parametrize("text", ["14,000,000", "1,234,567"])
def test_a_grouped_number_does_not_read_its_groups_as_zero(text):
    out = normalize(text, "ar")
    assert ZERO not in out, f"{text} -> {out}"
    assert "," not in out, f"separator survived: {text} -> {out}"
