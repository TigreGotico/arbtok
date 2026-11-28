"""The article vowel after a consonant-final word, in the lects whose grammar states it."""
import pytest

from arbtok.plugin import ArbtokG2PPlugin


def words(lect, text):
    return ArbtokG2PPlugin(lang=lect, diacritize=False, nativize=False, pausal=False).transcribe(text).split()


# Gulf: Qafisheh 1970, Basic Gulf Arabic, pp. 20-21. Lebanese: Feghali 1919, §VI.
# Cairene: Abdel-Massih et al. 1979, "Definite article: form".
@pytest.mark.parametrize("lect", ["ar-AE", "ar-KW", "ar-QA", "ar-x-gulf", "ar-LB", "ar-EG"])
def test_the_article_takes_i_after_a_consonant(lect):
    assert words(lect, "زَيْن الْيَوم")[1].lstrip("ˈ").startswith("il")


@pytest.mark.parametrize("lect,vowel", [("ar-AE", "a"), ("ar-x-gulf", "a"), ("ar-LB", "i"), ("ar-EG", "i")])
def test_the_article_vowel_at_the_start(lect, vowel):
    assert words(lect, "الْيَوم زَيْن")[0].lstrip("ˈ").startswith(vowel + "l")


# Sanʿani: Qafisheh 1984, Yemeni Arabic I, pp. 37-38 ("min al-yaman"). Sudanese: Dickins §4.2.
@pytest.mark.parametrize("lect", ["ar-YE", "ar-SD"])
def test_the_article_keeps_a_after_a_consonant(lect):
    assert words(lect, "زَيْن الْيَوم")[1].lstrip("ˈ").startswith("al")
