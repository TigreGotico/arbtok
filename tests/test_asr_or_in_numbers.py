"""A recognizer's او inside a spoken number is the conjunction و, said u- in Saudi and
Gulf speech; everywhere else او is "or" and stays."""
from importlib.metadata import version

import pytest

from arbtok import textnorm
from arbtok.textnorm import AsrNorm, CER_NORM, TRUTH_CHECK, normalize_asr

JOINED = [
    ("ست مية او عشرة الف وميتين", "ست مية وعشرة الف وميتين", "610200"),
    ("ثلاثمية او عشرة الف وميتين", "ثلاثمية وعشرة الف وميتين", "310200"),
    ("خمسمية او عشرين الف", "خمسمية وعشرين الف", "520000"),
    ("مليون وست مية او عشرة الف", "مليون وست مية وعشرة الف", "1610000"),
]

APART = [
    ("الف او خمسمية", "1000 او 500"),
    ("الفين او ثلاثة", "2000 او 3"),
    ("مية او اثنين", "100 او 2"),
    ("تسعمية او عشرة ملايين", "900 او 10000000"),
    ("ثلاثة او اربعة", "3 او 4"),
]


def test_the_parser_under_test_is_named():
    print("ovos-number-parser", version("ovos-number-parser"))


@pytest.mark.parametrize("heard, repaired, digits", JOINED, ids=[d for _, _, d in JOINED])
def test_or_inside_a_spoken_number_is_and(heard, repaired, digits):
    assert normalize_asr(heard, fix_asr_errors=True) == repaired
    assert normalize_asr(heard, fix_asr_errors=True, spoken_numbers_to_digits=True) == digits


@pytest.mark.parametrize("heard, digits", APART, ids=[h for h, _ in APART])
def test_or_between_two_numbers_stays_or(heard, digits):
    assert normalize_asr(heard, fix_asr_errors=True) == heard
    assert normalize_asr(heard, fix_asr_errors=True, spoken_numbers_to_digits=True) == digits


@pytest.mark.parametrize("heard", [h for h, _, _ in JOINED] + [h for h, _ in APART])
def test_with_the_repair_off_or_is_left_as_written(heard):
    assert normalize_asr(heard) == heard
    for config in (TRUTH_CHECK, CER_NORM):
        assert normalize_asr(heard, config).split().count("او") == 1


def test_the_repair_keeps_the_rest_of_the_sentence():
    heard = "السعر ست مية او عشرة الف ريال او اكثر"
    assert normalize_asr(heard, fix_asr_errors=True) == "السعر ست مية وعشرة الف ريال او اكثر"
    assert normalize_asr(heard, fix_asr_errors=True, spoken_numbers_to_digits=True) == "السعر 610000 ريال او اكثر"


def test_the_repair_is_arabic_only_and_off_by_default():
    assert AsrNorm().fix_asr_errors is False
    bundles = [getattr(textnorm, name) for name in textnorm.__all__
               if isinstance(getattr(textnorm, name), AsrNorm)]
    assert len(bundles) == 6 and not any(bundle.fix_asr_errors for bundle in bundles)
    assert normalize_asr("ست مية او عشرة الف", fix_asr_errors=True, lang="fa") == "ست مية او عشرة الف"
    described = AsrNorm(fix_asr_errors=True).describe()
    assert ": fix_asr_errors;" in described and "; ovos-number-parser " in described


@pytest.mark.parametrize("fused, digits", [("ثلاثمية", "300"), ("خمسميه", "500"), ("تسعماية", "900")])
def test_a_hundred_written_fused_with_its_unit_is_arabic_and_stays_as_written(fused, digits):
    for fix in (False, True):
        assert normalize_asr(fused, fix_asr_errors=fix) == fused
        assert normalize_asr(fused, fix_asr_errors=fix, spoken_numbers_to_digits=True) == digits
