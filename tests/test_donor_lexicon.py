"""The bundled English donor lexicon and its registration."""
import pytest

import orthography2ipa as o2i

from arbtok.donor_lexicon import BUNDLED_DONOR, bundled_path, ensure_registered
from arbtok.translit import transliterate


@pytest.fixture(autouse=True)
def _clean_registry():
    o2i.clear_lexicons()
    yield
    o2i.clear_lexicons()


def test_the_lexicon_ships_with_the_package():
    path = bundled_path()
    assert path is not None and path.is_file()
    assert sum(1 for _ in path.open(encoding="utf-8")) > 50_000


def test_the_bundled_file_is_a_valid_lexicon():
    from orthography2ipa.lexicon import validate_lexicon_text
    assert validate_lexicon_text(bundled_path().read_text(encoding="utf-8")) == []


def test_registration_is_idempotent():
    assert ensure_registered() is True
    assert ensure_registered() is False


def test_a_callers_own_lexicon_is_never_overwritten(tmp_path):
    """Registration is global to the orthography2ipa process registry, so an
    application that brought its own English lexicon must keep it."""
    mine = tmp_path / "en-GB.tsv"
    mine.write_text("engine\tˈtɛst\n", encoding="utf-8")
    o2i.register_lexicon(BUNDLED_DONOR, str(mine))
    assert ensure_registered() is False
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


def test_without_the_lexicon_those_readings_are_not_reached():
    """The guard that keeps the test above from passing vacuously: it must be
    the lexicon producing these, not the rules."""
    o2i.clear_lexicons()
    import arbtok.donor_lexicon as dl
    original = dl.bundled_path
    dl.bundled_path = lambda code=BUNDLED_DONOR: None       # ship nothing
    try:
        assert transliterate("engine", "ar") != "indʒin"
    finally:
        dl.bundled_path = original
