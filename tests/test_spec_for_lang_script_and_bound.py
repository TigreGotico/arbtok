"""A script subtag on an Arabic variety picks no spec of its own, and the
closest-spec bound admits every Arabic variety and no other language."""
import pytest
from linguatag import lang_distance
from orthography2ipa import resolve

from arbtok.dialects import _MAX_SPEC_DISTANCE, DEFAULT_LANG, _arabic_codes, spec_for_lang


@pytest.mark.parametrize("tag, spec", [
    ("bbz-Arab-TD", "bbz"), ("bbz-Latn-TD", "bbz"),
    ("acm-Latn", "acm-IQ"), ("acm-Latn-IQ", "acm-IQ"), ("ary-Latn", "ary-MA"),
    ("ayl-Latn", "ayl"), ("apc-Latn-LB", "apc-LB"), ("mey-Latn", "mey-MR"),
    ("pga-Latn-SS", "pga"),
])
def test_an_arabic_variety_reads_as_its_lect_in_a_script_the_lect_reads(tag, spec):
    assert spec_for_lang(tag) == resolve(spec)


@pytest.mark.parametrize("tag", ["acm-Latn", "ayl-Latn-LY", "apc-Latn", "ajp-Latn-JO", "shu-Latn-TD"])
def test_a_latin_script_variety_reads_as_the_tag_without_its_script(tag):
    assert spec_for_lang(tag) == spec_for_lang(tag.replace("-Latn", ""))


@pytest.mark.parametrize("tag", ["pga-Arab-SA", "pga-Arab", "acy-Arab-TR", "ACY-ARAB"])
def test_a_latin_script_lect_does_not_read_arabic_script(tag):
    assert spec_for_lang(tag) == DEFAULT_LANG


def test_a_tag_that_names_buckwalter_still_reaches_it():
    assert spec_for_lang("ar-Latn-x-buckwalt") == resolve("ar-Latn-x-buckwalt")


@pytest.mark.parametrize("tag, spec", [("mey-SN", "mey-MR"), ("mey-Arab-SN", "mey-MR")])
def test_a_lect_of_the_own_language_outranks_msa_at_any_region(tag, spec):
    assert spec_for_lang(tag) == resolve(spec)


@pytest.mark.parametrize("tag", ["ckb", "ckb-IQ", "ckb-Arab-IQ", "en", "en-US", "fa-IR"])
def test_another_language_raises(tag):
    with pytest.raises(ValueError, match="not an Arabic variety"):
        spec_for_lang(tag)


def test_the_bound_admits_every_arabic_variety_and_no_other_language():
    codes = _arabic_codes()
    regions = {s for code in codes for s in code.split("-")[1:] if len(s) == 2 and s.isupper()}
    languages = {code.split("-")[0] for code in codes} | {"ajp", "bbz"}
    # mey stands 54 from mey-MR outside Mauritania; the own-language rule takes it.
    farthest = max(min(lang_distance(f"{language}-{region}", code) for code in codes)
                   for language in languages if language != "mey" for region in regions)
    nearest_other = min(lang_distance("ckb", code) for code in codes)
    assert farthest == 5
    assert nearest_other == 30
    assert farthest <= _MAX_SPEC_DISTANCE < nearest_other
