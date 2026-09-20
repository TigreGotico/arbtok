"""How a lect says its cardinals.

The number parser speaks Standard Arabic, in the nominative or the oblique case. No
lect says ``مئة وخمسة عشر`` for 115: Najd says it one way, Cairo another, Casablanca a
third. A table here gives, for one lect, the word it uses for a value, and
:func:`arbtok.textnorm.normalize_for_tts` lays those words over the cardinal the
parser composed. The parser still does the composing, so a table names the words that
differ and nothing else: the units, the teens, the tens, the hundreds, a thousand and
two thousand.

A table is ``data/number_forms/<code>.tsv`` with the columns ``value``, ``form`` and
``source``, one row per value, ``#`` for a comment. ``code`` is an orthography2ipa
spec code or a plain language-region tag. Every row says where its form comes from;
a row without a source is refused when the table is read.
"""
from __future__ import annotations

import functools
import hashlib
from pathlib import Path
from typing import Dict, List, Tuple

_DIR = Path(__file__).parent / "data" / "number_forms"


def _candidates(lang: str) -> List[str]:
    """The table names to try for ``lang``, the most specific first: the tag as given,
    the spec it resolves to, then that spec's parents — Kuwaiti reads the Gulf table
    because its spec declares ``ar-x-gulf`` as its parent. Bare ``ar`` is never tried:
    with no lect named, the cardinal stays the parser's, and a lect whose group has no
    table has none."""
    from arbtok.dialects import spec_for_lang
    names = [lang, spec_for_lang(lang)]
    seen_specs = set()
    while True:
        from orthography2ipa import get
        parent = getattr(get(names[-1]), "parent", None)
        if not parent or parent in seen_specs:
            break
        seen_specs.add(parent)
        names.append(parent)
    ordered, seen = [], set()
    for name in names:
        if name and "-" in name and name.lower() not in seen:
            seen.add(name.lower())
            ordered.append(name)
    return ordered


@functools.lru_cache(maxsize=None)
def _read(path: Path) -> Tuple[Tuple[int, str], ...]:
    rows: Dict[int, str] = {}
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip() or line.startswith("#"):
            continue
        fields = line.split("\t")
        if len(fields) != 3 or not all(field.strip() for field in fields):
            raise ValueError(f"{path.name}:{number}: a row is value, form and source, all three filled")
        value = int(fields[0])
        if value in rows:
            raise ValueError(f"{path.name}:{number}: {value} has a form already")
        rows[value] = fields[1].strip()
    return tuple(sorted(rows.items()))


def bundled_lects() -> List[str]:
    """The codes a number table ships for."""
    return sorted(path.stem for path in _DIR.glob("*.tsv"))


def number_forms(lang: str) -> Dict[int, str]:
    """The words ``lang`` uses for the values its table names, or ``{}`` when no table
    ships for it or for anything it falls back to.

    >>> number_forms("ar")
    {}
    """
    tables = {path.stem.lower(): path for path in _DIR.glob("*.tsv")}
    for name in _candidates(lang):
        if name.lower() in tables:
            return dict(_read(tables[name.lower()]))
    return {}


def tables_digest() -> str:
    """Names the shipped tables by content, for a record of what a text was read under."""
    digest = hashlib.sha256()
    for path in sorted(_DIR.glob("*.tsv")):
        digest.update(path.name.encode() + b"\0" + path.read_bytes() + b"\0")
    return digest.hexdigest()[:12]
