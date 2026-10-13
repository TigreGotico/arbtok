"""The words we already know how to vowel.

A diacritizer is a model of Arabic morphology, and on rare words that is the only
thing there is. On *common* words it is the wrong tool: which vowels كتاب carries
is not a thing to be inferred, it is a thing to be looked up. The model infers it
anyway, and on the highest-frequency vocabulary — precisely the words a TTS voice
says most often — it gets it wrong (كِتَاب read as كَتَاب, مَدْرَسَة as مُدْرَسَة).
espeak-ng, which has no model at all, gets those right, because it has a lexicon.

So we have one too. It maps an undiacritized surface form to the most frequent
**diacritized stem** for it in a large diacritized corpus. Two things about that
shape are load-bearing:

- It is a **diacritization** lexicon, not a pronunciation lexicon. The stem is fed
  back into arbtok's own engine, so a looked-up word still gets emphasis spread,
  gemination, stress and pausal treatment from the phonology — and still comes out
  as Najdi under a Najdi spec and MSA under an MSA one, from the *same* entry. A
  surface→IPA lexicon would freeze one variety's pronunciation into the data and
  bypass everything the engine knows.
- It is a **stem**, not a word form. The corpus is classical and writes the full
  iʿrāb, so the case ending is stripped before counting (see
  ``scripts/build_stem_lexicon.py``). What is stored is the part the model gets
  wrong; what is dropped is the part waqf would drop anyway.

Nothing is bundled. The data is mined from a GPL-2.0 corpus and arbtok is
Apache-2.0, so the lexicon lives beside the wheel rather than inside it — a
Hugging Face dataset, fetched on first use exactly as the diacritizer's own model
weights are, and cached. A caller may point at any other source, or at none::

    from arbtok.diacritize import LatticeDiacritizer

    LatticeDiacritizer()                          # the default lexicon
    LatticeDiacritizer(lexicon="/data/mine.tsv")  # a local file, or a URL, or hf://
    LatticeDiacritizer(lexicon=None)              # the model, unassisted
"""
from __future__ import annotations

import os
import urllib.request
from pathlib import Path
from typing import Dict, Optional

from arbtok.tokenizer import normalize_unicode

__all__ = ["StemLexicon", "DEFAULT_LEXICON", "AMBIGUOUS_SHARE", "MIN_CONTEXT_WORDS",
           "LexiconUnavailable", "resolve_source"]


class LexiconUnavailable(RuntimeError):
    """A lexicon was asked for and could not be read."""

#: The lexicon arbtok reaches for when the caller names none.
DEFAULT_LEXICON = "hf://TigreGotico/arabic-stem-lexicon/ar-stems.tsv"

CACHE_DIR = Path(
    os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")
) / "arbtok" / "lexicons"


def resolve_source(source: str) -> Path:
    """Turn a path, a URL, or an ``hf://repo/file`` id into a local file."""
    if source.startswith("hf://"):
        org, name, *path = source[len("hf://"):].split("/")
        from huggingface_hub import hf_hub_download
        return Path(hf_hub_download(f"{org}/{name}", "/".join(path),
                                    repo_type="dataset"))
    if source.startswith(("http://", "https://")):
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        target = CACHE_DIR / source.rsplit("/", 1)[-1]
        if not target.exists():
            urllib.request.urlretrieve(source, target)
        return target
    return Path(source).expanduser()


#: A spelling is ambiguous when its runner-up reading holds at least this share of
#: the two readings' attestations. For such a spelling the lexicon steps aside and
#: the diacritizer reads the word in its sentence. Measured on 395,617 ambiguous
#: words of held-out diacritised text, the lexicon's top reading is right on 62.8%
#: of words whose runner-up holds 25 to 40% and on 81.1% at 10 to 25%, where the
#: model reading the sentence is right on 83.6% and 90.8%; below 10% the two are
#: within half a point.
AMBIGUOUS_SHARE = 0.10

#: The shortest sentence in which an ambiguous spelling is left to the model. On
#: held-out sentences of three to seven words the model reading the sentence is
#: right more often than the lexicon in every length measured (+4.0 points on
#: every ambiguous word at three words, +15.2 on the words this rule hands over);
#: below three words it was not measured, and a word read alone has no sentence to
#: read, so there the lexicon answers as before.
MIN_CONTEXT_WORDS = 3


def parse(text: str) -> Dict[str, str]:
    """Read a ``key<TAB>stem[<TAB>count<TAB>runner_up]`` TSV. First entry wins.

    The counts are the file's own evidence: how often the stem was attested, and
    how often its closest competitor was. :func:`parse_shares` reads them.
    """
    entries: Dict[str, str] = {}
    for line in text.splitlines():
        parts = line.rstrip("\n").split("\t")
        if len(parts) < 2 or parts[0] == "key":
            continue
        key, stem = normalize_unicode(parts[0]), normalize_unicode(parts[1])
        if key and stem:
            entries.setdefault(key, stem)
    return entries


def parse_shares(text: str) -> Dict[str, float]:
    """The runner-up share of each entry that carries its counts: runner_up over
    count plus runner_up. An entry without counts has no share and is never
    treated as ambiguous."""
    shares: Dict[str, float] = {}
    for line in text.splitlines():
        parts = line.rstrip("\n").split("\t")
        if len(parts) < 4 or parts[0] == "key":
            continue
        key = normalize_unicode(parts[0])
        try:
            top, runner_up = int(parts[2]), int(parts[3])
        except ValueError:
            continue
        if key and key not in shares and top + runner_up > 0:
            shares[key] = runner_up / (top + runner_up)
    return shares


class StemLexicon:
    """Undiacritized surface form → its most frequent diacritized stem.

    Loading is lazy: constructing one reads nothing and fetches nothing, so a
    caller who never diacritizes never pays for it.
    """

    def __init__(self, source: str = DEFAULT_LEXICON,
                 ambiguous_share: Optional[float] = AMBIGUOUS_SHARE) -> None:
        self.source = source
        #: None consults the lexicon for every spelling, ambiguous or not.
        self.ambiguous_share = ambiguous_share
        self._entries: Optional[Dict[str, str]] = None
        self._shares: Dict[str, float] = {}

    @property
    def entries(self) -> Dict[str, str]:
        if self._entries is None:
            self._load()
        return self._entries

    def _load(self) -> None:
        try:
            path = resolve_source(self.source)
            text = path.read_text(encoding="utf-8")
        except Exception as exc:
            # A lexicon that was ASKED for and cannot be reached is an error.
            # Falling back to the model quietly would leave the caller with a
            # system that looks like it has a lexicon, transcribes as if it has
            # none, and says nothing — which is how a broken lexicon scores
            # identically to a working one and nobody notices. A caller who
            # wants the model unassisted asks for that, with lexicon=None.
            raise LexiconUnavailable(
                f"the stem lexicon {self.source!r} could not be read: {exc}\n\n"
                f"Pass lexicon=None to run the diacritizer without one."
            ) from exc
        self._entries = parse(text)
        self._shares = parse_shares(text)

    def get(self, word: str, context_words: Optional[int] = None) -> Optional[str]:
        """The diacritized stem for *word*, or ``None`` if we have never seen it.

        *context_words* is the length of the sentence the word is read in, when the
        caller reads a whole sentence. In a sentence of at least
        :data:`MIN_CONTEXT_WORDS` words an ambiguous spelling (see
        :data:`AMBIGUOUS_SHARE`) also gives ``None``, so the sentence decides it.
        """
        key = normalize_unicode(word)
        stem = self.entries.get(key)
        if stem is not None and context_words is not None \
                and context_words >= MIN_CONTEXT_WORDS and self.ambiguous(key):
            return None
        return stem

    def ambiguous(self, word: str) -> bool:
        """True when *word*'s runner-up reading holds at least the ambiguous share."""
        if self.ambiguous_share is None:
            return False
        if self._entries is None:
            self._load()
        return self._shares.get(normalize_unicode(word), 0.0) >= self.ambiguous_share

    def __len__(self) -> int:
        return len(self.entries)

    def __contains__(self, word: str) -> bool:
        return self.get(word) is not None
