"""A character's fragment can depend on the fragment of the character before it.

A long run of such characters is read without growing the call stack and in time
linear in the run, so one degenerate transcript cannot take a batch down with it.
"""
import pytest

from arbtok.tokenizer import CharToken, WordToken

ALIF, FATHA, KASRA, BA = "ا", "َ", "ِ", "ب"
ZERO_WIDTH_SPACE, RIGHT_TO_LEFT_MARK = "\u200B", "\u200F"


@pytest.mark.parametrize("run", [
    (ZERO_WIDTH_SPACE + RIGHT_TO_LEFT_MARK) * 4094,  # the shape of a transcript found in the wild
    KASRA * 5000,
    BA + FATHA + ALIF * 5000,
], ids=["zero-width marks", "kasras", "alifs after a fatha"])
def test_a_run_longer_than_the_call_stack_is_read(run):
    tokens = WordToken(surface=run, word_idx=0).tokens
    assert len(tokens) > 3000, "the fixture no longer reaches the token chain it is about"
    assert isinstance(tokens[-1].ipa, str)


def test_a_token_in_a_run_is_read_once_per_rule_chain(monkeypatch):
    reads = []
    fragment = CharToken.ipa
    monkeypatch.setattr(CharToken, "ipa", property(lambda tok: reads.append(tok.char_idx) or fragment.fget(tok)))
    tokens = WordToken(surface=BA + FATHA + ALIF * 18, word_idx=0).tokens
    tokens[-1].ipa
    assert len(reads) <= 2 * len(tokens)


@pytest.mark.parametrize("word, fragments", [
    (BA + FATHA + ALIF, ["b", "a", "ː"]),
    (BA + KASRA + KASRA, ["b", "i", ""]),
])
def test_the_rules_that_look_back_still_read_what_they_read(word, fragments):
    assert [t.ipa for t in WordToken(surface=word, word_idx=0).tokens] == fragments
