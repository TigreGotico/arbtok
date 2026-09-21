"""Every word exception produces a reading the grapheme rules do not.

An exception the rules already agree with is invisible: it cannot be told from a
live one by reading the table, and it hides the entries that carry real work. The
table was 21 entries and 15 of them were in that state.

The rules are consulted with the table emptied rather than with the module
attribute rebound, because the consumers import the dict by value: rebinding
``arbtok.dialects.WORD_EXCEPTIONS`` leaves every holder pointing at the original
and the comparison is then the exception path against itself.
"""
import pytest

from arbtok.dialects import WORD_EXCEPTIONS
from arbtok.tokenizer import Sentence

ENTRIES = sorted(WORD_EXCEPTIONS.items())


def _rules_only(word, without):
    saved = dict(WORD_EXCEPTIONS)
    WORD_EXCEPTIONS.clear()
    WORD_EXCEPTIONS.update({k: v for k, v in saved.items() if k != without})
    try:
        return Sentence(word, lang="ar", stress=False).ipa.replace("ˈ", "")
    finally:
        WORD_EXCEPTIONS.clear()
        WORD_EXCEPTIONS.update(saved)


def test_the_harness_can_actually_see_the_table():
    """Emptying the table has to change a reading, or every case below passes vacuously.
    The probe is an entry known to be load-bearing: a dead one would prove nothing."""
    word = "عَمْرٌو"
    assert word in WORD_EXCEPTIONS
    assert _rules_only(word, word) != WORD_EXCEPTIONS[word].replace("ˈ", "")


@pytest.mark.parametrize("word, ipa", ENTRIES, ids=[w for w, _ in ENTRIES])
def test_an_exception_reads_the_word_differently_from_the_rules(word, ipa):
    assert _rules_only(word, word) != ipa.replace("ˈ", "")


@pytest.mark.parametrize("word, ipa", ENTRIES, ids=[w for w, _ in ENTRIES])
def test_an_exception_is_what_the_word_actually_reads(word, ipa):
    assert Sentence(word, lang="ar", stress=False).ipa.replace("ˈ", "") == ipa.replace("ˈ", "")
