"""The public list of resolvable varieties tracks the o2i registry.

``supported_lects()`` is enumerated from orthography2ipa, so it cannot drift
from the installed data set the way a hand-kept table would.
"""
from orthography2ipa import available_codes

import arbtok
from arbtok.dialects import Lect, spec_for_lang


def _arabic_codes():
    return {c for c in available_codes()
            if c in {"ar", "arb"} or c.startswith("ar-")}


def test_supported_lects_matches_the_registry():
    codes = {lect.code for lect in arbtok.supported_lects()}
    assert codes == _arabic_codes()


def test_supported_lects_excludes_the_lookalike_languages():
    """arc (Aramaic) and arn (Mapudungun) sort next to Arabic but are not it."""
    codes = {lect.code for lect in arbtok.supported_lects()}
    assert "arc" not in codes and "arn" not in codes


def test_every_listed_code_actually_resolves_to_itself():
    """A code the list advertises must be one ``lang=`` honours exactly."""
    for lect in arbtok.supported_lects():
        assert spec_for_lang(lect.code) == lect.code


def test_lects_are_sorted_and_carry_a_known_tier():
    lects = arbtok.supported_lects()
    assert lects == sorted(lects, key=lambda lect: lect.code)
    known = {"stub", "skeleton", "research", "production"}
    assert all(isinstance(lect, Lect) and lect.tier in known for lect in lects)


def test_msa_is_research_tier():
    assert next(l.tier for l in arbtok.supported_lects() if l.code == "ar") == "research"
