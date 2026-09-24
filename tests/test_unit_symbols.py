"""A unit symbol after a number is read whatever case it is written in."""
import pytest

from arbtok.textnorm import normalize_for_tts
from arbtok.util import normalize


@pytest.mark.parametrize("written, spoken", [
    ("1,500 km", "ألف وخمسمئة كيلومتر"),
    ("100,000 KM", "مئة ألف كيلومتر"),
], ids=["1,500 km", "100,000 KM"])
def test_a_grouped_number_before_a_unit_is_read(written, spoken):
    assert normalize_for_tts(written, "ar") == spoken


# A grouping is groups of three digits, so a dot before fewer than three is a decimal
# point even where the language writes its groupings with dots. The German reading of
# a dot-decimal has a defect of its own in the number pass and is pinned as it stands.
@pytest.mark.parametrize("lang, written, spoken", [
    ("fr", "0.5 km", "zéro virgule cinq kilomètres"),
    ("fr", "2.5 km", "deux virgule cinq kilomètres"),
    ("es", "0.5 km", "cero coma cinco kilómetros"),
    ("es", "2.5 km", "dos coma cinco kilómetros"),
    ("pt", "0.5 km", "zero vírgula cinco quilômetros"),
    ("pt", "2.5 km", "dois vírgula cinco quilômetros"),
    ("de", "2.5 km", "zwei Komma fünf null null Kilometer"),
])
def test_a_dot_decimal_is_not_a_grouping(lang, written, spoken):
    assert normalize_for_tts(written, lang) == spoken


@pytest.mark.parametrize("lang, written, spoken", [
    ("ar", "1,000,000 km", "مليون كيلومتر"),
    ("en", "1,000,000 %", "one million per cent"),
], ids=["ar", "en"])
def test_a_number_of_several_groups_is_read_whole(lang, written, spoken):
    assert normalize_for_tts(written, lang) == spoken


@pytest.mark.parametrize("lang, written, spoken", [
    ("ar", "12,5 km", "مئة وخمسة وعشرون km"),
    ("ar", "1,0000 km", "عشرة آلاف km"),
    ("en", "1,0000 %", "ten thousand %"),
], ids=["12,5 km", "1,0000 km", "1,0000 %"])
def test_a_separator_that_forms_no_grouping_leaves_the_number_to_the_number_pass(lang, written, spoken):
    """A shape that is no grouping is not this pass to read, and the match may not begin
    inside it either: the whole number goes to the number pass, which reads it as it
    always did, and the unit is left as written. The exact reading is pinned because
    asserting that a wrong one is absent passes on every other wrong one."""
    assert normalize_for_tts(written, lang) == spoken



@pytest.mark.parametrize("written, spoken", [
    ("it is 5 km away", "it is five kilometers away"),
    ("it is 5 KM away", "it is five kilometers away"),
    ("it is 5 Km away", "it is five kilometers away"),
])
def test_a_unit_is_read_in_any_case(written, spoken):
    assert normalize(written, "en") == spoken


@pytest.mark.parametrize("written", ["it weighs 3 Kg", "temperature 20 °c", "it costs 10 EUR or 5 KM"])
def test_no_casing_of_a_symbol_raises(written):
    assert isinstance(normalize(written, "en"), str)
