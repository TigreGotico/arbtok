"""Dialect phonology for the arbtok rule cascade.

The cascade reads diacritized MSA-orthography text. "Dialect support"
therefore means *realizing that orthography with a regional zone's
reflexes* — the consonant sound a grapheme maps to, plus a few
context-conditioned rules — rather than modelling micro-dialects or the
lexical/morphological differences spoken varieties actually carry.

Five zones sit alongside the reference registers:

- ``MSA`` / ``CLA`` — the reference. No reflex overrides; output is
  byte-identical to the rule cascade's standard transcription.
- ``EGYPTIAN`` — Cairene reflexes.
- ``LEVANTINE`` — urban Levantine (Damascus/Beirut) defaults.
- ``GULF`` — Gulf proper, interdentals retained.
- ``MAGHREBI`` — North-African defaults, with a conservative short-vowel
  reduction approximation (see :func:`reduce_maghrebi_vowels`).

The data here is *model-generated from documented reflexes* and is
pending native-speaker validation, in the same spirit as the rest of the
repo's gold data. Where a grapheme has competing realizations, the
override picks the most widely cited urban default and the variability is
noted in comments — never silently chosen.
"""
from enum import Enum
from typing import Dict

from arbtok.constants import (B, T, DJ, X, D, R, Z, S, F, Q, K, M, N, H, LAM, WAW, YA,
                              FATHA, DAMMA, KASRA, DAGGER_ALIF, MADD,
                              HAMZA, ALEF_HAMZA_ABOVE, ALEF_HAMZA_BELOW, WAW_HAMZA, YA_HAMZA,
                              TANWIN_FATH, TANWIN_KASR, TANWIN_DAMM,
                              ALIF_MAKSURA)

# Interdental graphemes referenced by the zone overrides.
THEH = 'ث'   # ث
THAL = 'ذ'   # ذ
ZAH = 'ظ'    # ظ (emphatic interdental)


class ArabicDialect(str, Enum):
    # Reference registers (no reflex overrides — see DIALECT_CONSONANT_OVERRIDES).
    CLA = "CLA"          # Classical Arabic
    MSA = "MSA"          # Modern Standard Arabic (default)
    # Regional zones (broad, not micro-dialects).
    EGYPTIAN = "EGYPTIAN"
    LEVANTINE = "LEVANTINE"
    GULF = "GULF"
    MAGHREBI = "MAGHREBI"


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
# Dialect consonant reflexes
# ---------------------------------------------------------------------------
# Per-zone override of ARABIC_TO_IPA_CONSONANTS, consulted *before* the MSA
# table in the cascade. A grapheme absent from a zone's map keeps its MSA
# realization (so e.g. Gulf interdentals, retained, simply do not appear).
# Only the marketed regional zones get entries; MSA/CLA are intentionally
# empty so dialect=MSA is byte-identical to the reference cascade.
#
# Sources: widely documented urban/standard reflexes. Model-generated,
# pending native-speaker validation. Competing realizations are flagged
# inline; the override commits to the most-cited default.
DIALECT_CONSONANT_OVERRIDES: Dict[ArabicDialect, Dict[str, str]] = {
    ArabicDialect.EGYPTIAN: {
        # Cairene qāf → glottal stop; jīm → hard /g/.
        Q: "ʔ",
        DJ: "g",
        # Interdentals → dental stops. (Learned/loaned words instead take
        # the sibilant reflex ث→s, ذ→z; not modelled here — lexically
        # conditioned and unknowable from orthography.)
        THEH: "t",
        THAL: "d",
        # Emphatic interdental ظ → emphatic stop dˤ in inherited Cairene
        # vocabulary (merging with ض), consistent with the ث→t / ذ→d stop
        # reflexes above. The emphatic sibilant zˤ is the *borrowed* reflex
        # (parallel to the learned ث→s, ذ→z sibilants) and is lexically
        # conditioned — not modelled from orthography.
        ZAH: "dˤ",
    },
    ArabicDialect.LEVANTINE: {
        # Urban Levantine (Damascus/Beirut): qāf → glottal stop;
        # jīm → voiced postalveolar fricative ʒ.
        Q: "ʔ",
        DJ: "ʒ",
        # Interdentals: urban default is the dental stop (ث→t, ذ→d); the
        # sibilant reflex (t~s, d~z) surfaces in learned vocabulary —
        # variability noted, stop chosen.
        THEH: "t",
        THAL: "d",
        # ظ → emphatic stop dˤ, consistent with the ذ→d stop merger
        # (inferred to match the chosen interdental treatment; the zˤ
        # reflex also occurs).
        ZAH: "dˤ",
    },
    ArabicDialect.GULF: {
        # Gulf qāf → voiced velar /g/.
        Q: "g",
        # Gulf-proper jīm → palatal approximant /j/ (yodization), the
        # distinctive sedentary-Gulf reflex. The affricate dʒ is the broader
        # pan-Gulf / urban-Kuwaiti default and remains common; yodization is
        # phonologically conditioned and variable. The zone label commits to
        # /j/ as its marked feature — variability noted, not silently chosen.
        DJ: "j",
        # Interdentals (ث ذ ظ) are RETAINED → no override; they keep the
        # MSA θ, ð, ðˤ.
    },
    ArabicDialect.MAGHREBI: {
        # Maghrebi qāf has both q and g reflexes; the conservative q is
        # kept as default → no override for Q (variability noted).
        # jīm → ʒ.
        DJ: "ʒ",
        # Interdentals merged into dental stops.
        THEH: "t",
        THAL: "d",
        # ظ → emphatic stop dˤ, consistent with the interdental merger.
        ZAH: "dˤ",
    },
}


def consonant_ipa(grapheme: str, dialect: "ArabicDialect", default: str) -> str:
    """Resolve a consonant grapheme to IPA under *dialect*.

    Consults the zone's reflex override first, falling back to *default*
    (the MSA realization the caller already computed). For MSA/CLA the
    override table is empty, so this is the identity of *default*.
    """
    return DIALECT_CONSONANT_OVERRIDES.get(dialect, {}).get(grapheme, default)


# ---------------------------------------------------------------------------
# Maghrebi short-vowel reduction (approximation)
# ---------------------------------------------------------------------------
# Maghrebi's signature is heavy reduction/elision of short vowels, which
# operates below the orthography the cascade reads (CVCVC spellings give no
# stress or syllable cues). We apply a CONSERVATIVE, deterministic stand-in:
# a short vowel in a *non-initial, non-final, open* syllable (…C V C V…) is
# centralized to schwa. This is an approximation of the reduction pattern,
# not a syllabifier or stress model, and is intentionally cautious to avoid
# corrupting closed syllables and final vowels.
_SHORT_VOWELS = {"a", "i", "u"}


def reduce_maghrebi_vowels(ipa: str) -> str:
    """Centralize short vowels in non-initial open non-final syllables to ə.

    Approximation of Maghrebi short-vowel reduction; see module note. Long
    vowels (with the ``ː`` length mark) and vowels in closed or
    word-edge syllables are left untouched.
    """
    chars = list(ipa)
    n = len(chars)
    out = []
    # Track how many vowels have been emitted so we never touch the first
    # (onset) vowel, only medial ones.
    seen_vowel = False
    for i, ch in enumerate(chars):
        if ch in _SHORT_VOWELS:
            nxt = chars[i + 1] if i + 1 < n else None
            nxt2 = chars[i + 2] if i + 2 < n else None
            # Reduce only when: not the first vowel of the word (seen_vowel),
            # the vowel is short (not followed by length mark), it sits in an
            # OPEN syllable (V followed by a single consonant then a vowel,
            # i.e. C V . C V), and it is NOT the final vowel (nxt2 exists and
            # is itself a vowel, so a syllable follows).
            is_open_non_final = (
                seen_vowel
                and nxt is not None and nxt != "ː" and nxt not in _SHORT_VOWELS
                and nxt2 is not None and nxt2 in _SHORT_VOWELS
            )
            if is_open_non_final:
                out.append("ə")
            else:
                out.append(ch)
            seen_vowel = True
        else:
            out.append(ch)
            if ch == " ":
                seen_vowel = False  # reset at word boundaries
    return "".join(out)


# ---------------------------------------------------------------------------
# Language-code → dialect zone resolution
# ---------------------------------------------------------------------------
# Maps BCP-47 region subtags to the broad zone. Used by the G2P plugin to
# pick a zone from context.lang. Unknown/region-less codes fall back to MSA.
LANG_TO_DIALECT: Dict[str, ArabicDialect] = {
    # Egyptian
    "eg": ArabicDialect.EGYPTIAN,
    # Levantine
    "sy": ArabicDialect.LEVANTINE,
    "lb": ArabicDialect.LEVANTINE,
    "jo": ArabicDialect.LEVANTINE,
    "ps": ArabicDialect.LEVANTINE,
    # Gulf
    "ae": ArabicDialect.GULF,
    "bh": ArabicDialect.GULF,
    "kw": ArabicDialect.GULF,
    "om": ArabicDialect.GULF,
    "qa": ArabicDialect.GULF,
    "sa": ArabicDialect.GULF,
    # Maghrebi
    "ma": ArabicDialect.MAGHREBI,
    "dz": ArabicDialect.MAGHREBI,
    "tn": ArabicDialect.MAGHREBI,
    "ly": ArabicDialect.MAGHREBI,
}


def dialect_for_lang(lang: str) -> ArabicDialect:
    """Resolve a BCP-47 language tag to an :class:`ArabicDialect` zone.

    Reads the region subtag (``ar-EG`` → ``EGYPTIAN``); bare ``ar`` or any
    unmapped region resolves to MSA.
    """
    if not lang:
        return ArabicDialect.MSA
    parts = lang.replace("_", "-").lower().split("-")
    for part in parts[1:]:
        if part in LANG_TO_DIALECT:
            return LANG_TO_DIALECT[part]
    return ArabicDialect.MSA

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

    # TODO - why are these irregular?
    "مُسْتَشْفَى": "mustashfaː",
    "مَدْرَسَة": "madrasah",

    # Particles with genuine hamzat al-qat' (cutting hamza) on ALEF_HAMZA_BELOW.
    # These must not be confused with Form-IV masdar words whose initial إ is hamzat al-wasl
    # (e.g. إِيمَان = iːmaːn, no ʔ). The particles below are lexically fixed with ʔ.
    # Keys stored in _reorder_diacritics-normalized form (shadda precedes vowel):
    "إِلَّا": "ʔillaː",   # إِلَّا "except/but" — hamzat al-qat'
    "إِلَى": "ʔilaː",          # إِلَى "to/towards" — hamzat al-qat'
}

