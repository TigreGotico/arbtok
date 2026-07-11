"""Arabic word phonology on the orthography2ipa shared lattice.

arbtok builds on orthography2ipa's language-agnostic grapheme tokenizer
(:class:`~orthography2ipa.phonetok.PhonetokTokenizer`) and its ``ar``
spec grapheme table, rather than a private char-token tree. The Arabic
morpho-phonology that a plain table lookup cannot express is layered on
as :class:`~orthography2ipa.rescorer.LatticeRescorer`\\ s over the shared
per-position lattice (:meth:`~orthography2ipa.phonetok.PhonetokTokenizer.ipa_lattice`):

- :class:`GeminationRescorer` — shadda (ّ, tashdīd) doubles the preceding
  consonant instead of the spec's default length-mark realisation.
- :class:`SunLetterRescorer` — sun-letter assimilation (idghām
  ash-shamsiyya): the lām of the definite article ⟨ال⟩ assimilates into a
  following coronal (sun) consonant — ``al-šams`` → ``aš-šams`` — while a
  moon (non-coronal) letter keeps the lām — ``al-qamar`` → ``al-qamar``.
- :class:`WaslRescorer` — hamzat al-waṣl (the prosthetic connecting
  vowel): word-initial bare alif is silent, its following short vowel
  carrying the onset (``istiqbāl`` from اِسْتِقْبَال).
- :class:`HamzaCarrierRescorer` — a hamza-bearing alif/wāw/yāʾ realises
  as the bare glottal stop /ʔ/ when an explicit harakah follows, so the
  written vowel is not doubled (``ʔamīr`` from أَمِير, not ``ʔaamīr``).
- :class:`SemivowelOnsetRescorer` — a word-initial ⟨يَ⟩/⟨وَ⟩ is the
  consonantal onset /ja/, /wa/ (``jawm``), not the /aj/, /aw/ diphthong
  the spec lists (which is the *coda* grapheme ⟨َي⟩/⟨َو⟩).

The rescorers are pure, word-local, and composable (applied in the order
above). Cross-word sandhi — clitic joining, cross-word waṣl elision,
idghām/iqlāb, pausal forms — is orthogonal to the word lattice and lives
in the sentence-level orchestration (the sanctioned
:meth:`orthography2ipa.g2p_plugin.G2PPlugin.post_process` seam), not here.

Sources for the rescored rules:

- Sun/moon (solar/lunar) letters and lām assimilation: W. Wright,
  *A Grammar of the Arabic Language*, 3rd ed., I §17; K. Ryding,
  *A Reference Grammar of Modern Standard Arabic* (CUP 2005) §2.6.
- Hamzat al-waṣl as a silent prosthetic vowel: Ryding §2.4; Wright I §19.
- Shadda / tashdīd = gemination: Ryding §2.3.
"""
from __future__ import annotations

from typing import List, Sequence

from orthography2ipa import get
from orthography2ipa.phonetok import Candidate, PhonetokTokenizer, SegmentSlot
from orthography2ipa.rescorer import LatticeRescorer, RescoreContext

from arbtok.constants import (
    ALEF_HAMZA_ABOVE,
    ALEF_HAMZA_BELOW,
    ALIF,
    ALIF_MAKSURA,
    CLITIC_BASES,
    FATHA,
    DAMMA,
    KASRA,
    LAM,
    SHADDA,
    PUNCT,
    SUKUN,
    SUN_LETTERS,
    TANWIN_DAMM,
    TANWIN_FATH,
    TANWIN_KASR,
    WAW_HAMZA,
    YA_HAMZA,
)
from arbtok.tokenizer import normalize_unicode

# The definite-article grapheme as the ar spec tokenises it (alif+lām).
_ARTICLE = ALIF + LAM

# Explicit short-vowel harakāt that, when they follow a hamza carrier,
# already supply the syllable's vowel.
_SHORT_HARAKAT = {FATHA, DAMMA, KASRA}

# Hamza carriers whose spec grapheme bakes in a default vowel (ʔa / ʔi).
_HAMZA_CARRIERS = {ALEF_HAMZA_ABOVE, ALEF_HAMZA_BELOW, WAW_HAMZA, YA_HAMZA}

# Word-initial semivowel-plus-fatha graphemes the spec maps to a *coda*
# diphthong; as an onset they are the plain consonant + /a/.
_ONSET_SEMIVOWELS = {"يَ": "ja", "وَ": "wa"}


def _is_consonant_ipa(ipa: str) -> bool:
    """True for an IPA string that starts a consonant (not a vowel/length)."""
    return bool(ipa) and ipa[0] not in "aiueoɑəː"


# Harakāt (vowel/sukun diacritic slots) that Unicode canonical ordering
# places *between* a consonant and its shadda. Because NFC sorts combining
# marks by canonical combining class, a geminated, vowelled consonant
# always tokenises as ``C  harakah  ّ`` — the shadda never precedes the
# vowel. A per-slot rescorer cannot reorder slots, so gemination is
# realised on the consonant slot (doubling it) with the shadda slot
# deleted, keeping the geminate *before* the nucleus (aʃʃams, not aʃaʃ).
_HARAKAT = _SHORT_HARAKAT | {"ً", "ٌ", "ٍ", "ْ"}

# Short-vowel value of a harakah, for reconstructing a glide ligature's
# vowel when the glide is geminated.
_HARAKA_VOWEL = {FATHA: "a", DAMMA: "u", KASRA: "i"}


def _geminate_form(slot: SegmentSlot) -> str:
    """The doubled realisation of a shadda-bearing consonant slot, or ``""``.

    Shadda geminates *any* consonant, semivowels included (Wright I §14;
    Ryding §2.3). A plain consonant simply doubles (``m`` → ``mm``). A
    glide the spec merged into a ligature needs the glide itself doubled:
    an onset glide+vowel ligature (يِ, وَ …) becomes glide·glide·vowel
    (``يِ`` → ``jji``); a coda vowel+glide ligature (َو, َي) appends the
    glide (``aw`` → ``aww``).
    """
    top = slot.top.ipa
    g = slot.grapheme
    if _is_consonant_ipa(top):
        return top + top
    if g and g[0] in ("ي", "و"):  # onset glide (+ optional ligature vowel)
        glide = "j" if g[0] == "ي" else "w"
        vowel = "".join(_HARAKA_VOWEL.get(ch, "") for ch in g[1:])
        return glide + glide + vowel
    if "و" in g:  # coda vowel+glide ligature (َو)
        return top + "w"
    if "ي" in g:  # coda vowel+glide ligature (َي)
        return top + "j"
    return ""


class GeminationRescorer(LatticeRescorer):
    """Realise shadda (ّ) as gemination of its consonant (tashdīd).

    The ar spec maps the shadda grapheme to the length mark ``ː``; in
    Arabic tashdīd doubles the consonant it sits on — including the
    semivowels ي/و (عُيِّنَ → ``ʕujjina``). Unicode canonical ordering
    places the shadda slot *after* the consonant's harakah, so this doubles
    the owning consonant slot (scanning forward past the harakah) and
    deletes the shadda slot, keeping the geminate before the nucleus vowel
    (Ryding §2.3).
    """

    def rescore(
        self, slot: SegmentSlot, context: RescoreContext,
    ) -> Sequence[Candidate]:
        if slot.grapheme == SHADDA:
            return ()  # gemination is emitted on the consonant slot below
        # Look forward past this slot's harakah for an owning shadda.
        for nxt in context.slots[context.index + 1:]:
            if nxt.grapheme == SHADDA:
                doubled = _geminate_form(slot)
                if doubled:
                    return (Candidate(ipa=doubled, cost=slot.top.cost),)
                return slot.candidates
            if nxt.grapheme in _HARAKAT:
                continue
            break
        return slot.candidates


class GlideVowelRescorer(LatticeRescorer):
    """Read a non-onset ي/و as a long vowel rather than the consonant.

    A bare ي/و the spec ranks as the consonant /j/, /w/ is really a vowel
    when it is not a syllable onset: after its homorganic short vowel it is
    the length mater lectionis (يُصَلِّي → ``jusˤalliː``: kasra + ي → ``ː``),
    and word-final after a consonant it is the long vowel ``iː``/``uː``
    (Wright I §4). An onset ي/و (with a following harakah) keeps the
    consonant reading (:class:`SemivowelOnsetRescorer` handles the ⟨يَ⟩/⟨وَ⟩
    ligatures).
    """

    def rescore(
        self, slot: SegmentSlot, context: RescoreContext,
    ) -> Sequence[Candidate]:
        if slot.grapheme not in ("ي", "و") or context.is_word_initial:
            return slot.candidates
        # An onset glide is followed by its own harakah → keep /j/, /w/.
        nxt = context.next_slot
        if nxt is not None and nxt.grapheme in _HARAKAT and nxt.grapheme != "ْ":
            return slot.candidates
        long_vowel = "iː" if slot.grapheme == "ي" else "uː"
        short = "i" if slot.grapheme == "ي" else "u"
        prev = None
        for cand in reversed(context.slots[:context.index]):
            if cand.candidates:
                prev = cand
                break
        if prev is not None and prev.top.ipa.endswith(short):
            return (Candidate(ipa="ː", cost=0.0),)  # lengthen the short vowel
        if context.is_word_final and prev is not None \
                and _is_consonant_ipa(prev.top.ipa):
            return (Candidate(ipa=long_vowel, cost=0.0),)
        return slot.candidates


class MaterLectionisRescorer(LatticeRescorer):
    """Lengthen a bare alif that a shadda split from its fatha (mater lectionis).

    The ar spec merges ⟨َا⟩ (fatha+alif) into the single long-vowel
    grapheme ``aː``; when a shadda intervenes (النَّار → ن ّ ا) the merge
    is broken and the bare alif falls back to its ``ʔ``/``aː`` candidates.
    A bare alif whose preceding vowel is short ``a`` is the length mater
    lectionis, realised as ``ː`` (Wright I §4) — annaːr, not annaːʔr.
    """

    def rescore(
        self, slot: SegmentSlot, context: RescoreContext,
    ) -> Sequence[Candidate]:
        if slot.grapheme not in (ALIF, ALIF_MAKSURA) or context.is_word_initial:
            return slot.candidates
        # Scan back past slots an earlier rescorer emptied (a deleted shadda
        # sits between a geminated consonant and a bare alif: تّ + ا).
        prev = None
        for cand in reversed(context.slots[:context.index]):
            if cand.candidates:
                prev = cand
                break
        if prev is None or prev.grapheme == "ً":
            # After tanwīn al-fatḥ the alif is otiose (AccusativeAlifRescorer).
            return slot.candidates
        prev_ipa = prev.top.ipa
        if prev_ipa.endswith("ː"):
            # Already a long vowel (plural ⟨وا⟩, stacked length): silent.
            return (Candidate(ipa="", cost=0.0),)
        if prev_ipa.endswith(("a", "i", "u")):
            # Short vowel + alif = the length mater lectionis.
            return (Candidate(ipa="ː", cost=0.0),)
        # Bare medial/final alif with no vowel carrier reads as long /aː/,
        # not the rare glottal candidate.
        return (Candidate(ipa="aː", cost=0.0),)


class SunLetterRescorer(LatticeRescorer):
    """Sun-letter assimilation of the definite article (idghām ash-shamsiyya).

    When the ⟨ال⟩ article grapheme is followed by a coronal *sun* letter
    the lām assimilates and drops, leaving the article as bare ``a``
    (``al-šams`` → ``aš-šams``); before a *moon* letter the lām is kept
    (``al-qamar`` → ``al-qamar``). The following sun consonant's gemination
    is carried by the written shadda and handled by
    :class:`GeminationRescorer`. The 14 sun letters are the coronal
    obstruents and sonorants ت ث د ذ ر ز س ش ص ض ط ظ ل ن (Wright I §17).
    """

    def rescore(
        self, slot: SegmentSlot, context: RescoreContext,
    ) -> Sequence[Candidate]:
        if slot.grapheme != _ARTICLE:
            return slot.candidates
        nxt = context.next_slot
        if nxt is None:
            return slot.candidates
        if nxt.grapheme in SUN_LETTERS:
            # lām assimilates: article realises as bare /a/.
            return (Candidate(ipa="a", cost=0.0),)
        # moon letter: keep the lām (spec canonical /al/).
        return (Candidate(ipa="al", cost=0.0),)


class WaslRescorer(LatticeRescorer):
    """Elide word-initial hamzat al-waṣl (the prosthetic connecting vowel).

    A bare word-initial alif carrying hamzat al-waṣl (اِسْتِقْبَال,
    اِجْتِمَاع) is not itself a glottal onset — it is a prosthetic support
    whose short vowel carries the syllable. This deletes the initial
    alif slot so the following harakah supplies the vowel (``istiqbāl``).
    The article ⟨ال⟩ is a distinct grapheme and is untouched here
    (Ryding §2.4; Wright I §19).
    """

    def rescore(
        self, slot: SegmentSlot, context: RescoreContext,
    ) -> Sequence[Candidate]:
        if slot.grapheme != ALIF or not context.is_word_initial:
            return slot.candidates
        nxt = context.next_slot
        if nxt is not None and nxt.grapheme in _SHORT_HARAKAT:
            # An explicit harakah on the alif carries the vowel: delete it
            # (اِسْتِقْبَال → istiqbāl).
            return ()
        if nxt is not None and _is_consonant_ipa(nxt.top.ipa):
            # Bare waṣl-alif directly before a consonant takes the /i/ helper
            # vowel (انْتِمَاء → intimāʔ); its spec ʔ/aː readings are wrong.
            return (Candidate(ipa="i", cost=0.0),)
        return slot.candidates


class HamzaCarrierRescorer(LatticeRescorer):
    """Strip the baked-in vowel of a hamza carrier (أ إ ؤ ئ → /ʔ/).

    The ar spec maps أ→``ʔa`` and إ→``ʔi`` (the letter form implies a
    vowel). In fully-diacritized text the harakah is written explicitly, so
    the carrier is the bare consonant /ʔ/ and the following diacritic
    supplies the vowel: before a short harakah the built-in vowel would be
    doubled (أَمِير → ``ʔaamīr``), and before a sukūn or at word edge there
    is no vowel at all (تَأْثِير → ``taʔθīr``, نَبَأ → ``nabaʔ``). The
    word-initial alif-hamza-below إ is left to :class:`WaslRescorer`-free
    lexical handling and keeps its ``ʔi`` reading here.
    """

    def rescore(
        self, slot: SegmentSlot, context: RescoreContext,
    ) -> Sequence[Candidate]:
        if slot.grapheme not in _HAMZA_CARRIERS:
            return slot.candidates
        top = slot.top.ipa
        if not (top.startswith("ʔ") and len(top) > 1):
            return slot.candidates
        nxt = context.next_slot
        vowel_follows = nxt is not None and nxt.grapheme in _SHORT_HARAKAT
        no_vowel = nxt is None or nxt.grapheme == "ْ"  # word-final or sukūn
        # A following long-vowel/ligature slot (إِيمَان → إ + ⟨ِي⟩) also
        # carries its own vowel, so the carrier's baked vowel would double.
        vowel_slot_follows = nxt is not None and bool(nxt.top.ipa) \
            and not _is_consonant_ipa(nxt.top.ipa)
        if vowel_follows or no_vowel or vowel_slot_follows:
            return (Candidate(ipa="ʔ", cost=0.0),)
        return slot.candidates


class TaMarbutaRescorer(LatticeRescorer):
    """Silence a word-final tāʾ marbūṭa in pausal (isolated) form.

    ة is realised as /t/ only in connected speech (when a following word
    or case vowel continues); in pausal position — a word transcribed in
    isolation — it is silent, the preceding fatḥa carrying the syllable
    (مَدِينَة → ``madīna``). Connected /t/ is a cross-word effect handled by
    the sentence orchestration, not the word lattice (Ryding §2.1.2).
    """

    def rescore(
        self, slot: SegmentSlot, context: RescoreContext,
    ) -> Sequence[Candidate]:
        if slot.grapheme != "ة" or not context.is_word_final:
            return slot.candidates
        return (Candidate(ipa="", cost=0.0),)


class AccusativeAlifRescorer(LatticeRescorer):
    """Silence the otiose alif after tanwīn al-fatḥ (accusative -an).

    An accusative indefinite noun writes a final alif after tanwīn al-fatḥ
    (مَرْحَبًا); the alif is orthographic only — the ending is ``-an`` — so
    the alif contributes no segment (Wright I §4, note; Ryding §5.3.1.1).
    Pausal shortening of the ``-an`` itself is a cross-word/utterance
    effect handled by the sentence orchestration.
    """

    def rescore(
        self, slot: SegmentSlot, context: RescoreContext,
    ) -> Sequence[Candidate]:
        if slot.grapheme not in (ALIF, ALIF_MAKSURA):
            return slot.candidates
        prev = context.prev_slot
        if prev is not None and prev.grapheme == "ً":
            return (Candidate(ipa="", cost=0.0),)
        return slot.candidates


class SemivowelOnsetRescorer(LatticeRescorer):
    """Realise a word-initial ⟨يَ⟩/⟨وَ⟩ as the onset /ja/, /wa/.

    The ar spec maps these ligature graphemes to the *coda* diphthongs
    /aj/, /aw/, but a semivowel + fatḥa is always a consonantal onset —
    the glide precedes the vowel — whether word-initial (يَوْم → ``jawm``)
    or medial after a consonant (أَبْوَاب → ``ʔabwaːb``). The coda diphthong
    is the distinct vowel-first ⟨َي⟩/⟨َو⟩ grapheme and is unaffected.
    """

    def rescore(
        self, slot: SegmentSlot, context: RescoreContext,
    ) -> Sequence[Candidate]:
        onset = _ONSET_SEMIVOWELS.get(slot.grapheme)
        # Only rewrite the raw diphthong candidate; if an earlier rescorer
        # (gemination) already re-costed this slot, leave it be.
        if onset is None or slot.top.ipa not in ("aw", "aj"):
            return slot.candidates
        return (Candidate(ipa=onset, cost=0.0),)


# Rescorer pipeline order: gemination first (so a later rescorer sees a
# geminated neighbour), then the article/waṣl/hamza/semivowel rules which
# are mutually independent.
DEFAULT_RESCORERS: List[LatticeRescorer] = [
    GeminationRescorer(),
    SemivowelOnsetRescorer(),
    AccusativeAlifRescorer(),
    MaterLectionisRescorer(),
    GlideVowelRescorer(),
    TaMarbutaRescorer(),
    SunLetterRescorer(),
    WaslRescorer(),
    HamzaCarrierRescorer(),
]

# Arabic presentation-form ligatures the ``ar`` spec does not tokenise;
# decomposed to their base letters before the lattice runs so they never
# fall through to an empty transcription (ﻻ → laː).
_LIGATURES = {"ﻻ": "لا", "ﻼ": "لا", "ﯼ": "ى"}

_tokenizer = PhonetokTokenizer(get("ar"))


def word_lattice(word: str) -> List[SegmentSlot]:
    """Return the rescored shared lattice for a single diacritized *word*."""
    text = normalize_unicode(word)
    for lig, base in _LIGATURES.items():
        if lig in text:
            text = text.replace(lig, base)
    return _tokenizer.ipa_lattice(text, rescorer=DEFAULT_RESCORERS)


def word_ipa(word: str) -> str:
    """Transcribe one diacritized *word* via the shared lattice + rescorers.

    Concatenates the best (lowest-cost) candidate of each rescored slot.
    Input must be diacritized (tashkeel) — the same contract the ar spec
    and arbtok share.
    """
    return "".join(slot.top.ipa for slot in word_lattice(word))


_ALL_DIACRITICS = _HARAKAT | {SHADDA, "ٰ", "ٓ"}


def defers_to_cascade(word: str) -> bool:
    """True when a word needs cross-word/lexical rules the word lattice lacks.

    The shared lattice is a *word* engine: two Arabic phenomena live outside
    it and must stay on arbtok's sentence/lexical cascade until the o2i
    ar-spec gaps are resolved, so the public output never regresses:

    - **word-initial إ (alif-hamza-below)** — whether it is hamzat al-qaṭʿ
      (kept: إِلَّا → ``ʔillaː``) or hamzat al-waṣl (elided: إِيمَان →
      ``iːmaːn``) is *lexically* conditioned and unknowable from the
      orthography alone;
    - **a proclitic (و ف ب ك ل س …) prefixed to a stem carrying an internal
      hamzat al-waṣl or the article** — the waṣl elision spans the
      proclitic↔stem boundary (وَبِاسْمِ → ``wabismi``), a cross-word effect.

    Deferring is always safe: the cascade is the current reference path.
    """
    norm = normalize_unicode(word)
    if any(c in PUNCT for c in norm):
        # Trailing punctuation marks a pausal form (tanwīn/tāʾ-marbūṭa
        # shortening) — an utterance-level effect the cascade owns.
        return True
    bare = "".join(c for c in norm if c not in _ALL_DIACRITICS)
    if bare[:1] == ALEF_HAMZA_BELOW:
        return True
    # Peel leading proclitics (a clitic-base consonant + optional harakah);
    # if the stem then opens with a waṣl-alif or the article lām (بِاسْمِ,
    # بِالـ, لِلـ), the waṣl elision crosses the proclitic boundary.
    i, peeled = 0, False
    while i < len(norm) and norm[i] in CLITIC_BASES:
        j = i + 1
        if j < len(norm) and norm[j] in _SHORT_HARAKAT:
            j += 1
        # A proclitic lām directly before the article lām (لِلـ = li + al-,
        # the article's alif elided) — do not peel the article away; leave
        # the stem opening on لـ so it is recognised below.
        if norm[i] == LAM and j < len(norm) and norm[j] == LAM:
            break
        i, peeled = j, True
    if peeled:
        stem = "".join(c for c in norm[i:] if c not in _ALL_DIACRITICS)
        if stem[:1] in (ALIF, LAM):
            return True
    return False
