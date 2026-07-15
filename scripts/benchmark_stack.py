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
``arbtok+lex+t2t``     the same, with the diacritized-stem lexicon consulted first
                       (:mod:`arbtok.lexicon`). Which vowels a word carries is a
                       lexical fact; this is the arm that stops guessing at it.
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
from typing import Callable, Dict, List, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from benchmark_diacritization import load_gold  # noqa: E402

from arbtok.lexicon import DEFAULT_LEXICON  # noqa: E402


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


def build_stack(lang: str, lexicon: str) -> Dict[str, Callable[[str], str]]:
    from orthography2ipa import G2P

    from arbtok.diacritize import LatticeDiacritizer
    from arbtok.plugin import ArbtokG2PPlugin

    o2i = G2P(lang)
    guarded_full = LatticeDiacritizer(lang=lang, waqf=False, lexicon=None)
    arbtok_bare = ArbtokG2PPlugin(lang=lang, diacritize=False)
    arbtok_full = ArbtokG2PPlugin(lang=lang, diacritize=True, lexicon=None)
    arbtok_lex = ArbtokG2PPlugin(lang=lang, diacritize=True, lexicon=lexicon)
    # Rawi-lattice fusion: the diacritizer as a scorer over licensed readings
    # rather than a free generator (docs/rawi-fusion.md). Off in the shipped
    # stack; measured here against the generator arm on the same lexicon.
    arbtok_fusion = ArbtokG2PPlugin(lang=lang, diacritize=True, lexicon=lexicon,
                                    fusion=True)

    def raw_t2t():
        """text2tashkeel with no lattice guard — the model's own unchecked guess."""
        from text2tashkeel import Diacritizer  # optional, benchmark-only (not an arbtok dependency)
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
        "arbtok+lex+t2t": lambda w: arbtok_lex.transcribe_word(
            arbtok_lex.normalize(w)),
        "arbtok+lex+fusion": lambda w: arbtok_fusion.transcribe_word(
            arbtok_fusion.normalize(w)),
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


# ─── per-lect TTS-gold benchmark (roadmap F1 + D1) ────────────────────────
#
# A second gold and a second question. The WikiPron arm above asks "MSA word →
# IPA"; this arm asks "does a *dialect* sentence, diacritized or bare, come out
# the way the requested lect's cited rules say it should?" — the thing the
# spec-driven resolution (``supported_lects``) exists to make measurable.
#
# The gold is orthography2ipa's Arabic TTS set: one TSV per lect, sentence-level,
# with a vocalized ``sentence``, its bare ``raw`` skeleton, and a reference
# ``ipa``. Its provenance is honest and load-bearing: the reference IPA is
# LLM-generated from the specs' cited rules, then rule-anchored — it is an
# o2i-regression snapshot, NOT native-validated ground truth. So every number
# here is *engine similarity* to cited-rule o2i output, and a lect where arbtok
# scores well means "arbtok reproduces what o2i's rules predict", not "a native
# speaker signed off". Read docs/benchmarks.md before quoting any figure.

import csv  # noqa: E402
import glob  # noqa: E402
import json  # noqa: E402
import unicodedata  # noqa: E402

_STRESS = ("ˈ", "ˌ")
_PUNCT = "،؟؛.,!?:؛«»\"'()[]{}…—–-"


def gold_dir() -> str:
    """The installed orthography2ipa's Arabic TTS gold directory.

    Read from the package so it tracks whatever spec data is installed rather
    than a path baked in here.
    """
    import orthography2ipa
    return os.path.join(os.path.dirname(orthography2ipa.__file__),
                        "data", "gold", "arabic_tts")


def strip_harakat(text: str) -> str:
    """Drop the vowel marks the writing may omit (every combining mark).

    This is the undiacritized path's input: the same sentence a person actually
    types. On this gold it reproduces the ``raw`` column exactly (verified), so
    the diacritized/undiacritized delta prices exactly the missing harakat.
    """
    return "".join(c for c in unicodedata.normalize("NFC", text)
                   if unicodedata.category(c) != "Mn")


def _words(ipa: str) -> List[str]:
    """Comparable tokens: stress-stripped, punctuation-stripped, non-empty.

    Sentence PER and WER both ask only what the words sound like, so stress and
    orthographic punctuation — which neither espeak nor the gold treat
    consistently — are removed before either is measured.
    """
    for mark in _STRESS:
        ipa = ipa.replace(mark, "")
    out = []
    for tok in ipa.split():
        tok = tok.strip(_PUNCT)
        if tok:
            out.append(tok)
    return out


def score_pair(pred: str, gold: str) -> Tuple[int, int, int, int]:
    """(char_dist, char_len, word_dist, word_len) for one sentence."""
    pw, gw = _words(pred), _words(gold)
    cp, cg = "".join(pw), "".join(gw)
    return (edit_distance(cg, cp), len(cg),
            edit_distance(gw, pw), len(gw))


def load_lect_gold(path: str) -> List[Tuple[str, str, str, str]]:
    """(id, vocalized sentence, bare skeleton, reference IPA) rows for one lect."""
    rows = []
    with open(path, encoding="utf-8") as fh:
        for r in csv.DictReader(fh, delimiter="\t"):
            raw = r.get("raw") or strip_harakat(r["sentence"])
            rows.append((r["id"], r["sentence"], raw, r["ipa"]))
    return rows


def _espeak_available() -> bool:
    import shutil
    return bool(shutil.which("espeak-ng") or shutil.which("espeak"))


def run_lect_benchmark(codes: Optional[List[str]] = None,
                       lexicon: Optional[str] = None,
                       limit: int = 0,
                       with_espeak: bool = True,
                       pausal: bool = True) -> dict:
    """Score arbtok (diacritized and undiacritized) and espeak-ng per lect.

    arbtok runs the shipped full stack (diacritizer + lexicon where given) on the
    variety's own spec. espeak-ng has no dialect voices, so *every* lect is scored
    against its single ``ar`` (MSA) voice — an honest apples-to-oranges baseline:
    espeak is not being asked the dialect question, it simply has no way to answer
    it, and the gap is the point.

    The arbtok columns never skip. The espeak column is skipped as a whole (per
    lect ``espeak`` left ``None``) only when no espeak binary is installed.
    """
    from arbtok.dialects import supported_lects
    from arbtok.plugin import ArbtokG2PPlugin

    tiers = {lect.code: lect.tier for lect in supported_lects()}

    files = sorted(glob.glob(os.path.join(gold_dir(), "*.tsv")))
    available = {os.path.splitext(os.path.basename(f))[0]: f for f in files}
    if codes:
        available = {c: available[c] for c in codes if c in available}

    espeak_on = with_espeak and _espeak_available()
    espeak = None
    if espeak_on:
        from arbtok.espeak_wrapper import EspeakPhonemizer
        espeak = EspeakPhonemizer(pausal=True)

    results = {}
    for code, path in available.items():
        rows = load_lect_gold(path)
        if limit:
            rows = rows[:limit]
        plugin = ArbtokG2PPlugin(lang=code, diacritize=True, lexicon=lexicon,
                                 pausal=pausal)

        acc = {k: [0, 0, 0, 0] for k in ("diac", "undiac", "espeak")}
        n = 0
        for _id, sentence, raw, gold in rows:
            n += 1
            for arm, source, on in (("diac", sentence, True),
                                    ("undiac", raw, True),
                                    ("espeak", sentence, espeak_on)):
                if not on:
                    continue
                try:
                    if arm == "espeak":
                        pred = espeak.phonemize_string(source, "ar")
                    else:
                        pred = plugin.transcribe(source)
                except Exception:
                    pred = ""
                for i, v in enumerate(score_pair(pred, gold)):
                    acc[arm][i] += v

        def rates(key):
            cd, cl, wd, wl = acc[key]
            return {"per": cd / max(cl, 1), "wer": wd / max(wl, 1)}

        entry = {
            "tier": tiers.get(code, "unknown"),
            "sentences": n,
            "arbtok_diac": rates("diac"),
            "arbtok_undiac": rates("undiac"),
        }
        entry["undiac_delta_per"] = (entry["arbtok_undiac"]["per"]
                                     - entry["arbtok_diac"]["per"])
        entry["undiac_delta_wer"] = (entry["arbtok_undiac"]["wer"]
                                     - entry["arbtok_diac"]["wer"])
        entry["espeak"] = rates("espeak") if espeak_on else None
        results[code] = entry

    return {
        "gold": "orthography2ipa/data/gold/arabic_tts (o2i #358)",
        "provenance": "LLM-generated from cited spec rules; engine-similarity, "
                      "not native-validated ground truth",
        "espeak": "ar (MSA) voice for every lect — no dialect voices exist",
        "lexicon": lexicon,
        "pausal": pausal,
        "lects": results,
    }


def lect_markdown_table(report: dict) -> str:
    """A markdown table of the per-lect report, sorted worst-arbtok-first."""
    rows = sorted(report["lects"].items(),
                  key=lambda kv: kv[1]["arbtok_diac"]["per"])
    head = ("| Lect | Tier | N | arbtok PER (diac) | arbtok WER (diac) | "
            "arbtok PER (bare) | arbtok WER (bare) | ΔPER (bare−diac) | "
            "espeak PER | espeak WER |")
    sep = "|" + "|".join(["---"] * 10) + "|"
    lines = [head, sep]
    for code, e in rows:
        es = e["espeak"]
        es_per = f"{es['per']:.3f}" if es else "n/a"
        es_wer = f"{es['wer']:.3f}" if es else "n/a"
        lines.append(
            f"| {code} | {e['tier']} | {e['sentences']} | "
            f"{e['arbtok_diac']['per']:.3f} | {e['arbtok_diac']['wer']:.3f} | "
            f"{e['arbtok_undiac']['per']:.3f} | {e['arbtok_undiac']['wer']:.3f} | "
            f"{e['undiac_delta_per']:+.3f} | {es_per} | {es_wer} |")
    return "\n".join(lines)


def _run_lect_mode(args) -> int:
    codes = [c.strip() for c in args.lects.split(",")] if args.lects else None
    report = run_lect_benchmark(codes=codes, lexicon=args.lexicon,
                                limit=args.limit,
                                with_espeak=not args.no_espeak,
                                pausal=not args.full_irab)
    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump(report, fh, ensure_ascii=False, indent=2)
    print(f"gold: {report['gold']}")
    print(f"provenance: {report['provenance']}")
    print(f"espeak baseline: {report['espeak']}\n")
    print(lect_markdown_table(report))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--lect", action="store_true",
                    help="per-lect TTS-gold mode (roadmap F1 + D1): score arbtok "
                         "diacritized AND undiacritized, plus espeak-ng, over the "
                         "o2i Arabic TTS gold, one row per lect")
    ap.add_argument("--lects", default="",
                    help="--lect mode: comma-separated subset of lect codes; "
                         "default is every lect with a gold file")
    ap.add_argument("--json", default="",
                    help="--lect mode: also write the full report as JSON here")
    ap.add_argument("--full-irab", action="store_true",
                    help="--lect mode: run arbtok with pausal=False — the "
                         "full-iʿrāb passthrough register, the right mode "
                         "against iʿrāb-keeping gold (Wright I §372 "
                         "pausal forms are the default)")
    ap.add_argument("--no-espeak", action="store_true",
                    help="--lect mode: skip the espeak column (arbtok never skips)")
    ap.add_argument("--lang", default="ar")
    ap.add_argument("--limit", type=int, default=0,
                    help="score a sample of this size, spread ACROSS the gold. "
                         "The gold is sorted alphabetically, so taking the first "
                         "N would score only the words that start with alif.")
    ap.add_argument("--lexicon", default=DEFAULT_LEXICON,
                    help="the stem lexicon the lexicon arm consults: a path, a "
                         "URL, or an hf:// id")
    ap.add_argument("--arms", default="",
                    help="comma-separated subset; default is the whole stack")
    args = ap.parse_args()

    if args.lect:
        return _run_lect_mode(args)

    pairs = load_gold(0)
    if args.limit and args.limit < len(pairs):
        stride = len(pairs) // args.limit
        pairs = pairs[::stride][:args.limit]

    stack = build_stack(args.lang, args.lexicon)
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
