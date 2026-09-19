"""Which generator the o2i plugin uses, and that a typo cannot pass for the default.

`FusionDiacritizer` was unreachable through the plugin: `normalize` constructed
`LatticeDiacritizer` with no branch. It is selectable now, and the default stays the
lattice because the measurement says so, not because it was already there.
"""
import pytest

from arbtok.o2i_plugins import ArbtokDiacritizer


def test_the_default_is_the_lattice(monkeypatch):
    monkeypatch.delenv("ARBTOK_DIACRITIZER", raising=False)
    assert ArbtokDiacritizer._path() == "lattice"


def test_fusion_is_selectable(monkeypatch):
    monkeypatch.setenv("ARBTOK_DIACRITIZER", "fusion")
    assert ArbtokDiacritizer._path() == "fusion"


def test_a_typo_is_refused_rather_than_silently_defaulted(monkeypatch):
    """The failure this guards: `ARBTOK_DIACRITIZER=fussion` quietly keeping the
    lattice looks exactly like the setting working, so a measurement comparing the
    two paths would compare one path with itself."""
    monkeypatch.setenv("ARBTOK_DIACRITIZER", "fussion")
    with pytest.raises(ValueError) as exc:
        ArbtokDiacritizer._path()
    assert "fussion" in str(exc.value)


def test_the_plugin_builds_the_selected_class(monkeypatch):
    from arbtok.diacritize import LatticeDiacritizer
    from arbtok.fusion import FusionDiacritizer

    monkeypatch.setenv("ARBTOK_DIACRITIZER", "fusion")
    p = ArbtokDiacritizer()
    p.normalize("كتاب", "ar-EG")
    assert isinstance(p._by_lang[("ar-EG", "fusion")], FusionDiacritizer)

    monkeypatch.setenv("ARBTOK_DIACRITIZER", "lattice")
    p.normalize("كتاب", "ar-EG")
    assert isinstance(p._by_lang[("ar-EG", "lattice")], LatticeDiacritizer)


def test_the_cache_keys_on_the_path_not_just_the_lect(monkeypatch):
    """Keying on lang alone would hand back the first path ever built for that lect,
    so switching the variable mid-process would silently do nothing."""
    p = ArbtokDiacritizer()
    monkeypatch.setenv("ARBTOK_DIACRITIZER", "lattice")
    p.normalize("كتاب", "ar-EG")
    monkeypatch.setenv("ARBTOK_DIACRITIZER", "fusion")
    p.normalize("كتاب", "ar-EG")
    assert ("ar-EG", "lattice") in p._by_lang and ("ar-EG", "fusion") in p._by_lang
