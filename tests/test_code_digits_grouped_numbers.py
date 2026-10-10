"""Digits kept beside a Latin word are a name's digits, never a piece of a grouped number."""
import pytest

from arbtok.textnorm import TtsNorm, normalize_for_tts

KEEP = TtsNorm(keep_code_digits=True, cardinal_numbers=True, oblique_numbers=True, space_fused_hundreds=True,
               spoken_forms=False, canonical_unicode=False)
CARDINAL = TtsNorm(cardinal_numbers=True, spoken_forms=False, canonical_unicode=False)


@pytest.mark.parametrize("written", ["cash price 99,999", "cash price 12,500 ريال", "price 1,250.50",
                                     "السعر 99,999 cash", "price ٩٩٬٩٩٩", "price ١٢٣٤٥"])
def test_a_grouped_number_after_a_latin_word_is_spoken_whole(written):
    said = normalize_for_tts(written, "ar", KEEP)
    assert not any(c.isdigit() for c in said), said


def test_a_models_digits_are_still_kept():
    assert normalize_for_tts("سيارة MG 5 بسعر 70,000", "ar", KEEP) == "سيارة MG 5 بسعر سبعين ألف"
    assert normalize_for_tts("7 Series موديل 2024", "ar", KEEP).startswith("7 Series ")


@pytest.mark.parametrize("written, spoken", [
    ("12,5", "اثنا عشر فاصلة خمسة"),
    ("12,5 km", "اثنا عشر فاصلة خمسة km"),
    ("0,75", "صفر فاصلة سبعة خمسة"),
    ("3,14", "ثلاثة فاصلة واحد أربعة"),
    ("٢,٥", "اثنان فاصلة خمسة"),
    ("1,0000", "واحد"),
    ("1,0000 km", "واحد km"),
])
def test_a_short_or_overlong_comma_group_reads_as_a_decimal_on_the_cardinal_path(written, spoken):
    """cardinal_numbers (arbtok.textnorm._speak_numbers) is a separate number-reading
    path from spoken_forms (arbtok.util.normalize, fixed by #223's first half): a comma
    followed by one or two digits, or by more than three, is not a thousands grouping,
    and to a decimal-comma writer it marks the fraction — '12,5' reads as '12.5' does.
    Before this rule reached this path, the comma survived as written and the two
    halves were read as two separate numbers ('12,5' -> 'اثنا عشر,خمسة')."""
    assert normalize_for_tts(written, "ar", CARDINAL) == spoken


@pytest.mark.parametrize("written, spoken", [
    ("1,500", "ألف وخمسمئة"),
    ("1,234,567", "مليون ومئتان وأربعة وثلاثون ألف وخمسمئة وسبعة وستون"),
])
def test_a_well_formed_thousands_grouping_is_unchanged_on_the_cardinal_path(written, spoken):
    """A single grouping of exactly three digits, repeated, stays the ambiguous grouped
    integer it always read as: '1,500' is fifteen hundred, not '1.5'."""
    assert normalize_for_tts(written, "ar", CARDINAL) == spoken


def test_a_multi_comma_word_that_forms_no_grouping_reads_group_by_group_on_the_cardinal_path():
    """Two or more separators that do not form a grouping are not one fraction either: a
    number has one fractional part, so each comma-delimited group is read on its own,
    keeping every digit and the separators exactly as written — the same reading PR
    230's second commit gave this shape on the spoken_forms path."""
    assert normalize_for_tts("1,2,3", "ar", CARDINAL) == "واحد,اثنان,ثلاثة"
