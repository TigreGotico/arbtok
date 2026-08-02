#!/usr/bin/env python3
"""How does arbtok read the Qur'an? Score it against IqraEval/Iqra_train.

The gold is `IqraEval/Iqra_train <https://huggingface.co/datasets/IqraEval/Iqra_train>`_
(74k rows of Qur'anic and MSA sentences with a custom phoneme notation, built for
the IqraEval / Qur'an recitation-assessment shared task). Three text columns
matter here, all pulled straight off HF at run time and cached locally
(``scripts/.cache_iqraeval`` — **no gold is vendored into this repo**, see
docs/benchmarks.md and the repo's existing ``benchmark_gold20.py`` for the same
convention):

  ``sentence``            undiacritized orthography — bare abjad skeleton.
  ``tashkeel_sentence``   fully diacritized orthography — arbtok's input contract.
  ``phoneme_ref``         space-separated phoneme reference, one symbol/pair per
                          phone (``phoneme_aug`` is byte-identical on every row we
                          sampled — dev + 8k train rows — so it is not scored
                          separately).

Only the parquet's *text* columns are ever read: ``load_gold`` opens the remote
parquet with ``pyarrow`` + ``huggingface_hub.HfFileSystem`` and requests
``columns=[...]`` without ``audio``, so pyarrow's column projection fetches HTTP
byte-ranges for the requested columns only — the multi-GB ``audio`` column, and
its bytes, are never transferred. This is why the loader needs ``pyarrow``
directly rather than the ``datasets`` library's default (whole-file) download path.

Notation
--------
``phoneme_ref`` is Nawar Halabi's Arabic-Phonetiser output notation (the same
rule-based G2P vendored as ``mantoq/buck/phonetise_buckwalter.py`` in phoonnx's
thirdparty tree, adapted from
https://github.com/nawarhalabi/Arabic-Phonetiser/blob/master/phonetise-Buckwalter.py,
CC BY-NC 4.0). Verified symbol-by-symbol against a 5,050-row sample (the full dev
split + 2,462 train rows): every one of the 67 distinct space-separated tokens
that appear is accounted for by ``NOTATION`` below, and ``phoneme_aug`` is
identical to ``phoneme_ref`` on every sampled row (0/5050 differ).

  consonant b t ^ j H x d * r z s $ S D T Z E g f q k l m n h w y <
  IPA       b t θ dʒ ħ x d ð r z s ʃ sˤ dˤ tˤ ðˤ ʕ ɣ f q k l m n h w j ʔ

  vowel   a  aa  A  AA  i  ii  I   II  u  uu  U  UU
  IPA     a  aː  ɑ  ɑː  i  iː  ɪ   ɪː  u  uː  ʊ  ʊː

Plain-case ``a/i/u`` (short) and ``aa/ii/uu`` (long) are the ordinary
fatḥa/kasra/ḍamma vowels; the upper-case pair is Halabi's emphatic-context
allophone, triggered by a neighbouring pharyngealized consonant (``D S T Z g x q``)
— the same environment o2i's own ``ar`` spec licenses ɑ/ɪ/ʊ in
(``docs/dialects.md``, "emphasis spreading"). A doubled *consonant* token
(``bb``, ``nn``, ``$$`` …) is gemination from shadda: the base consonant's IPA
plus ``ː``. No silence, pause, or explicit stress token appears in the sample;
Halabi's notation carries no stress mark of its own — see "Honesty" below for
what that means for scoring.

Two input arms, scored separately (arbtok's contract is diacritized text; it can
also self-diacritize):

  ``diac``  arbtok on ``tashkeel_sentence`` with ``diacritize=False`` — the marks
            are already there, nothing to restore.
  ``bare``  arbtok on ``sentence`` with ``diacritize=True`` — the bundled rawi
            ensemble must restore the vowels this task's ``sentence`` column
            omits (n.b.: on this corpus ``sentence`` frequently already carries
            *some* tashkeel — Qur'anic text is rarely typed fully bare — so
            ``bare`` prices "restore what's missing", not "restore everything").

Register: this is continuous Qur'anic recitation, not TTS. arbtok defaults to
the pausal (spoken) register; the gold keeps full case/mood endings throughout
(tajweed waṣl — connected recitation only pauses at a marked waqf sign), so both
arms run with ``register="full"`` (``pausal=False``), matching the convention
``benchmark_gold20.py`` already uses for MSA/Classical gold.

Usage
-----
    python scripts/benchmark_iqraeval.py                  # dev split, full
    python scripts/benchmark_iqraeval.py --split train --limit 5000
    python scripts/benchmark_iqraeval.py --json out.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import unicodedata
from collections import Counter
from typing import Dict, List, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from benchmark_stack import edit_distance  # noqa: E402

HF_REPO = "IqraEval/Iqra_train"
CACHE_DIR = os.environ.get(
    "IQRAEVAL_CACHE",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), ".cache_iqraeval"),
)
TEXT_COLUMNS = ["id", "sentence", "tashkeel_sentence", "phoneme_ref"]

# ─── Halabi phonetiser notation → IPA (see module docstring for citation) ─────

_CONSONANTS = {
    "b": "b", "t": "t", "^": "θ", "j": "dʒ", "H": "ħ", "x": "x", "d": "d",
    "*": "ð", "r": "r", "z": "z", "s": "s", "$": "ʃ", "S": "sˤ", "D": "dˤ",
    "T": "tˤ", "Z": "ðˤ", "E": "ʕ", "g": "ɣ", "f": "f", "q": "q", "k": "k",
    "l": "l", "m": "m", "n": "n", "h": "h", "w": "w", "y": "j", "<": "ʔ",
}
_VOWELS = {
    "a": "a", "aa": "aː", "A": "ɑ", "AA": "ɑː",
    "i": "i", "ii": "iː", "I": "ɪ", "II": "ɪː",
    "u": "u", "uu": "uː", "U": "ʊ", "UU": "ʊː",
}

NOTATION: Dict[str, str] = dict(_VOWELS)
for _sym, _ipa in _CONSONANTS.items():
    NOTATION[_sym] = _ipa
    NOTATION[_sym * 2] = _ipa + "ː"  # gemination: doubled token, shadda


def phoneme_ref_to_ipa(ref: str) -> str:
    """Map one space-separated ``phoneme_ref`` string to a bare IPA string.

    Unmapped tokens are surfaced verbatim inside ``{{ }}`` rather than silently
    dropped — the benchmark treats an unknown symbol as an error to investigate,
    never a skip (see module docstring: every symbol in the 5,050-row sample is
    accounted for, so this path should not trigger on the dev/train splits).
    """
    out = []
    for tok in ref.split():
        ipa = NOTATION.get(tok)
        out.append(ipa if ipa is not None else f"{{{{{tok}}}}}")
    return "".join(out)


# ─── gold access (HF parquet, column-projected, cached; never vendored) ───────

def _cache_path(split: str) -> str:
    os.makedirs(CACHE_DIR, exist_ok=True)
    return os.path.join(CACHE_DIR, f"{split}.parquet")


def _remote_files(split: str) -> List[str]:
    from huggingface_hub import HfApi
    api = HfApi()
    info = api.dataset_info(HF_REPO)
    files = sorted(
        s.rfilename for s in info.siblings
        if s.rfilename.startswith(f"data/{split}-")
    )
    if not files:
        raise FileNotFoundError(f"no {split!r} parquet files in {HF_REPO}")
    return files


def load_gold(split: str, limit: int = 0) -> "list[dict]":
    """Text-only rows for *split* ('dev' or 'train'), pulled and cached once.

    Reads only ``TEXT_COLUMNS`` (never ``audio``) via pyarrow column projection
    over ``HfFileSystem`` — this is what keeps a 74k-row, multi-GB dataset to a
    few MB on the wire.
    """
    import pandas as pd

    # Cache key includes the limit for train (71k rows; fetching all 29 shards
    # just to keep the first N would pull the whole split over the wire for
    # nothing — one shard is ~2.4k rows, so a handful cover any reasonable
    # --limit). The dev split is one file and is always cached whole.
    cache = _cache_path(split if split == "dev" or not limit else f"{split}-{limit}")
    if os.path.exists(cache):
        df = pd.read_parquet(cache)
    else:
        import pyarrow.parquet as pq
        from huggingface_hub import HfFileSystem

        fs = HfFileSystem()
        frames = []
        rows_so_far = 0
        for fname in _remote_files(split):
            print(f"fetching columns {TEXT_COLUMNS} from {HF_REPO}/{fname} …",
                  file=sys.stderr)
            path = f"datasets/{HF_REPO}/{fname}"
            table = pq.read_table(path, filesystem=fs, columns=TEXT_COLUMNS)
            frames.append(table.to_pandas())
            rows_so_far += table.num_rows
            if limit and rows_so_far >= limit:
                break  # enough shards fetched to satisfy the row cap
        df = pd.concat(frames, ignore_index=True) if len(frames) > 1 else frames[0]
        df.to_parquet(cache)
    if limit:
        df = df.iloc[:limit]
    return df.to_dict(orient="records")


# ─── scoring ───────────────────────────────────────────────────────────────────

_STRESS = ("ˈ", "ˌ")


def normalize(ipa: str) -> str:
    """NFC, stress-stripped, whitespace-collapsed — applied to both sides."""
    s = unicodedata.normalize("NFC", ipa)
    for m in _STRESS:
        s = s.replace(m, "")
    return "".join(s.split())


def score(rows: "list[dict]", transcribe, undiac: bool) -> Tuple[dict, list]:
    """Aggregate PER + a per-row detail list (pred, gold, id) for confusion work."""
    char_dist = char_len = 0
    details = []
    col = "sentence" if undiac else "tashkeel_sentence"
    for row in rows:
        text = row[col]
        gold_ipa = normalize(phoneme_ref_to_ipa(row["phoneme_ref"]))
        try:
            pred_ipa = normalize(transcribe(text))
        except Exception as exc:  # a crash is a data point, not a silent skip
            pred_ipa = f"<<ERROR:{exc}>>"
        d = edit_distance(gold_ipa, pred_ipa)
        char_dist += d
        char_len += len(gold_ipa)
        details.append({"id": row["id"], "text": text, "pred": pred_ipa,
                         "gold": gold_ipa, "dist": d})
    per = char_dist / max(char_len, 1)
    return {"per": per, "n": len(rows), "char_len": char_len}, details


def confusion_pairs(details: "list[dict]", top: int = 20) -> "list[tuple]":
    """Top character-substitution confusions via a simple aligned edit trace.

    Not a full alignment (this is a diagnostic, not the scored metric): walks
    both strings greedily from the shorter prefix match, which is enough to
    surface the dominant confusion classes on a corpus this size.
    """
    import difflib
    counts: Counter = Counter()
    for d in details:
        if d["dist"] == 0:
            continue
        sm = difflib.SequenceMatcher(None, d["gold"], d["pred"])
        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            if tag == "equal":
                continue
            g = d["gold"][i1:i2] or "∅"
            p = d["pred"][j1:j2] or "∅"
            counts[(g, p)] += 1
    return counts.most_common(top)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--split", choices=["dev", "train"], default="dev")
    ap.add_argument("--limit", type=int, default=0,
                    help="row cap (default: 0 = full dev; use for train, which is 71k rows)")
    ap.add_argument("--json", default=None)
    args = ap.parse_args()

    from arbtok.plugin import ArbtokG2PPlugin

    diac_engine = ArbtokG2PPlugin(lang="ar", diacritize=False, register="full")
    bare_engine = ArbtokG2PPlugin(lang="ar", diacritize=True, register="full")

    rows = load_gold(args.split, limit=args.limit)
    print(f"{args.split}: {len(rows)} rows", file=sys.stderr)

    diac_metrics, diac_details = score(rows, diac_engine.transcribe, undiac=False)
    bare_metrics, bare_details = score(rows, bare_engine.transcribe, undiac=True)

    print("-" * 72)
    print(f"arbtok on IqraEval/{args.split} (register=full, n={diac_metrics['n']})")
    print(f"  diac (tashkeel_sentence, diacritize=False): PER {diac_metrics['per']:.4f}")
    print(f"  bare (sentence, diacritize=True):           PER {bare_metrics['per']:.4f}")
    print("-" * 72)

    print("Top 20 confusion pairs — diac arm (gold -> pred):")
    for (g, p), c in confusion_pairs(diac_details):
        print(f"  {g!r:>8} -> {p!r:<8}  x{c}")

    if args.json:
        out = {
            "split": args.split,
            "n": diac_metrics["n"],
            "diac": diac_metrics,
            "bare": bare_metrics,
            "confusions_diac": confusion_pairs(diac_details),
            "confusions_bare": confusion_pairs(bare_details),
        }
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump(out, fh, ensure_ascii=False, indent=2)
        print(f"wrote {args.json}", file=sys.stderr)


if __name__ == "__main__":
    main()
