"""A caller can name the rawi export the diacritizer reads.

The class always accepted `model_path`; nothing could reach it, because the factory
took no arguments and the diacritizers call the factory. These tests pin the route,
not the model — swapping in a real fine-tune is a separate exercise.
"""
import pytest

from arbtok._ensemble import DEFAULT_ENSEMBLE_ONNX, DEFAULT_VOCAB, get_ensemble
from arbtok.diacritize import LatticeDiacritizer


def test_the_default_pair_is_still_one_session():
    """The cache keys on the paths, so asking twice for the bundled pair builds once."""
    assert get_ensemble() is get_ensemble()
    assert get_ensemble(None, None) is get_ensemble()


def test_naming_the_bundled_paths_explicitly_is_the_same_reader():
    """Passing the defaults by name must not fork a second session."""
    explicit = get_ensemble(str(DEFAULT_ENSEMBLE_ONNX), str(DEFAULT_VOCAB))
    assert explicit is get_ensemble(str(DEFAULT_ENSEMBLE_ONNX), str(DEFAULT_VOCAB))
    assert explicit.classes == get_ensemble().classes


def test_the_diacritizer_passes_the_paths_down():
    """The gap this closes: before, a path set here never reached the factory."""
    d = LatticeDiacritizer(lang="ar-EG", model_path=str(DEFAULT_ENSEMBLE_ONNX),
                           vocab_path=str(DEFAULT_VOCAB))
    assert d.model_path == str(DEFAULT_ENSEMBLE_ONNX)
    assert d.diacritizer is get_ensemble(str(DEFAULT_ENSEMBLE_ONNX), str(DEFAULT_VOCAB))


def test_a_missing_model_is_refused_at_load_not_at_the_first_word():
    """A wrong path must fail when it is named, not on some later sentence."""
    d = LatticeDiacritizer(lang="ar-EG", model_path="/nonexistent/rawi.onnx")
    with pytest.raises(Exception):
        _ = d.diacritizer
