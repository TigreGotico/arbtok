#!/usr/bin/env python3
"""Does rawi-lattice *fusion* beat the shipped diacritize→phonemize pipeline?

Same question, same gold, two diacritizers. The input is the ``raw`` (bare,
undiacritized) column — what a TTS frontend actually receives — and the
reference is the Fable-corrected ``ipa`` column. For each lect we score:

``current``  ArbtokG2PPlugin(fusion=False) — the shipped stack (rawi-ensemble
             generator); rawi writes one string, the lattice checks it, an
             unlicensed guess falls back to the skeleton.
``curr-v2``  the same generator pipeline but forced to the rawi-v2 single head —
             the model fusion itself uses, so ``fusion − curr-v2`` isolates the
             *mechanism* from the ensemble→single-head model swap.
``fusion``   ArbtokG2PPlugin(fusion=True)  — rawi-v2 *scores* the lattice's
             licensed readings; the best licensed reading is chosen.

Metric is mean per-sentence PER (segment edit distance / reference length),
stress- and punctuation-stripped, the same normalization the shipped harness
uses. The empirical gate: fusion ships only if it beats current on the mean.

    python scripts/benchmark_fusion.py --gold DIR [--lects ar,ar-EG,...]
"""
from __future__ import annotations

import argparse
import csv
import glob
import os
import unicodedata
from typing import List, Tuple

from arbtok.plugin import ArbtokG2PPlugin

_MODS = set("ːˤʰʷʲ̯̃‿ˠ") | {chr(0x0331), chr(0x0301)}


def _norm(ipa: str) -> str:
    s = unicodedata.normalize("NFC", ipa)
    for ch in "ˈˌ.|‖":
        s = s.replace(ch, "")
    return " ".join(s.split())


def _segs(ipa: str) -> List[str]:
    out: List[str] = []
    for ch in _norm(ipa).replace(" ", ""):
        if out and (ch in _MODS or unicodedata.combining(ch)):
            out[-1] += ch
        else:
            out.append(ch)
    return out


def _per(pred: str, gold: str) -> float:
    a, b = _segs(pred), _segs(gold)
    if not b:
        return 0.0
    d = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        prev, d[0] = d[0], i
        for j, cb in enumerate(b, 1):
            prev, d[j] = d[j], min(d[j] + 1, d[j - 1] + 1, prev + (ca != cb))
    return d[-1] / len(b)


def _curr_v2(lect: str) -> ArbtokG2PPlugin:
    """The generator pipeline pinned to rawi-v2 (fusion's model)."""
    from arbtok.diacritize import LatticeDiacritizer
    from arbtok.lexicon import DEFAULT_LEXICON
    p = ArbtokG2PPlugin(lang=lect, diacritize=True, fusion=False)
    p._diacritizer = LatticeDiacritizer(lang=p.lang, model="rawi-v2",
                                        waqf=p.pausal, lexicon=DEFAULT_LEXICON)
    return p


def score_lect(path: str) -> Tuple[str, float, float, float, int]:
    lect = os.path.basename(path)[:-4]
    rows = list(csv.DictReader(open(path, encoding="utf-8"), delimiter="\t"))
    cur = ArbtokG2PPlugin(lang=lect, diacritize=True, fusion=False)
    cv2 = _curr_v2(lect)
    fus = ArbtokG2PPlugin(lang=lect, diacritize=True, fusion=True)
    pc = pv = pf = 0.0
    n = 0
    for r in rows:
        g, raw = r["ipa"], r["raw"]
        for plug, acc in ((cur, "c"), (cv2, "v"), (fus, "f")):
            try:
                pred = plug.transcribe(raw)
            except Exception:
                pred = ""
            d = _per(pred, g)
            if acc == "c":
                pc += d
            elif acc == "v":
                pv += d
            else:
                pf += d
        n += 1
    return lect, pc / n, pv / n, pf / n, n


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gold", required=True, help="dir of <lect>.tsv gold files")
    ap.add_argument("--lects", default="", help="comma-separated subset")
    args = ap.parse_args()

    files = sorted(glob.glob(os.path.join(args.gold, "*.tsv")))
    if args.lects:
        want = {c.strip() for c in args.lects.split(",")}
        files = [f for f in files if os.path.basename(f)[:-4] in want]

    print(f"{'lect':20} {'current':>9} {'curr-v2':>9} {'fusion':>9} "
          f"{'Δvs-cur':>8} {'Δvs-v2':>8} {'N':>4}")
    print("-" * 74)
    rows = []
    for f in files:
        lect, cur, cv2, fus, n = score_lect(f)
        rows.append((lect, cur, cv2, fus, n))
        print(f"{lect:20} {cur:9.3f} {cv2:9.3f} {fus:9.3f} "
              f"{fus - cur:+8.3f} {fus - cv2:+8.3f} {n:4}", flush=True)
    mc = sum(r[1] for r in rows) / len(rows)
    mv = sum(r[2] for r in rows) / len(rows)
    mf = sum(r[3] for r in rows) / len(rows)
    print("-" * 74)
    print(f"{'MEAN':20} {mc:9.3f} {mv:9.3f} {mf:9.3f} "
          f"{mf - mc:+8.3f} {mf - mv:+8.3f}")
    print(f"\nfusion vs shipped current: {mf:.3f} vs {mc:.3f} "
          f"({'BEATS' if mf < mc else 'does NOT beat'})")
    print(f"fusion vs curr-v2 (mechanism, same model): {mf:.3f} vs {mv:.3f} "
          f"({'BEATS' if mf < mv else 'does NOT beat'})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
