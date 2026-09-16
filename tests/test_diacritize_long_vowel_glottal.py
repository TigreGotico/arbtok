"""A mater lectionis must not acquire a hamza it was never written with.

`diacritize=True` used to read الموديل as `almuʔˈdiːl`, a glottal stop where the long
vowel belongs. The cause was in the fusion diacritizer, which is the default: an
unmarked letter position was free for the model to assign any class, including one that
seats a hamza, so a bare و became ؤ. The restoration exists for alif, where a writer
really does leave the hamza off (اكل for أكل), and is now limited to it -- on و or ي a
restored hamza is not a missing mark, it is a different letter.

Fixed in `arbtok/fusion.py`. These were `xfail(strict=True)` before the fix and are
plain assertions now; the one that remains xfail is a different disagreement, named
below. The five native controls must keep passing, because a fix that changed them
would be trading one defect for a worse one.
"""
from __future__ import annotations

import pytest

pytest.importorskip("orthography2ipa", reason="the pipeline needs orthography2ipa")


def _plugin(diacritize):
    from arbtok.plugin import ArbtokG2PPlugin
    return ArbtokG2PPlugin(lang="ar", diacritize=diacritize, nativize=True, pausal=True)


#: word, what the combined path gives today, what the diacritizer writes, and what
#: transcribing that diacritized string on its own gives -- which is the correct answer.
CASES = [
    ("الموديل", "almuʔˈdiːl", "الْمُوْدِيل", "almuːˈdiːl"),
    ("الموبايل", "almuːˈbaːʔil", "الْمُوبَايِل", "almuːˈbaːjil"),  # see the xfail below
    ("استوديو", "ʔisˈtuʔdijuː", "اسْتُوْدِيُو", "ʔisˈtuːdijuː"),
]


@pytest.mark.parametrize("word, _broken, diacritized, correct", CASES)
def test_the_diacritizer_writes_a_long_vowel_not_a_glottal(word, _broken, diacritized,
                                                           correct):
    """Neither half is at fault, which is the point of the bug report."""
    from arbtok.diacritize import LatticeDiacritizer
    assert LatticeDiacritizer().diacritize(word) == diacritized
    assert _plugin(False).transcribe(diacritized) == correct


@pytest.mark.parametrize("word, broken, _diacritized, _correct", CASES)
def test_no_glottal_is_restored_onto_a_mater_lectionis(word, broken, _diacritized,
                                                       _correct):
    """The defect itself, on all three words: no [ʔ] where the long vowel is."""
    got = _plugin(True).transcribe(word)
    assert got != broken, f"{word}: still the known-broken reading"
    assert "ʔ" not in got[1:], f"{word}: {got!r} still seats a hamza"


@pytest.mark.parametrize("word, correct", [
    ("الموديل", "almuːˈdiːl"),
    ("استوديو", "ʔisˈtuːdijuː"),
])
def test_the_combined_path_agrees_with_its_own_two_halves(word, correct):
    """What the report was: the two halves are each right, so the whole must be."""
    assert _plugin(True).transcribe(word) == correct


@pytest.mark.xfail(strict=True, reason="fusion writes الْمُوبَايْل where the lattice "
                                       "writes الْمُوبَايِل -- a ḥaraka disagreement "
                                       "between the two diacritizers, not the hamza; "
                                       "the bare موبايل reads muːˈbaːjl in both, so "
                                       "the final cluster predates this")
def test_the_two_diacritizers_agree_on_the_mobile_haraka():
    from arbtok.diacritize import LatticeDiacritizer
    p = _plugin(True)
    lattice = LatticeDiacritizer(lang="ar", waqf=True, lexicon=p.lexicon,
                                 dialect_lexicon=p.dialect_lexicon)
    assert p._diacritize("الموبايل") == lattice.diacritize("الموبايل")


@pytest.mark.parametrize("word, expected", [
    ("مدينة", "maˈdiːna"),
    ("موسيقى", "muːˈsiːqaː"),
    ("يوم", "ˈjawm"),
    ("نور", "ˈnuːr"),
    ("المدير", "almuˈdiːr"),
])
def test_native_words_with_the_same_letters_are_unaffected(word, expected):
    """و and ي as matres lectionis in ordinary Arabic, through the same path.

    These hold today. They are here so that a fix for the three above cannot be one
    that breaks ordinary Arabic to do it.
    """
    assert _plugin(True).transcribe(word) == expected
