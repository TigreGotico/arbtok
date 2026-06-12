"""Dialect reflex cascade tests.

Gold data and reasoning live in ``arbtok.test_dialects`` (model-generated,
pending native-speaker validation).
"""
import string

import pytest

from arbtok.test_dialects import (
    ALL_DIALECT_TESTS,
    EGYPTIAN_TESTS,
    LEVANTINE_TESTS,
    GULF_TESTS,
    MAGHREBI_TESTS,
)
from arbtok.tokenizer import PUNCT, Sentence
from arbtok.dialects import (
    ArabicDialect,
    dialect_for_lang,
    consonant_ipa,
    ARABIC_TO_IPA_CONSONANTS,
)

_STRIP = PUNCT + string.whitespace


@pytest.mark.parametrize("arabic, expected, dialect, reasoning", ALL_DIALECT_TESTS)
def test_dialect_to_ipa(arabic, expected, dialect, reasoning):
    """Each zone gold item realizes to its reasoned target IPA."""
    result = Sentence(arabic, dialect=dialect).ipa
    assert result.strip(_STRIP) == expected.strip(_STRIP), (
        f"{dialect.value}: '{arabic}' -> '{result}', expected '{expected}'. "
        f"Reasoning: {reasoning}"
    )


@pytest.mark.parametrize("arabic, expected, dialect, reasoning", ALL_DIALECT_TESTS)
def test_msa_unchanged_by_dialect_words(arabic, expected, dialect, reasoning):
    """The same orthography under dialect=MSA equals the reference cascade.

    Regression gate: dialect support must never alter MSA output, even for
    the very words the dialect golds exercise.
    """
    msa_default = Sentence(arabic).ipa
    msa_explicit = Sentence(arabic, dialect=ArabicDialect.MSA).ipa
    cla_explicit = Sentence(arabic, dialect=ArabicDialect.CLA).ipa
    assert msa_explicit == msa_default
    assert cla_explicit == msa_default


def test_zone_counts():
    """Each zone ships a non-trivial gold set (10-14 items)."""
    for name, cases in (
        ("EGYPTIAN", EGYPTIAN_TESTS),
        ("LEVANTINE", LEVANTINE_TESTS),
        ("GULF", GULF_TESTS),
        ("MAGHREBI", MAGHREBI_TESTS),
    ):
        assert 10 <= len(cases) <= 14, f"{name}: {len(cases)} items"


def test_dialect_for_lang():
    """BCP-47 region subtags resolve to the right zone; bare/unknown → MSA."""
    assert dialect_for_lang("ar-EG") == ArabicDialect.EGYPTIAN
    assert dialect_for_lang("ar-SY") == ArabicDialect.LEVANTINE
    assert dialect_for_lang("ar-LB") == ArabicDialect.LEVANTINE
    assert dialect_for_lang("ar-JO") == ArabicDialect.LEVANTINE
    assert dialect_for_lang("ar-PS") == ArabicDialect.LEVANTINE
    assert dialect_for_lang("ar-AE") == ArabicDialect.GULF
    assert dialect_for_lang("ar-SA") == ArabicDialect.GULF
    assert dialect_for_lang("ar-KW") == ArabicDialect.GULF
    assert dialect_for_lang("ar-MA") == ArabicDialect.MAGHREBI
    assert dialect_for_lang("ar-DZ") == ArabicDialect.MAGHREBI
    assert dialect_for_lang("ar_TN") == ArabicDialect.MAGHREBI  # underscore form
    assert dialect_for_lang("ar") == ArabicDialect.MSA
    assert dialect_for_lang("arb") == ArabicDialect.MSA
    assert dialect_for_lang("ar-XX") == ArabicDialect.MSA
    assert dialect_for_lang("") == ArabicDialect.MSA
    assert dialect_for_lang(None) == ArabicDialect.MSA


def test_consonant_override_is_identity_for_reference():
    """MSA/CLA never override a consonant; zones override the documented set."""
    qaf = "ق"
    for grapheme, msa in ARABIC_TO_IPA_CONSONANTS.items():
        assert consonant_ipa(grapheme, ArabicDialect.MSA, msa) == msa
        assert consonant_ipa(grapheme, ArabicDialect.CLA, msa) == msa
    # spot-check a zone reflex
    assert consonant_ipa(qaf, ArabicDialect.GULF, "q") == "g"
    assert consonant_ipa(qaf, ArabicDialect.EGYPTIAN, "q") == "ʔ"
