"""Per-lect closed-class lexicons: a hard prior for the words a dialect writes
in MSA orthography but does not pronounce in MSA.

The stem lexicon (:mod:`arbtok.lexicon`) answers *which vowels a written word
carries* from a Modern Standard Arabic corpus, and that is the right answer for
the shared vocabulary the dialects inherit unchanged. It is the wrong answer for
the **closed class** — the negators, demonstratives, relatives, interrogatives,
prepositions and the handful of very-high-frequency verbs and particles a
dialect spells in the inherited orthography but vocalizes its own way. The MSA
diacritizer, asked to point ⟨كي⟩ for a Maghrebi voice, restores the MSA reading
⟨كَي⟩ /kaj/; the dialect says ⟨كِي⟩ /kiː/. It is not guessing badly — it is
answering a different question, because the word it is pointing is not the word
that is spoken.

These words are few, frequent, and **written down** — every one is listed in the
reference grammar or dictionary of its dialect. So, exactly as the stem lexicon
does for MSA, arbtok looks them up rather than inferring them, and it looks them
up *first*: a closed-class dialect entry is a hard prior consulted ahead of the
stem lexicon and ahead of the model, because the model's answer here is not
merely uncertain, it is systematically for the wrong variety.

The shape mirrors the stem lexicon deliberately:

- The value is a **diacritized surface form**, not IPA. It is fed back through
  the variety's own lattice, so a looked-up ⟨كِي⟩ still gets the lect's
  allophony, stress and pausal treatment from the engine — the same entry reads
  correctly under every spec that shares the word. Freezing IPA into the data
  would bypass everything the engine knows and pin one leaf's pronunciation.
- The entry is held to **every guard a model proposal is**: it must spell the
  word it keys (marks added, letters untouched) and it must tokenize against the
  variety's grapheme table. The lexicon is data, and data can be wrong.

Unlike the stem lexicon, this data is **hand-authored from the dialect grammars**
(Harrell, Cowell, Erwin, Ingham, Badawi & Hinds, Holes, Heath, …) rather than
mined from a corpus, so it is small, Apache-2.0-clean, and **bundled** in the
wheel beside the code (``arbtok/data/lexicons/<lect>.tsv``) rather than fetched.
Each row carries its source in a third column, for a human auditing the data;
lookup does not read it.

A lect inherits its ancestors' entries: ``ar-MA`` sees the pan-Maghrebi function
words in ``ar-x-maghrebi.tsv`` *and* its own Moroccan-specific ones, with the
more specific file winning on a collision. That mirrors how a dialect's closed
class is mostly its group's, with a thin lect-specific layer on top.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

from arbtok.tokenizer import normalize_unicode

__all__ = ["DialectLexicon", "lexicon_dir", "lexicon_file", "available_lects"]


def lexicon_dir() -> Path:
    """The bundled directory of per-lect closed-class TSVs."""
    return Path(__file__).parent / "data" / "lexicons"


def lexicon_file(lect: str) -> Optional[Path]:
    """The TSV bundled for *lect*, or ``None`` when the lect carries none."""
    path = lexicon_dir() / f"{lect}.tsv"
    return path if path.exists() else None


def available_lects() -> List[str]:
    """Every lect code that ships a closed-class lexicon, sorted."""
    d = lexicon_dir()
    if not d.exists():
        return []
    return sorted(p.stem for p in d.glob("*.tsv"))


def parse(text: str) -> Dict[str, str]:
    """Read a ``key<TAB>vocalization[<TAB>source[<TAB>gloss]]`` TSV.

    First entry for a key wins, the header row and blank/``#`` lines are
    skipped, and the source and gloss columns are ignored by lookup — they are
    there for a human auditing the data.
    """
    entries: Dict[str, str] = {}
    for line in text.splitlines():
        line = line.rstrip("\n")
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) < 2 or parts[0] == "key":
            continue
        key, voc = normalize_unicode(parts[0]), normalize_unicode(parts[1])
        if key and voc:
            entries.setdefault(key, voc)
    return entries


def _parent_chain(lang: str) -> List[str]:
    """*lang* and its ``parent``-typed ancestors, most specific first.

    Only the genealogical parent edge is followed (not substrate/adstrate
    influences): a lect's closed class is its own layered over its group's, so
    ``ar-MA`` reads ``ar-MA`` then ``ar-x-maghrebi``. Resolution is best-effort;
    if orthography2ipa cannot be consulted the chain is just *lang* itself.
    """
    chain = [lang]
    try:
        from orthography2ipa import get
        seen = {lang}
        cur = lang
        while True:
            parent = getattr(get(cur), "parent", None)
            if not parent or parent in seen:
                break
            chain.append(parent)
            seen.add(parent)
            cur = parent
    except Exception:
        pass
    return chain


class DialectLexicon:
    """Undiacritized surface form → the lect's diacritized vocalization.

    Loading is lazy: constructing one reads nothing, so a caller who never
    diacritizes a lect that has a lexicon never pays for it, and a lect with no
    lexicon at all is a cost-free empty map.

    The lect's own file and its ancestors' files are merged with the more
    specific file winning, so ``DialectLexicon("ar-MA")`` answers with a
    Moroccan-specific entry where one exists and falls through to the
    pan-Maghrebi entry otherwise.
    """

    def __init__(self, lang: str, data_dir: Optional[Path] = None) -> None:
        self.lang = lang
        self._data_dir = data_dir
        self._entries: Optional[Dict[str, str]] = None

    @property
    def entries(self) -> Dict[str, str]:
        if self._entries is None:
            base = self._data_dir or lexicon_dir()
            merged: Dict[str, str] = {}
            # Least specific first, so the specific lect overwrites on collision.
            for lect in reversed(_parent_chain(self.lang)):
                path = base / f"{lect}.tsv"
                if path.exists():
                    merged.update(parse(path.read_text(encoding="utf-8")))
            self._entries = merged
        return self._entries

    def get(self, word: str) -> Optional[str]:
        """The lect's vocalization for *word*, or ``None`` if it lists none."""
        return self.entries.get(normalize_unicode(word))

    def __len__(self) -> int:
        return len(self.entries)

    def __contains__(self, word: str) -> bool:
        return self.get(word) is not None
