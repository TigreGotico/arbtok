#!/usr/bin/env python3
"""Is arbtok earning its keep?

arbtok sits on top of orthography2ipa and text2tashkeel. It is worth having only
if the whole is better than its parts, so this scores every layer of the stack on
one gold set, with one metric, and prints them next to each other.

The gold is WikiPron ``ara_arab_broad`` (17,563 pairs). Its shape is what makes it
the right question: the **words are bare skeletons** (آبد, not آبِد) and the **IPA
is the full pronunciation** (ʔaːbid). So the task *is* "undiacritized Arabic → IPA",
which is the thing we actually have to do, and which cannot be solved without
putting back the vowels the writing omits.

The arms, bottom of the stack upward
------------------------------------
``o2i``                orthography2ipa alone, on the undiacritized word. The floor:
                       what the grapheme rules can read from a skeleton.
``o2i+t2t``            orthography2ipa on text2tashkeel's raw output — the
                       diacritizer's own guess, unguarded. This is the arm that
                       says how much of the win is *just the model*.
``arbtok``             arbtok with no diacritizer, on the skeleton. Its lattice,
                       rescorers, stress and pausal rules, and nothing restored.
``arbtok+t2t``         the shipped system: arbtok on the lattice-guarded
                       diacritizer's output.
``arbtok+t2t (no waqf)`` the same, keeping the full iʿrāb. The gold is mostly
                       pausal, so this prices the case endings.
``espeak``             espeak-ng's Arabic — the external baseline everyone else
                       uses, and the number to beat.

Metrics
-------
``PER``   character edit distance / gold length over the whole set. Lower is better.
``WER``   fraction of words that are not exactly right. This is the honest headline:
          PER rewards being close, and a TTS voice gets no partial credit for a word
          it mispronounces.

Both sides are stress-stripped and space-joined, so the arms differ only in what
they claim the word sounds like.

Usage
-----
    python scripts/benchmark_stack.py               # full gold
    python scripts/benchmark_stack.py --limit 4000  # strided sample
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from typing import Callable, Dict, List, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from benchmark_diacritization import load_gold  # noqa: E402


def normalize(ipa: str) -> str:
    """Strip what the arms are not being asked about: stress and segmentation."""
    return ipa.replace(" ", "").replace("ˈ", "").replace("ˌ", "")


def edit_distance(a: str, b: str) -> int:
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def build_stack(lang: str) -> Dict[str, Callable[[str], str]]:
    from orthography2ipa import G2P

    from arbtok.diacritize import LatticeDiacritizer
    from arbtok.plugin import ArbtokG2PPlugin

    o2i = G2P(lang)
    guarded = LatticeDiacritizer(lang=lang)
    guarded_full = LatticeDiacritizer(lang=lang, waqf=False)
    arbtok_bare = ArbtokG2PPlugin(lang=lang, diacritize=False)
    arbtok_full = ArbtokG2PPlugin(lang=lang, diacritize=True)

    def raw_t2t():
        """text2tashkeel with no lattice guard — the model's own unchecked guess."""
        from text2tashkeel import Diacritizer
        return Diacritizer(waqf=True)

    loose = raw_t2t()

    def espeak(word: str) -> str:
        from arbtok.espeak_wrapper import EspeakPhonemizer
        return EspeakPhonemizer(pausal=True).phonemize_string(word, "ar")

    return {
        "o2i": o2i.transcribe_word,
        "o2i+t2t": lambda w: o2i.transcribe_word(loose.diacritize(w)),
        "arbtok": arbtok_bare.transcribe_word,
        "arbtok+t2t": lambda w: arbtok_full.transcribe_word(arbtok_full.normalize(w)),
        "arbtok+t2t (no waqf)": lambda w: arbtok_bare.transcribe_word(
            guarded_full.diacritize_word(w)),
        "espeak": espeak,
    }


def evaluate(arm: Callable[[str], str],
             pairs: List[Tuple[str, str]]) -> dict:
    dist = length = exact = failed = 0
    t0 = time.time()
    for word, gold in pairs:
        try:
            pred = normalize(arm(word))
        except Exception:
            pred = ""
            failed += 1
        gold = normalize(gold)
        dist += edit_distance(gold, pred)
        length += len(gold)
        exact += (gold == pred)
    return {
        "per": dist / max(length, 1),
        "wer": 1 - exact / max(len(pairs), 1),
        "exact": exact,
        "failed": failed,
        "seconds": time.time() - t0,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--lang", default="ar")
    ap.add_argument("--limit", type=int, default=0,
                    help="score a sample of this size, spread ACROSS the gold. "
                         "The gold is sorted alphabetically, so taking the first "
                         "N would score only the words that start with alif.")
    ap.add_argument("--arms", default="",
                    help="comma-separated subset; default is the whole stack")
    args = ap.parse_args()

    pairs = load_gold(0)
    if args.limit and args.limit < len(pairs):
        stride = len(pairs) // args.limit
        pairs = pairs[::stride][:args.limit]

    stack = build_stack(args.lang)
    if args.arms:
        wanted = [a.strip() for a in args.arms.split(",")]
        stack = {k: v for k, v in stack.items() if k in wanted}

    print(f"gold: WikiPron ara_arab_broad — {len(pairs)} words, lang={args.lang}\n")
    print(f"{'arm':24} {'PER':>8} {'WER':>8} {'exact':>7} {'fail':>6} {'sec':>7}")
    print("-" * 64)
    for name, arm in stack.items():
        r = evaluate(arm, pairs)
        print(f"{name:24} {r['per']:8.4f} {r['wer']:8.4f} {r['exact']:7} "
              f"{r['failed']:6} {r['seconds']:7.1f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
