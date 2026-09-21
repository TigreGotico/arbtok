"""A shadda geminates a consonant, so it never doubles a reading that ends in `ː`.

A reading ending in the length mark is a vowel or a bare length mark: the letter
was read as a mater lectionis although it carries gemination. Doubling it emits
the vowel and its length twice, `aːaː`, which is not a phone and which a
character-level reader cannot see, since two length marks are simply two symbols
to it.
"""
import pytest

from arbtok.tokenizer import Sentence, WordToken

LENGTH_MARK = "ː"


def _cascade(word):
    return "".join(tok.ipa for tok in WordToken(surface=word, word_idx=0).tokens)


@pytest.mark.parametrize("word, expected", [
    # an alif carrying a shadda straight after the definite article: the alif is
    # a mater lectionis and reads `aː`, and the shadda used to repeat all of it
    ("الاّ", "alaː"),
    ("الاّلم", "alaːlm"),
    # the madda carries its own glottal stop and length, `ʔaː`
    ("الآّ", "alʔaː"),
], ids=["alif after the article", "alif after the article with a tail", "madda after the article"])
def test_a_mater_lectionis_is_not_geminated(word, expected):
    reading = _cascade(word)
    assert LENGTH_MARK * 2 not in reading
    assert reading.count(LENGTH_MARK) == 1
    assert reading == expected


@pytest.mark.parametrize("word, expected", [
    ("مَدَّ", "madda"),          # مَدَّ, a plain geminate
    ("القَّلَم", "alqqalam"),  # a moon letter after the article
    ("تِيّ", "tijj"),                 # a ya with a shadda is the consonant
    ("مُوّ", "muww"),                 # and so is a waw
], ids=["dal", "qaf after the article", "ya", "waw"])
def test_a_consonant_still_doubles(word, expected):
    """The half that must stay still: a reading that does not end in the length
    mark is a consonant, and its shadda still geminates it."""
    assert _cascade(word) == expected


def test_the_sentence_layer_agrees():
    """Whatever layer reads the word, the doubled vowel is gone from both."""
    reading = Sentence("الاّلم", lang="ar").ipa
    assert LENGTH_MARK * 2 not in reading
    assert "aːaː" not in reading
