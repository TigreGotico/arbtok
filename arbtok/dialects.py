"""
TODO: to be extended with different phoneme realizations per dialect.
logic in tokenizer might use ArabicDialect enum if needed for further contextual rules

currently only MSA is targeted
"""
from enum import Enum
from arbtok.constants import (B, T, DJ, X, D, R, Z, S, F, Q, K, M, N, H, LAM, WAW, YA,
                              FATHA, DAMMA, KASRA, DAGGER_ALIF, MADD,
                              HAMZA, ALEF_HAMZA_ABOVE, ALEF_HAMZA_BELOW, WAW_HAMZA, YA_HAMZA,
                              TANWIN_FATH, TANWIN_KASR, TANWIN_DAMM,
                              ALIF_MAKSURA)


class ArabicDialect(str, Enum):
    CLA = "CLA"
    MSA = "MSA"


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

