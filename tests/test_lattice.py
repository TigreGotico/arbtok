"""Tests for the orthography2ipa shared-lattice Arabic word engine.

Exercises :mod:`arbtok.lattice` — the shared
:class:`~orthography2ipa.phonetok.PhonetokTokenizer` over the ``ar`` spec
plus arbtok's :class:`~orthography2ipa.rescorer.LatticeRescorer` cascade.
The flagship is sun-letter assimilation (idghām ash-shamsiyya) expressed
as a rescorer over the shared lattice, with a moon-letter control.
"""
import pytest

from orthography2ipa import get
from orthography2ipa.phonetok import PhonetokTokenizer
from orthography2ipa.rescorer import LatticeRescorer

from arbtok.constants import SUN_LETTERS
from arbtok.lattice import (
    DEFAULT_RESCORERS,
    SunLetterRescorer,
    WaslRescorer,
    word_ipa,
    word_lattice,
)


def test_builds_on_shared_tokenizer():
    """The engine consumes orthography2ipa's tokenizer and ar spec."""
    tok = PhonetokTokenizer(get("ar"))
    assert tok.tokenize("كِتَاب")  # spec loads and tokenises Arabic
    assert all(isinstance(r, LatticeRescorer) for r in DEFAULT_RESCORERS)


# ─── Sun-letter assimilation (the flagship) ──────────────────────────────

# The article + sun letter → lām assimilates, sun consonant geminates.
SUN_CASES = [
    ("الشَّمْس", "aʃˈʃams", "ش shīn"),
    ("السَّمَك", "ˈassamak", "س sīn"),
    ("التَّاج", "atˈtaːdʒ", "ت tāʾ"),
    ("الثَّوْب", "aθˈθawb", "ث thāʾ"),
    ("الذَّهَب", "ˈaððahab", "ذ dhāl"),
    ("الرَّجُل", "ˈarradʒul", "ر rāʾ"),
    ("الزَّيْت", "azˈzajt", "ز zāy"),
    ("الطَّعَام", "ɑtˤtˤɑˈʕaːm", "ط ṭāʾ"),
    ("الظَّبْي", "ɑðˤˈðˤɑbj", "ظ ẓāʾ"),
    ("اللَّوْن", "alˈlawn", "ل lām"),
    ("النَّار", "anˈnaːr", "ن nūn"),
    ("الصَّوْت", "ɑsˤˈsˤɑwt", "ص ṣād"),
    ("الدَّار", "adˈdaːr", "د dāl"),
    ("الضَّوْء", "ɑdˤˈdˤɑwʔ", "ض ḍād"),
]


@pytest.mark.parametrize("word, expected, name", SUN_CASES)
def test_sun_letter_assimilation(word, expected, name):
    """Every one of the 14 coronal sun letters assimilates the article lām."""
    assert word_ipa(word) == expected, name


# Moon letters keep the lām (control: no assimilation).
MOON_CASES = [
    ("الْقَمَر", "ˈalqamar", "ق qāf"),
    ("الْكِتَاب", "alkiˈtaːb", "ك kāf"),
    ("الْمَسْجِد", "alˈmasdʒid", "م mīm"),
]


@pytest.mark.parametrize("word, expected, name", MOON_CASES)
def test_moon_letter_no_assimilation(word, expected, name):
    """Moon (non-coronal) letters keep the article lām — the control."""
    assert word_ipa(word) == expected, name


def test_sun_letter_set_is_the_14_coronals():
    """The sun-letter set is exactly the 14 cited coronal graphemes."""
    assert len(SUN_LETTERS) == 14
    # ق (qāf) and ك (kāf) are moon letters, never in the set.
    assert "ق" not in SUN_LETTERS and "ك" not in SUN_LETTERS


def test_sun_letter_rescorer_only_touches_the_article():
    """The rescorer is a no-op on a slot that is not the article grapheme."""
    slots = word_lattice("كِتَاب")  # no article
    assert "".join(s.top.ipa for s in slots) == "kitaːb"


# ─── Hamzat al-waṣl ──────────────────────────────────────────────────────

@pytest.mark.parametrize("word, expected", [
    ("اِسْتِقْبَال", "istiqˈbaːl"),
    ("اِجْتِمَاع", "idʒtiˈmaːʕ"),
    ("اِعْتِمَاد", "iʕtiˈmaːd"),
    ("اِنْقَطَع", "ˈinqɑtˤɑʕ"),
])
def test_hamzat_al_wasl_elision(word, expected):
    """Word-initial hamzat al-waṣl is silent; the harakah carries the vowel."""
    assert word_ipa(word) == expected


# ─── Gemination (shadda / tashdīd) ───────────────────────────────────────

@pytest.mark.parametrize("word, expected", [
    ("عَمَّ", "ˈʕamma"),
    ("كُلّ", "ˈkull"),
    ("ظَلَّ", "ˈðˤɑlla"),
    ("حَتَّى", "ˈħattaː"),
])
def test_gemination(word, expected):
    """Shadda doubles its consonant before the nucleus (not a length mark)."""
    assert word_ipa(word) == expected


# ─── Hamza carrier vowel de-duplication & semivowel onset ────────────────

@pytest.mark.parametrize("word, expected", [
    ("أَمِير", "ʔaˈmiːr"),   # hamza carrier + explicit fatḥa, not ʔaamīr
    ("تَأْثِير", "taʔˈθiːr"),  # carrier + sukūn
    ("يَوْم", "ˈjawm"),       # ⟨يَ⟩ onset /ja/, not the /aj/ coda diphthong
    ("بَيْت", "ˈbajt"),       # ⟨َي⟩ coda diphthong retained
])
def test_carrier_and_onset(word, expected):
    assert word_ipa(word) == expected


# ─── Regression guards: geminate glides, final glide vowel, ligatures ─────

@pytest.mark.parametrize("word, expected", [
    ("عُيِّنَ", "ˈʕujjina"),    # geminate yāʾ (glide) — not dropped
    ("قَوَّاس", "qawˈwaːs"),    # geminate wāw in a coda ligature
    ("اِفْعَوَّل", "ifˈʕawwal"),  # geminate wāw, form IX
])
def test_geminate_glides_not_dropped(word, expected):
    """Shadda geminates the semivowels ي/و too (Wright I §14; Ryding §2.3)."""
    assert word_ipa(word) == expected


# ─── Consonantal glide vs mater lectionis (ConsonantalGlideRescorer) ──────

@pytest.mark.parametrize("word, expected", [
    ("أَتْشِيُوت", "ʔatʃiˈjuːt"),   # ⟨ـِيُو⟩: yāʾ bears its own ḍamma → onset /j/
    ("أَبْخَازِيَا", "ʔabˈxaːzijaː"),  # ⟨ـِيَا⟩: yāʾ before /aː/ → onset /j/
    ("أَحُوَل", "ˈʔaħuwal"),       # ⟨ـُوَ⟩: wāw before fatḥa → onset /w/
])
def test_prevocalic_glide_is_a_consonant(word, expected):
    """A yāʾ/wāw after its homorganic vowel is length only when it CLOSES
    the syllable; before another vowel it retains its consonantal power
    and is the onset (Wright I §4; Watson 2002 §2.6.1: onsets are
    obligatory, so /i/ + V resolves as i.jV, never *iː.V)."""
    assert word_ipa(word) == expected


@pytest.mark.parametrize("word, expected", [
    ("أَشُورِيّ", "ʔaʃuːˈrijj"),    # nisba ـِيّ = doubled /-ijj/ (Ryding §5.4.1)
    ("أَرْمِيَّة", "ʔarˈmijja"),    # feminine nisba ـِيَّة = /-ijja/
    ("أُبُوَّة", "ʔuˈbuwwa"),      # ـُوَّة = /-uwwa/: geminate wāw, not /uːwa/
])
def test_geminated_glide_after_homorganic_vowel(word, expected):
    """Shadda doubles the semivowels too (Wright I §14), so ⟨ِي⟩ before the
    yāʾ's geminate copy is /ij/ + /j/ — the nisba suffix -iyy (Ryding,
    Reference Grammar of MSA, §5.4.1) — never the long vowel *iːiː/*iːja."""
    assert word_ipa(word) == expected


def test_word_final_glide_is_a_long_vowel():
    """A word-final ي reads as the long vowel, not the consonant /j/."""
    assert word_ipa("يُصَلِّي") == "jʊˈsˤɑlliː"


def test_presentation_ligature_never_empty():
    """The lam-alif ligature ﻻ decomposes; output is never empty."""
    assert word_ipa("ﻻ") == "ˈlaː"


def test_medial_semivowel_onset():
    """A medial ⟨وَ⟩ after a consonant is the onset /wa/ (أَبْوَاب → ʔabwaːb)."""
    assert word_ipa("أَبْوَاب") == "ʔabˈwaːb"


# ─── Deferral of cross-word / lexical cases (no public regression) ───────

from arbtok.lattice import defers_to_cascade  # noqa: E402


@pytest.mark.parametrize("word", [
    "وَبِاسْمِ",    # proclitic + internal (non-article) hamzat al-waṣl
    "مَرْحَبًا!",   # trailing punctuation → pausal (utterance-level)
])
def test_lexical_and_crossword_words_defer(word):
    """Words needing cross-word/lexical rules route to the cascade, not the
    word lattice — so the public word path never regresses on them."""
    assert defers_to_cascade(word) is True


@pytest.mark.parametrize("word", [
    "الشَّمْس", "الْقَمَر", "كِتَاب", "يَوْم", "عُيِّنَ", "أَبْوَاب",
    # ⟨إ⟩ carries a written hamza, so it is always hamzat al-qaṭʿ.
    "إِيْمَان", "إِلَّا", "إِحْسَاس",
    # A proclitic prefixed to the ARTICLE is read by the word lattice, which
    # elides the waṣl and assimilates exactly as orthography2ipa does
    # (وَالرُّطُوبَة → warrutˤuːba) — the cascade mis-read it (waːlrr…), so
    # it no longer defers. Only the non-article waṣl-alif stem still does.
    "فَبِالْحَقِّ", "وَالرُّطُوبَة", "بِالزَّعْفَرَان",
])
def test_flagship_words_do_not_defer(word):
    """The lattice-handled words are not needlessly deferred."""
    assert defers_to_cascade(word) is False


def test_rescorers_are_pure_no_ops_off_target():
    """Each flagship rescorer leaves an unrelated word byte-identical."""
    base = PhonetokTokenizer(get("ar")).ipa_lattice("قَلَم")
    base_ipa = "".join(s.top.ipa for s in base)
    for rescorer in (SunLetterRescorer(), WaslRescorer()):
        got = PhonetokTokenizer(get("ar")).ipa_lattice(
            "قَلَم", rescorer=[rescorer])
        assert "".join(s.top.ipa for s in got) == base_ipa


# ---------------------------------------------------------------------------
# The article test: an ⟨ال⟩ inside a stem is not the definite article
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("word, keeps, name", [
    ("خالد", "xald", "Khalid — the lām is the stem's second radical"),
    ("مزالت", "mazalt", "ma-zalat — ⟨ال⟩ spans stem letters"),
    ("فقالت", "faqalt", "fa-qalat — likewise, behind a proclitic"),
])
def test_a_stem_internal_alif_lam_keeps_its_consonant(word, keeps, name):
    """`SunLetterRescorer` assimilates any ⟨ال⟩ before a sun letter in an
    unpointed word. In these the ⟨ال⟩ is stem-internal, not the article, so
    dropping the lām deletes a root consonant: خالد reads `xad`."""
    ipa = word_ipa(word, "ar")
    assert "l" in ipa, (name, word, ipa)


def test_the_article_still_assimilates_when_it_really_is_the_article():
    """The control. The fix must not cost the behaviour the rescorer exists
    for, at word start or behind a proclitic."""
    assert "l" not in word_ipa("الشمس", "ar")
    assert "l" not in word_ipa("والشمس", "ar")


def test_a_word_with_both_keeps_the_stem_lam_and_drops_the_articles():
    """الثالث: the initial ⟨ال⟩ is the article before a sun letter ث and
    assimilates; the second is the stem's own alif-lām and must survive."""
    assert "l" in word_ipa("الثالث", "ar")


# ---------------------------------------------------------------------------
# A rescorer expresses a preference as cost, not as deletion
# ---------------------------------------------------------------------------

def _article_slot(word):
    return next(s for s in word_lattice(word, "ar") if s.grapheme == "ال")


@pytest.mark.parametrize("word", ["الشمس", "القمر", "خالِد"])
def test_the_rescorer_keeps_the_alternative_it_did_not_choose(word):
    """Every branch of the rescorer returns a one-element tuple, so the base
    lattice's two readings collapse to one at every ⟨ال⟩ — including the
    moon-letter and pointed cases where nothing is being assimilated. A
    consumer reading candidate sets rather than winners loses what was
    possible. A rescorer that has decided should say so in cost."""
    slot = _article_slot(word)
    assert len(slot.candidates) >= 2, (word, slot.candidates)


@pytest.mark.parametrize("word, winner", [
    ("الشمس", "a"),
    ("القمر", "al"),
    ("خالِد", "al"),
])
def test_the_rescorers_choice_is_still_the_cheapest_candidate(word, winner):
    """Keeping the alternative must not change what gets chosen."""
    slot = _article_slot(word)
    best = min(slot.candidates, key=lambda c: c.cost)
    assert best.ipa == winner, (word, slot.candidates)
