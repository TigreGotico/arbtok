"""The span-level gold is its cited items, and its comparison can fail."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import span_gold as G  # noqa: E402


def _rows():
    return [json.loads(line) for path in sorted(G.GOLD_DIR.glob("*.jsonl"))
            for line in path.read_text(encoding="utf-8").splitlines()]


def test_every_accepted_reading_names_its_source_page_and_printed_form():
    for row in _rows():
        assert row["accepted"], row["id"]
        for acc in row["accepted"]:
            assert acc["source"] and acc["page"] and acc["printed"] and acc["phones"], row["id"]


def test_the_committed_files_are_what_the_items_build(tmp_path, monkeypatch):
    committed = {p.name: p.read_text(encoding="utf-8") for p in G.GOLD_DIR.glob("*.jsonl")}
    monkeypatch.setattr(G, "GOLD_DIR", tmp_path)
    G.build()
    built = {p.name: p.read_text(encoding="utf-8") for p in tmp_path.glob("*.jsonl")}
    assert built == committed


def test_the_span_occurs_in_its_sentence():
    for row in _rows():
        assert row["span"] in row["sentence"], row["id"]


def test_the_part_follows_the_id_and_some_items_are_held_out():
    rows = _rows()
    assert all(r["part"] == ("held_out" if G.held_out(r["id"]) else "dev") for r in rows)
    assert 0 < sum(r["part"] == "held_out" for r in rows) < len(rows)


def test_fold_removes_only_what_the_rules_name():
    assert G.fold("ˈtsi.bi:r") == "tsibiːr"
    assert G.fold("tˤɑˈriːdz") == "tˤariːdz"
    assert G.fold("ˈgumar") == "ɡumar"
    assert G.fold("masaːʔan") == G.fold("masaːʔ")
    assert G.fold("ʃoːk") != G.fold("ʃawk")


def test_a_wrong_reading_fails_and_a_cited_one_passes():
    dog = next(r for r in _rows() if r["sentence"] == "كلب")
    assert G.passes(dog, "ˈtsalb") and G.passes(dog, "ˈkalb")
    assert not G.passes(dog, "ˈkilb")
    thorns = next(r for r in _rows() if r["sentence"] == "شوك")
    assert not G.passes(thorns, "ˈʃawk"), "the diphthong the Najdi source does not print"
    pm = next(r for r in _rows() if r["gloss"] == "p.m.")
    assert G.passes(pm, "almawˈʕid asˈsaːʕa ˈxamsa maˈsaːʔ")
    assert not G.passes(pm, "almawˈʕid asˈsaːʕa ˈxamsa ˈmiːm")
    vein = next(r for r in _rows() if r["sentence"] == "عرق")
    assert G.passes(vein, "ˈʕirdz") and G.passes(vein, "ˈʕirɡ"), "free variation of [dz] with /g/"
    assert not G.passes(vein, "ˈʕirq")
    ad = next(r for r in _rows() if r["gloss"] == "AD")
    assert G.passes(ad, "wulid sana 1990 miːlaːdij") and G.passes(ad, "wulid sana miːlaːdijj")
    assert not G.passes(ad, "wulid sana ˈmiːm")
