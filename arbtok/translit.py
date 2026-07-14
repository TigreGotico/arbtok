"""A Latin-script word in an Arabic sentence.

Real Arabic text is full of English: *عندي meeting الساعة ٣*. The engine's input
contract is Arabic script, so a Latin word has no graphemes and no reading, and
what came out was the letters themselves — ``meeting`` transcribed as ``meeˈting``,
``Google`` as ``ˈGoogle``. Those are not phonemes. Fed to a TTS frontend they are
symbols with no embedding vector, and the word is unpronounceable, permanently and
silently.

So a Latin span has to be *read*. The question is how, and the obvious answer is
wrong.

## Why "transcribe it as English" is wrong

Running the span through an English G2P and splicing the result in gives::

    عندي meeting الساعة   →   ˈʕindiː ˈmiːtɪŋ asˈsaːʕa

No Saudi speaker says that. And every one of /ɪ/ and /ŋ/ is outside the Arabic
phoneme inventory, so the two symbols the naive answer introduces are exactly the
two the TTS model cannot say.

A loanword is not pronounced in its donor's phonology. It is **nativised** — mapped
into the phonology of the language actually being spoken. That is the whole content
of the loanword-adaptation literature, and for this variety it has been measured.

## The map

Alhoody, M. M. A. (2019), *Phonological Adaptation of English Loanwords into
Qassimi Arabic: an Optimality-Theoretic Account*, PhD thesis, Newcastle University.
Qassimi **is** Najdi — the variety of the ``ar-SA-x-najd`` spec — so this is not a
map borrowed from a neighbouring dialect, it is the map for the language we are
transcribing.

* Consonants English has and Arabic does not: /p/ → [b], /v/ → [f], /tʃ/ → [ʃ],
  /ʒ/ → [dʒ] (§5.1).
* **/ŋ/ is conditioned** (§5.1.10): [n] before /k/, but **[nɡ]** elsewhere. So
  *meeting* ends [-inɡ] and *pancreas* is [ban.kirˈjaːs]. This is why the naive
  answer's /ŋ/ is not merely mapped to /n/.
* Vowels collapse into the Arabic three-quality system: the English inventory has
  no /ɪ ʊ ɛ æ ə/ to give.

Stress is **not** carried over. It is re-derived by the matrix language's own rule
— Arabic's quantity-sensitive weight rule, over the Arabic syllabification of the
*adapted* form. *album* /ˈæl.bəm/ surfaces as [ʔalˈbuːm]: the stress has moved, and
the engine that moves it is the one already in this library.

## What this deliberately does not do

**Detect languages.** A Latin-script run is not a language, and guessing one from
character ranges is how ⟨Arabizi⟩ ("3ala", "7abibi") gets read as English — it is
Arabic, in Latin letters. This module assumes the donor it is told, and the caller
is what tells it. The engine never sniffs.

**Emit a symbol the matrix spec does not declare.** Every output is checked against
the spec's own inventory, and an escape is an error rather than a silent token with
no embedding. If a variety really does keep /p/ in loans, that is a claim about its
phonology and it belongs in the spec, where it can be read and cited.
"""

from __future__ import annotations

import functools
import re
import unicodedata
from typing import Dict, List, Optional, Sequence, Tuple

from orthography2ipa import G2P
from orthography2ipa.distance import segment_distance
from orthography2ipa.inventory import phoneme_inventory
from orthography2ipa.inventory import tokenize as ipa_tokenize

__all__ = ["nativize", "transliterate", "is_latin", "guest_script", "segment_ipa",
           "SEGMENT_MAP", "DONOR_LANG", "DONOR_BY_SCRIPT"]

#: The donor assumed when the caller names none. English is the overwhelming
#: source of live code-switching in Gulf Arabic, and it is the donor the map is
#: measured for — but it is a DEFAULT, not an assumption baked into the code:
#: :func:`transliterate` takes any orthography2ipa language as its donor.
DONOR_LANG = "en-GB"

#: A guess at the donor from the script alone, for a caller who has not said. This
#: is weak evidence and it is meant to be overridden — a script is not a language.
#: Latin letters spell English, French, Malay and *Arabizi* (Arabic in Latin
#: letters), and only the caller knows which.
DONOR_BY_SCRIPT = {
    "Latin": "en-GB",
    "Cyrillic": "ru",
    "Greek": "el",
}

#: Alhoody (2019) §5.1: the English phonemes Arabic has no room for. Ordered
#: longest-first at use so a two-character symbol wins over its first character.
SEGMENT_MAP: Dict[str, str] = {
    # consonants Arabic lacks
    "p": "b",
    "v": "f",
    "tʃ": "ʃ",
    "dʒ": "dʒ",   # Arabic HAS this one; listed so it is not touched by /ʒ/ below
    "ʒ": "dʒ",
    "ɡ": "ɡ",     # a Najdi phoneme (the reflex of qāf) — kept
    "ɹ": "r",
    "ɫ": "l",
    # vowels: English has no /ɪ ʊ ɛ æ ə/ to give, so they fall into the three
    # Arabic qualities.
    "ɪ": "i",
    "iː": "iː",
    "ʊ": "u",
    "uː": "uː",
    "ɛ": "i",
    "æ": "a",
    "ə": "a",
    "ʌ": "a",
    "ɑː": "aː",
    "ɔː": "uː",
    "ɒ": "u",
    "ɜː": "a",
    "eɪ": "eː",
    "əʊ": "oː",
    "aɪ": "aj",
    "aʊ": "aw",
    "ɔɪ": "uj",
    "ɪə": "iː",
    "eə": "eː",
    "ʊə": "uː",
}

#: /ŋ/ is not a simple substitution (Alhoody §5.1.10): [n] before /k/, [nɡ] else.
_NG = "ŋ"

_LATIN = re.compile(r"[A-Za-z]")


def is_latin(word: str) -> bool:
    """True when *word* is written in Latin letters."""
    return bool(_LATIN.search(word))


#: Multi-character IPA segments that must not be split: affricates, long vowels and
#: the diphthongs the donor maps name. Longest-first at use.
_LIGATURES = tuple(sorted(
    set(SEGMENT_MAP) | {"tʃ", "dʒ", "ts", "dz", "aː", "iː", "uː", "eː", "oː"},
    key=len, reverse=True,
))

_COMBINING = "ːʰʲˤ̃"


def segment_ipa(ipa: str) -> List[str]:
    """Split an IPA string into phonemes.

    Not ``orthography2ipa.inventory.tokenize``: that matches greedily against a
    spec's declared readings, and a declared reading may be a whole syllable — it
    segments ``miːtɪŋ`` as ``miː | t | ɪ | ŋ``, and a guest segment that is really a
    consonant plus a vowel gets adapted as if it were one sound. A phoneme is what
    a map is stated over, so a phoneme is what we cut.
    """
    out: List[str] = []
    i = 0
    while i < len(ipa):
        for lig in _LIGATURES:
            if ipa.startswith(lig, i):
                out.append(lig)
                i += len(lig)
                break
        else:
            j = i + 1
            while j < len(ipa) and ipa[j] in _COMBINING:
                j += 1
            out.append(ipa[i:j])
            i = j
    return out


@functools.lru_cache(maxsize=32)
def _targets(lang: str) -> Tuple[str, ...]:
    """The phonemes a guest may be projected ONTO: *lang*'s own, and only those.

    The declared inventory also carries multi-segment readings — a grapheme that
    spells a whole syllable contributes its whole reading — and those are not
    phonemes and cannot be projection targets. A guest segment must land on a
    single sound.
    """
    spec = G2P(lang).spec
    return tuple(sorted(
        p for p in phoneme_inventory(spec)
        if p and len(ipa_tokenize(p, spec)) == 1 and len(p) <= 3
    ))


@functools.lru_cache(maxsize=4096)
def _project(segment: str, lang: str) -> Optional[str]:
    """The phoneme of *lang* that is closest to *segment*, by phonological features.

    The generic answer, for a donor nobody has studied against this matrix. A cited
    map beats it wherever one exists — measured adaptation beats feature arithmetic,
    because what a speaker actually does is not always what the features predict
    (Alhoody's /tʃ/ → [ʃ], where the nearest Arabic segment by features is /dʒ/).
    """
    targets = _targets(lang)
    if not targets:
        return None
    if segment in targets:
        return segment
    best = min(targets, key=lambda t: segment_distance(segment, t))
    return best if segment_distance(segment, best) < 1.0 else None


def _map_segments(segments: Sequence[str], lang: str) -> List[str]:
    out: List[str] = []
    for i, seg in enumerate(segments):
        if seg == _NG:
            nxt = segments[i + 1] if i + 1 < len(segments) else ""
            # [n] before /k/, [nɡ] elsewhere — meeting → -inɡ, pancreas → ban.k…
            out.append("n" if nxt == "k" else "nɡ")
            continue
        cited = SEGMENT_MAP.get(seg)
        if cited is not None:
            out.append(cited)
            continue
        projected = _project(seg, lang)
        out.append(projected if projected is not None else seg)
    return out


def guest_script(word: str) -> Optional[str]:
    """The script *word* is written in, or ``None`` for Arabic script.

    A script is not a language. This says only what alphabet the word uses, which
    is where the caller's knowledge has to take over.
    """
    for char in word:
        if not char.isalpha():
            continue
        name = unicodedata.name(char, "")
        for script in DONOR_BY_SCRIPT:
            if name.startswith(script.upper()):
                return script
        if name.startswith("ARABIC"):
            return None
    return None


def nativize(donor_ipa: str, lang: str, donor: str = DONOR_LANG) -> str:
    """Map *donor_ipa* into the phonology of *lang*.

    The donor's stress is dropped: it is re-derived by the matrix language's own
    rule over the adapted form, which is why *album* comes out [ʔalˈbuːm] and not
    [ˈʔalbuːm].
    """
    stripped = donor_ipa.replace("ˈ", "").replace("ˌ", "")
    return "".join(_map_segments(segment_ipa(stripped), lang))


def transliterate(
    word: str, lang: str, donor: Optional[str] = None,
) -> Optional[str]:
    """Read a foreign-script *word* as a speaker of *lang* would say it.

    *lang* is the **matrix** — the language actually being spoken, and the one with
    the last word on every symbol emitted. Any orthography2ipa variety works, so the
    same English word is adapted differently for Najdi and for MSA, out of each
    one's own declared inventory.

    *donor* is the language the word comes FROM. It is the caller's to name, because
    a script does not determine a language: Latin letters spell English, French and
    *Arabizi* (Arabic in Latin letters) alike. When it is not given, the script is
    used as a weak guess (:data:`DONOR_BY_SCRIPT`).

    Returns ``None`` when the result would use a phoneme *lang* does not declare —
    the honest answer, because a symbol with no embedding is not a pronunciation.
    Notably the Najdi reading of *meeting* is refused for MSA: it needs /ɡ/, which
    is a Gulf reflex of qāf that MSA does not have.
    """
    if donor is None:
        script = guest_script(word)
        donor = DONOR_BY_SCRIPT.get(script or "", DONOR_LANG)

    try:
        donor_ipa = G2P(donor).transcribe_word(word)
    except Exception:
        return None
    if not donor_ipa:
        return None

    adapted = nativize(donor_ipa, lang, donor=donor)

    spec = G2P(lang).spec
    declared = phoneme_inventory(spec)
    outside = [t for t in ipa_tokenize(adapted, spec) if t not in declared]
    if outside:
        return None
    return adapted
