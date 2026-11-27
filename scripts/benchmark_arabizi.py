"""Score the Arabizi path on data/gold_arabizi.

    python scripts/benchmark_arabizi.py [--attested CACHE_DIR] [--out benchmarks/arabizi.json]

The `constructed` tier is data/gold_arabizi. `--attested` adds human-written Arabizi
from three public sets, fetched at pinned commits into CACHE_DIR because their
licences do not allow a copy in this repository: DODa (ar-MA, sentences, CC BY-NC
4.0), NArabizi (ar-DZ, test split, Arabic tokens only; Seddah et al. 2020, Touileb & Barnes 2021) and TArC
(ar-TN, words tagged `arabizi` whose CODA field is all Arabic script, CC BY-NC-SA 4.0). Each attested tier takes its
first LIMIT units.

Two scores for each row of each tier:

* skeleton: `to_arabic_skeleton` of each Latin token against the reference Arabic
  spelling, by character error rate after both sides lose their marks and take one
  form of alef, yeh and teh marbuta;
* reading: `ArbtokG2PPlugin.transcribe` of the Arabizi against the same call on the
  reference Arabic, by phoneme error rate. This needs no hand-written IPA: it asks
  whether the Arabizi reads as the Arabic it spells.
"""
import argparse
import csv
import json
import re
import unicodedata
import urllib.request
from collections import defaultdict
from pathlib import Path

from orthography2ipa import resolve

from arbtok.arabizi import to_arabic_skeleton
from arbtok.plugin import ArbtokG2PPlugin
from arbtok.translit import segment_ipa

GOLD = Path(__file__).resolve().parent.parent / "data" / "gold_arabizi"
_FOLD = str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا", "ى": "ي", "ة": "ه", "ـ": None})
_PUNCT = re.compile(r"[?!.,،؛؟]")


def fold(text: str) -> str:
    text = "".join(c for c in unicodedata.normalize("NFD", text) if not unicodedata.combining(c))
    return " ".join(_PUNCT.sub("", unicodedata.normalize("NFC", text)).translate(_FOLD).split())


def distance(a, b) -> int:
    row = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        prev, row[0] = row[0], i
        for j, y in enumerate(b, 1):
            prev, row[j] = row[j], min(row[j] + 1, row[j - 1] + 1, prev + (x != y))
    return row[-1]


def phones(ipa: str):
    return [p for word in ipa.replace("ˈ", "").replace("ˌ", "").split() for p in segment_ipa(word)]


LIMIT = 300
ATTESTED = {
    "doda": ("https://raw.githubusercontent.com/darija-open-dataset/dataset/"
             "feb88ff23153283c47d83dd677b432fe0cbac15a/sentences/sentences.csv"),
    "narabizi": ("https://raw.githubusercontent.com/SamiaTouileb/NArabizi/"
                 "1434f57bbaa718994f9080e4402f72d81a2962b2/data/Narabizi/pos/test_NArabizi.conllu"),
    "tarc": "https://raw.githubusercontent.com/eligugliotta/tarc/ee2b293c5af994ff8f03cedbf8d1868f3bcd9689/tarc.tsv",
}
_DIGIT = re.compile(r"[2-9]")
_CODA = re.compile(r"[\u0600-\u06FF]+")


def fetch(name: str, cache: Path) -> Path:
    path = cache / f"{name}{Path(ATTESTED[name]).suffix}"
    if not path.exists():
        cache.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(ATTESTED[name], path)
    return path


def doda(path):
    for r in csv.DictReader(path.open(encoding="utf-8")):
        if _DIGIT.search(r["darija"]) and r["darija_ar"].strip():
            yield "ar-MA", r["darija"], r["darija_ar"]


def narabizi(path):
    latin, arabic = [], []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines() + [""]:
        cols = line.split("\t")
        if len(cols) >= 10 and cols[0].isdigit() and "lang=ar_dz" in cols[-1]:
            latin.append(cols[1].strip())
            arabic.append(cols[3].strip())
        elif not line.strip() and latin:
            if _DIGIT.search(" ".join(latin)):
                yield "ar-DZ", " ".join(latin), " ".join(arabic)
            latin, arabic = [], []


def tarc(path):
    seen = set()
    for r in csv.DictReader(path.open(encoding="utf-8"), delimiter="\t"):
        word = (r["arabish"] or "").strip()
        if r["class"] == "arabizi" and _DIGIT.search(word) and _CODA.fullmatch(r["CODA"].strip()) and word not in seen:
            seen.add(word)
            yield "ar-TN", word, r["CODA"].strip()


def load(cache=None):
    for path in sorted(GOLD.glob("*.tsv")):
        yield from csv.DictReader(path.open(encoding="utf-8"), delimiter="\t")
    if cache is None:
        return
    for name, read in (("doda", doda), ("narabizi", narabizi), ("tarc", tarc)):
        for n, (lect, latin, arabic) in enumerate(read(fetch(name, cache))):
            if n == LIMIT:
                break
            yield {"tier": f"attested-{name}", "lect": lect, "arabizi": latin, "arabic": arabic}


def score(cache=None):
    sums = defaultdict(lambda: defaultdict(int))
    plugins = {}
    for row in load(cache):
        lect = resolve(row["lect"])
        plugin = plugins.setdefault(lect, ArbtokG2PPlugin(lang=lect))
        skeleton = fold(" ".join(to_arabic_skeleton(_PUNCT.sub("", t)) for t in row["arabizi"].split()))
        reference = fold(row["arabic"])
        heard, meant = phones(plugin.transcribe(row["arabizi"])), phones(plugin.transcribe(row["arabic"]))
        for key in (row["tier"], f"{row['tier']}/{row['lect']}"):
            s = sums[key]
            s["rows"] += 1
            s["char_edits"] += distance(skeleton, reference)
            s["chars"] += len(reference)
            s["skeleton_exact"] += skeleton == reference
            s["phone_edits"] += distance(heard, meant)
            s["phones"] += len(meant)
            s["reading_exact"] += heard == meant
    return {key: {"rows": s["rows"],
                  "skeleton_cer": round(s["char_edits"] / s["chars"], 4),
                  "skeleton_exact": s["skeleton_exact"],
                  "reading_per": round(s["phone_edits"] / s["phones"], 4),
                  "reading_exact": s["reading_exact"]}
            for key, s in sorted(sums.items())}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--attested", type=Path, metavar="CACHE_DIR")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    results = score(args.attested)
    for key, r in results.items():
        if "/" not in key:
            print(f"{key}: {r['rows']} rows, skeleton CER {r['skeleton_cer']}, exact {r['skeleton_exact']}; "
                  f"reading PER {r['reading_per']}, exact {r['reading_exact']}")
    if args.out:
        args.out.write_text(json.dumps(results, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
