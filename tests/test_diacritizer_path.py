"""Which generator the o2i plugin uses, and that a typo cannot pass for the default.

The default stays the lattice because the measurement says so, not because it
was already there.
"""
import pytest

from arbtok.o2i_plugins import ArbtokDiacritizer


def test_the_default_is_the_lattice():
    assert ArbtokDiacritizer().path == "lattice"


def test_fusion_is_selectable():
    assert ArbtokDiacritizer("fusion").path == "fusion"


def test_a_typo_is_refused_rather_than_silently_defaulted():
    """The failure this guards: ``path="fussion"`` quietly keeping the lattice
    looks exactly like the setting working, so a measurement comparing the two
    paths would compare one path with itself."""
    with pytest.raises(ValueError) as exc:
        ArbtokDiacritizer("fussion")
    assert "fussion" in str(exc.value)


@pytest.mark.parametrize("path, expected", [("fusion", "FusionDiacritizer"),
                                            ("lattice", "LatticeDiacritizer")])
def test_the_plugin_builds_the_selected_class(path, expected):
    p = ArbtokDiacritizer(path)
    p.normalize("كتاب", "ar-EG")
    assert type(p._by_lang["ar-EG"]).__name__ == expected


def test_the_environment_no_longer_selects_the_path(monkeypatch):
    """The path is an argument, so the environment cannot change an output."""
    monkeypatch.setenv("ARBTOK_DIACRITIZER", "fusion")
    assert ArbtokDiacritizer().path == "lattice"
