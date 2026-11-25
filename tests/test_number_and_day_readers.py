"""The number and day readers in arbtok.textnorm. The day readers call chronologia directly, and
give the values that the ovos-date-parser layer gave before. The expected values are that
layer's own answers, written down before the change."""
import pytest

from arbtok.textnorm import (_hour_value, _is_day, _number_value, _numbers_to_digits, _one_number,
                             _period_hour)

NUMBER_VALUES = [
    ("خمسة وعشرين", 25), ("ثمانية", 8), ("واحد", 1), ("ثلاثة ملايين", 3000000),
    ("مية و خمسين الف", 150000), ("ثلث", 1 / 3), ("٠٠٧", 7), ("١٢٫٥", 12.5),
    ("الثامنة", None), ("الحادي والعشرين", None), ("كتاب", None),
]


@pytest.mark.parametrize("words, value", NUMBER_VALUES)
def test_number_value(words, value):
    assert _number_value(words) == value


@pytest.mark.parametrize("words, value", [("الثامنة", 8), ("الحادي والعشرين", 21), ("ثمانية", 8), ("كتاب", None)])
def test_an_ordinal_is_an_hour(words, value):
    assert _hour_value(words) == value


@pytest.mark.parametrize("words, value", [("خمسة وعشرين", 25), ("ثمانية", 8), ("٠٠٧", 7), ("ثلث", None),
                                          ("الثامنة", None), ("١٢٫٥", None), ("كتاب", None)])
def test_one_number_is_a_whole_number_of_digits(words, value):
    assert _one_number(words) == value


@pytest.mark.parametrize("text, written", [
    ("  خمسة  ست  ", "  5 6  "), ("ثلث", "0.3333333333333333"), ("١٢٣٤", "1234"),
    ("الاول", "الاول"), ("x_1", "x_1"), ("كتاب", "كتاب"), ("", ""),
])
def test_numbers_to_digits(text, written):
    assert _numbers_to_digits(text, "ar") == written


def test_a_language_numtag_has_no_words_for_is_left_as_written():
    assert _numbers_to_digits("خمسة", "xx") == "خمسة"


@pytest.mark.parametrize("word, day", [("اليوم", True), ("غدا", True), ("الخميس", True), ("كتاب", False),
                                       ("١٢٣٤٥", False), ("ومارس", False)])
def test_is_day(word, day):
    assert _is_day(word) is day


@pytest.mark.parametrize("hour, word, read", [(5, "ظهرا", 17), (8, "مساء", 20), (5, "غدا", 5), (8, "غدا", 8),
                                              (5, "اليوم", None), (8, "كتاب", None)])
def test_period_hour(hour, word, read):
    assert _period_hour(hour, word) == read
