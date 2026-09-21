"""A shadda at the fourth character reads what the article actually did.

The article assimilates into a SUN letter, and the sun letter is doubled where
it is read. A moon letter is not: the article keeps its lam, and a shadda on the
moon letter still has a consonant of its own to geminate. The guard dropped the
shadda for both, on a reason that only holds for one of them.
"""
import pytest

from arbtok.tokenizer import WordToken


def _cascade(word):
    return "".join(tok.ipa for tok in WordToken(surface=word, word_idx=0).tokens)


@pytest.mark.parametrize("word, expected", [
    ("القَّلَم", "alqqalam"),
    ("الكَّتب", "alkkatb"),
    ("البَّاب", "albbaːb"),
    ("المَّاء", "almmaːʔ"),
    # a real row of the omniasr Arabic dialects set writes the Levantine
    # الجُّمعة with a shadda on a moon letter, and the word lattice reads it
    # aldʒdʒumʕa; the cascade dropped the gemination and disagreed with it
    ("الجُّمعة", "aldʒdʒumʕ"),
], ids=["qaf", "kaf", "ba", "mim", "jim in a corpus row"])
def test_a_moon_letter_keeps_its_gemination(word, expected):
    """The article's lam stays before a moon letter, so nothing doubled the
    letter for the shadda, and dropping the shadda loses the gemination."""
    assert _cascade(word) == expected


@pytest.mark.parametrize("word, expected", [
    ("الشَّمس", "aʃʃams"),  # written without the sukun on the lam
    ("الرَّجل", "arradʒl"),
    ("النَّاس", "annaːs"),
], ids=["shin", "ra", "nun"])
def test_a_sun_letter_is_doubled_once(word, expected):
    """The sun letter was already doubled where it was read, so its shadda has
    nothing left to do and stays silent."""
    assert _cascade(word) == expected
