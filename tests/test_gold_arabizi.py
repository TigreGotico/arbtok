"""data/gold_arabizi holds Arabizi with the Arabic it spells; the code-switched gold holds none."""
import csv
import re
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"
DIGIT_WORD = re.compile(r"[A-Za-z]\S*[2-9]|[2-9]\S*[A-Za-z]")


def rows(path):
    return list(csv.DictReader(path.open(encoding="utf-8"), delimiter="\t"))


def test_every_constructed_row_has_arabizi_and_an_arabic_reference():
    gold = rows(DATA / "gold_arabizi" / "constructed.tsv")
    assert len(gold) == 86
    assert len({r["id"] for r in gold}) == 86
    for r in gold:
        assert DIGIT_WORD.search(r["arabizi"]), r["id"]
        assert re.fullmatch(r"[؀-ۿً-ْٰ ]+", r["arabic"]), r["id"]


def test_the_code_switched_gold_has_no_arabizi_row():
    for path in sorted((DATA / "gold_code_switched").glob("*.tsv")):
        for r in rows(path):
            assert not DIGIT_WORD.search(r["raw"]), r["id"]
