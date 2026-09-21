"""The bundled French donor lexicon: closed-class words, read from a cited dictionary."""
import importlib.util
from pathlib import Path

import pytest

from arbtok import translit
from arbtok.donor_lexicon import bundled_path

DATA = Path(translit.__file__).parent / "data" / "donor_lexicons"
FRENCH_PHONES = set("abdefijklmnopstuvwyzøœɑɔəɛɡɥɲʁʃʒ") | {"̃"}


def _rows(name):
    return [line.split("\t") for line in (DATA / name).read_text(encoding="utf-8").splitlines()
            if line and not line.startswith("#")]


def _builder():
    path = Path(translit.__file__).parents[1] / "scripts" / "build_french_donor_lexicon.py"
    spec = importlib.util.spec_from_file_location("build_french_donor_lexicon", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_lexicon_is_bundled_where_the_donor_lookup_finds_it():
    assert bundled_path("fr-FR") == DATA / "fr-FR.tsv"
    assert len(_rows("fr-FR.tsv")) > 150


def test_every_reading_is_the_cited_dictionarys_and_is_spelled_in_french_phones():
    sources = {word: (ipa, phones) for word, _, ipa, phones, _ in _rows("fr-FR.sources.tsv")}
    assert (DATA / "fr-FR.sources.tsv").read_text(encoding="utf-8").startswith("# French MFA dictionary v3.0.0")
    mapping = _builder().PHONES
    for word, ipa in _rows("fr-FR.tsv"):
        assert sources[word][0] == ipa == "".join(mapping.get(p, p) for p in sources[word][1].split())
        assert set(ipa) <= FRENCH_PHONES, (word, ipa, set(ipa) - FRENCH_PHONES)
    assert len(sources) == len(_rows("fr-FR.tsv"))


def test_no_entry_is_one_the_donor_lookup_could_never_reach():
    assert not [word for word, _ in _rows("fr-FR.tsv") if "'" in word]


@pytest.mark.parametrize("word, donor, adapted", [
    ("les", "le", None), ("des", "de", None), ("et", "e", None),
    ("déjà", "deʒa", "deʒa"), ("voilà", "vwala", "vwala"), ("dix", "dis", "dis"), ("là", "la", "la"),
])
def test_a_function_word_is_read_from_the_lexicon_and_not_from_its_spelling(word, donor, adapted):
    """Spelling alone gives l, d, ɛ, deʒ, vwal, di and l for these."""
    assert dict(_rows("fr-FR.tsv"))[word] == donor
    got = translit.transliterate(word, "ar-MA", donor="fr-FR")
    assert got == translit.nativize(donor, "ar-MA", donor="fr-FR")
    if adapted is not None:
        assert got == adapted


def test_the_builder_takes_the_most_probable_reading_and_says_what_it_left_out(tmp_path):
    builder = _builder()
    (tmp_path / "toy.dict").write_text(
        "le\t0.07\t0.0\t0.0\t0.0\tl ə\n" "le\t0.99\t0.0\t0.0\t0.0\tl ø\n" "qui\t0.99\t0.0\t0.0\t0.0\tc i\n",
        encoding="utf-8")
    builder.CLOSED_CLASSES = {"article": "le l'", "pronoun": "qui dont"}
    written, absent, elided = builder.build(tmp_path / "toy.dict", tmp_path)
    assert (written, absent, elided) == (2, ["dont"], ["l'"])
    assert (tmp_path / "fr-FR.tsv").read_text(encoding="utf-8") == "le\tlø\nqui\tki\n"
