#!/usr/bin/env python3
"""Does diacritization actually help? Measure it.

arbtok's input contract is *diacritized* Arabic. Real text is not diacritized —
standard Arabic writes no short vowels — so a diacritizer stands between the two.
This asks whether that diacritizer earns its place, and by how much.

The gold is WikiPron's ``ara_arab_broad`` (~17.5k Wiktionary pairs). It is the
right shape for the question by luck rather than design: its **words are bare
skeletons** (آبد, not آبِد) and its **IPA is the full pronunciation** (ʔaːbid) in
**pausal form**. So the gold task *is* "undiacritized word → IPA", which cannot be
solved without restoring the vowels the writing omits.

Arms
----
``bare``        arbtok straight on the skeleton, no diacritization. The floor:
                whatever the engine can read from consonants alone.
``t2t``         arbtok on ``LatticeDiacritizer`` output — the shipped system.
``t2t-raw``     the same, with the lattice guards OFF (the model's proposal is
                taken as-is). Isolates what the guards are worth.
``t2t-full``    guarded, but with the full iʿrāb kept (waqf off). The gold is
                pausal, so this measures what dropping the endings buys.
``espeak``      espeak-ng's Arabic, the external baseline everyone else uses.

Metrics
-------
``PER``   character-level edit distance / gold length, over the whole set. Lower
          is better. Segmentation-free and broad-normalized on both sides, the
          same way orthography2ipa's own scoreboard scores — so these numbers sit
          on the same scale as the ones already in the repo.
``WER``   fraction of words transcribed exactly right. This is the honest headline:
          PER rewards being *close*, and a TTS voice does not get partial credit
          for a word it mispronounces.

Usage
-----
    python scripts/benchmark_diacritization.py --limit 2000
    python scripts/benchmark_diacritization.py            # full set
    python scripts/benchmark_diacritization.py --arms bare,t2t
"""
from __future__ import annotations

import argparse
import os
import sys
import time
import unicodedata
import urllib.request
from typing import Callable, Dict, List, Tuple

WIKIPRON = (
    "https://raw.githubusercontent.com/CUNY-CL/wikipron/master/data/scrape/tsv/"
    "ara_arab_broad.tsv"
)
CACHE = os.path.join(os.path.dirname(__file__), ".cache_ara_arab_broad.tsv")

# Scoring notation, matched to orthography2ipa's scoreboard so the numbers are
# comparable to the ones already committed there.
_STRESS = "ˈˌ'"
_TIE_BARS = "͜͡‿"
_NARROW = "̝̞̪̺̼̘̙.·()"
_PUNCT = "|‖,.;:!?¡¿\"«»—–-"


def normalize(ipa: str) -> str:
    """Broad, stress-free, segmentation-free — the gold's tier, on both sides."""
    s = unicodedata.normalize("NFC", ipa)
    for ch in _STRESS + _TIE_BARS + _PUNCT:
        s = s.replace(ch, "")
    decomposed = unicodedata.normalize("NFD", s)
    s = unicodedata.normalize("NFC", "".join(c for c in decomposed if c not in _NARROW))
    return "".join(s.split())


def edit_distance(a: str, b: str) -> int:
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def load_gold(limit: int) -> List[Tuple[str, str]]:
    if not os.path.exists(CACHE):
        print(f"fetching {WIKIPRON} …", file=sys.stderr)
        urllib.request.urlretrieve(WIKIPRON, CACHE)
    pairs = []
    with open(CACHE, encoding="utf-8") as fh:
        for line in fh:
            parts = line.rstrip("\n").split("\t")
            if len(parts) != 2:
                continue
            word, ipa = parts
            # Single words only: the engine's contract is a word, and a phrase
            # would score the sandhi rather than the diacritizer.
            if " " in word.strip():
                continue
            pairs.append((word.strip(), ipa))
            if limit and len(pairs) >= limit:
                break
    return pairs


# ─── the arms ───────────────────────────────────────────────────────────

def build_arms(names: List[str], lang: str) -> Dict[str, Callable[[str], str]]:
    from arbtok.plugin import ArbtokG2PPlugin
    from arbtok.diacritize import LatticeDiacritizer

    arms: Dict[str, Callable[[str], str]] = {}

    if "bare" in names:
        plugin = ArbtokG2PPlugin(lang=lang, diacritize=False)
        arms["bare"] = plugin.transcribe_word

    if "t2t" in names:
        plugin = ArbtokG2PPlugin(lang=lang, diacritize=True)
        arms["t2t"] = lambda w: plugin.transcribe_word(plugin.normalize(w))

    if "t2t-raw" in names:
        # The guards off: take the model's proposal verbatim.
        from text2tashkeel import Diacritizer
        raw = Diacritizer(waqf=True)
        bare = ArbtokG2PPlugin(lang=lang, diacritize=False)
        arms["t2t-raw"] = lambda w: bare.transcribe_word(raw.diacritize(w))

    if "t2t-full" in names:
        guarded_full = LatticeDiacritizer(lang=lang, waqf=False)
        bare = ArbtokG2PPlugin(lang=lang, diacritize=False)
        arms["t2t-full"] = lambda w: bare.transcribe_word(
            guarded_full.diacritize_word(w))

    if "espeak" in names:
        from arbtok.espeak_wrapper import EspeakPhonemizer
        espeak = EspeakPhonemizer(pausal=True)
        arms["espeak"] = lambda w: espeak.phonemize_string(w, "ar")

    return arms


def evaluate(arm: Callable[[str], str], pairs: List[Tuple[str, str]]) -> dict:
    total_dist = total_len = exact = failed = 0
    t0 = time.time()
    for word, gold_ipa in pairs:
        gold = normalize(gold_ipa)
        try:
            hyp = normalize(arm(word) or "")
        except Exception:
            hyp, failed = "", failed + 1
        total_dist += edit_distance(hyp, gold)
        total_len += len(gold)
        exact += hyp == gold
    n = len(pairs)
    return {
        "PER": 100.0 * total_dist / max(total_len, 1),
        "WER": 100.0 * (1 - exact / max(n, 1)),
        "exact": exact,
        "n": n,
        "failed": failed,
        "secs": time.time() - t0,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--limit", type=int, default=0, help="0 = the whole gold set")
    ap.add_argument("--lang", default="ar")
    ap.add_argument("--arms", default="bare,t2t,t2t-raw,t2t-full")
    args = ap.parse_args()

    pairs = load_gold(args.limit)
    names = [a.strip() for a in args.arms.split(",") if a.strip()]
    arms = build_arms(names, args.lang)

    print(f"\ngold: WikiPron ara_arab_broad — {len(pairs)} single-word pairs")
    print(f"lang: {args.lang}   (PER and WER: lower is better)\n")
    print(f"{'arm':10} {'PER %':>8} {'WER %':>8} {'exact':>8} {'failed':>7} {'secs':>7}")
    print("-" * 54)

    results = {}
    for name in names:
        if name not in arms:
            continue
        r = evaluate(arms[name], pairs)
        results[name] = r
        print(f"{name:10} {r['PER']:8.2f} {r['WER']:8.2f} {r['exact']:8d} "
              f"{r['failed']:7d} {r['secs']:7.1f}")

    if "bare" in results and "t2t" in results:
        d_per = results["bare"]["PER"] - results["t2t"]["PER"]
        d_wer = results["bare"]["WER"] - results["t2t"]["WER"]
        print(f"\ndiacritization is worth {d_per:+.2f} PER points and "
              f"{d_wer:+.2f} WER points")
    if "t2t" in results and "t2t-raw" in results:
        d = results["t2t-raw"]["PER"] - results["t2t"]["PER"]
        print(f"the lattice guards are worth {d:+.2f} PER points")
    if "t2t" in results and "t2t-full" in results:
        d = results["t2t-full"]["PER"] - results["t2t"]["PER"]
        print(f"waqf (dropping the iʿrāb) is worth {d:+.2f} PER points "
              f"— the gold is pausal")
    print()


if __name__ == "__main__":
    main()
