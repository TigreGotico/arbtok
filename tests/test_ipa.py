"""
gold test set defined in arbtok.test
"""
import string

import pytest

from arbtok.test import ALL_TEST_CASES
from arbtok.tokenizer import Sentence, WORD_EXCEPTIONS, WordToken, PUNCT


def test_hardcoded_wordlist():
    """Built-in word dictionary."""
    for text, expected in WORD_EXCEPTIONS.items():
        assert WordToken(text, word_idx=0).ipa == expected


def test_punctuation_preservation():
    """Ensure non-Arabic characters and punctuation are handled correctly."""
    text = "يَوْم جميل!"
    result = Sentence(text).ipa
    assert "!" in result
    assert result.startswith("jawm")


@pytest.mark.parametrize("arabic_text, expected_ipa, description", ALL_TEST_CASES)
def test_arabic_to_ipa(arabic_text, expected_ipa, description):
    """
    Parametrized test to verify Arabic to IPA conversion.
    The description helps identify which phonological rule failed.
    """
    result = Sentence(arabic_text).ipa
    assert result.strip(PUNCT + string.whitespace) == expected_ipa.strip(
        PUNCT + string.whitespace), f"Failed {description}: Input '{arabic_text}'"
