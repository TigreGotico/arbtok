#!/usr/bin/env python3
"""Code-switched Arabic gold set — build and validation tooling.

The set lives in ``data/gold_code_switched/<lect>.tsv`` (one file per lect,
20 rows) and pins arbtok's *loanword-nativisation* pipeline: a Latin-script
word embedded in dialectal Arabic is read as a loan and mapped into the matrix
lect's phonology out of that lect's own cited table (:mod:`arbtok.translit`) —
Najdi = Alhoody (2019), Egyptian = Hafez (1996) + Watson (2002), Levantine =
Al-Saidat (2011) + Cowell (1964), default = Watson (2002) + Holes (2004).

The ``ipa`` column is **pipeline output**, never hand-written: ``build`` regenerates
it and ``validate`` re-runs the pipeline and asserts equality, so the file is a
regression gate mirroring orthography2ipa's ``scripts/arabic_tts_gold.py``.

Subcommands
-----------
build [lect ...]
    (Re)generate the TSVs from the frame set below: fill the per-zone dialectal
    particles, run ``ArbtokG2PPlugin(lang, diacritize=True, nativize=True,
    pausal=True).transcribe`` for the ``ipa`` column, and derive ``cs_words`` and
    ``notes`` (which nativisation reflex each embedded word takes, with the
    refusals marked) from the pipeline itself.

validate [lect ...]
    CI gate: schema, 20-row minimum, ``raw == sentence`` stripped of ḥarakāt,
    ``ipa == transcribe(sentence)`` (regression), no Latin leakage in ``ipa`` for
    the nativised rows, and ``cs_words`` all present in the sentence.

Schema (TSV, tab-separated, UTF-8, header row)
----------------------------------------------
id, sentence (vocalised Arabic + inline Latin), raw (ḥarakāt-stripped),
ipa (pipeline output), gloss_en, cs_words (semicolon Latin list), notes
"""
import argparse
import csv
import re
import sys
import unicodedata
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

GOLD_DIR = REPO_ROOT / "data" / "gold_code_switched"
FIELDS = ["id", "sentence", "raw", "ipa", "gloss_en", "cs_words", "notes"]
MIN_ROWS = 20
HARAKAT = "ًٌٍَُِّْٰ"
_LATIN = re.compile(r"[A-Za-z]")
PUNCT_STRIP = ".,;:!?()[]\"'،؛؟"

# Every ar* spec arbtok resolves is covered EXCEPT ar-Latn-buckwalter: that code
# is a Latin romanisation of Arabic, so a mixed Arabic/Latin sentence has no
# stable Arabic run for the pipeline to phonemise — the whole line would look
# Latin. It is a machine-readable regression anchor, not a spoken lect, and is
# deliberately excluded from the code-switching set.
SKIP = {"ar-Latn-buckwalter"}

# Which dialectal-particle set each lect frames its Arabic in. The English words
# and their nativised reflexes (the point of this set) are identical across
# lects; only the surrounding function words change, per the lect's grammar.
ZONES = {
    "eg":   ["ar-EG"],
    "lev":  ["ar-SY", "ar-LB", "ar-JO", "ar-PS", "ar-x-levantine"],
    "gulf": ["ar-KW", "ar-AE", "ar-BH", "ar-QA", "ar-OM", "ar-x-gulf",
             "ar-SA-x-najd", "ar-SA-x-hejaz", "ar-SA-x-qassim",
             "ar-SA-x-rijal-alma", "ar-SA-x-sharqiyya", "ar-YE",
             "ar-x-peninsular"],
    "iraq": ["ar-IQ", "ar-IQ-x-qeltu", "ar-x-mashriqi"],
    "magh": ["ar-MA", "ar-TN", "ar-DZ", "ar-LY", "ar-MR", "ar-x-maghrebi"],
    "sd":   ["ar-SD", "ar-TD", "ar-NG"],
    "msa":  ["ar", "arb"],
}
_LECT_ZONE = {code: z for z, codes in ZONES.items() for code in codes}

# Vocalised dialectal fillers. Colloquial, literature-attested function words;
# the set is editor-authored (see docs/gold-code-switched.md) — pipeline-verified,
# not native-validated.
PARTICLES = {
    "NEG":  {"eg": "مِش", "lev": "مِش", "gulf": "مُو", "iraq": "مُو",
             "magh": "ماشِي", "sd": "مَا", "msa": "مِش"},
    "WANT": {"eg": "عَايِز", "lev": "بِدِّي", "gulf": "أَبِي", "iraq": "أَرِيد",
             "magh": "بْغِيت", "sd": "دَايِر", "msa": "أُرِيد"},
    "THIS": {"eg": "دَه", "lev": "هَادَا", "gulf": "هَذَا", "iraq": "هَذَا",
             "magh": "هَادْ", "sd": "دَا", "msa": "هَذَا"},
    "NOW":  {"eg": "دِلْوَقْتِي", "lev": "هَلَّق", "gulf": "الْحِين", "iraq": "هَسَّه",
             "magh": "دَابَا", "sd": "هَسَّع", "msa": "الْآن"},
    "GOOD": {"eg": "كْوَيِّس", "lev": "مْنِيح", "gulf": "زَيْن", "iraq": "زَيْن",
             "magh": "مْزْيَان", "sd": "كْوَيِّس", "msa": "جَيِّد"},
}


def _fill(template: str, zone: str) -> str:
    for key, table in PARTICLES.items():
        template = template.replace("{" + key + "}", table[zone])
    return re.sub(r"\s+", " ", template).strip()


# domain, template (vocalised Arabic + inline Latin), gloss, english words
FRAMES = [
    ("tech", "{WANT} أَبْعَت email لِلْمُدِير {NOW}",
     "I want to send an email to the manager now", ["email"]),
    ("tech", "عِنْدِي laptop جَدِيد بَسّ wifi بَطِيء",
     "I have a new laptop but the wifi is slow", ["laptop", "wifi"]),
    ("tech", "لَازِم نَعْمَل update لِلْبَرْنَامِج {NOW}",
     "we have to do an update for the program now", ["update"]),
    ("tech", "نَزَّلْت file بَسّ download بَطِيء",
     "I downloaded a file but the download is slow", ["file", "download"]),
    ("tech", "نَسِيت password تَاع email",
     "I forgot the password of the email", ["password", "email"]),
    ("tech", "ابْعَتْلِي link عَلَى message",
     "send me the link on a message", ["link", "message"]),
    ("tech", "عِنْدِي meeting مُهِمّ مَعَ manager",
     "I have an important meeting with a manager", ["meeting", "manager"]),
    ("tech", "شُفْت video عَلَى online",
     "I saw a video online", ["video", "online"]),
    ("commerce", "فِي offer {GOOD} وْ discount كْبِير",
     "there is a good offer and a big discount", ["offer", "discount"]),
    ("commerce", "delivery يُوصَل بُكْرَة وْ الدَّفْع cash",
     "delivery arrives tomorrow and payment is cash", ["delivery", "cash"]),
    ("commerce", "{WANT} أَشْتَرِي online بَسّ مَا لَقِيت offer",
     "I want to buy online but I did not find an offer", ["online", "offer"]),
    ("commerce", "service {NEG} {GOOD} وْ delivery مِتْأَخِّر",
     "the service is not good and the delivery is late", ["service", "delivery"]),
    ("commerce", "دَفَعْت cash مُو بِكَرْت",
     "I paid cash not by card", ["cash"]),
    ("automotive", "وَدِّيت car عَلَى service {NOW}",
     "I took the car to service now", ["car", "service"]),
    ("automotive", "{THIS} model جَدِيد وْ automatic",
     "this model is new and automatic", ["model", "automatic"]),
    ("automotive", "{NEG} عَارِف بَسّ أَنَا think {THIS} model غَالِي",
     "I don't know but I think this model is expensive", ["think", "model"]),
    ("daily", "نَشُوفَك فِي weekend إِنْ شَاءَ الله",
     "we see you on the weekend, God willing", ["weekend"]),
    ("daily", "sorry تَأَخَّرْت عَلَى meeting",
     "sorry, I was late for the meeting", ["sorry", "meeting"]),
    ("daily", "ok {GOOD} نِتْكَلَّم {NOW}",
     "ok fine, we'll talk now", ["ok"]),
    ("daily", "شُفْت manager فِي garage",
     "did you see the manager in the garage", ["manager", "garage"]),
]


def strip_tashkeel(text: str) -> str:
    return "".join(c for c in text if c not in HARAKAT)


# ── nativisation-note derivation (pipeline-derived, honest about refusals) ──

_TABLE_CITE = {
    "ar-SA-x-najd": "Najdi (Alhoody 2019)",
    "ar-EG": "Egyptian (Hafez 1996; Watson 2002)",
    "ar-x-levantine": "Levantine (Al-Saidat 2011; Cowell 1964)",
    "ar": "default pan-Arabic (Watson 2002; Holes 2004)",
}


def _table_citation(lect: str) -> str:
    from arbtok.translit import nativization_table, _TABLES
    table = nativization_table(lect)
    for code, tbl in _TABLES.items():
        if tbl is table:
            return _TABLE_CITE[code]
    return _TABLE_CITE["ar"]


def _refusal_reason(word: str, lect: str) -> str:
    """Why a word is refused: the adapted segment(s) the lect does not declare."""
    from arbtok.translit import nativize, DONOR_LANG
    from orthography2ipa import G2P
    from orthography2ipa.inventory import phoneme_inventory, tokenize as ipa_tok
    try:
        donor_ipa = G2P(DONOR_LANG).transcribe_word(word)
        adapted = nativize(donor_ipa, lect)
        spec = G2P(lect).spec
        declared = phoneme_inventory(spec)
        outside = [t for t in ipa_tok(adapted, spec) if t not in declared]
    except Exception:
        outside = []
    if outside:
        return "needs [" + " ".join(sorted(set(outside))) + "] (not in inventory)"
    return "no donor reading"


def _notes(sentence: str, lect: str, cs_words) -> str:
    from arbtok.translit import transliterate
    parts = []
    for w in cs_words:
        r = transliterate(w, lect)
        if r:
            parts.append(f"{w}→{r}")
        else:
            parts.append(f"{w} REFUSED—{_refusal_reason(w, lect)}, dropped")
    return "; ".join(parts) + f". table: {_table_citation(lect)}"


def _roster():
    import arbtok
    return [l.code for l in arbtok.supported_lects() if l.code not in SKIP]


def _build_rows(lect):
    from arbtok.plugin import ArbtokG2PPlugin
    zone = _LECT_ZONE.get(lect, "msa")
    plugin = ArbtokG2PPlugin(lang=lect, diacritize=True, nativize=True, pausal=True)
    rows = []
    for i, (domain, template, gloss, en) in enumerate(FRAMES, 1):
        sentence = _fill(template, zone)
        raw = strip_tashkeel(sentence)
        ipa = plugin.transcribe(sentence)
        cs = [t.strip(PUNCT_STRIP) for t in sentence.split() if _LATIN.search(t)]
        cs_words = ";".join(cs)
        notes = f"[{domain}] " + _notes(sentence, lect, cs)
        rows.append({
            "id": f"{lect}-cs-{i:03d}", "sentence": sentence, "raw": raw,
            "ipa": ipa, "gloss_en": gloss, "cs_words": cs_words, "notes": notes,
        })
    return rows


def cmd_build(args):
    GOLD_DIR.mkdir(parents=True, exist_ok=True)
    lects = args.lects or _roster()
    for lect in lects:
        rows = _build_rows(lect)
        with open(GOLD_DIR / f"{lect}.tsv", "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=FIELDS, delimiter="\t")
            w.writeheader()
            w.writerows(rows)
        print(f"wrote {lect}: {len(rows)} rows")
    return 0


def _leakage_failures(rid, row, lect):
    """The honest no-Latin-leakage gate.

    A literal ``[a-zA-Z]`` ban on the ipa is unsatisfiable: Arabic IPA is
    ASCII-heavy (``b d f k l m n r s t w z h j a i u e o`` …). Leakage is a *guest
    word surviving untranscribed*, which with ``nativize=True`` cannot happen by
    construction (``transliterate`` returns a nativised IPA string or ``None`` —
    never the source token). This proves it row-by-row: every embedded Latin word
    is either present as its nativised reflex or absent (refused → dropped), never
    verbatim; and no uppercase Latin (a brand-name leak signal) survives.
    """
    from arbtok.translit import transliterate
    out = []
    if re.search(r"[A-Z]", row["ipa"]):
        out.append(f"{rid}: uppercase Latin in ipa: {row['ipa']!r}")
    tokens = row["ipa"].split()
    for w in [t for t in row["cs_words"].split(";") if t]:
        if w not in row["sentence"]:
            out.append(f"{rid}: cs_word {w!r} not in sentence")
        nat = transliterate(w, lect)
        if nat is None:
            # refused → dropped: the raw token must not appear as an ipa token
            if w in tokens:
                out.append(f"{rid}: refused word {w!r} leaked into ipa")
        elif nat not in row["ipa"]:
            out.append(f"{rid}: nativised {w!r}→{nat!r} not spliced into ipa")
    return out


def _load(lect):
    p = GOLD_DIR / f"{lect}.tsv"
    if not p.is_file():
        return None
    with open(p, encoding="utf-8") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def cmd_validate(args):
    from arbtok.plugin import ArbtokG2PPlugin
    lects = args.lects or _roster()
    failures = []
    total = 0
    for lect in lects:
        rows = _load(lect)
        if rows is None:
            failures.append(f"{lect}: missing gold file")
            continue
        if len(rows) < MIN_ROWS:
            failures.append(f"{lect}: only {len(rows)} rows (< {MIN_ROWS})")
        plugin = ArbtokG2PPlugin(lang=lect, diacritize=True, nativize=True, pausal=True)
        seen = set()
        for r in rows:
            total += 1
            rid = r.get("id", "?")
            if set(FIELDS) - set(r):
                failures.append(f"{rid}: bad columns {list(r)}")
                continue
            if not all(r[f] for f in ("id", "sentence", "raw", "ipa", "gloss_en", "cs_words")):
                failures.append(f"{rid}: empty required field")
            if r["sentence"] in seen:
                failures.append(f"{rid}: duplicate sentence within {lect}")
            seen.add(r["sentence"])
            if strip_tashkeel(r["sentence"]) != unicodedata.normalize("NFC", r["raw"]):
                failures.append(f"{rid}: raw != sentence stripped of ḥarakāt")
            got = plugin.transcribe(r["sentence"])
            if got != r["ipa"]:
                failures.append(f"{rid}: ipa regression\n    stored: {r['ipa']}\n    got:    {got}")
            failures += _leakage_failures(rid, r, lect)
    print(f"validated {total} rows across {len(lects)} lects")
    if failures:
        print(f"\n{len(failures)} FAILURE(S):")
        for f in failures:
            print("  -", f)
        return 1
    print("all green")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("build"); p.add_argument("lects", nargs="*"); p.set_defaults(fn=cmd_build)
    p = sub.add_parser("validate"); p.add_argument("lects", nargs="*"); p.set_defaults(fn=cmd_validate)
    args = ap.parse_args()
    sys.exit(args.fn(args) or 0)


if __name__ == "__main__":
    main()
