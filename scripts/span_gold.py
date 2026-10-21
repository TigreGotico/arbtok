"""The span-level pronunciation gold: build it from its cited items, and score arbtok against it.

Each item is a sentence, one span in it, a category, a lect, and the readings a cited source
accepts for that span, in phones. A span passes when arbtok's phones for the sentence hold one of
the accepted readings. Nothing is judged by ear and no audio is used: every accepted reading is a
form a source prints, with the page it is printed on and the form as printed.

Comparison, fixed before any score was read:

- stress marks, syllable dots and spaces are removed;
- ASCII g is IPA ɡ, and خ is x whether a source writes it x or χ;
- the allophonic vowel qualities fold to the three-vowel system the sources write: ɑ→a, ɪ→i,
  ʊ→u, with their long forms; eː and oː stay;
- a span-final short vowel and a following n are ignored, because arbtok reads text in pause and
  a source may print the full form (masaːʔan) where the pausal one (masaːʔ) is equally right;
- when the span is the whole sentence the folded strings must be equal; otherwise the accepted
  reading must occur in the sentence's folded phones.

Items are split into a development part and a held-out part by a hash of their id, and the two
are reported apart: no rule may be tuned against the held-out part.

usage:
  span_gold.py build            write data/span_gold/<lect>.jsonl from ITEMS
  span_gold.py score [lect ...] score arbtok, per category and per part
"""
import hashlib
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

GOLD_DIR = Path(__file__).resolve().parents[1] / "data" / "span_gold"
HELD_OUT_SHARE = 3  # of 10

ALSHAMMARI = {"source": "Alshammari 2026, An Optimality-Theoretic Account of Velar Affrication in "
                        "Northern Najdi Arabic, Journal of Language Teaching and Research 17(4)"}
FREE_VARIATION = ("the two allophonic segments [k] and [ts] are assumed to be in free variation and "
                  "acceptable by NNA speakers. It is very uncommon to find words pronounced with an "
                  "affricate [ts] that alternates with [k].")
NEXT_TO_LONG_A = ("it is difficult to find words where /k/ is in free variation with the affricate [ts] "
                  "adjacent to /a:/")
K_CHOICE = ("The paper assumes free variation (p. 1335), finds it uncommon in the next sentence, "
            "finds it hard to attest next to /a:/ (p. 1336) and calls the forms complementary "
            "(p. 1337). Accepting the plain form beside the printed one is this gold's choice.")
FREE_VARIATION_G = ("affrication is generally an optional process due to the free variation of [dz] "
                    "with /g/. Hence, both pronunciations in the underlying and surface forms above "
                    "are acceptable by NNA speakers. [...] For instance, pronouncing the word "
                    "[θi.dzi:l] rather than [θi.gi:l] will be acceptable and understandable by NNA "
                    "speakers.")
INGHAM_1982 = {"source": "Ingham 1982, North East Arabian Dialects, Kegan Paul, text 6 (Shammar)",
               "page": "132 or 133 (unpaginated copy)",
               "example": "gīmat xamsat 'ašar lēlih aw sab'at 'ašar lēlih"}
FRAME = "the sentence is this gold's frame for the teen; the source prints the teen, not the sentence"
POINTING = "the phones are this gold's pointing of the printed expansion; the source gives no phones"
WIKTIONARY = {"source": "English Wiktionary"}


def _k(word, surface, underlying, page, example, gloss, long_a=False):
    """A /k/ word: the affricated form printed, and the plain form by this gold's choice."""
    plain = {**ALSHAMMARI, "page": page, "example": example, "printed": underlying,
             "quote_page": 1335, "quote": FREE_VARIATION, "choice": K_CHOICE}
    if long_a:
        plain["quote_long_a"] = {"page": 1336, "quote": NEXT_TO_LONG_A}
    return {"category": "dialect", "lect": "ar-SA-x-najd", "sentence": word, "span": word,
            "gloss": gloss, "accepted": [
                {**ALSHAMMARI, "page": page, "example": example, "printed": surface}, plain]}


def _g(word, surface, underlying, page, example, gloss):
    """A /g/ word: the affricated form printed, and the plain form under free variation."""
    return {"category": "dialect", "lect": "ar-SA-x-najd", "sentence": word, "span": word,
            "gloss": gloss, "accepted": [
                {**ALSHAMMARI, "page": page, "example": example, "printed": surface},
                {**ALSHAMMARI, "page": page, "example": example, "printed": underlying,
                 "quote_page": 1337, "quote": FREE_VARIATION_G}]}


def _one(word, printed, page, example, gloss):
    """A word whose one printed surface form is accepted: a loan, or a word that resists."""
    return {"category": "dialect", "lect": "ar-SA-x-najd", "sentence": word, "span": word,
            "gloss": gloss, "accepted": [
                {**ALSHAMMARI, "page": page, "example": example, "printed": printed}]}


ITEMS = [
    # /k/ -> [ts] word-initially, (1)
    _k("كبير", "tsi.bi:r", "ki.bi:r", 1335, "(1a)", "big"),
    _k("كبريت", "tsib.ri:t", "kib.ri:t", 1335, "(1b)", "matches"),
    _k("كيس", "tsi:s", "ki:s", 1335, "(1c)", "bag"),
    _k("كلب", "tsalb", "kalb", 1335, "(1d)", "dog"),
    _k("كبد", "tsabd", "kabd", 1335, "(1e)", "liver"),
    _k("كايد", "tsa:.jid", "ka:.jid", 1335, "(1f)", "hard", long_a=True),
    # word-medially, (2)
    _k("أكل", "ʔa.tsil", "ʔa.kil", 1336, "(2a)", "food"),
    _k("باكر", "ba:.tsir", "ba:.kir", 1336, "(2b)", "tomorrow", long_a=True),
    _k("مسيكين", "msi.tsi:n", "msi.ki:n", 1336, "(2c)", "poor, diminutive"),
    _k("دكاكين", "di.ka:.tsi:n", "di.ka:.ki:n", 1336, "(2d)", "shops", long_a=True),
    _k("مكان", "mi.tsa:n", "mi.ka:n", 1336, "(2f)", "place", long_a=True),
    # word-finally, (3)
    _k("سالك", "sa:.lits", "sa:.lik", 1336, "(3a)", "passable"),
    _k("علك", "ʕilits", "ʕilik", 1336, "(3b)", "gum"),
    _k("ديك", "di:ts", "di:k", 1336, "(3c)", "rooster"),
    _k("سليك", "sli:ts", "sli:k", 1336, "(3d)", "wire, diminutive"),
    _k("سمك", "si.mats", "si.mak", 1336, "(3e)", "fish"),
    _k("ورك", "warts", "wark", 1336, "(3g)", "hip"),
    # loans that do not affricate, (4)
    _one("كلتش", "ka.latʃ", 1336, "(4a)", "clutch"),
    _one("تذكرة", "tað.ki.rah", 1336, "(4b)", "ticket"),
    _one("مكينة", "mi.ki:.nah", 1336, "(4d)", "machine"),
    # /k/ that does not affricate, (5)
    _one("كوخ", "ku:χ", 1336, "(5a)", "cottage"),
    _one("كسوف", "ku.su:f", 1336, "(5c)", "eclipse"),
    _one("شوك", "ʃo:k", 1336, "(5e)", "thorns"),
    _one("متروك", "mat.ro:k", 1336, "(5f)", "antiquated"),
    # /g/ -> [dz], (6), (7), (8)
    _g("قليب", "dzi.li:b", "gi.li:b", 1337, "(6a)", "a water well"),
    _g("قربة", "dzir.bah", "gir.bah", 1337, "(6b)", "bottle of water"),
    _g("قيمة", "dzi:.mah", "gi:.mah", 1337, "(6d)", "price"),
    _g("قريب", "dzi.ri:b", "gi.ri:b", 1337, "(6e)", "close"),
    _g("مقبل", "midz.bil", "mig.bil", 1337, "(7b)", "coming over"),
    _g("ثقيل", "θi.dzi:l", "θi.gi:l", 1337, "(7c)", "heavy"),
    _g("رقيب", "ri.dzi:b", "ri.gi:b", 1337, "(7d)", "observer"),
    _g("ريق", "ri:dz", "ri:g", 1337, "(8a)", "saliva"),
    _g("حريق", "ħa.ri:dz", "ħa.ri:g", 1337, "(8b)", "fire"),
    _g("عرق", "ʕirdz", "ʕirg", 1337, "(8c)", "vein"),
    _g("طريق", "tˤi.ri:dz", "tˤi.ri:g", 1337, "(8d)", "road"),
    # /g/ that does not affricate, (9)
    _one("قمر", "gu.mar", 1337, "(9a)", "moon"),
    _one("سروق", "si.ru:g", 1337, "(9c)", "thief"),
    _one("بروق", "bru:g", 1337, "(9d)", "thunderbolts"),
    _one("مقبول", "mag.bul", 1337, "(9e)", "accepted"),
    _one("لقب", "la.gab", 1337, "(9f)", "nickname"),
    # numbers in a Najdi narrative: teens are two words with the construct -t
    {"category": "normalisation", "lect": "ar-SA-x-najd", "sentence": "مشوا 15 ليلة",
     "span": "15", "gloss": "fifteen nights", "frame": FRAME, "accepted": [
         {**INGHAM_1982, "printed": "xamsat 'ašar", "phones": "xamsatʕaʃar"}]},
    {"category": "normalisation", "lect": "ar-SA-x-najd", "sentence": "مشوا 17 ليلة",
     "span": "17", "gloss": "seventeen nights", "frame": FRAME, "accepted": [
         {**INGHAM_1982, "printed": "sab'at 'ašar", "phones": "sabʕatʕaʃar"}]},
    # abbreviations, written input: the expansion Wiktionary gives, pointed by this gold
    {"category": "abbreviation", "lect": "ar", "sentence": "الموعد الساعة 5 م",
     "span": "م", "gloss": "p.m.", "accepted": [
         {**WIKTIONARY, "page": "م, Arabic, Symbol, sense 2", "printed": "مَسَاءً",
          "phones": "masaːʔan", "pointing": POINTING}]},
    {"category": "abbreviation", "lect": "ar", "sentence": "الموعد الساعة 9 ص",
     "span": "ص", "gloss": "a.m.", "accepted": [
         {**WIKTIONARY, "page": "ص, Arabic, Letter, sense 3", "printed": "صباحًا", "phones": "sˤabaːħan",
          "pointing": POINTING}]},
    {"category": "abbreviation", "lect": "ar", "sentence": "ولد سنة 1990 م",
     "span": "م", "gloss": "AD", "accepted": [
         {**WIKTIONARY, "page": "م, Arabic, Symbol, sense 3", "printed": "مِيلَادِيّ",
          "phones": "miːlaːdijj", "pointing": POINTING},
         {**WIKTIONARY, "page": "م, Arabic, Symbol, sense 3", "printed": "مِيلَادِيّ",
          "phones": "miːlaːdij", "pointing": POINTING + "; the pausal form"}]},
    {"category": "abbreviation", "lect": "ar", "sentence": "في عام 1445 هـ",
     "span": "هـ", "gloss": "AH", "accepted": [
         {**WIKTIONARY, "page": "هـ, Arabic", "printed": "هِجْرِيّ", "phones": "hidʒrijj",
          "pointing": POINTING},
         {**WIKTIONARY, "page": "هـ, Arabic", "printed": "هِجْرِيّ", "phones": "hidʒrij",
          "pointing": POINTING + "; the pausal form"}]},
    {"category": "abbreviation", "lect": "ar", "sentence": "طول الغرفة 5 م",
     "span": "م", "gloss": "metre", "accepted": [
         {**WIKTIONARY, "page": "م, Arabic, Symbol, sense 4", "printed": "مِتْر",
          "phones": "mitr", "pointing": POINTING}]},
]

_FOLD = str.maketrans({"ɑ": "a", "ɪ": "i", "ʊ": "u", "g": "ɡ", "χ": "x"})
_DROP = re.compile(r"[ˈˌ.\s]")
_FINAL = re.compile(r"[aiu]n?$")


def fold(phones: str, final: bool = True) -> str:
    """The comparison form of a phone string (see the module docstring)."""
    s = _DROP.sub("", phones.replace(":", "ː")).translate(_FOLD)
    return _FINAL.sub("", s) if final else s


def item_id(item) -> str:
    key = json.dumps([item["lect"], item["category"], item["sentence"], item["span"]],
                     ensure_ascii=False)
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:12]


def held_out(iid: str) -> bool:
    return int(iid, 16) % 10 < HELD_OUT_SHARE


def build() -> None:
    GOLD_DIR.mkdir(parents=True, exist_ok=True)
    by_lect = defaultdict(list)
    for item in ITEMS:
        for acc in item["accepted"]:
            if "phones" not in acc:
                acc["phones"] = acc["printed"].replace(".", "")
        iid = item_id(item)
        by_lect[item["lect"]].append({"id": iid, "part": "held_out" if held_out(iid) else "dev",
                                      **item})
    for lect, rows in by_lect.items():
        path = GOLD_DIR / f"{lect}.jsonl"
        path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows),
                        encoding="utf-8")
        print(f"wrote {path.name}: {len(rows)} items")


def passes(item, phones: str) -> bool:
    got = fold(phones)
    whole = item["span"] == item["sentence"]
    for acc in item["accepted"]:
        want = fold(acc["phones"])
        if (got == want) if whole else (want in got):
            return True
    return False


def score(lects=None) -> dict:
    from arbtok.plugin import ArbtokG2PPlugin
    tally = defaultdict(lambda: [0, 0])
    for path in sorted(GOLD_DIR.glob("*.jsonl")):
        lect = path.stem
        if lects and lect not in lects:
            continue
        plugin = ArbtokG2PPlugin(lang=lect)
        for line in path.read_text(encoding="utf-8").splitlines():
            item = json.loads(line)
            ok = passes(item, plugin.transcribe(item["sentence"]))
            for key in ((lect, item["category"], item["part"]), (lect, "all", item["part"])):
                tally[key][0] += ok
                tally[key][1] += 1
    for (lect, cat, part), (ok, n) in sorted(tally.items()):
        print(f"{lect:<14} {cat:<14} {part:<9} {ok}/{n}")
    return {f"{k[0]}|{k[1]}|{k[2]}": v for k, v in tally.items()}


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "build":
        build()
    elif cmd == "score":
        score(sys.argv[2:] or None)
    else:
        sys.exit(__doc__)
