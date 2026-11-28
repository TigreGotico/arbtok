"""The loom sandhi fragment gives the IR arbtok's cross-word forms."""
import json
from pathlib import Path

import pytest
from orthography2ipa.ir.compiler import build_ir
from orthography2ipa.ir.interpreter import Interpreter

FRAGMENT = json.loads((Path(__file__).resolve().parent.parent / "arbtok" / "data" / "loom" / "sandhi.json")
                      .read_text(encoding="utf-8"))


@pytest.mark.parametrize("text", ["جَدِيد وْ قَدِيم", "جَدِيد وْ"])
def test_the_bare_conjunction_carries_no_stress(text):
    # arbtok writes the bare conjunction unstressed; the loom file must match it.
    plain = Interpreter(build_ir("abv-BH")).transcribe(text).split()
    words = Interpreter(build_ir("abv-BH", fragments=[FRAGMENT])).transcribe(text).split()
    assert plain[1] == "ˈw"
    assert words[1] == "w"
    assert words[0] == plain[0]


ARTICLE = json.loads((Path(__file__).resolve().parent.parent / "arbtok" / "data" / "loom" / "article.json")
                     .read_text(encoding="utf-8"))


@pytest.mark.parametrize("lect, text, expected", [
    # Qafisheh (1970: 20-21): after a consonant the article vowel is i (ma° is-salaama).
    ("afb-KW", "وَدَّيت السَّيَّارَة", "issajˈjaːra"),
    ("afb-AE", "وَدَّيت السَّيَّارَة", "issajˈjaːra"),
    # Abdel-Massih et al. (1979), "Definite article: form": il- after a consonant.
    ("arz-EG", "عَن الْعَرَبِيَّة", "ilʕaraˈbijja"),
])
def test_the_article_after_a_consonant_has_i(lect, text, expected):
    words = Interpreter(build_ir(lect, fragments=[FRAGMENT, ARTICLE])).transcribe(text).split()
    assert words[1] == expected


def test_a_lect_with_no_source_keeps_its_article():
    # Bahraini has no source for the article vowel (#415), so the fragment leaves it.
    text = "زَيْن الْيَوم"
    plain = Interpreter(build_ir("afb-BH", fragments=[FRAGMENT])).transcribe(text)
    assert Interpreter(build_ir("afb-BH", fragments=[FRAGMENT, ARTICLE])).transcribe(text) == plain
