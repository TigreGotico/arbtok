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
the sentence orchestration), not here.

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

from typing import Dict, List, Sequence, Tuple

from orthography2ipa import get
from orthography2ipa.allophony import compile_allophone_rescorer
from orthography2ipa.stress import is_cliticless
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
from arbtok.stress import stress_ipa
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
        # A written article + shadda-marked sun letter never reaches this
        # rescorer: the spec fuses it into one grapheme (⟨السس⟩ → ``ass``) and
        # assimilates natively. An ⟨ال⟩ standing as its own slot has NO
        # written gemination, and what that means depends on whether anyone
        # vocalized the word:
        #
        # * a **vocalized** word whose author pointed the stem but wrote no
        #   shadda on the sun letter is deliberate — orthography2ipa reads
        #   الصْبَاح as ``alsˤbaːħ`` and the relative اللِي as ``alliː``,
        #   keeping the lām the page wrote (idghām ash-shamsiyya is carried by
        #   the shadda, Wright I §17). The article is spec-canonical /al/.
        # * a **bare** word omits every mark, the assimilating shadda with
        #   them, so nothing can be read off the (absent) pointing: the letter
        #   class is the only signal, and the classical rule applies —
        #   assimilate before a sun letter, keep the lām before a moon.
        if nxt.grapheme == LAM:
            # ⟨ال⟩ + a lām slot is the relative/geminate-lām class — اللِي
            # written with two lāms, or الّي whose written shadda the
            # tokenizer's gemination expansion has already turned into that
            # second lām (erasing the mark before this rescorer can see it).
            # Either spelling is read /all-/ (orthography2ipa: ``alliː``);
            # assimilating would swallow the geminate.
            return (Candidate(ipa="al", cost=0.0),)
        if nxt.grapheme in SUN_LETTERS and not any(
                ch in _HARAKAT or ch == SHADDA
                for s in context.slots for ch in s.grapheme):
            # bare word: lām assimilates, article realises as bare /a/ (the
            # sun letter's gemination is likewise unwritten and unrealised).
            return (Candidate(ipa="a", cost=0.0),)
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


#: Slots the ar spec emits for a yāʾ that continues a glide sequence — a
#: bare geminate copy or a yāʾ fused with its own harakah. Any of these
#: directly after a ⟨ِي⟩ mater-lectionis slot proves the yāʾ is consonantal.
_YA_ONSETS = {"ي", "يَ", "يِ", "يُ"}
#: Same for wāw (including the wāw+fatḥa+alif coda ligature).
_WAW_ONSETS = {"و", "وَ", "وِ", "وُ", "وَا"}

#: IPA vowel onsets: a following slot starting in one of these means the
#: glide sits between two vowels (so it must be a consonant, not length).
_VOWEL_ONSETS = "aiueoɑə"


class ConsonantalGlideRescorer(LatticeRescorer):
    """Read a prevocalic/geminated glide as a consonant, not vowel length.

    The ar spec's mater-lectionis digraphs ⟨ِي⟩ → ``iː`` and ⟨ُو⟩ → ``uː``
    are correct only when the glide letter is *quiescent* (bears no vowel
    of its own): a yāʾ/wāw after its homorganic short vowel is length
    solely "when it closes the syllable" — otherwise it "retains its
    consonantal power" and syllabifies as the onset of the next vowel
    (Wright, *A Grammar of the Arabic Language*, 3rd ed., I §4; Watson,
    *The Phonology and Morphology of Arabic*, OUP 2002, §2.6.1: onsets are
    obligatory, so a high vowel before another vowel resolves as V.GV).
    The spec matches the digraph greedily, so it swallows a consonantal
    glide too; this rescorer restores the consonant in exactly the two
    contexts that prove it:

    - the next slot begins with a vowel (⟨ـِيُو⟩ ``ijuː`` in أَتْشِيُوت,
      ⟨ـِيَا⟩ ``ijaː`` in أَبْخَازِيَا, ⟨ـُوَ⟩ ``uwa`` in أَحُوَل) —
      length before a vowel would leave that vowel onsetless;
    - the next slot is the glide's own geminate copy from a shadda
      (Wright I §14: shadda doubles the semivowels too), covering the
      nisba suffixes ـِيّ ``-ijj`` and ـِيَّة ``-ijja`` (Ryding,
      *A Reference Grammar of Modern Standard Arabic*, CUP 2005, §5.4.1:
      the relative adjective ends in doubled -iyy) and ـُوَّة ``-uwwa``
      (أُبُوَّة → ``ʔubuwwa``), where the first half of the geminate is
      consonantal by definition.

    The short vowel of the digraph is kept (``ij`` / ``uw``), and a bare
    geminate copy slot after the rescored digraph is forced to its
    consonant reading so ⟨ـِيّ⟩ ends in ``ijj`` and not ``ijiː``. A truly
    quiescent glide — word-final فِي → ``fiː``, preconsonantal — is left
    to the spec's long-vowel reading.
    """

    def rescore(
        self, slot: SegmentSlot, context: RescoreContext,
    ) -> Sequence[Candidate]:
        # The next slot proves a vowel onset only when it (a) actually renders
        # one — an empty rendering (a sukūn slot: كِيْف) proves nothing, and an
        # unguarded ``""[:1] in _VOWEL_ONSETS`` is vacuously true — and (b) is
        # not itself a bare mater glide: a bare و/ي read as ``uː``/``iː`` is
        # vowel *length*, and the spec resolves the sequence as hiatus
        # (Maghrebi 1pl ⟨ـِيو⟩ → ``iːuː``, orthography2ipa's own reading), not
        # by consonantizing the first glide. A glide bearing its own harakah
        # (⟨يُ⟩, ⟨ُو⟩ as a digraph slot) still proves the onset.
        nxt = context.next_slot
        nxt_vowel_onset = (
            nxt is not None and nxt.top.ipa
            and nxt.top.ipa[0] in _VOWEL_ONSETS
            and nxt.grapheme not in ("و", "ي"))
        if slot.grapheme == KASRA + "ي" and nxt is not None and (
                nxt.grapheme in _YA_ONSETS or nxt_vowel_onset):
            return (Candidate(ipa="ij", cost=0.0),)
        if slot.grapheme == DAMMA + "و" and nxt is not None and (
                nxt.grapheme in _WAW_ONSETS or nxt_vowel_onset):
            return (Candidate(ipa="uw", cost=0.0),)
        # The bare geminate copy after a rescored ⟨ِي⟩/⟨ُو⟩: force the
        # consonant so the shadda yields ``ijj``/``uww``, not ``ijiː``.
        prev = context.prev_slot
        if prev is not None:
            if slot.grapheme == "ي" and prev.grapheme == KASRA + "ي":
                return (Candidate(ipa="j", cost=0.0),)
            if slot.grapheme == "و" and prev.grapheme == DAMMA + "و":
                return (Candidate(ipa="w", cost=0.0),)
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
    ConsonantalGlideRescorer(),
]

#: The spec code used when a caller names no variety.
DEFAULT_LANG = "ar"

#: One tokenizer + rescorer chain per orthography2ipa spec code.
_ENGINES: Dict[str, Tuple[PhonetokTokenizer, List[LatticeRescorer]]] = {}


def _engine(lang: str) -> Tuple[PhonetokTokenizer, List[LatticeRescorer]]:
    """Build (and cache) the tokenizer + rescorer chain for a spec code.

    The chain is arbtok's structural rescorers followed by the rescorer
    compiled from the spec's own ``allophone_rules``. Order matters: the
    structural rules resolve *which segment* a slot is (silencing the
    otiose alif, assimilating the article's lām, stripping a hamza
    carrier's baked-in vowel), and the allophone pass then realizes those
    resolved segments in context (emphatic backing, Najdi affrication and
    gahawa epenthesis, Hejazi monophthongization). Realization must see
    the final segments, so it runs last.
    """
    engine = _ENGINES.get(lang)
    if engine is None:
        spec = get(lang)
        rescorers = list(DEFAULT_RESCORERS)
        allophones = compile_allophone_rescorer(spec.allophone_rules)
        if allophones is not None:
            rescorers.append(allophones)
        engine = (PhonetokTokenizer(spec), rescorers)
        _ENGINES[lang] = engine
    return engine


def word_lattice(word: str, lang: str = DEFAULT_LANG) -> List[SegmentSlot]:
    """Return the rescored shared lattice for a single diacritized *word*.

    *lang* is an orthography2ipa spec code — ``ar`` (MSA), ``ar-SA-x-najd``,
    ``ar-SA-x-hejaz``, ``ar-EG``, … — and selects both the grapheme table
    and the allophone rules the variety declares.
    """
    text = normalize_unicode(word)
    tokenizer, rescorers = _engine(lang)
    return tokenizer.ipa_lattice(text, rescorer=rescorers)



def word_ipa(word: str, lang: str = DEFAULT_LANG, stress: bool = True) -> str:
    """Transcribe one diacritized *word* via the shared lattice + rescorers.

    Concatenates the best (lowest-cost) candidate of each rescored slot.
    Input must be diacritized (tashkeel) — the same contract the ar spec
    and arbtok share. *lang* selects the variety; see :func:`word_lattice`.

    *stress* marks the stressed syllable. Arabic stress is quantity-sensitive —
    it falls on a syllable because that syllable is *heavy*, and weight is a
    property of the transcription, not of the spelling — so it can only be
    placed once the IPA exists. Given diacritized input, weight is fully
    determined and the placement is exact: superheavy final (kiˈtaːb) > heavy
    penult (muˈdarris) > antepenult (ˈmadrasa). See the spec's stress block.

    It matters for TTS: stress drives vowel duration and prominence, and getting
    it wrong is one of the loudest cues of a non-native-sounding voice. Turn it
    off for a consumer that scores against stress-free gold.
    """
    ipa = spec_word_exception(word, lang)
    if ipa is None:
        ipa = "".join(slot.top.ipa for slot in word_lattice(word, lang))
    # A declared prosodic clitic (a preposition, a vocative particle) bears no
    # word stress — it leans on its host. The engine leaves it unmarked, so the
    # stack must too, or a bare ``ˈfiː`` diverges from o2i on every phrase.
    if not stress or is_cliticless(word, get(lang)):
        return ipa
    return stress_ipa(ipa, lang)


def spec_word_exception(word: str, lang: str = DEFAULT_LANG):
    """The spec's whole-word IPA override for *word*, or ``None``.

    orthography2ipa specs carry inline ``word_exceptions`` — the lexical
    forms a variety's rules cannot derive (Lebanese هَيْدَا → ``hajda``
    against the monophthongization rule, Emirati عِيش → ``ʕeːʃ``, qeltu
    بَاكِر → ``baːkiʁ``). Its own engine consults them before the rules
    (``G2P._override_for``); a lattice path that skips them re-derives those
    words from rules the spec's authors have explicitly overridden, and
    drifts from the reference output word by word. Matched on the same
    NFC-normalized key the o2i engine uses (Arabic has no case), with
    arbtok's mark-reordered normalization tried as well so a
    vowel-before-shadda spelling still hits.
    """
    exceptions = get(lang).word_exceptions
    if not exceptions:
        return None
    import unicodedata
    from orthography2ipa.phonetok import _expand_arabic_gemination
    hit = exceptions.get(unicodedata.normalize("NFC", word))
    if hit is None:
        hit = exceptions.get(normalize_unicode(word))
    if hit is None:
        # o2i keys the table on its tokenizer's normalized form, in which a
        # shadda is already expanded to a doubled letter (التِّلِيفُون is
        # stored as التتِلِيفُون) — expand the same way before giving up.
        hit = exceptions.get(_expand_arabic_gemination(normalize_unicode(word)))
    return hit


_ALL_DIACRITICS = _HARAKAT | {SHADDA, "ٰ", "ٓ"}


def defers_to_cascade(word: str) -> bool:
    """True when a word needs cross-word/lexical rules the word lattice lacks.

    Two cases remain:

    - **trailing punctuation** — it marks a pausal form (tanwīn/tāʾ-marbūṭa
      shortening), an utterance-level effect the cascade owns;
    - **a proclitic (و ف ب ك ل س …) prefixed to a stem opening on a bare
      waṣl-alif that is NOT the article** (وَبِاسْمِ → ``wabismi``) — the
      elision of that internal hamzat al-waṣl spans the proclitic↔stem
      boundary, and only the cascade performs it (the lattice reads the
      alif as a vowel: ``wabiaːsmi``).

    The proclitic + **article** case (وَالرُّطُوبَة, بِالزَّعْفَرَان) used to
    defer here too, and must not: the cascade mis-reads it — an unelided و
    and an unassimilated article lām, ``waːlrrutˤuːba`` — while the word
    lattice elides the waṣl and assimilates exactly as orthography2ipa does
    (``warrutˤuːba``, ``bizzaʕfaraːn``). It now stays on the lattice.

    Deferring is only safe where the cascade is actually the better path.
    """
    norm = normalize_unicode(word)
    if any(c in PUNCT for c in norm):
        # Trailing punctuation marks a pausal form (tanwīn/tāʾ-marbūṭa
        # shortening) — an utterance-level effect the cascade owns.
        return True
    # Peel leading proclitics (a clitic-base consonant + optional harakah);
    # if the stem then opens on a bare waṣl-alif that does not start the
    # article (بِاسْمِ but not بِالْبَيْت), the waṣl elision crosses the
    # proclitic boundary and only the cascade models it. A FATḤA on the
    # peeled consonant rules the case out: ⟨بَا⟩ is that consonant plus the
    # mater-lectionis /aː/ — the ب is part of the word, not a clitic
    # (بَاش /baːʃ/, بَاچِر /baːtʃir/) — and the lattice reads it correctly.
    i, peeled, last_harakah = 0, False, None
    while i < len(norm) and norm[i] in CLITIC_BASES:
        j = i + 1
        # A letter carrying shadda is a geminate — part of the stem, never a
        # clitic (لِسَّا is li-ssa the word, not لِ+سَّا): stop peeling here,
        # or a stem-internal alif would be mistaken for a waṣl-alif and the
        # word sent to the cascade, off the spec lattice.
        if j < len(norm) and norm[j] == SHADDA:
            break
        last_harakah = None
        if j < len(norm) and norm[j] in _SHORT_HARAKAT:
            last_harakah = norm[j]
            j += 1
        i, peeled = j, True
    if peeled and last_harakah != FATHA:
        stem = "".join(c for c in norm[i:] if c not in _ALL_DIACRITICS)
        if stem[:1] == ALIF and stem[1:2] != LAM:
            return True
    return False
