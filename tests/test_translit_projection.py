"""A guest vowel with no counterpart in the matrix lands on its own quality.

`segment_distance` returns one constant for every candidate when the guest's quality
is absent from the matrix altogether. `min` over that tie returns whichever sorts
first, which is alphabetical -- so [o] landed on [a] and *video* came out `fidiaː` on
every lect declaring no /o/, the pan-Arabic default among them.
"""
import pytest

from arbtok import translit


@pytest.mark.parametrize("segment, expected", [
    ("o", "u"), ("oː", "uː"), ("ɔ", "ʊ"),
])
def test_a_mid_back_vowel_raises_rather_than_lowering(segment, expected):
    """[o] is one step from [u] and three from [a]; the metric cannot see it."""
    assert translit._project(segment, "ar") == expected


@pytest.mark.parametrize("lect", [
    "ar", "ar-SA-x-najd", "ar-EG", "ar-LB", "ar-x-gulf", "ar-MA", "ar-IQ", "ar-YE",
])
def test_no_lect_lowers_a_mid_back_vowel_to_a_low_one(lect):
    """Whatever a lect declares, [o] must not come out as [a].

    Asserted on the projection rather than on a transliterated word: the reading of
    a word also depends on which donor lexicon is registered, so a word-level
    assertion here would be testing two things and would move when either changed.
    """
    for segment in ("o", "oː"):
        got = translit._project(segment, lect)
        assert got is not None, f"{lect}: {segment} projects nowhere"
        assert got[0] not in "aɑæ", f"{lect}: {segment} -> {got}"


def test_a_lect_that_declares_the_quality_is_untouched():
    """The tie-break fires only on a tie: ar-SA-x-najd declares /o/ and keeps it."""
    assert translit._project("o", "ar-SA-x-najd") == "o"
    assert translit._project("oː", "ar-EG") == "oː"
