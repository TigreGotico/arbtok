"""`diacritize=True` does not transcribe the string the diacritizer returns.

A long vowel comes out as a glottal stop. The diacritizer is right and the bare
transcription of its output is right; only the combined path is wrong, so the defect
sits between them rather than in either.

These are `xfail(strict=True)`: they fail today and the run goes red the moment they
start passing, which is what tells whoever fixes the cause that it is fixed. The five
native controls are plain assertions -- they pass now and must keep passing, because a
"fix" that changed them would be trading this defect for a worse one.
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
    ("الموبايل", "almuːˈbaːʔil", "الْمُوبَايِل", "almuːˈbaːjil"),
    ("استوديو", "ʔisˈtuʔdijuː", "اسْتُوْدِيُو", "ʔisˈtuːdijuː"),
]


@pytest.mark.parametrize("word, _broken, diacritized, correct", CASES)
def test_the_diacritizer_writes_a_long_vowel_not_a_glottal(word, _broken, diacritized,
                                                           correct):
    """Neither half is at fault, which is the point of the bug report."""
    from arbtok.diacritize import LatticeDiacritizer
    assert LatticeDiacritizer().diacritize(word) == diacritized
    assert _plugin(False).transcribe(diacritized) == correct


@pytest.mark.xfail(strict=True, reason="diacritize=True emits [ʔ] where the "
                                       "diacritizer wrote a long vowel; cause not "
                                       "located")
@pytest.mark.parametrize("word, broken, _diacritized, correct", CASES)
def test_the_combined_path_agrees_with_its_own_two_halves(word, broken, _diacritized,
                                                          correct):
    got = _plugin(True).transcribe(word)
    assert got != broken, f"{word}: still the known-broken reading"
    assert got == correct, f"{word}: {got!r} != {correct!r}"


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
