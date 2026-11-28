"""Write the orthography2ipa IR fragment that carries arbtok's loanword reading for one lect.

    python scripts/loom_fragment.py --lect arz-EG --out arz-EG.contact.json

The fragment has one `contact` part for Latin script: the established loans, the
bundled donor lexicon, the ŋ rewrite, and arbtok's own reading of every donor segment
(arbtok.translit): the cited map of the lect's zone, else arbtok's projection. The
segments are the donor phonemes and arbtok's ligatures, so a diphthong such as eɪ maps
as one unit, as `translit.segment_ipa` cuts it.
"""
import argparse
import json
from pathlib import Path

from orthography2ipa import phoneme_set, resolve

from arbtok import translit
from arbtok.donor_lexicon import bundled_path

IR_VERSION = 1


def donor_words(code: str) -> dict:
    path = bundled_path(code)
    if path is None:
        return {}
    rows = (line.rstrip("\n").split("\t") for line in path.read_text(encoding="utf-8").splitlines()
            if line and not line.startswith("#"))
    return {word: ipa for word, ipa, *_ in rows}


def phone_map(lect: str, donor: str, words: dict) -> dict:
    """arbtok's reading in *lect* of each segment of the donor phoneme set, of arbtok's
    ligatures and of the donor lexicon *words*. ŋ is left out: the rewrite and its own
    entry handle it."""
    segments = set(phoneme_set(donor)) | set(translit._LIGATURES)
    for ipa in words.values():
        segments.update(translit.segment_ipa(ipa.replace("ˈ", "").replace("ˌ", "")))
    segments -= {"ŋ", "ː"}
    return {seg: "".join(translit._map_segments([seg], lect)) for seg in sorted(segments)}


def fragment(lect: str) -> dict:
    donor = resolve(translit.DONOR_BY_SCRIPT["Latin"])
    lexicon = donor_words(donor)
    return {
        "ir_version": IR_VERSION,
        "langs": [lect],
        "contact": [{
            "script": "Latn",
            "donor": donor,
            "words": dict(sorted(translit.ESTABLISHED_LOANS.get(donor, {}).items())),
            "donor_words": dict(sorted(lexicon.items())),
            "rewrite": [{"pattern": "ŋ(?=k)", "template": "n"}],
            "map": {**phone_map(resolve(lect), donor, lexicon), "ŋ": "nɡ"},
        }],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--lect", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    doc = fragment(args.lect)
    part = doc["contact"][0]
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{args.lect}: {len(part['words'])} loans, {len(part['donor_words'])} donor words, "
          f"{len(part['map'])} map entries -> {args.out}")


if __name__ == "__main__":
    main()
