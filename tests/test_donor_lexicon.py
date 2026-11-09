"""The bundled English donor lexicon and the engine that holds it."""
import warnings

import pytest

import orthography2ipa as o2i
from orthography2ipa import G2P, load_lexicon

from arbtok import donor_lexicon as dl
from arbtok.donor_lexicon import BUNDLED_DONOR, bundled_path, donor_engine
from arbtok.translit import transliterate


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
