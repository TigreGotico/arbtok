"""A lect's ISO 639-3 code resolves back to the lect it was given for."""
import pytest

from arbtok.dialects import _SPEC_LANGUAGE_CODES, lect_code, spec_for_lang


@pytest.mark.parametrize("spec, code", sorted(_SPEC_LANGUAGE_CODES.items()))
def test_a_lect_code_resolves_to_its_own_spec(spec, code):
    assert lect_code(spec) == code
    assert spec_for_lang(code) == spec


@pytest.mark.parametrize("tag, spec", [
    ("arz", "ar-EG"), ("ARZ", "ar-EG"), ("acw", "ar-SA-x-hejaz"),
    ("afb", "ar-x-gulf"), ("ars", "ar-SA-x-najd"), ("arz-EG", "ar-EG"),
])
def test_a_tag_led_by_a_lect_code_names_that_lect(tag, spec):
    assert spec_for_lang(tag) == spec


@pytest.mark.parametrize("tag, spec", [("ar", "ar"), ("ar-EG", "ar-EG"), ("ar-SA", "ar-SA-x-najd")])
def test_macrolanguage_tags_resolve_as_before(tag, spec):
    assert spec_for_lang(tag) == spec


@pytest.mark.parametrize("tag, spec", [
    ("arz-x-saidi", "ar-EG-x-saidi"), ("arz-x-fayyum", "ar-EG-x-fayyum"),
    ("ars-x-qassim", "ar-SA-x-qassim"), ("ars-SA-x-dawasir", "ar-SA-x-dawasir"),
])
def test_a_sub_lect_in_a_subtag_outranks_the_lect_code(tag, spec):
    """The code names the lect; a subtag naming one of its varieties is more specific."""
    assert spec_for_lang(tag) == spec
