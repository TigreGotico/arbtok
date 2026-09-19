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


def test_a_gold_row_holding_a_double_quote_survives_a_rewrite(tmp_path):
    """`_write_rows` must not lose data on the one file it exists to protect.

    `ar-LB-cs-008`'s notes contain `hedged as "sometimes"`. Through `csv` that row
    either came back reformatted (QUOTE_MINIMAL wraps it and doubles the quotes) or
    took the file down with it: QUOTE_NONE raises on the quotechar, and `open(path,
    "w")` has already truncated by then, which left the file at 8 of its 21 lines.
    """
    import csv as _csv
    import scripts.gold_code_switched as gcs

    src = gcs.GOLD_DIR / "ar-LB.tsv"
    original = src.read_bytes()
    path = tmp_path / "ar-LB.tsv"
    path.write_bytes(original)

    with open(path, encoding="utf-8") as fh:
        reader = _csv.DictReader(fh, delimiter="\t")
        fields, rows = reader.fieldnames, list(reader)
    quoted = [r for r in rows if '"' in (r.get("notes") or "")]
    assert quoted, "ar-LB.tsv no longer holds a row with a double quote; pick another"

    gcs._write_rows(path, fields, rows)
    assert path.read_bytes() == original, "rewriting an untouched gold changed its bytes"
