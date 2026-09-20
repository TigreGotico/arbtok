"""A unit symbol after a number is read whatever case it is written in."""
import pytest

from arbtok.util import normalize


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
