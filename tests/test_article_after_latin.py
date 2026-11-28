"""The article after a nativized Latin loanword reads the loanword as the word before it."""
import pytest

from arbtok.plugin import ArbtokG2PPlugin


@pytest.mark.parametrize("lang, text, article", [
    # Qafisheh 1970, pp. 20-21: il- after a consonant, al- at the start.
    ("ar-KW", "عَلَى service الْيَوم", "ilˈjoːm"),
    ("ar-KW", "service الْيَوم", "ilˈjoːm"),
    # Punctuation after the loanword is a pause.
    ("ar-KW", "عَلَى service. الْيَوم", "alˈjoːm"),
    ("ar", "عَلَى service الْيَوم", "alˈjawm"),
])
def test_the_article_after_a_loanword(lang, text, article):
    p = ArbtokG2PPlugin(lang=lang, diacritize=True, nativize=True, pausal=True)
    assert p.transcribe(text).split()[-1] == article
