#!/usr/bin/env python3
"""Rebuild the bundled English donor lexicon (arbtok/data/lexicons/en-GB.tsv).

    python scripts/build_donor_lexicon.py <gb_gold.json> arbtok/data/lexicons/en-GB.tsv
    python scripts/build_donor_lexicon.py --rhoticise arbtok/data/lexicons/en-GB.tsv

The second form rewrites an existing lexicon in place and touches nothing but the
rhotics. It exists because the bundled lexicon does not reproduce from any misaki
release currently installable: 0.7.4's gb_gold is short 1,487 of its words, among
them alright, plow, pajamas, skeptic, fervor and the whole -ise family. Rebuilding
from source would fix the rhotics and silently drop those, so the rhotics are fixed
where the words already are, and the provenance is a separate question.

Output is a word<TAB>ipa TSV — UTF-8, NFC, sorted, first-entry-wins — the format
orthography2ipa's lexicon overlay reads. Re-running is deterministic.

Source: misaki (Apache-2.0) gb_gold.json — a British English gold lexicon, so
it speaks the RP convention the en-GB spec targets, unlike the CMUdict pilot
which is General American.

misaki writes a few phonemes as single-character shorthands. The map below is
applied SIMULTANEOUSLY (str.translate): applied in sequence, "I"->"aɪ" followed
by "a"->"æ" rewrites the a of the diphthong it just produced and turns every aɪ
into æɪ.

The readings are RHOTICISED on the way out. RP is non-rhotic and the gold speaks
RP, so it gives `car` as kˈɑː and `manager` as mˈænɪdʒə -- and this lexicon does
not exist to say how an English speaker says the word, it exists to feed loanword
adaptation into Arabic. Arabic has /r/ and its loans keep it: كارت, كارد, برنتر,
تشارجر and كونسرت all write the rāʾ. Left non-rhotic, the adapter faithfully
produced `kaː` for car and `manidʒa` for manager, and the hand-written notes in
the code-switched gold had said kaːrd, brintar and manadʒar all along.
"""
import json, re, sys, unicodedata

MISAKI_TO_IPA = {"A": "eɪ", "I": "aɪ", "Q": "əʊ", "W": "aʊ", "Y": "ɔɪ",
                 "ʤ": "dʒ", "ʧ": "tʃ", "a": "æ", "ᵊ": "ə"}
TABLE = str.maketrans(MISAKI_TO_IPA)

#: RP nuclei that can carry a lost /r/. NURSE, START/PALM, NORTH/THOUGHT, NEAR,
#: CURE, SQUARE and schwa -- some of which are r-coloured only sometimes, which is
#: why the spelling decides rather than the nucleus.
_NUCLEI = ("ɜː", "əː", "ɪə", "ʊə", "eə", "ɛː", "ɑː", "ɔː", "ə")
_NUCLEUS_RE = re.compile("|".join(_NUCLEI))
#: <rr> spells one /r/; <r> before a vowel survives in RP and is already in the IPA.
_SPELLED_R = re.compile(r"rr?")


def rhoticise(word, ipa):
    """Restore the /r/ that RP dropped, where the spelling says there is one.

    The count decides how many, and position decides which. A word's spelling gives
    the number of /r/ it has; whatever the reading is already short by was lost, and
    what was lost was lost at the end of a syllable -- so the deficit is filled from
    the RIGHTMOST eligible nuclei backwards. That is what separates `father`
    (fˈɑːðə -> fˈɑːðəɹ, the ɑː is PALM and not r-coloured) from `barber`
    (bˈɑːbə -> bˈɑːɹbəɹ, where both are), without either being listed anywhere.

    A nucleus already followed by ɹ is skipped, so `stirring` is left alone.
    """
    deficit = len(_SPELLED_R.findall(word)) - ipa.count("ɹ")
    if deficit <= 0:
        return ipa
    # The gold writes NURSE as both ɜː and əː, so a bare ə can match with the length
    # mark still to come; the /r/ goes after the whole nucleus, never inside it.
    ends = []
    for m in _NUCLEUS_RE.finditer(ipa):
        end = m.end() + 1 if ipa.startswith("ː", m.end()) else m.end()
        if not ipa.startswith("ɹ", end):
            ends.append(end)
    for end in reversed(ends[-deficit:] if deficit <= len(ends) else ends):
        ipa = ipa[:end] + "ɹ" + ipa[end:]
    return ipa


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
        rows[w] = rhoticise(w, unicodedata.normalize("NFC", val.translate(TABLE)))
    with open(out, "w", encoding="utf-8") as fh:
        for w in sorted(rows):
            fh.write(f"{w}\t{rows[w]}\n")
    print(f"{len(rows)} entries -> {out}")

def rhoticise_file(path):
    """Rewrite a built lexicon in place, changing nothing but the rhotics."""
    rows = []
    changed = 0
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            w, _, ipa = line.rstrip("\n").partition("\t")
            if not w or not ipa:
                continue
            out = rhoticise(w, ipa)
            changed += out != ipa
            rows.append((w, out))
    with open(path, "w", encoding="utf-8") as fh:
        for w, ipa in rows:
            fh.write(f"{w}\t{ipa}\n")
    print(f"{len(rows)} entries, {changed} rhoticised -> {path}")


if __name__ == "__main__":
    if sys.argv[1] == "--rhoticise":
        rhoticise_file(sys.argv[2])
    else:
        main(sys.argv[1], sys.argv[2])
