#!/usr/bin/env python3
"""Where does arbtok stand against o2i — and everyone else — on real gold?

The gold here is the ``arabic-dialects-gold20`` set: 20 sentences per lect of
**dialectal, fully-vocalized** orthography, each with a reference IPA that was
seeded from orthography2ipa's own engine (``ipa_o2i``) and then corrected, row by
row, against the dialectology literature (``ipa`` — the ``fable_corrections`` /
``notes`` columns cite the source of every change). It is pulled from Hugging Face
at run time and cached locally; **no gold is vendored into this repo.**

Two facts about the gold decide how to read every number below:

1. **The reference ``ipa`` began as o2i output.** So o2i is close to the ruler by
   construction, and arbtok — which reassembles the pronunciation itself rather
   than calling ``G2P.transcribe`` — can only *match* the gold where its lattice,
   rescorers, sandhi and stress reproduce o2i's engine, and *loses* wherever they
   diverge. The point of this script is to find exactly those rows.
2. **The rows are already vocalized.** So arbtok is run with ``diacritize=False``:
   the diacritizer has nothing to restore and could only add noise. This is the
   honest scoring config for this gold, and it isolates the *phonology* delta from
   the diacritization delta.

Arms, all scored against the gold ``ipa`` column with one metric:
  ``o2i``     ``orthography2ipa.G2P(lang).transcribe`` — the substrate, the floor.
  ``arbtok``  ``ArbtokG2PPlugin(lang, diacritize=False).transcribe`` — the stack.
  ``espeak``  espeak-ng's single ``ar`` (MSA) voice — no dialect voices exist.
  ``epitran`` epitran ``ara-Arab`` — optional; skipped whole if unavailable.

Two questions, two outputs:
  * a per-lect PER/WER table, printed **twice** — stress-stripped (the headline: a
    TTS voice gets no partial credit, but stress marks it treats loosely) and
    stress-kept (so a stress-only regression cannot hide);
  * a categorised diff of every row where ``arbtok`` is worse than ``o2i``:
      Bucket A — **arbtok degrades o2i**: o2i matches the gold (or is closer) but
                 arbtok diverges. An arbtok regression to fix downstream.
      Bucket B — **o2i is itself wrong**: o2i already differs from the gold. A
                 cited-rule bug lead for the o2i specs (``fable_corrections`` says
                 what the fix is).

Usage
-----
    python scripts/benchmark_gold20.py                 # every lect
    python scripts/benchmark_gold20.py --lects ar-EG,ar-SY
    python scripts/benchmark_gold20.py --json out.json # full machine report
    python scripts/benchmark_gold20.py --no-epitran
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import urllib.request
from typing import Callable, Dict, List, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from benchmark_stack import _words, edit_distance  # noqa: E402

HF_REPO = "Salesteq/arabic-dialects-gold20"
HF_BASE = f"https://huggingface.co/datasets/{HF_REPO}/resolve/main"
CACHE_DIR = os.environ.get(
    "GOLD20_CACHE",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), ".cache_gold20"),
)
# A local checkout of the gold (e.g. the private Salesteq validation repo) takes
# precedence over the HF pull, so the benchmark runs offline and against
# work-in-progress gold without ever committing it here.
LOCAL_GOLD = os.environ.get("SALESTEQ_GOLD20", "")

# Out of scope for this gold (dataset excludes them): the Buckwalter Latin
# transliteration bucket and the unassigned xaa node.
EXCLUDE = {"ar-Latn-buckwalter", "xaa"}

_STRESS = ("ˈ", "ˌ")


# ─── gold access (HF at run time, or a local dir; never vendored) ─────────────

def _lect_files() -> List[str]:
    """Every ``ar*.tsv`` in the gold repo, from the HF dataset API."""
    url = f"https://huggingface.co/api/datasets/{HF_REPO}"
    with urllib.request.urlopen(url) as fh:
        info = json.load(fh)
    return sorted(
        s["rfilename"] for s in info.get("siblings", [])
        if s["rfilename"].endswith(".tsv")
    )


def _gold_path(fname: str) -> str:
    """Local gold if present, else the cached HF pull (fetched on first use)."""
    if LOCAL_GOLD:
        local = os.path.join(LOCAL_GOLD, fname)
        if os.path.exists(local):
            return local
    os.makedirs(CACHE_DIR, exist_ok=True)
    cached = os.path.join(CACHE_DIR, fname)
    if not os.path.exists(cached):
        print(f"fetching {HF_REPO}/{fname} …", file=sys.stderr)
        urllib.request.urlretrieve(f"{HF_BASE}/{fname}", cached)
    return cached


def load_gold(code: str) -> List[dict]:
    """The gold rows for one lect (id, sentence, raw, ipa, ipa_o2i, …)."""
    with open(_gold_path(f"{code}.tsv"), encoding="utf-8") as fh:
        return list(csv.DictReader(fh, delimiter="\t"))


# ─── scoring (reuses benchmark_stack.edit_distance / _words) ──────────────────

def _tokens(ipa: str, keep_stress: bool) -> List[str]:
    """Comparable tokens. ``_words`` strips stress; the kept-stress path splits
    the same way but leaves the marks on, so the two passes differ only in that."""
    if not keep_stress:
        return _words(ipa)
    return [t for t in (tok.strip() for tok in ipa.split()) if t]


def _per_wer(pred: str, gold: str, keep_stress: bool) -> Tuple[int, int, int, int]:
    """(char_dist, char_len, word_dist, word_len) for one sentence."""
    pw, gw = _tokens(pred, keep_stress), _tokens(gold, keep_stress)
    cp, cg = "".join(pw), "".join(gw)
    return (edit_distance(cg, cp), len(cg), edit_distance(gw, pw), len(gw))


def _rates(acc: List[int]) -> Dict[str, float]:
    cd, cl, wd, wl = acc
    return {"per": cd / max(cl, 1), "wer": wd / max(wl, 1)}


# ─── arms ─────────────────────────────────────────────────────────────────────

def build_arms(code: str, with_epitran: bool,
               pausal: bool = False) -> Dict[str, Callable[[str], str]]:
    """One transcriber per system, keyed by arm name. Optional arms that cannot
    load are simply omitted (the caller reports them as absent, never crashes).

    ``pausal`` picks arbtok's register. The o2i arm is plain ``transcribe``, which
    never pausalizes, and the MSA/Classical gold is cited in full iʿrāb, so the
    like-for-like default is ``pausal=False`` — otherwise arbtok drops a
    phrase-final case ending the gold and o2i both keep, and the gap is a register
    choice, not a phonology error. Dialect gold is already pausal (no case
    endings in the orthography), so the flag barely moves those lects.
    """
    from orthography2ipa import G2P

    from arbtok.plugin import ArbtokG2PPlugin

    arms: Dict[str, Callable[[str], str]] = {}
    arms["o2i"] = G2P(code).transcribe
    arms["arbtok"] = ArbtokG2PPlugin(
        lang=code, diacritize=False, pausal=pausal).transcribe

    try:
        from arbtok.espeak_wrapper import EspeakPhonemizer
        esp = EspeakPhonemizer(pausal=True)
        arms["espeak"] = lambda s: esp.phonemize_string(s, "ar")
    except Exception as exc:  # noqa: BLE001 — optional baseline
        print(f"  (espeak arm unavailable: {exc})", file=sys.stderr)

    if with_epitran:
        try:
            import epitran
            epi = epitran.Epitran("ara-Arab")
            arms["epitran"] = epi.transliterate
        except Exception as exc:  # noqa: BLE001 — optional baseline
            print(f"  (epitran arm unavailable: {exc})", file=sys.stderr)
    return arms


def _safe(arm: Callable[[str], str], text: str) -> str:
    try:
        return arm(text)
    except Exception:  # noqa: BLE001 — a failed arm scores as empty, not a crash
        return ""


# ─── per-lect run + row bucketing ─────────────────────────────────────────────

def run_lect(code: str, with_epitran: bool, pausal: bool = False) -> dict:
    rows = load_gold(code)
    arms = build_arms(code, with_epitran, pausal=pausal)
    # acc[arm][keep_stress] = [char_dist, char_len, word_dist, word_len]
    acc = {a: {False: [0, 0, 0, 0], True: [0, 0, 0, 0]} for a in arms}
    bucket_a, bucket_b = [], []

    for r in rows:
        gold = r["ipa"]
        preds = {a: _safe(fn, r["sentence"]) for a, fn in arms.items()}
        for a, pred in preds.items():
            for keep in (False, True):
                for i, v in enumerate(_per_wer(pred, gold, keep)):
                    acc[a][keep][i] += v

        # Bucketing uses the headline (stress-stripped) char PER on this row.
        def row_per(pred: str) -> float:
            cd, cl, _, _ = _per_wer(pred, gold, keep_stress=False)
            return cd / max(cl, 1)

        o2i_per = row_per(preds["o2i"])
        arb_per = row_per(preds["arbtok"])
        # Also compute stress-kept so a stress-only regression is captured.
        arb_per_s = _per_wer(preds["arbtok"], gold, True)
        o2i_per_s = _per_wer(preds["o2i"], gold, True)
        arb_worse_stress = (arb_per_s[0] / max(arb_per_s[1], 1)) > (
            o2i_per_s[0] / max(o2i_per_s[1], 1))

        if arb_per > o2i_per or (arb_per == o2i_per and arb_worse_stress):
            entry = {
                "id": r["id"], "raw": r["raw"], "sentence": r["sentence"],
                "gold": gold, "o2i": preds["o2i"], "arbtok": preds["arbtok"],
                "o2i_per": round(o2i_per, 4), "arbtok_per": round(arb_per, 4),
                "tag": _subtag(preds["arbtok"], preds["o2i"], arb_per, o2i_per,
                               arb_worse_stress),
            }
            bucket_a.append(entry)

        # Bucket B is independent of arbtok: any row where o2i itself misses the
        # gold. The stored ipa_o2i + fable_corrections say what the spec fix is.
        if o2i_per > 0 or (r.get("ipa_o2i", "") and r["ipa_o2i"] != gold):
            bucket_b.append({
                "id": r["id"], "raw": r["raw"], "gold": gold,
                "o2i": preds["o2i"], "ipa_o2i_snapshot": r.get("ipa_o2i", ""),
                "o2i_per": round(o2i_per, 4),
                "features": r.get("features", ""),
                "fable_corrections": r.get("fable_corrections", ""),
                "notes": r.get("notes", ""),
            })

    return {
        "code": code,
        "sentences": len(rows),
        "arms": {a: {"stripped": _rates(acc[a][False]),
                     "stress": _rates(acc[a][True])} for a in arms},
        "bucket_a": bucket_a,
        "bucket_b": bucket_b,
    }


def _subtag(arb: str, o2i: str, arb_per: float, o2i_per: float,
            stress_only: bool) -> str:
    """A cheap first-pass label for an arbtok-degrades-o2i row, to route the fix.

    Stress-only when the two agree once stress is removed; otherwise a guess from
    the divergent segments so the diff is skimmable. Confirmed by hand in Phase 2.
    """
    if stress_only and arb_per <= o2i_per:
        return "stress"
    aw, ow = _words(arb), _words(o2i)
    diff = [(a, o) for a, o in zip(aw, ow) if a != o]
    if not diff:
        return "segmentation"
    a, o = diff[0]
    if "iː" in a or "uː" in a or "j" in a or "w" in a:
        return "glide/nisba"
    if len(aw) != len(ow):
        return "sandhi"
    return "phonology"


# ─── reporting ────────────────────────────────────────────────────────────────

def _table(report: List[dict], keep_stress: bool) -> str:
    key = "stress" if keep_stress else "stripped"
    arm_order = ["o2i", "arbtok", "espeak", "epitran"]
    head = "| Lect | N | " + " | ".join(
        f"{a} PER" for a in arm_order) + " | " + " | ".join(
        f"{a} WER" for a in arm_order) + " | arbtok≤o2i |"
    sep = "|" + "|".join(["---"] * (2 + 2 * len(arm_order) + 1)) + "|"
    lines = [head, sep]
    for lect in sorted(report, key=lambda e: e["code"]):
        arms = lect["arms"]

        def cell(a: str, m: str) -> str:
            return f"{arms[a][key][m]:.3f}" if a in arms else "n/a"

        ok = "✓" if ("arbtok" in arms and "o2i" in arms and
                     arms["arbtok"][key]["per"] <= arms["o2i"][key]["per"]) else "✗"
        lines.append(
            f"| {lect['code']} | {lect['sentences']} | "
            + " | ".join(cell(a, "per") for a in arm_order) + " | "
            + " | ".join(cell(a, "wer") for a in arm_order) + f" | {ok} |")
    return "\n".join(lines)


def _mean(report: List[dict], arm: str, keep_stress: bool, m: str) -> Optional[float]:
    key = "stress" if keep_stress else "stripped"
    vals = [e["arms"][arm][key][m] for e in report if arm in e["arms"]]
    return sum(vals) / len(vals) if vals else None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--lects", default="",
                    help="comma-separated subset; default is every gold lect")
    ap.add_argument("--no-epitran", action="store_true",
                    help="skip the epitran arm")
    ap.add_argument("--pausal", action="store_true",
                    help="run arbtok in pausal/waqf register (default off, to match the\n                         o2i arm and the full-iʿrab MSA/Classical gold)")
    ap.add_argument("--json", default="",
                    help="write the full machine report (tables + both buckets) here")
    ap.add_argument("--show-buckets", action="store_true",
                    help="also print the per-row Bucket A / Bucket B diffs")
    args = ap.parse_args()

    from arbtok.dialects import supported_lects
    known = {l.code for l in supported_lects()} - EXCLUDE

    if args.lects:
        codes = [c.strip() for c in args.lects.split(",")]
    else:
        gold_codes = {os.path.splitext(f)[0] for f in _lect_files()}
        codes = sorted(gold_codes & known)

    report = []
    for code in codes:
        if code in EXCLUDE:
            continue
        print(f"scoring {code} …", file=sys.stderr)
        report.append(run_lect(code, with_epitran=not args.no_epitran,
                               pausal=args.pausal))

    print(f"\ngold: {HF_REPO} (fully-vocalized, o2i-seeded + paper-corrected)")
    print("arbtok run with diacritize=False; scored vs the `ipa` column\n")
    print("### PER / WER — stress-stripped (headline)\n")
    print(_table(report, keep_stress=False))
    print("\n### PER / WER — stress-kept\n")
    print(_table(report, keep_stress=True))

    for keep in (False, True):
        tag = "stress-kept" if keep else "stripped"
        print(f"\nmean PER ({tag}): "
              + ", ".join(
                  f"{a}={_mean(report, a, keep, 'per'):.3f}"
                  for a in ("o2i", "arbtok", "espeak", "epitran")
                  if _mean(report, a, keep, "per") is not None))

    na = sum(len(e["bucket_a"]) for e in report)
    nb = sum(len(e["bucket_b"]) for e in report)
    print(f"\nBucket A (arbtok degrades o2i): {na} rows  "
          f"— the Phase-2 gate is 0")
    print(f"Bucket B (o2i itself wrong vs gold): {nb} rows  "
          f"— cited-rule leads for the o2i specs")

    if args.show_buckets:
        for e in report:
            for row in e["bucket_a"]:
                print(f"\n[A/{row['tag']}] {row['id']}  ({e['code']})")
                print(f"  raw   : {row['raw']}")
                print(f"  gold  : {row['gold']}")
                print(f"  o2i   : {row['o2i']}   PER={row['o2i_per']}")
                print(f"  arbtok: {row['arbtok']}   PER={row['arbtok_per']}")
            for row in e["bucket_b"]:
                print(f"\n[B] {row['id']}  ({e['code']})  o2i PER={row['o2i_per']}")
                print(f"  gold  : {row['gold']}")
                print(f"  o2i   : {row['o2i']}")
                if row["fable_corrections"]:
                    print(f"  fix   : {row['fable_corrections']}")

    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump({"gold": HF_REPO, "lects": report}, fh,
                      ensure_ascii=False, indent=2)
        print(f"\nwrote {args.json}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
