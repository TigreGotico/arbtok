#!/usr/bin/env python3
"""Rebuild the bundled English donor lexicon (arbtok/data/lexicons/en-GB.tsv).

    python scripts/build_donor_lexicon.py <gb_gold.json> arbtok/data/lexicons/en-GB.tsv

Output is a word<TAB>ipa TSV — UTF-8, NFC, sorted, first-entry-wins — the format
orthography2ipa's lexicon overlay reads. Re-running is deterministic.

Source: misaki (Apache-2.0) gb_gold.json — a British English gold lexicon, so
it speaks the RP convention the en-GB spec targets, unlike the CMUdict pilot
which is General American.

misaki writes a few phonemes as single-character shorthands. The map below is
applied SIMULTANEOUSLY (str.translate): applied in sequence, "I"->"aɪ" followed
by "a"->"æ" rewrites the a of the diphthong it just produced and turns every aɪ
into æɪ.
"""
import json, sys, unicodedata

MISAKI_TO_IPA = {"A": "eɪ", "I": "aɪ", "Q": "əʊ", "W": "aʊ", "Y": "ɔɪ",
                 "ʤ": "dʒ", "ʧ": "tʃ", "a": "æ", "ᵊ": "ə"}
TABLE = str.maketrans(MISAKI_TO_IPA)

def main(src, out):
    gold = json.load(open(src, encoding="utf-8"))
    rows = {}
    for word, val in gold.items():
        if isinstance(val, dict):
            # Part-of-speech variants (ˈrecord vs reˈcord). The overlay is a
            # word->ipa map with no POS channel, so only the unambiguous
            # DEFAULT is taken and a word without one is left to the rules
            # rather than guessed at.
            val = val.get("DEFAULT")
        if not isinstance(val, str) or not val:
            continue
        w = unicodedata.normalize("NFC", word)
        if not w.isalpha() or not w.islower():
            continue
        rows[w] = unicodedata.normalize("NFC", val.translate(TABLE))
    with open(out, "w", encoding="utf-8") as fh:
        for w in sorted(rows):
            fh.write(f"{w}\t{rows[w]}\n")
    print(f"{len(rows)} entries -> {out}")

main(sys.argv[1], sys.argv[2])
