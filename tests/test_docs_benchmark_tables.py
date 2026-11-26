"""Each PER and WER cell of the docs/benchmarks.md lect tables equals its result file."""
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PAGE = (ROOT / "docs" / "benchmarks.md").read_text(encoding="utf-8")


def load(name):
    return json.loads((ROOT / "benchmarks" / name).read_text(encoding="utf-8"))["lects"]


def rows(header):
    start = PAGE.index(header)
    lines = PAGE[start:].splitlines()[2:]
    table = []
    for line in lines:
        if not line.startswith("|"):
            break
        table.append([c.strip().strip("*`") for c in line.strip("|").split("|")])
    return table


def cell(value):
    return "n/a" if value is None else f"{value:.3f}"


FULL = rows("| Lect | Tier | N | arbtok PER (diac)")


def test_the_lect_table_lists_every_lect():
    assert sorted(r[0] for r in FULL) == sorted(load("lect_results.json"))


@pytest.mark.parametrize("row", FULL, ids=[r[0] for r in FULL])
def test_lect_row_matches_lect_results(row):
    lect = load("lect_results.json")[row[0]]
    espeak = lect["espeak"] or {"per": None, "wer": None}
    expected = [lect["tier"], str(lect["sentences"]),
                cell(lect["arbtok_diac"]["per"]), cell(lect["arbtok_diac"]["wer"]),
                cell(lect["arbtok_undiac"]["per"]), cell(lect["arbtok_undiac"]["wer"]),
                f"{lect['undiac_delta_per']:+.3f}", cell(espeak["per"]), cell(espeak["wer"])]
    assert row[1:] == expected


IRAB = rows("| Lect | mode | PER (diac)")


@pytest.mark.parametrize("row", IRAB, ids=[f"{r[0]}-{r[1][:6]}" for r in IRAB])
def test_register_row_matches_its_result_file(row):
    name = "lect_results_full_irab.json" if "full-irab" in row[1] else "lect_results.json"
    lect = load(name)[row[0]]
    assert row[2:] == [cell(lect["arbtok_diac"]["per"]), cell(lect["arbtok_diac"]["wer"]),
                       cell(lect["arbtok_undiac"]["per"]), cell(lect["arbtok_undiac"]["wer"])]
