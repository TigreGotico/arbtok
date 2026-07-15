"""The per-lect TTS-gold runner (roadmap F1 + D1) does what it claims.

This is a wiring test, not an accuracy gate: it proves the runner reads the
orthography2ipa Arabic TTS gold, scores the shipped arbtok stack on both the
diacritized and the bare-skeleton input, and reports a per-lect delta — over a
tiny slice (2 lects x 3 sentences) so it stays fast and needs no network.

The arbtok column must always be produced (its input contract is text, always
available); the espeak column is skipped only when no espeak binary is present.
The lexicon is left off (``None``) so nothing is fetched from Hugging Face.
"""
import shutil
import sys
import unicodedata

import pytest

# The runner lives in scripts/, not on the package path.
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "scripts"))

from benchmark_stack import (  # noqa: E402
    _words,
    gold_dir,
    load_lect_gold,
    run_lect_benchmark,
    score_pair,
    strip_harakat,
    lect_markdown_table,
)

TWO_LECTS = ["ar-EG", "ar-SA-x-najd"]


def test_strip_harakat_reproduces_the_bare_column():
    """The undiacritized path's input equals the gold's own ``raw`` skeleton.

    Verifies the D1 premise: stripping combining marks from the vocalized
    sentence is exactly the everyday bare-abjad input, so the diacritized vs
    undiacritized delta prices only the missing harakat.
    """
    path = os.path.join(gold_dir(), "ar-EG.tsv")
    for _id, sentence, raw, _ipa in load_lect_gold(path):
        assert strip_harakat(sentence) == raw
        # And stripping is a real reduction: the vocalized form carries marks.
        assert any(unicodedata.category(c) == "Mn" for c in sentence)


def test_words_strips_stress_and_punctuation():
    assert _words("ˈʔahwa، ˌʃaːj.") == ["ʔahwa", "ʃaːj"]


def test_score_pair_is_zero_on_identity():
    cd, cl, wd, wl = score_pair("ˈbeːt ˈkalb", "beːt kalb")
    assert cd == 0 and wd == 0
    assert cl > 0 and wl == 2


def test_runner_on_two_lects_three_sentences():
    """The runner produces both arbtok arms per lect over a 2x3 slice."""
    report = run_lect_benchmark(codes=TWO_LECTS, lexicon=None, limit=3,
                                with_espeak=False)
    lects = report["lects"]
    assert set(lects) == set(TWO_LECTS)
    for code in TWO_LECTS:
        e = lects[code]
        assert e["sentences"] == 3
        # arbtok is never skipped and produces a real (finite) rate.
        for arm in ("arbtok_diac", "arbtok_undiac"):
            assert 0.0 <= e[arm]["per"]
            assert 0.0 <= e[arm]["wer"] <= 1.0
        # Reading the marks off the vocalized input is at least as easy as
        # restoring them from the bare skeleton.
        assert e["arbtok_diac"]["per"] <= e["arbtok_undiac"]["per"] + 1e-9
        assert e["undiac_delta_per"] == pytest.approx(
            e["arbtok_undiac"]["per"] - e["arbtok_diac"]["per"])
        assert e["espeak"] is None  # with_espeak=False


def test_markdown_table_renders_every_requested_lect():
    report = run_lect_benchmark(codes=TWO_LECTS, lexicon=None, limit=3,
                                with_espeak=False)
    table = lect_markdown_table(report)
    for code in TWO_LECTS:
        assert code in table
    assert "arbtok PER (diac)" in table


@pytest.mark.skipif(not (shutil.which("espeak-ng") or shutil.which("espeak")),
                    reason="espeak binary not installed")
def test_espeak_column_present_when_binary_available():
    report = run_lect_benchmark(codes=["ar-EG"], lexicon=None, limit=3,
                                with_espeak=True)
    assert report["lects"]["ar-EG"]["espeak"] is not None
