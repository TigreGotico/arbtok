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

## The map is per-lect, not one-size-fits-all

A loanword is adapted into *the lect actually being spoken*, and lects adapt
differently: a Cairene says *manager* with the native ǧīm stop [ɡ] where a Najdi
keeps the affricate [dʒ], and merges the English interdental of *think* into [t]
where the Najdi keeps [θ]. So there is not one nativisation table but several, each
cited to the loanword phonology *of its own lect*, and the table is chosen by the
matrix spec — walking the o2i parent chain, so a leaf inherits its group's table
(``ar-LB`` → the Levantine table) and an un-studied lect falls back to a
conservative pan-Arabic default rather than borrowing a neighbour's map.

### Najdi — ``ar-SA-x-najd`` (:data:`SEGMENT_MAP`)

Alhoody, M. M. A. (2019), *Phonological Adaptation of English Loanwords into
Qassimi Arabic: an Optimality-Theoretic Account*, PhD thesis, Newcastle University.
Qassimi **is** Najdi — the variety of the ``ar-SA-x-najd`` spec — so this is not a
map borrowed from a neighbouring dialect, it is the map for the language we are
transcribing.

* Consonants English has and Arabic does not: /p/ → [b], /v/ → [f], /tʃ/ → [ʃ],
  /ʒ/ → [dʒ] (§5.1). The native ǧīm reflex /dʒ/ is a Najdi phoneme and is kept.
* **/ŋ/ is conditioned** (§5.1.10): [n] before /k/, but **[nɡ]** elsewhere. So
  *meeting* ends [-inɡ] and *pancreas* is [ban.kirˈjaːs]. This is why the naive
  answer's /ŋ/ is not merely mapped to /n/.
* Vowels collapse into the Arabic three-quality system: the English inventory has
  no /ɪ ʊ ɛ æ ə/ to give.

### Egyptian — ``ar-EG`` (:data:`_EGYPTIAN_MAP`)

Hafez, O. (1996), *Phonological and Morphological Integration of Loanwords into
Egyptian Arabic*, Égypte/Monde arabe 27–28, 383–410; with the consonant inventory
of Watson, J. C. E. (2002), *The Phonology and Morphology of Arabic*, OUP.

* /p/ → [b] (Hafez p. 383), /v/ → [f] (p. 385), /tʃ/ → [ʃ] (p. 386).
* The native ǧīm of Cairene is the **stop [ɡ]**, so a loan /dʒ/ adapts to it —
  *manager* → [manaɡar], not the Najdi [manadʒar] (Watson 2002 §1; Hafez p. 386).
* /ʒ/ is a retained marginal loan phoneme, **[ʒ]** — *garage* keeps its final
  [ʒ] where Najdi has no /ʒ/ and refuses or substitutes [dʒ].
* Cairene has merged the interdentals into the dental stops, so English /θ/ → [t]
  (Hafez p. 385, *thermos* → [tormos]) and /ð/ → [d]. The Najdi keeps [θ]/[ð].
* Vowels are limited to the EA set (Hafez p. 388); the /e/ and /o/ of the donor
  fall into that set.

### Levantine — ``ar-x-levantine`` (:data:`_LEVANTINE_MAP``; inherited by ``ar-LB``,
``ar-SY``, ``ar-PS``, ``ar-JO``)

Al-Saidat, E. (2011), *English Loanwords in Jordanian Arabic: Gender and Number
Assignment*, Language Forum 37(1); with the Syrian consonant/vowel system of
Cowell, M. W. (1964), *A Reference Grammar of Syrian Arabic*, Georgetown UP.

* /v/ → [f], /tʃ/ → [ʃ], /ɹ/ → [r] and — basilectally — /p/ → [b] (Al-Saidat
  2011; he records /p/ variably approximated by more anglicised speakers, so this
  is the integrated, monolingual value).
* The urban Levantine ǧīm is [ʒ], retained; interdentals /θ/ /ð/ are retained in
  the group as a whole (the spec declares them), so unlike Cairene they are kept.
* The mid long vowels [eː] [oː] are native (Cowell 1964), so /eɪ/ → [eː] and
  /əʊ/ → [oː] — monophthongisation the three-vowel lects do not have.

### Default — ``ar`` (:data:`_DEFAULT_MAP`)

The conservative pan-Arabic core for a lect with no studied table of its own
(e.g. ``ar-KW``, which walks ``ar-x-gulf`` → ``ar-x-peninsular`` → ``arb`` and
finds none): the substitutions every survey agrees on — /p/ → [b], /v/ → [f],
/tʃ/ → [ʃ] — over MSA's three-vowel system, with interdentals kept (Watson 2002;
Holes, C. (2004), *Modern Arabic: Structures, Functions and Varieties*, GUP).
The inventory check does the rest: /ɡ/ passes for a Gulf lect that declares it and
is refused for MSA that does not.

Stress is **not** carried over by any table. It is re-derived by the matrix
language's own rule — Arabic's quantity-sensitive weight rule, over the Arabic
syllabification of the *adapted* form. *album* /ˈæl.bəm/ surfaces as [ʔalˈbuːm]:
the stress has moved, and the engine that moves it is the one already in this
library.

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
           "SEGMENT_MAP", "DONOR_LANG", "DONOR_BY_SCRIPT", "nativization_table"]

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

#: The pan-Arabic consonant substitutions every loanword survey agrees on, and the
#: three-quality vowel collapse shared by lects without a mid-vowel system. Each
#: cited table is built on top of this and overrides only what its own literature
#: says differs. ``ɡ`` is the script-g (U+0261), the Arabic reflex — not ASCII ``g``.
_PAN_ARABIC_CONSONANTS: Dict[str, str] = {
    "p": "b",
    "v": "f",
    "tʃ": "ʃ",
    "ɹ": "r",
    "ɫ": "l",
}
_THREE_VOWELS: Dict[str, str] = {
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
    "aɪ": "aj",
    "aʊ": "aw",
    "ɔɪ": "uj",
    "ɪə": "iː",
    "ʊə": "uː",
}

#: Egyptian (Cairene), ``ar-EG``. Hafez (1996); Watson (2002). The ǧīm is the stop
#: [ɡ], so a loan /dʒ/ lands on it; /ʒ/ is a retained loan phoneme; the interdentals
#: are merged into the dental stops. Vowels stay in the EA set (Hafez p. 388).
_EGYPTIAN_MAP: Dict[str, str] = {
    **_PAN_ARABIC_CONSONANTS,
    **_THREE_VOWELS,
    "dʒ": "ɡ",   # Cairene ǧīm is a stop (Watson 2002 §1) — manager → [manaɡar]
    "ʒ": "ʒ",    # retained marginal loan phoneme — garage keeps [ʒ]
    "ɡ": "ɡ",    # native ǧīm
    "θ": "t",    # interdental merger (Hafez p. 385) — think → [tink]
    "ð": "d",
}

#: Levantine, ``ar-x-levantine`` (inherited by ``ar-LB``/``ar-SY``/``ar-PS``/``ar-JO``).
#: Al-Saidat (2011); Cowell (1964). Urban ǧīm is [ʒ], interdentals kept, and the
#: native mid long vowels [eː]/[oː] give monophthongised reflexes.
_LEVANTINE_MAP: Dict[str, str] = {
    **_PAN_ARABIC_CONSONANTS,
    **_THREE_VOWELS,
    "dʒ": "dʒ",  # kept where the spec declares it
    "ʒ": "ʒ",    # urban ǧīm is [ʒ] (Cowell 1964)
    "ɡ": "ɡ",
    "eɪ": "eː",  # monophthongisation to the native mid long vowels (Cowell 1964)
    "əʊ": "oː",
}

#: The conservative pan-Arabic default, ``ar`` — for any lect with no cited table
#: of its own. Interdentals are kept (MSA declares them); /ɡ/ passes for a lect
#: that declares it and is refused by the inventory check for one that does not.
_DEFAULT_MAP: Dict[str, str] = {
    **_PAN_ARABIC_CONSONANTS,
    **_THREE_VOWELS,
    "dʒ": "dʒ",
    "ʒ": "dʒ",   # MSA/Gulf have no /ʒ/; the nearest declared segment is /dʒ/
    "ɡ": "ɡ",
    "eɪ": "eː",  # in-inventory for Gulf/peninsular lects; refused for MSA
    "əʊ": "oː",
}

#: Nativisation tables keyed by the o2i spec code they are cited FOR. Selection
#: (:func:`nativization_table`) resolves the matrix tag to a spec, then walks its
#: parent chain and takes the first code carrying a table — so a leaf inherits its
#: group's map and an un-tabled lect lands on the default. There is no hardcoded
#: lang→zone map here: the chain is o2i's own declared genealogy.
_TABLES: Dict[str, Dict[str, str]] = {
    "ar-SA-x-najd": SEGMENT_MAP,      # Alhoody (2019)
    "ar-EG": _EGYPTIAN_MAP,           # Hafez (1996), Watson (2002)
    "ar-x-levantine": _LEVANTINE_MAP,  # Al-Saidat (2011), Cowell (1964)
    "ar": _DEFAULT_MAP,               # conservative pan-Arabic default
}


@functools.lru_cache(maxsize=256)
def nativization_table(lang: str) -> Dict[str, str]:
    """The nativisation map for matrix *lang*, by walking o2i's parent chain.

    *lang* is resolved to a spec code (:func:`arbtok.dialects.spec_for_lang`), then
    the code and each of its ancestors is tried against :data:`_TABLES` in order,
    so ``ar-EG`` takes the Egyptian table, ``ar-LB`` inherits the Levantine one
    (``ar-LB`` → ``ar-x-levantine``), and ``ar-KW`` — whose chain
    ``ar-x-gulf`` → ``ar-x-peninsular`` → ``arb`` carries no table — falls back to
    the conservative :data:`_DEFAULT_MAP`. Cached; the returned dict is read-only.
    """
    from arbtok.dialects import spec_for_lang
    from orthography2ipa import get

    code: Optional[str] = spec_for_lang(lang)
    seen = set()
    while code and code not in seen:
        table = _TABLES.get(code)
        if table is not None:
            return table
        seen.add(code)
        try:
            parent = get(code).primary_parent
        except Exception:
            break
        code = getattr(parent, "code", parent)
    return _DEFAULT_MAP


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
    seg_map = nativization_table(lang)
    out: List[str] = []
    for i, seg in enumerate(segments):
        if seg == _NG:
            nxt = segments[i + 1] if i + 1 < len(segments) else ""
            # [n] before /k/, [nɡ] elsewhere — meeting → -inɡ, pancreas → ban.k…
            out.append("n" if nxt == "k" else "nɡ")
            continue
        cited = seg_map.get(seg)
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
