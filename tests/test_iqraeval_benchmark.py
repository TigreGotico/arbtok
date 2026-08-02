"""The IqraEval Qur'anic-gold runner reads Halabi notation and scores arbtok.

Two layers: the notation mapping (pure, no network — every symbol observed in
a 5,050-row sample of ``IqraEval/Iqra_train`` is exercised) and a tiny live
pull (5 dev rows) that proves the HF loader and the two arbtok arms actually
wire up. The live test is skipped, not failed, if the network/HF hub is
unreachable — mirroring the espeak-optional pattern in
``test_lect_benchmark.py``.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "scripts"))

from benchmark_iqraeval import (  # noqa: E402
    NOTATION,
    confusion_pairs,
    normalize,
    phoneme_ref_to_ipa,
    score,
)

# Every one of the 67 distinct tokens observed across the full dev split (2,588
# rows) plus 2,462 train rows — see the module docstring for the citation and
# the verification method.
_OBSERVED_SYMBOLS = (
    "$ $$ * ** < A AA D DD E EE H HH I II S SS T TT U UU Z ZZ ^ ^^ "
    "a aa b bb d dd f ff g gg h hh i ii j jj k kk l ll m mm n nn "
    "q qq r rr s ss t tt u uu w ww x xx y yy z zz"
).split()


def test_every_observed_symbol_is_mapped():
    """No unmapped token — an unresolved symbol is a benchmark bug, not a skip."""
    assert len(_OBSERVED_SYMBOLS) == 67
    missing = [s for s in _OBSERVED_SYMBOLS if s not in NOTATION]
    assert missing == [], f"unmapped Halabi-notation symbols: {missing}"


def test_gemination_doubles_the_base_consonant_ipa():
    assert NOTATION["nn"] == NOTATION["n"] + "ː"
    assert NOTATION["$$"] == NOTATION["$"] + "ː"
    assert NOTATION["ll"] == "lː"


def test_emphatic_vowel_allophones_are_distinguished_from_plain():
    assert NOTATION["a"] != NOTATION["A"]
    assert NOTATION["aa"] == NOTATION["a"] + "ː"
    assert NOTATION["AA"] == NOTATION["A"] + "ː"


def test_phoneme_ref_to_ipa_known_row():
    # dev row 0: "الآن قد استوعبتها" -> "< a l < aa n a q A d i s t a w E a b t u h aa"
    ref = "< a l < aa n a q A d i s t a w E a b t u h aa"
    ipa = phoneme_ref_to_ipa(ref)
    assert "{{" not in ipa  # nothing unmapped
    assert ipa.startswith("ʔalʔaːn")


def test_phoneme_ref_to_ipa_flags_unknown_symbols_instead_of_dropping():
    ipa = phoneme_ref_to_ipa("a ZZZ_not_real b")
    assert "{{ZZZ_not_real}}" in ipa


def test_normalize_strips_stress_and_whitespace():
    assert normalize("ˈka ˌtaːb") == "kataːb"


def test_confusion_pairs_counts_substitutions():
    details = [
        {"id": "1", "text": "x", "gold": "ab", "pred": "ac", "dist": 1},
        {"id": "2", "text": "y", "gold": "ab", "pred": "ac", "dist": 1},
        {"id": "3", "text": "z", "gold": "ab", "pred": "ab", "dist": 0},
    ]
    pairs = confusion_pairs(details, top=5)
    assert pairs[0] == (("b", "c"), 2)


@pytest.mark.timeout(120)
def test_live_dev_rows_score_with_both_arbtok_arms():
    """5 real dev rows: the loader, the mapping, and both arms all wire up."""
    try:
        from benchmark_iqraeval import load_gold
        rows = load_gold("dev", limit=5)
    except Exception as exc:  # network/HF unavailable — skip, don't fail
        pytest.skip(f"IqraEval/Iqra_train unreachable: {exc}")

    assert len(rows) == 5
    for row in rows:
        assert row["sentence"] and row["tashkeel_sentence"] and row["phoneme_ref"]

    from arbtok.plugin import ArbtokG2PPlugin

    diac_engine = ArbtokG2PPlugin(lang="ar", diacritize=False, register="full")
    bare_engine = ArbtokG2PPlugin(lang="ar", diacritize=True, register="full")

    diac_metrics, diac_details = score(rows, diac_engine.transcribe, undiac=False)
    bare_metrics, _ = score(rows, bare_engine.transcribe, undiac=True)

    assert diac_metrics["n"] == 5
    assert 0.0 <= diac_metrics["per"]
    assert 0.0 <= bare_metrics["per"]
    for d in diac_details:
        assert d["gold"]  # every gold IPA is non-empty
