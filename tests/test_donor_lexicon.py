"""The bundled English donor lexicon and the engine that holds it."""
import warnings
from pathlib import Path

import pytest

import orthography2ipa as o2i
from orthography2ipa import G2P, load_lexicon

from arbtok import donor_lexicon as dl
from arbtok.donor_lexicon import BUNDLED_DONOR, bundled_path, donor_engine
from arbtok.translit import transliterate

DATA = Path(dl.__file__).parent / "data" / "donor_lexicons"


def _entry(name, word):
    """The reading the shipped file *name* gives *word*, read without the code under test."""
    for line in (DATA / name).read_text(encoding="utf-8").splitlines():
        key, _, ipa = line.partition("\t")
        if key == word:
            return ipa
    raise KeyError(word)


@pytest.fixture
def process_lexicons():
    """Clear the deprecated process-wide registry before and after a test that sets it."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        o2i.clear_lexicons()
    yield
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        o2i.clear_lexicons()


def test_the_lexicon_ships_with_the_package():
    path = bundled_path()
    assert path is not None and path.is_file()
    assert sum(1 for _ in path.open(encoding="utf-8")) > 50_000


def test_the_bundled_file_is_a_valid_lexicon():
    from orthography2ipa.lexicon import validate_lexicon_text
    assert validate_lexicon_text(bundled_path().read_text(encoding="utf-8")) == []


def test_the_donor_engine_holds_the_bundled_lexicon():
    engine = donor_engine()
    assert engine is donor_engine()
    assert engine.pipeline.lexicon == load_lexicon(bundled_path())


def test_no_other_engine_reads_the_bundled_lexicon():
    """The donor engine holds the lexicon. An engine the caller builds for the
    same code reads the rules, as the orthography2ipa contract requires."""
    assert transliterate("engine", "ar") == "indʒin"
    assert G2P(BUNDLED_DONOR).transcribe_word("engine") != donor_engine().transcribe_word("engine")
    assert G2P(BUNDLED_DONOR).pipeline.lexicon is None


def test_a_donor_with_no_bundled_lexicon_reads_the_rules():
    assert bundled_path("de-DE") is None
    assert donor_engine("de-DE").pipeline.lexicon is None


@pytest.mark.parametrize("donor", ["en", "EN-gb", "en_GB", "en-gb"])
def test_a_donor_tag_finds_the_lexicon_of_the_spec_it_names(donor):
    """A bare tag names the variety of the language's motherland, and a tag is
    read without regard to case or separator: each of these is en-GB."""
    assert bundled_path(donor) == DATA / "en-GB.tsv"
    assert donor_engine(donor) is donor_engine(BUNDLED_DONOR)
    assert donor_engine(donor).transcribe_word("engine") == _entry("en-GB.tsv", "engine")


@pytest.mark.parametrize("word, reading", [
    ("engine", "indʒin"),
    ("machine", "maʃiːn"),
    ("medicine", "midisin"),
    ("laptop", "labtub"),
])
def test_a_bare_english_donor_tag_gives_the_documented_reading(word, reading):
    """en names en-GB, so it gives the en-GB readings that
    test_a_loanword_takes_its_documented_reading pins."""
    assert transliterate(word, "ar", donor="en") == reading


def test_a_name_that_is_not_a_language_tag_finds_no_lexicon():
    """The French source table sits beside the lexicons. Its file name names no
    spec, so no donor code reaches it, and the engine reads the rules."""
    assert bundled_path("fr-FR.sources") is None
    assert donor_engine("fr-FR.sources").pipeline.lexicon is None


def test_a_callers_own_lexicon_wins(tmp_path, process_lexicons):
    """A caller who set a process-wide English lexicon keeps it."""
    mine = tmp_path / "en-GB.tsv"
    mine.write_text("engine\tˈtɛst\n", encoding="utf-8")
    with pytest.warns(DeprecationWarning):
        o2i.register_lexicon(BUNDLED_DONOR, str(mine))
    assert donor_engine().pipeline.lexicon is None
    assert transliterate("engine", "ar") is not None
    assert "dʒ" not in transliterate("engine", "ar")


@pytest.mark.parametrize("word, reading", [
    ("engine", "indʒin"),
    ("machine", "maʃiːn"),
    ("medicine", "midisin"),
    ("project", "brudʒikt"),
    ("laptop", "labtub"),
    ("weekend", "wiːkind"),
])
def test_a_loanword_takes_its_documented_reading(word, reading):
    """These are the readings this repository's own gold `notes` column
    documents. Without the lexicon the rule spec reaches a different one for
    every entry here — `engine` came out `inkajn`, `machine` `maʃajn` —
    because English spelling does not determine them."""
    assert transliterate(word, "ar") == reading


def test_without_the_lexicon_those_readings_are_not_reached(monkeypatch):
    """The guard that keeps the test above from passing vacuously: it must be
    the lexicon producing these, not the rules."""
    monkeypatch.setattr(dl, "bundled_path", lambda code=BUNDLED_DONOR: None)   # ship nothing
    assert transliterate("engine", "ar") != "indʒin"
