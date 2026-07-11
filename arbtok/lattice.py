"""Arabic word phonology on the orthography2ipa shared lattice.

arbtok builds on orthography2ipa's language-agnostic grapheme tokenizer
(:class:`~orthography2ipa.phonetok.PhonetokTokenizer`) and its ``ar``
spec grapheme table, rather than a private char-token tree. As of
orthography2ipa 1.64 the ``ar`` engine natively handles the segment-local
Arabic phonology arbtok once expressed as rescorers — gemination
(shadda ّ doubling a consonant, glides included), presentation-form /
lam-alif ligature normalisation (ﻻ → لا → ``laː``), onset glides
(يَ → ``ja``, وَ → ``wa``), the bare glottal stop of a hamza carrier
before an explicit harakah (أَمِير → ``ʔamiːr``), the word-final glide as
a long vowel, and pausal tāʾ marbūṭa (مَدِينَة → ``madiːna``). Those
private rescorers are gone.

What remains are the phenomena the shared ``ar`` table still cannot
express, layered on as :class:`~orthography2ipa.rescorer.LatticeRescorer`\\ s
over the per-position lattice
(:meth:`~orthography2ipa.phonetok.PhonetokTokenizer.ipa_lattice`):

- :class:`SunLetterRescorer` — sun-letter assimilation (idghām
  ash-shamsiyya): the lām of the definite article ⟨ال⟩ assimilates into a
  following coronal (sun) consonant — ``al-šams`` → ``aš-šams`` — while a
  moon (non-coronal) letter keeps the lām — ``al-qamar`` → ``al-qamar``.
- :class:`WaslRescorer` — hamzat al-waṣl (the prosthetic connecting
  vowel): word-initial bare alif is silent, its following short vowel
  carrying the onset (``istiqbāl`` from اِسْتِقْبَال).
- :class:`HamzaCarrierRescorer` — a hamza-bearing carrier before a sukūn
  or at a word edge is the bare glottal stop /ʔ/ with no vowel
  (تَأْثِير → ``taʔθīr``, نَبَأ → ``nabaʔ``); the ``ar`` engine strips the
  carrier's baked-in vowel only when an explicit harakah follows.
- :class:`AccusativeAlifRescorer` — the otiose alif after tanwīn al-fatḥ
  (accusative ``-an``) contributes no segment (مَرْحَبًا → ``marħaban``).

As of orthography2ipa 1.70 (upstream #251) the ``ar`` engine also natively
produces the two forms arbtok once patched with private rescorers, so those
rescorers are gone:

- a fatḥa before a standalone alif maksūra ى collapses to one long vowel
  (حَتَّى → ``ħattaː``, رَمَى → ``ramaː``) — the former
  ``MaterLectionisRescorer``;
- a word-final ي/و directly after a sukūn-bearing consonant is a coda glide,
  not a mater-lectionis long vowel (رَمْي → ``ramj``, ظَبْي → ``ðˤabj``,
  while فِي still → ``fiː``) — the former ``GlideCodaRescorer``.

The rescorers are pure, word-local, and composable. Cross-word sandhi —
clitic joining, cross-word waṣl elision, idghām/iqlāb, pausal forms — is
orthogonal to the word lattice and lives in the sentence-level
orchestration (the sanctioned
:meth:`orthography2ipa.g2p_plugin.G2PPlugin.post_process` seam), not here.

Sources for the rescored rules:

- Sun/moon (solar/lunar) letters and lām assimilation: W. Wright,
  *A Grammar of the Arabic Language*, 3rd ed., I §17; K. Ryding,
  *A Reference Grammar of Modern Standard Arabic* (CUP 2005) §2.6.
- Hamzat al-waṣl as a silent prosthetic vowel: Ryding §2.4; Wright I §19.
- Mater lectionis (a glide/alif after its homorganic short vowel is
  length, not a segment): Wright I §4.
- Otiose accusative alif after tanwīn al-fatḥ: Wright I §4 note;
  Ryding §5.3.1.1.
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

# The full set of harakāt (vowel/sukūn diacritic slots), used to strip a
# word down to its bare consonantal skeleton in :func:`defers_to_cascade`.
_HARAKAT = _SHORT_HARAKAT | {"ً", "ٌ", "ٍ", "ْ"}


def _is_consonant_ipa(ipa: str) -> bool:
    """True for an IPA string that starts a consonant (not a vowel/length)."""
    return bool(ipa) and ipa[0] not in "aiueoɑəː"


class SunLetterRescorer(LatticeRescorer):
    """Sun-letter assimilation of the definite article (idghām ash-shamsiyya).

    When the ⟨ال⟩ article grapheme is followed by a coronal *sun* letter
    the lām assimilates and drops, leaving the article as bare ``a``
    (``al-šams`` → ``aš-šams``); before a *moon* letter the lām is kept
    (``al-qamar`` → ``al-qamar``). The following sun consonant's gemination
    is carried by the written shadda, which the ``ar`` engine geminates
    natively. The 14 sun letters are the coronal obstruents and sonorants
    ت ث د ذ ر ز س ش ص ض ط ظ ل ن (Wright I §17).
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
    """Strip a hamza carrier's baked vowel before a sukūn or word edge.

    The ar spec maps أ→``ʔa`` and إ→``ʔi``; the ``ar`` engine (1.64) drops
    the baked vowel when an explicit harakah follows the carrier, so
    أَمِير → ``ʔamīr`` needs no help here. It does *not* drop it before a
    sukūn or at a word edge, where the carrier is the bare consonant /ʔ/
    with no vowel: تَأْثِير → ``taʔθīr`` (carrier + sukūn), نَبَأ →
    ``nabaʔ`` (word-final). This restores the bare /ʔ/ in exactly those
    positions. The word-initial إ (alif-hamza-below) is left to
    :func:`defers_to_cascade` (its waṣl-vs-qaṭʿ reading is lexical).
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
        if nxt is None or nxt.grapheme == SUKUN:  # word-final or sukūn
            return (Candidate(ipa="ʔ", cost=0.0),)
        return slot.candidates


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


# Rescorer pipeline: the accusative-alif rule first, then the mutually
# independent article/waṣl/hamza rules.
DEFAULT_RESCORERS: List[LatticeRescorer] = [
    AccusativeAlifRescorer(),
    SunLetterRescorer(),
    WaslRescorer(),
    HamzaCarrierRescorer(),
]

_tokenizer = PhonetokTokenizer(get("ar"))


def word_lattice(word: str) -> List[SegmentSlot]:
    """Return the rescored shared lattice for a single diacritized *word*."""
    text = normalize_unicode(word)
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
