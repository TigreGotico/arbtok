"""Write the orthography2ipa IR fragment that carries arbtok's loanword reading for one lect.

    python scripts/loom_fragment.py --lect arz-EG --out arz-EG.contact.json

The fragment has one `contact` part for Latin script: the established loans, the
bundled donor lexicon, the ŋ rewrite and the cited phone map of the lect's zone
(arbtok.translit). The orthography2ipa compiler adds the projection of every other
donor phoneme onto the lect inventory.
"""
import argparse
import json
from pathlib import Path

from orthography2ipa import resolve

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


def fragment(lect: str) -> dict:
    donor = resolve(translit.DONOR_BY_SCRIPT["Latin"])
    return {
        "ir_version": IR_VERSION,
        "langs": [lect],
        "contact": [{
            "script": "Latn",
            "donor": donor,
            "words": dict(sorted(translit.ESTABLISHED_LOANS.get(donor, {}).items())),
            "donor_words": dict(sorted(donor_words(donor).items())),
            "rewrite": [{"pattern": "ŋ(?=k)", "template": "n"}],
            "map": {**dict(sorted(translit.nativization_table(resolve(lect)).items())), "ŋ": "nɡ"},
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
