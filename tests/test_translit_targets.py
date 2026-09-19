"""A guest sound may only be projected onto a sound.

`_targets` filtered the declared inventory by asking `orthography2ipa`'s own
tokenizer whether a reading was a single token. That question is circular: a spec
tokenizes `al` as one unit *because* it declares `al` as the reading of the article,
so the article came back as a candidate phoneme. Across the Arabic specs 2,748
declared readings reached the projector that way -- `al`, `bil`, `kal`, `lil`, `ʔa`,
`iθθ`, `awa` -- and French /y/, having nowhere rounded and front to go, landed on
`bi` on 34 lects: one guest vowel replaced by a consonant and a vowel.
"""
import pytest

from arbtok import translit
from arbtok.dialects import supported_lects


ARABIC_LECTS = sorted(l.code for l in supported_lects())


def _sample(n=12):
    return ARABIC_LECTS[:: max(1, len(ARABIC_LECTS) // n)][:n]


@pytest.mark.parametrize("lect", _sample())
def test_every_projection_target_is_one_phoneme(lect):
    """The set a guest is projected onto contains sounds and nothing else."""
    bad = [p for p in translit._targets(lect) if len(translit.segment_ipa(p)) != 1]
    assert not bad, f"{lect} offers {len(bad)} non-phoneme targets, e.g. {bad[:6]}"


@pytest.mark.parametrize("lect", _sample())
def test_no_lect_is_left_with_nothing_to_project_onto(lect):
    """The narrower filter must not empty a spec: an empty target set makes
    `_project` return None and a guest segment passes through unadapted."""
    assert len(translit._targets(lect)) >= 20, translit._targets(lect)


@pytest.mark.parametrize("segment", ["y", "ʉ", "ɵ", "ɨ"])
def test_a_guest_vowel_lands_on_a_vowel_not_a_syllable(segment):
    """French /y/ in *bureau*, /ɨ/ and the rest: one sound in, one sound out."""
    for lect in ("ar", "ar-MA", "ar-EG", "ar-SA-x-najd"):
        got = translit._project(segment, lect)
        assert got is not None, f"{lect}: {segment} projects nowhere"
        assert len(translit.segment_ipa(got)) == 1, f"{lect}: {segment} -> {got}"


def test_the_arabic_article_is_not_a_phoneme():
    """The reading that made the defect visible, pinned by name."""
    for lect in ("ar", "ar-MA", "ar-LB"):
        targets = translit._targets(lect)
        for reading in ("al", "bil", "kal", "lil", "ʔa"):
            assert reading not in targets, f"{lect} offers {reading!r} as a phoneme"
