"""One spoken form written several ways: the dialect closing "في أمان الله" is one word
in some transcripts and three in a recogniser's, and a character comparison must not
count that as a lost ending."""
import dataclasses

import pytest

from arbtok import textnorm
from arbtok.textnorm import AsrNorm, CER_NORM, CER_NORM_MARKS_FIRST, normalize_asr

THREE_WORDS = normalize_asr("في أمان الله", CER_NORM_MARKS_FIRST)

FUSED = ["فمانيلا", "فمان الله", "في مان الله", "فأمان الله", "فامان الله", "فأمانيلا",
         "في أمان الله", "في امان الله", "في إمان الله", "فى مان الله", "فى أمان الله"]


def edits(a, b):
    """Levenshtein distance, the quantity a character-error rate counts."""
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


@pytest.mark.parametrize("bundle", [CER_NORM, CER_NORM_MARKS_FIRST], ids=["CER_NORM", "CER_NORM_MARKS_FIRST"])
@pytest.mark.parametrize("written", FUSED)
def test_every_spelling_of_the_closing_normalises_to_the_three_words(bundle, written):
    assert normalize_asr(written, bundle) == normalize_asr("في أمان الله", bundle)
    assert normalize_asr(written, bundle).count(" ") == 2


@pytest.mark.parametrize("bundle", [CER_NORM, CER_NORM_MARKS_FIRST], ids=["CER_NORM", "CER_NORM_MARKS_FIRST"])
@pytest.mark.parametrize("written", ["وفمان الله", "وفمانيلا", "وفي مان الله", "وفى امان الله"])
def test_a_leading_conjunction_stays_on_the_closing(bundle, written):
    assert normalize_asr(written, bundle) == "و" + normalize_asr("في أمان الله", bundle)


def test_the_fused_word_costs_no_edit_against_the_recognisers_three_words():
    assert edits("فمانيلا", "في أمان الله") > 0
    fused = normalize_asr("شكرا لكم فمانيلا", CER_NORM_MARKS_FIRST)
    heard = normalize_asr("شكرا لكم في أمان الله", CER_NORM_MARKS_FIRST)
    assert edits(fused, heard) == 0


def test_the_closing_is_found_inside_a_sentence_and_beside_punctuation():
    assert normalize_asr("مع السلامة، فمان الله.", CER_NORM_MARKS_FIRST) == f"مع السلامه {THREE_WORDS}"
    assert normalize_asr("فَمَانِ اللهِ", CER_NORM_MARKS_FIRST) == THREE_WORDS


@pytest.mark.parametrize("text", ["في مانيلا", "سافرت الى مانيلا", "الامانة", "فمانيلا1", "كفمان الله", "امان الله"])
def test_other_text_is_left_alone(text):
    without = dataclasses.replace(CER_NORM_MARKS_FIRST, unify_spoken_variants=False)
    assert normalize_asr(text, CER_NORM_MARKS_FIRST) == normalize_asr(text, without)


def test_the_rule_is_off_unless_asked_for_and_arabic_only():
    assert AsrNorm().unify_spoken_variants is False
    assert normalize_asr("فمانيلا", unify_spoken_variants=False) == "فمانيلا"
    assert normalize_asr("فمانيلا", unify_spoken_variants=True) == "في أمان الله"
    assert normalize_asr("فمانيلا", unify_spoken_variants=True, lang="fa") == "فمانيلا"
    assert ": unify_spoken_variants" in AsrNorm(unify_spoken_variants=True).describe()
    on = [n for n in textnorm.__all__ if isinstance(getattr(textnorm, n), AsrNorm)
          and getattr(textnorm, n).unify_spoken_variants]
    assert sorted(on) == ["CER_NORM", "CER_NORM_MARKS_FIRST"]
