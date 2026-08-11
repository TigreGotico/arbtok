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
from typing import Dict, List, NamedTuple, Optional

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
    # Non-standard Perso-Arabic letters used in loanwords and colloquial
    # spelling (چ tʃ, گ ɡ, پ p, ڤ v, ژ ʒ). They are real graphemes the cascade
    # must transcribe, not drop: without them ⟨بَاچِر⟩ /baːtʃir/ loses its
    # affricate. The word lattice already reads them; the cascade must too, so
    # the two paths agree.
    "چ": 'tʃ',  # چ
    "گ": 'ɡ',   # گ
    "پ": 'p',   # پ
    "ڤ": 'v',   # ڤ
    "ژ": 'ʒ',   # ژ
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

#: When a region carries several sibling specs, the one a bare region tag
#: resolves to. Saudi Arabia has six varieties in the data set; Najdi is the
#: most widely spoken, so ``ar-SA`` (and ``ar-SA-najdi``, ``ar-x-najdi``, …)
#: land on it rather than on whichever sibling happens to sort first.
_REGION_DEFAULTS = ("ar-SA-x-najd",)

#: Dialect names that a caller may write where the spec uses a different
#: private-use token. langcodes ignores private-use content when it measures
#: tag distance, so ``ar-x-najdi`` would otherwise fall through to MSA; these
#: map the spoken adjective to the spec's own token.
_DIALECT_NAME_ALIASES = {
    "najdi": "najd",
    "hejazi": "hejaz",
    "hijazi": "hejaz",
    "hijaz": "hejaz",
    "qassimi": "qassim",
    "gulf": "gulf",
    "gulfi": "gulf",
    "khaleeji": "gulf",
    "levantine": "levantine",
    "levant": "levantine",
    "shami": "levantine",
    "maghrebi": "maghrebi",
    "maghribi": "maghrebi",
}


def _arabic_codes() -> List[str]:
    """Available Arabic spec codes, ordered to steer ``closest_match`` ties.

    :func:`langcodes.closest_match` breaks equal-distance ties by list order, so
    the order encodes two preferences: MSA (:data:`DEFAULT_LANG`) leads, so an
    unmatched region (``ar-ZZ`` — equidistant from MSA and every regional spec)
    settles on MSA rather than an arbitrary dialect; then the
    :data:`_REGION_DEFAULTS`, so a bare region matching several private-use
    siblings at distance zero (``ar-SA``) settles on the declared default
    (Najdi) rather than whichever sibling sorts first; then the rest, by code.
    """
    from orthography2ipa import available_codes

    codes = [c for c in available_codes() if _is_arabic_code(c)]
    return sorted(
        codes,
        key=lambda c: (c != DEFAULT_LANG, c not in _REGION_DEFAULTS, c),
    )


def _dialect_index(codes: List[str]) -> Dict[str, str]:
    """Map a dialect token (spec private-use tokens + aliases) to its spec code."""
    index: Dict[str, str] = {}
    for code in codes:
        if "-x-" in code:
            index.setdefault(code.split("-x-")[-1].lower(), code)
    for alias, token in _DIALECT_NAME_ALIASES.items():
        target = index.get(token)
        if target:
            index[alias] = target
    return index


def spec_for_lang(lang: Optional[str]) -> str:
    """Resolve a language tag to an orthography2ipa Arabic spec code.

    An exact spec code wins (``ar-SA-x-najd``, ``ar-EG``, ``ar-x-gulf``), so a
    caller can name any variety the data set carries. Otherwise the tag is
    matched to the closest available spec:

    * a dialect named in a subtag — private-use or not — resolves to that
      variety's spec (``ar-x-najdi`` and ``ar-SA-najdi`` → ``ar-SA-x-najd``),
      even though BCP-47 tag distance ignores private-use content;
    * a region resolves to that region's spec, defaulting to the most widely
      spoken variety when the region carries several (``ar-SA`` → Najdi,
      ``ar-EG`` → Egyptian) via subtag-aware BCP-47 matching;
    * anything with no Arabic match — an unknown region, a non-Arabic tag —
      falls back to the ``ar`` (MSA) leaf rather than raising.
    """
    if not lang:
        return DEFAULT_LANG

    codes = _arabic_codes()
    normalized = lang.replace("_", "-")

    # 1. Exact spec code (case-insensitive) — a caller naming a variety directly.
    lowered = {code.lower(): code for code in codes}
    exact = lowered.get(normalized.lower())
    if exact:
        return exact

    # 2. A dialect named in a subtag. Private-use content is invisible to tag
    #    distance, so it has to be matched by name here.
    dialects = _dialect_index(codes)
    for token in normalized.lower().split("-"):
        if token in ("ar", "x"):
            continue
        match = dialects.get(token)
        if match:
            return match

    # 3. Closest region-bearing spec via subtag-aware BCP-47 matching. Codes
    #    with a subtag langcodes cannot parse (a private-use token over eight
    #    characters) are dropped from the pool — they are only ever reached by
    #    the exact-code path above, and one of them would abort the whole match.
    from langcodes import closest_match

    matchable = [c for c in codes
                 if all(len(sub) <= 8 for sub in c.split("-"))]
    try:
        best, _ = closest_match(normalized, matchable)
    except Exception:
        best = "und"
    if best in codes:
        return best

    return DEFAULT_LANG


class Lect(NamedTuple):
    """A resolvable Arabic variety and the maturity of its spec.

    :attr:`code` is an orthography2ipa spec code accepted by :func:`spec_for_lang`
    and by ``lang=`` on the plugin. :attr:`tier` is that spec's
    ``QualityTier`` value as declared upstream (``research``, ``skeleton``,
    ``stub``, ``production``) — how far its cited rule set has been taken, not a
    promise about arbtok's cascade.
    """

    code: str
    tier: str


def _is_arabic_code(code: str) -> bool:
    """Whether *code* names an Arabic-macrolanguage spec.

    ``ar`` (MSA) and ``arb`` (Classical) plus every ``ar-…`` leaf and grouping
    node. The lookalikes ``arc`` (Aramaic) and ``arn`` (Mapudungun) sort next to
    them in the registry but are unrelated languages, so they are excluded.

    Assumes the registry names Arabic varieties in BCP-47 form only: an ISO
    639-3 dialect code (``arz``, ``ary``, ``apc``, …) would be silently missed
    here and must be added explicitly if o2i ever registers one.
    """
    return code == "ar" or code == "arb" or code.startswith("ar-")


def supported_lects() -> List[Lect]:
    """Every Arabic variety arbtok can phonemize, with its o2i quality tier.

    Enumerated from the orthography2ipa registry, so it tracks the data set
    rather than a table here: whatever ``ar*`` specs are installed are what
    ``lang=`` resolves to. Sorted by code.

    >>> from orthography2ipa import available_codes
    >>> lects = supported_lects()
    >>> [l.code for l in lects if l.code in ("ar", "ar-EG", "ar-SA-x-najd")]
    ['ar', 'ar-EG', 'ar-SA-x-najd']
    >>> len(lects) == sum(1 for c in available_codes() if c in {"ar", "arb"}
    ...                   or c.startswith("ar-"))
    True
    >>> next(l.tier for l in lects if l.code == "ar")
    'research'
    """
    from orthography2ipa import available_codes, get

    return sorted(
        (Lect(code, get(code).quality.value)
         for code in available_codes() if _is_arabic_code(code)),
        key=lambda lect: lect.code,
    )


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
    # NOTE: ⟨مِائَة⟩ "hundred" used to need an entry here for its silent alif,
    # but arbtok.tokenizer.normalize_unicode now collapses that spelling onto
    # ⟨مئة⟩ before any lexicon lookup runs (see elide_silent_alif), so the
    # normal grapheme-to-IPA path already reads it correctly. This exception
    # would never fire.
    "عَمْرٌو": "ʕamrun",  # 'Amr - final Waw is silent (differentiates from 'Umar)
    "أُولِي": "ʔuliː",  # 'uli (owners of) - silent Waw
    "أُولُو": "ʔuluː",  # 'ulu - silent Waw

    # Particles carrying hamzat al-qaṭʿ on ALEF_HAMZA_BELOW. Keys are stored in
    # _reorder_diacritics-normalized form (shadda precedes vowel):
    "إِلَّا": "ʔillaː",   # إِلَّا "except/but" — hamzat al-qat'
    "إِلَى": "ʔilaː",          # إِلَى "to/towards" — hamzat al-qat'
}

