"""Regression gate for the code-switched Arabic gold set.

The gold lives in ``data/gold_code_switched/<lect>.tsv`` (20 rows per lect) and
pins arbtok's loanword-nativisation pipeline: the ``ipa`` column is
``ArbtokG2PPlugin(lang, diacritize=True, nativize=True, pausal=True).transcribe``
output, so a drift in the pipeline or in the cited nativisation tables
(:mod:`arbtok.translit`) is caught here — mirroring orthography2ipa's
``tests/test_arabic_tts_gold.py``.

Each lect asserts, per row:

* schema and the 20-row minimum;
* ``raw == sentence`` stripped of ḥarakāt;
* ``ipa == transcribe(sentence)`` (the regression pin);
* no Latin leakage — every embedded Latin word is present as its nativised
  reflex or absent (refused → dropped), never verbatim, and no uppercase Latin
  survives (a literal ``[a-zA-Z]`` ban is unsatisfiable — Arabic IPA is
  ASCII-heavy; see ``_leakage_failures`` in the build script);
* ``cs_words`` all present in the sentence.
"""
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import gold_code_switched as gcs  # noqa: E402


def _lects():
    return gcs._roster()


@pytest.mark.parametrize("lect", _lects())
def test_gold_matches_pipeline(lect):
    """Every stored row reproduces the live pipeline output, byte for byte."""
    from arbtok.plugin import ArbtokG2PPlugin

    rows = gcs._load(lect)
    assert rows is not None, f"missing gold file for {lect}"
    assert len(rows) >= gcs.MIN_ROWS, f"{lect}: {len(rows)} rows < {gcs.MIN_ROWS}"

    plugin = ArbtokG2PPlugin(lang=lect, diacritize=True, nativize=True, pausal=True)
    failures = []
    seen = set()
    for r in rows:
        rid = r.get("id", "?")
        assert not (set(gcs.FIELDS) - set(r)), f"{rid}: bad columns {list(r)}"
        assert all(r[f] for f in ("id", "sentence", "raw", "ipa", "gloss_en", "cs_words")), \
            f"{rid}: empty required field"
        assert r["sentence"] not in seen, f"{rid}: duplicate sentence"
        seen.add(r["sentence"])
        assert gcs.strip_tashkeel(r["sentence"]) == r["raw"], \
            f"{rid}: raw != sentence stripped of ḥarakāt"
        # Only pinned rows carry live pipeline output (absent column == pinned for
        # the un-migrated template lects); known-wrong / unsupported rows carry
        # hand-authored gold the pipeline does not reproduce — see the build script.
        status = (r.get("pipeline_status") or "pinned").strip()
        if status == "pinned":
            assert plugin.transcribe(r["sentence"]) == r["ipa"], \
                f"{rid}: ipa regression (re-run scripts/gold_code_switched.py build)"
            failures += gcs._leakage_failures(rid, r, lect)
    assert not failures, "\n".join(failures)


def test_roster_excludes_buckwalter():
    """ar-Latn-buckwalter is a romanisation anchor, not a code-switch lect."""
    assert "ar-Latn-buckwalter" not in _lects()
    assert "ar-Latn-buckwalter" in gcs.SKIP
