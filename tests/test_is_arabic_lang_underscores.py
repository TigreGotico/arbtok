"""``is_arabic_lang`` and ``spec_for_lang`` normalise the same underscore-for-hyphen
tags the same way. ``spec_for_lang`` already replaces an underscore with a hyphen
before resolving a tag; ``is_arabic_lang`` used not to, so the same library
phonemised ``ar_SA`` as Saudi Arabic and then refused to call it Arabic."""
import pytest

from arbtok import is_arabic_lang
from arbtok.dialects import spec_for_lang


def test_an_underscore_tag_is_arabic_the_defect_this_guards():
    """arbtok.spec_for_lang("ar_SA") resolves to the Saudi spec, so is_arabic_lang
    must not say the same tag is not Arabic."""
    assert is_arabic_lang("ar_SA")


@pytest.mark.parametrize("hyphenated,underscored", [
    ("ar-SA", "ar_SA"),
    ("ar-EG", "ar_EG"),
    ("ar-SA-x-najd", "ar_SA_x_najd"),
    ("AR-eg", "AR_eg"),
    ("ar-x-gulf", "ar_x_gulf"),
])
def test_spec_for_lang_and_is_arabic_lang_agree_on_underscore_and_hyphen_spellings(hyphenated, underscored):
    assert spec_for_lang(hyphenated) == spec_for_lang(underscored)
    assert is_arabic_lang(hyphenated) and is_arabic_lang(underscored)


@pytest.mark.parametrize("tag", ["en_GB", "fr_FR", "en_US"])
def test_a_non_arabic_tag_with_an_underscore_is_still_not_arabic(tag):
    assert not is_arabic_lang(tag)
