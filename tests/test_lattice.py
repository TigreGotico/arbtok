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
    GeminationRescorer,
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
    ("الشَّمْس", "aʃʃams", "ش shīn"),
    ("السَّمَك", "assamak", "س sīn"),
    ("التَّاج", "attaːdʒ", "ت tāʾ"),
    ("الثَّوْب", "aθθawb", "ث thāʾ"),
    ("الذَّهَب", "aððahab", "ذ dhāl"),
    ("الرَّجُل", "arradʒul", "ر rāʾ"),
    ("الزَّيْت", "azzajt", "ز zāy"),
    ("الطَّعَام", "atˤtˤaʕaːm", "ط ṭāʾ"),
    ("الظَّبْي", "aðˤðˤabj", "ظ ẓāʾ"),
    ("اللَّوْن", "allawn", "ل lām"),
    ("النَّار", "annaːr", "ن nūn"),
    ("الصَّوْت", "asˤsˤawt", "ص ṣād"),
    ("الدَّار", "addaːr", "د dāl"),
    ("الضَّوْء", "adˤdˤawʔ", "ض ḍād"),
]


@pytest.mark.parametrize("word, expected, name", SUN_CASES)
def test_sun_letter_assimilation(word, expected, name):
    """Every one of the 14 coronal sun letters assimilates the article lām."""
    assert word_ipa(word) == expected, name


# Moon letters keep the lām (control: no assimilation).
MOON_CASES = [
    ("الْقَمَر", "alqamar", "ق qāf"),
    ("الْكِتَاب", "alkitaːb", "ك kāf"),
    ("الْمَسْجِد", "almasdʒid", "م mīm"),
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
    ("اِسْتِقْبَال", "istiqbaːl"),
    ("اِجْتِمَاع", "idʒtimaːʕ"),
    ("اِعْتِمَاد", "iʕtimaːd"),
    ("اِنْقَطَع", "inqatˤaʕ"),
])
def test_hamzat_al_wasl_elision(word, expected):
    """Word-initial hamzat al-waṣl is silent; the harakah carries the vowel."""
    assert word_ipa(word) == expected


# ─── Gemination (shadda / tashdīd) ───────────────────────────────────────

@pytest.mark.parametrize("word, expected", [
    ("عَمَّ", "ʕamma"),
    ("كُلّ", "kull"),
    ("ظَلَّ", "ðˤalla"),
    ("حَتَّى", "ħattaː"),
])
def test_gemination(word, expected):
    """Shadda doubles its consonant before the nucleus (not a length mark)."""
    assert word_ipa(word) == expected


# ─── Hamza carrier vowel de-duplication & semivowel onset ────────────────

@pytest.mark.parametrize("word, expected", [
    ("أَمِير", "ʔamiːr"),   # hamza carrier + explicit fatḥa, not ʔaamīr
    ("تَأْثِير", "taʔθiːr"),  # carrier + sukūn
    ("يَوْم", "jawm"),       # ⟨يَ⟩ onset /ja/, not the /aj/ coda diphthong
    ("بَيْت", "bajt"),       # ⟨َي⟩ coda diphthong retained
])
def test_carrier_and_onset(word, expected):
    assert word_ipa(word) == expected


def test_rescorers_are_pure_no_ops_off_target():
    """Each flagship rescorer leaves an unrelated word byte-identical."""
    base = PhonetokTokenizer(get("ar")).ipa_lattice("قَلَم")
    base_ipa = "".join(s.top.ipa for s in base)
    for rescorer in (GeminationRescorer(), SunLetterRescorer(), WaslRescorer()):
        got = PhonetokTokenizer(get("ar")).ipa_lattice(
            "قَلَم", rescorer=[rescorer])
        assert "".join(s.top.ipa for s in got) == base_ipa
