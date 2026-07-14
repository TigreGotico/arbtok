#!/usr/bin/env python3
"""Mine a diacritized-**stem** lexicon from a diacritized corpus.

Which short vowels a word carries is a *lexical fact* — كتاب is /kitaːb/ and not
/kataːb/ because that is the word, not because a rule says so. A statistical
diacritizer has to re-derive that fact every time it sees the word, and on
high-frequency vocabulary it gets it wrong. A lexicon does not have to derive it
at all: it looked the word up. espeak-ng's Arabic beats a neural diacritizer on
common words for exactly this reason, and this is how we take that back.

The stem
--------
A classical corpus writes the full iʿrāb, so one word appears as كِتَابٌ / كِتَابَ
/ كِتَابِ depending on where it stood in the sentence. The case ending is *syntax*,
not lexicon, and arbtok's waqf step drops it anyway — so every token is reduced to
its **stem** before it is counted: the word-final short vowel, tanwīn, sukūn, and
the mute alif that tanwīn-fatḥ drags along are stripped. What survives is the part
the model keeps getting wrong — the internal vowels — and the three case forms
collapse into one entry that is three times better attested.

Shadda is **kept**: gemination is lexical (عَرَبِيّ, رَدّ), not inflectional.

The gate
--------
Only tokens the corpus has diacritized *completely* are counted, which
orthography2ipa can answer for us: :func:`~orthography2ipa.mark_density` is
``1.0`` exactly when the writing leaves no letter's reading to a guess. Partially
marked text — a book that marks only the words it thinks are ambiguous — would
otherwise contribute half-vowelled stems that are worse than the model's guess.

The output
----------
A TSV of ``key<TAB>stem<TAB>count<TAB>runner_up_count``: the undiacritized surface
form, its most frequent stem diacritization, how often that stem was seen, and how
often the *second* most frequent one was. The runner-up is not used at lookup — the
most frequent stem wins, full stop — but it is what makes an entry's ambiguity
visible to anyone reading the file.

Usage
-----
    python scripts/build_stem_lexicon.py --out ar-stems.tsv
    python scripts/build_stem_lexicon.py --dataset arbml/tashkeela --min-count 5
"""
from __future__ import annotations

import argparse
import sys
from collections import Counter, defaultdict
from typing import Dict, Iterable, Tuple

from arbtok.tokenizer import normalize_unicode

#: Marks that only ever spell the iʿrāb when they sit at the end of a word: the
#: three short vowels, the three tanwīn, and the sukūn of the pausal form itself.
#: Shadda is absent on purpose — it is part of the word.
_FINAL_MARKS = "ًٌٍَُِْ"

#: Every Arabic combining mark, iʿrāb or not.
_MARKS = set("ًٌٍَُِّْٰٓ")

_TANWEEN_FATH = "ً"
_ALIF = "ا"

#: The letters a lexicon key may be made of. Anything else in a token — a Latin
#: letter, a digit, a punctuation mark, a Qurʾānic annotation sign — means the
#: token is not a word of Arabic and is not counted.
_LETTERS = set("ابتثجحخدذرزسشصضطظعغفقكلمنهويءأإآئؤةىٱ")


def stem(word: str) -> str:
    """*word* with its case/mood ending removed — the form that is spoken.

    The mute alif of tanwīn-fatḥ (كِتَابًا) goes with the tanwīn that wrote it, so
    the accusative token contributes its count to the same key as the nominative
    rather than to a spelling that only exists because of the ending.

    The whole run of final marks is taken apart rather than peeled off in order,
    because a corpus is free to write the ending's vowel *before* the shadda
    (عَرَبِيٌّ) — and what the word keeps is decided by which mark it is, not by
    where in the run it was written. Shadda and the dagger-alef stay; they are the
    word. The vowels and tanwīn go; they are the sentence.
    """
    word = normalize_unicode(word)
    if word.endswith(_ALIF) and len(word) > 1 and word[-2] == _TANWEEN_FATH:
        word = word[:-2]
    tail = ""
    while word and word[-1] in _MARKS:
        tail = word[-1] + tail
        word = word[:-1]
    return word + "".join(ch for ch in tail if ch not in _FINAL_MARKS)


def undiacritize(word: str) -> str:
    """The consonantal skeleton — the form the lexicon is keyed on."""
    return "".join(ch for ch in word if ch not in _MARKS)


def is_arabic_word(token: str) -> bool:
    return bool(token) and all(ch in _LETTERS or ch in _MARKS for ch in token)


def trim(token: str) -> str:
    """*token* without the punctuation the running text hung off it."""
    while token and token[0] not in _LETTERS:
        token = token[1:]
    while token and token[-1] not in _LETTERS and token[-1] not in _MARKS:
        token = token[:-1]
    return token


def count_tokens(rows: Iterable[str]) -> Counter:
    """Count every fully-formed Arabic token in *rows*, as written."""
    counts: Counter = Counter()
    for text in rows:
        for token in text.split():
            token = trim(normalize_unicode(token))
            if not is_arabic_word(token):
                continue
            if not any(ch in _MARKS for ch in token):
                continue
            counts[token] += 1
    return counts


def stems_by_key(tokens: Counter, spec) -> Dict[str, Counter]:
    """Group the corpus's fully-marked tokens into ``key → Counter[stem]``."""
    from orthography2ipa import mark_density

    grouped: Dict[str, Counter] = defaultdict(Counter)
    for token, n in tokens.items():
        if mark_density(token, spec) < 1.0:
            continue
        s = stem(token)
        key = undiacritize(s)
        if len(key) < 2 or not s:
            continue
        grouped[key][s] += n
    return grouped


def select(grouped: Dict[str, Counter],
           min_count: int) -> Iterable[Tuple[str, str, int, int]]:
    """The most frequent stem per key, with the runner-up's count beside it."""
    for key, stems in sorted(grouped.items()):
        ranked = stems.most_common(2)
        best, n = ranked[0]
        if n < min_count:
            continue
        runner_up = ranked[1][1] if len(ranked) > 1 else 0
        yield key, best, n, runner_up


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--dataset", default="arbml/tashkeela")
    ap.add_argument("--split", default="train")
    ap.add_argument("--column", default="diacratized")
    ap.add_argument("--lang", default="ar")
    ap.add_argument("--min-count", type=int, default=3,
                    help="how often a stem must be attested to be believed. A "
                         "single sighting is as likely to be a typo in a scanned "
                         "book as it is to be a word.")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    from datasets import load_dataset
    from orthography2ipa import get

    print(f"loading {args.dataset}:{args.split} …", file=sys.stderr)
    data = load_dataset(args.dataset, split=args.split)

    tokens = count_tokens(data[args.column])
    print(f"{sum(tokens.values()):,} tokens, {len(tokens):,} distinct",
          file=sys.stderr)

    grouped = stems_by_key(tokens, get(args.lang))
    print(f"{len(grouped):,} keys before the frequency floor", file=sys.stderr)

    written = ambiguous = 0
    with open(args.out, "w", encoding="utf-8") as fh:
        fh.write("key\tstem\tcount\trunner_up\n")
        for key, best, n, runner_up in select(grouped, args.min_count):
            fh.write(f"{key}\t{best}\t{n}\t{runner_up}\n")
            written += 1
            ambiguous += runner_up > 0
    print(f"wrote {written:,} entries to {args.out} "
          f"({ambiguous:,} with a competing stem)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
