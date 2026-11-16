"""A number written with more than one thousands separator reads as its value.

`1,500` has always worked and `14,000,000` has not, which is the shape of a guard
that strips one separator and a body that strips all of them. The failure is
silent and expensive: the digits disappear, so a leak test sees clean text, and
what replaces them is a different number.

A separator is a thousands grouping only where every one of them is followed by
exactly three digits, end to end. A single separator followed by fewer digits,
or by more, is a decimal comma to a writer whose decimal mark is a comma, and
reads as the decimal rule reads a dot: `12,5` reads as `12.5` does, not as
`125`. A single grouping of exactly three digits stays ambiguous and keeps the
grouped reading: `1,500` is read as fifteen hundred, not as `1.5`.

Two or more separators that do not form a grouping are not one fraction either:
a number has one fractional part, so folding every group after the first
separator into it reads a number nobody wrote, and can drop digits a float
rounds away (`055,123,4567` lost its last group this way when this was tried).
`1,2,3` and `055,123,4567` are left to the digit-run fallback that already
existed for a shape this pass does not resolve, which reads every run and
drops none.
"""
import pytest

from arbtok.util import normalize

MILLION = "مليون"
ZERO = "صفر"
DECIMAL_MARK = "فاصلة"


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


@pytest.mark.parametrize("text,spoken", [
    ("12,5", "اثنا عشر فاصلة خمسة"),
    ("1,5", "واحد فاصلة خمسة"),
    ("0,75", "صفر فاصلة سبعة خمسة"),
    ("12,50", "اثنا عشر فاصلة خمسة"),
    ("3,14", "ثلاثة فاصلة واحد أربعة"),
    ("٢,٥", "اثنان فاصلة خمسة"),
])
def test_a_comma_followed_by_fewer_than_three_digits_reads_as_a_decimal(text, spoken):
    """`12,5` reads as `12.5` does: a comma to a decimal-comma writer, not a
    thousands separator with one digit missing from its group."""
    out = normalize(text, "ar")
    assert out == spoken, f"{text} -> {out}"
    assert DECIMAL_MARK in out, f"{text} -> {out}"


def test_a_single_group_of_exactly_three_digits_stays_ambiguous_and_grouped():
    """`1,500` carries no further comma to settle it either way, so it keeps the
    grouped reading it always had, matching a decimal reading of the same
    magnitude by coincidence."""
    out = normalize("1,500", "ar")
    assert out == "ألف وخمسمئة", out
    assert DECIMAL_MARK not in out, out


def test_a_well_formed_number_with_two_groupings_stays_grouped():
    """`1,500,000` has two separators, but both are followed by exactly three
    digits: a well-formed grouping, unaffected by the rule for a comma that
    does not group."""
    out = normalize("1,500,000", "ar")
    assert out == "مليون وخمسمئة ألف", out
    assert DECIMAL_MARK not in out, out
    assert "," not in out, out


@pytest.mark.parametrize("text,spoken", [
    ("1,2,3", "واحد,اثنان,ثلاثة"),
    ("1,500,00", "واحد,خمسمئة,صفر"),
    ("055,123,4567", "خمسة وخمسون,مئة وثلاثة وعشرون,أربعة آلاف وخمسمئة وسبعة وستون"),
    ("1,2,3,4", "واحد,اثنان,ثلاثة,أربعة"),
])
def test_two_or_more_non_grouping_separators_read_every_digit(text, spoken):
    """Two or more separators that do not form a complete grouping are not a
    single fraction: a number has one fractional part, so folding every group
    after the first separator into it reads a number nobody wrote, and can
    drop digits a float rounds away (`055,123,4567` lost its last group this
    way when this was tried). Each digit run is read on its own instead,
    exactly as it was before this pass tried to read the whole word, and no
    digit is dropped."""
    out = normalize(text, "ar")
    assert out == spoken, f"{text} -> {out}"
    assert DECIMAL_MARK not in out, out
