"""Arabic lexical exceptions and the variety→spec bridge for the cascade.

A variety is not a hardcoded bucket of consonant swaps: it is an
orthography2ipa **spec** (``ar``, ``ar-SA-x-najd``, ``ar-EG``, …) that declares
its own grapheme table and ``allophone_rules``. :func:`spec_for_lang` resolves a
language tag to one, and :func:`consonant_ipa` reads a consonant's realization
straight out of that spec — so the qāf reflex, the interdental treatment and the
jīm all come from cited spec data rather than a table in this file.

The word lattice (:mod:`arbtok.lattice`) additionally compiles the spec's
``allophone_rules``, so context-conditioned phonology — Najdi affrication and
gahawa epenthesis, Hejazi monophthongization, emphatic spreading — fires there.
The sentence cascade below reads the spec's grapheme layer only; it has no
allophone pass yet.
"""

from enum import Enum
from typing import Dict, Optional

from arbtok.constants import (B, T, DJ, X, D, R, Z, S, F, Q, K, M, N, H, LAM, WAW, YA,
                              FATHA, DAMMA, KASRA, DAGGER_ALIF, MADD,
                              HAMZA, ALEF_HAMZA_ABOVE, ALEF_HAMZA_BELOW, WAW_HAMZA, YA_HAMZA,
                              TANWIN_FATH, TANWIN_KASR, TANWIN_DAMM,
                              ALIF_MAKSURA)

# Interdental graphemes referenced by the zone overrides.
THEH = 'ث'   # ث
THAL = 'ذ'   # ذ
ZAH = 'ظ'    # ظ (emphatic interdental)


ARABIC_TO_IPA_CONSONANTS = {
    HAMZA: "ʔ", ALEF_HAMZA_ABOVE: "ʔ", ALEF_HAMZA_BELOW: "ʔ", WAW_HAMZA: "ʔ", YA_HAMZA: "ʔ",
    B: 'b',
    T: 't',
    '\u062B': 'θ',
    DJ: 'dʒ',  # DJ: 'ʤ',
    '\u062D': 'ħ',
    X: 'x',
    D: 'd',
    '\u0630': 'ð',
    R: 'r',
    Z: 'z',
    S: 's',
    '\u0634': 'ʃ',
    '\u0635': 'sˤ',
    '\u0636': 'dˤ',
    '\u0637': 'tˤ',
    '\u0638': 'ðˤ',
    '\u0639': 'ʕ',
    '\u063A': 'ɣ',
    F: 'f',
    Q: 'q',
    K: 'k',
    M: 'm',
    N: 'n',
    H: 'h',
    LAM: 'l',
    WAW: 'w',
    YA: 'j',
    # Other unicode variations
    "ﻻ": "laː"
}

DIACRITIC_TO_IPA = {
    FATHA: 'a',
    DAMMA: 'u',
    KASRA: 'i',
    DAGGER_ALIF: 'aː',
    MADD: 'aː'
}
TANWIN_TO_IPA = {
    TANWIN_FATH: "an",
    TANWIN_DAMM: "un",
    TANWIN_KASR: "in"
}

VOWEL_MAP = {**DIACRITIC_TO_IPA,
             **TANWIN_TO_IPA,
             MADD: ":",
             ALIF_MAKSURA: 'aː'}

# ---------------------------------------------------------------------------
# Variety resolution: consonants come from the spec, not from a table here
# ---------------------------------------------------------------------------

_CONSONANT_MAPS: Dict[str, Dict[str, str]] = {}

#: Vowel segments. A spec reading containing one is not a bare consonant.
_VOWEL_CHARS = set("aiueoɑæəː")


def consonant_map(lang: str) -> Dict[str, str]:
    """The consonant realizations *lang*'s spec declares, keyed by grapheme.

    Only the graphemes the cascade treats as consonants are taken, and only
    their first (highest-ranked) reading — the cascade is a single-path engine
    and cannot carry candidates. A grapheme the spec does not override keeps
    the reference realization in :data:`ARABIC_TO_IPA_CONSONANTS`.

    A reading carrying a vowel is skipped. Some spec graphemes bake a default
    vowel into the consonant — the hamza carriers read ⟨أ⟩ as ``ʔa``, which is
    the right *lattice* candidate (a rescorer strips the vowel when an explicit
    harakah follows) but the wrong thing to hand a cascade that appends the
    harakah itself: it would yield ``ʔaa``. The cascade wants the bare
    consonant, so it keeps its own ``ʔ``.
    """
    cached = _CONSONANT_MAPS.get(lang)
    if cached is None:
        from orthography2ipa import get
        cached = {
            grapheme: readings[0]
            for grapheme, readings in get(lang).graphemes.items()
            if grapheme in ARABIC_TO_IPA_CONSONANTS and readings
            and not (_VOWEL_CHARS & set(readings[0]))
        }
        _CONSONANT_MAPS[lang] = cached
    return cached


def consonant_ipa(grapheme: str, lang: str, default: str) -> str:
    """Resolve a consonant grapheme to IPA under the variety *lang*.

    Consults the variety's spec first, falling back to *default* (the reference
    realization the caller already computed).
    """
    return consonant_map(lang).get(grapheme, default)


#: The spec code used when a caller names no variety.
DEFAULT_LANG = "ar"


def spec_for_lang(lang: Optional[str]) -> str:
    """Resolve a language tag to an orthography2ipa Arabic spec code.

    An exact spec code wins (``ar-SA-x-najd``, ``ar-EG``, ``ar-x-gulf``), so a
    caller can name any variety the data set carries. Otherwise the tag is
    narrowed a subtag at a time (``ar-SA-x-najd`` → ``ar-SA`` → ``ar``) until a
    spec exists. A tag naming no Arabic spec at all falls back to the ``ar``
    leaf rather than raising: an unknown region is MSA.
    """
    from orthography2ipa import available_codes

    if not lang:
        return DEFAULT_LANG
    codes = set(available_codes())
    lowered = {code.lower(): code for code in codes}
    parts = lang.replace("_", "-").split("-")
    for stop in range(len(parts), 0, -1):
        candidate = "-".join(parts[:stop])
        if candidate.endswith("-x"):  # a bare private-use marker is not a code
            continue
        if candidate in codes:
            return candidate
        match = lowered.get(candidate.lower())
        if match:
            return match
    return DEFAULT_LANG


# --- Word Exceptions ---
# TODO - LLM generated, needs validation from native speaker
# Dictionary for words with irregular orthography vs pronunciation.
# These words have "deficient" or "historical" spelling where vowels
# are pronounced but not written, or written letters are silent.
WORD_EXCEPTIONS = {
    # === Unicode / orthographic variants ===

    # Demonstratives with "Dagger Alif" (pronounced long /a:/ but written short or omitted)
    "هَٰذَا": "haːðaː",  # ha-dha (this, m.)
    "هٰذَا": "haːðaː",  # variant
    "هَذَا": "haːðaː",  # common deficient spelling
    "هَٰذِهِ": "haːðihi",  # ha-dhi-hi (this, f.)
    "هٰذِهِ": "haːðihi",  # variant
    "ذَٰلِكَ": "ðaːlika",  # dha-li-ka (that)
    "ذٰلِكَ": "ðaːlika",  # variant
    "أُولَٰئِكَ": "ʔulaːʔika",  # u-la-i-ka (those) - note medial hamza logic is complex, hardcoded here

    # Particles
    "لَٰكِن": "laːkin",  # la-kin (but) - unwritten medial alif
    "لَكِن": "laːkin",  # deficient spelling
    "لَٰكِنَّ": "laːkinna",  # la-kin-na (but...)

    # Divine Names
    "ﷲ": "allaːh",
    "اللّٰه": "allaːh",  # Allah - heavy L, unwritten alif
    "اللَّه": "allaːh",  # variant
    "إِلَٰه": "ʔilaːh",  # ilah (god)
    "الرَّحْمَٰن": "arraħmaːn",  # Ar-Rahman

    # Irregular pronunciations
    "مِائَة": "miʔa",  # mi'a (hundred) - silent extra Alif in spelling
    "عَمْرٌو": "ʕamrun",  # 'Amr - final Waw is silent (differentiates from 'Umar)
    "أُولِي": "ʔuliː",  # 'uli (owners of) - silent Waw
    "أُولُو": "ʔuluː",  # 'ulu - silent Waw

    # Particles carrying hamzat al-qaṭʿ on ALEF_HAMZA_BELOW. Keys are stored in
    # _reorder_diacritics-normalized form (shadda precedes vowel):
    "إِلَّا": "ʔillaː",   # إِلَّا "except/but" — hamzat al-qat'
    "إِلَى": "ʔilaː",          # إِلَى "to/towards" — hamzat al-qat'
}

