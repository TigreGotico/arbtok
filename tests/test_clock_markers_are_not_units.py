"""A 12-hour clock marker after a time is not the unit that shares its symbol."""
import pytest

from arbtok.textnorm import normalize_for_tts


@pytest.mark.parametrize("written", [
    "at 7 pm", "الموعد 7 pm", "الموعد 7pm", "الموعد 7 PM", "الموعد 12 pm", "الموعد 7:30 pm", "الموعد 1 pm",
])
def test_a_clock_time_is_not_read_as_picometres(written):
    assert "بيكومتر" not in normalize_for_tts(written, "ar")


def test_a_length_in_picometres_is_still_a_unit():
    assert "بيكومتر" in normalize_for_tts("الطول 300 pm", "ar")


def test_thirteen_is_no_hour_of_the_12_hour_clock():
    assert "بيكومتر" in normalize_for_tts("الطول 13 pm", "ar")
