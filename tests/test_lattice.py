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
    ("الشَّمْس", "aˈʃʃams", "ش shīn"),
    ("السَّمَك", "ˈassamak", "س sīn"),
    ("التَّاج", "aˈttaːdʒ", "ت tāʾ"),
    ("الثَّوْب", "aˈθθawb", "ث thāʾ"),
    ("الذَّهَب", "ˈaððahab", "ذ dhāl"),
    ("الرَّجُل", "ˈarradʒul", "ر rāʾ"),
    ("الزَّيْت", "aˈzzajt", "ز zāy"),
    ("الطَّعَام", "ɑtˤtˤɑˈʕaːm", "ط ṭāʾ"),
    ("الظَّبْي", "ɑˈðˤðˤɑbj", "ظ ẓāʾ"),
    ("اللَّوْن", "aˈllawn", "ل lām"),
    ("النَّار", "aˈnnaːr", "ن nūn"),
    ("الصَّوْت", "ɑˈsˤsˤɑwt", "ص ṣād"),
    ("الدَّار", "aˈddaːr", "د dāl"),
    ("الضَّوْء", "ɑˈdˤdˤɑwʔ", "ض ḍād"),
]


@pytest.mark.parametrize("word, expected, name", SUN_CASES)
def test_sun_letter_assimilation(word, expected, name):
    """Every one of the 14 coronal sun letters assimilates the article lām."""
    assert word_ipa(word) == expected, name


# Moon letters keep the lām (control: no assimilation).
MOON_CASES = [
    ("الْقَمَر", "ˈalqamar", "ق qāf"),
    ("الْكِتَاب", "alkiˈtaːb", "ك kāf"),
    ("الْمَسْجِد", "aˈlmasdʒid", "م mīm"),
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
    ("اِسْتِقْبَال", "istiˈqbaːl"),
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
    ("تَأْثِير", "taˈʔθiːr"),  # carrier + sukūn
    ("يَوْم", "ˈjawm"),       # ⟨يَ⟩ onset /ja/, not the /aj/ coda diphthong
    ("بَيْت", "ˈbajt"),       # ⟨َي⟩ coda diphthong retained
])
def test_carrier_and_onset(word, expected):
    assert word_ipa(word) == expected


# ─── Regression guards: geminate glides, final glide vowel, ligatures ─────

@pytest.mark.parametrize("word, expected", [
    ("عُيِّنَ", "ˈʕujjina"),    # geminate yāʾ (glide) — not dropped
    ("قَوَّاس", "qaˈwwaːs"),    # geminate wāw in a coda ligature
    ("اِفْعَوَّل", "iˈfʕawwal"),  # geminate wāw, form IX
])
def test_geminate_glides_not_dropped(word, expected):
    """Shadda geminates the semivowels ي/و too (Wright I §14; Ryding §2.3)."""
    assert word_ipa(word) == expected


# ─── Consonantal glide vs mater lectionis (ConsonantalGlideRescorer) ──────

@pytest.mark.parametrize("word, expected", [
    ("أَتْشِيُوت", "ʔatʃiˈjuːt"),   # ⟨ـِيُو⟩: yāʾ bears its own ḍamma → onset /j/
    ("أَبْخَازِيَا", "ʔaˈbxaːzijaː"),  # ⟨ـِيَا⟩: yāʾ before /aː/ → onset /j/
    ("أَحُوَل", "ˈʔaħuwal"),       # ⟨ـُوَ⟩: wāw before fatḥa → onset /w/
])
def test_prevocalic_glide_is_a_consonant(word, expected):
    """A yāʾ/wāw after its homorganic vowel is length only when it CLOSES
    the syllable; before another vowel it retains its consonantal power
    and is the onset (Wright I §4; Watson 2002 §2.6.1: onsets are
    obligatory, so /i/ + V resolves as i.jV, never *iː.V)."""
    assert word_ipa(word) == expected


@pytest.mark.parametrize("word, expected", [
    ("أَشُورِيّ", "ʔaʃuˈːrijj"),    # nisba ـِيّ = doubled /-ijj/ (Ryding §5.4.1)
    ("أَرْمِيَّة", "ʔaˈrmijja"),    # feminine nisba ـِيَّة = /-ijja/
    ("أُبُوَّة", "ʔuˈbuwwa"),      # ـُوَّة = /-uwwa/: geminate wāw, not /uːwa/
])
def test_geminated_glide_after_homorganic_vowel(word, expected):
    """Shadda doubles the semivowels too (Wright I §14), so ⟨ِي⟩ before the
    yāʾ's geminate copy is /ij/ + /j/ — the nisba suffix -iyy (Ryding,
    Reference Grammar of MSA, §5.4.1) — never the long vowel *iːiː/*iːja."""
    assert word_ipa(word) == expected


def test_word_final_glide_is_a_long_vowel():
    """A word-final ي reads as the long vowel, not the consonant /j/."""
    assert word_ipa("يُصَلِّي") == "juˈsˤɑlliː"


def test_presentation_ligature_never_empty():
    """The lam-alif ligature ﻻ decomposes; output is never empty."""
    assert word_ipa("ﻻ") == "ˈlaː"


def test_medial_semivowel_onset():
    """A medial ⟨وَ⟩ after a consonant is the onset /wa/ (أَبْوَاب → ʔabwaːb)."""
    assert word_ipa("أَبْوَاب") == "ʔaˈbwaːb"


# ─── Deferral of cross-word / lexical cases (no public regression) ───────

from arbtok.lattice import defers_to_cascade  # noqa: E402


@pytest.mark.parametrize("word", [
    "إِيْمَان",     # word-initial إ: waṣl vs qaṭʿ is lexical
    "وَبِاسْمِ",    # proclitic + internal hamzat al-waṣl (cross-word)
    "فَبِالْحَقِّ",  # proclitic + article
    "مَرْحَبًا!",   # trailing punctuation → pausal (utterance-level)
])
def test_lexical_and_crossword_words_defer(word):
    """Words needing cross-word/lexical rules route to the cascade, not the
    word lattice — so the public word path never regresses on them."""
    assert defers_to_cascade(word) is True


@pytest.mark.parametrize("word", [
    "الشَّمْس", "الْقَمَر", "كِتَاب", "يَوْم", "عُيِّنَ", "أَبْوَاب",
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
