"""Vocalized-input parity with the orthography2ipa spec engine.

arbtok is built ON orthography2ipa: on author-vocalized input its reading of a
word must match what the variety's own spec produces, or the two drift word by
word (dialect gold: arbtok trailed raw o2i on every Levantine/Gulf/Maghrebi
lect until the divergences below were closed). Each test class here pins one
divergence class at the layer that owned it:

- the spec's inline ``word_exceptions`` were never consulted;
- ``ConsonantalGlideRescorer`` consonantized a glide before an *empty* slot
  (a sukūn — vacuous ``"" in vowels``) and before a bare mater glide;
- ``SunLetterRescorer`` invented sun assimilation the page did not write;
- ``defers_to_cascade`` peeled a shadda-bearing letter as a clitic;
- the diacritizer re-vocalized author-(near-)complete words, overruling the
  writing with a register guess;
- IPA-level waqf and nūn-assimilation (iʿrāb facts) fired on dialect lects
  that have no iʿrāb;
- ``waqf`` lengthened tanwīn al-fatḥ on a tāʾ marbūṭa, which has no carrying
  alif to lengthen.
"""
import pytest

from arbtok.diacritize import _author_complete, _proclitic_complete
from arbtok.lattice import defers_to_cascade, spec_word_exception, word_ipa
from arbtok.plugin import ArbtokG2PPlugin
from arbtok.tokenizer import Sentence
from arbtok.waqf import pausal


# ─── spec word_exceptions are consulted ─────────────────────────────────

# (lect, word, spec-exception IPA): lexical forms the variety's own rules
# cannot derive, recorded inline in the o2i spec. The lattice path must read
# them exactly as orthography2ipa's engine does.
EXCEPTION_CASES = [
    ("ar-LB", "مَا", "maː"),            # imāla-immune negator (cowell1964)
    ("ar-LB", "هَيْدَا", "hajda"),      # demonstrative keeps /aj/
    ("ar-LB", "بُكْرَا", "bukra"),      # final vowel short
    ("ar-AE", "عِيش", "ʕeːʃ"),          # lexical /eː/ (szreder_derrick2023)
    ("ar-AE", "لَو", "law"),            # conditional keeps /aw/
    ("ar-IQ-x-qeltu", "بَاكِر", "baːkiʁ"),  # qeltu uvular r (blanc1964)
]


@pytest.mark.parametrize("lect, word, expected", EXCEPTION_CASES)
def test_spec_word_exception_lookup(lect, word, expected):
    assert spec_word_exception(word, lect) == expected


@pytest.mark.parametrize("lect, word, expected", EXCEPTION_CASES)
def test_word_ipa_honours_spec_exceptions(lect, word, expected):
    assert word_ipa(word, lect, stress=False) == expected


def test_exception_key_matches_shadda_spelling():
    """o2i keys exceptions on its tokenizer's shadda-EXPANDED form
    (التِّلِيفُون is stored as التتِلِيفُون); the shadda spelling must hit."""
    assert spec_word_exception("التِّلِيفُون", "ar-MR") is not None


# ─── glide rescorer: sukūn and bare-mater neighbours ─────────────────────

def test_kasra_ya_sukun_is_long_vowel():
    """⟨ِيْ⟩ is the mater /iː/, not /ij/: the following sukūn slot renders
    nothing, and an empty rendering proves no vowel onset (the vacuous
    ``\"\" in vowels`` read it as one)."""
    assert word_ipa("كِيْف", "ar-LB", stress=False) == "kiːf"


def test_mater_before_bare_waw_is_hiatus():
    """Maghrebi 1pl ⟨ـِيو⟩ is /iːuː/ in the spec's own reading — a bare mater
    wāw is vowel length, not an onset that forces /ij/."""
    assert word_ipa("نْمْشِيو", "ar-x-maghrebi", stress=False) == "nmʃiːuː"


def test_nisba_geminate_still_consonantal():
    """The shadda copy after ⟨ِي⟩ stays consonantal: the nisba ends /ijj/."""
    assert word_ipa("عَرَبِيّ", "ar", stress=False).endswith("ijj")


# ─── article without written gemination ──────────────────────────────────

def test_vocalized_word_keeps_unassimilated_article():
    """An author who pointed the stem but wrote no shadda on the sun letter
    means it: Maghrebi الصْبَاح is /alsˤbaːħ/ (o2i's reading), not an invented
    assimilation."""
    assert word_ipa("الصْبَاح", "ar-x-maghrebi", stress=False) == "alsˤbaːħ"


@pytest.mark.parametrize("word", ["اللِي", "الّي"])
def test_article_plus_lam_is_geminate(word):
    """The relative — two lāms written out, or one lām + shadda that the
    gemination expansion rewrites to two — reads /all-/, never /al-/ with the
    geminate swallowed."""
    assert word_ipa(word, "ar-KW", stress=False).startswith("all")


def test_bare_word_still_assimilates():
    """A word with no marks at all omits the assimilating shadda with them;
    the classical letter-class rule still applies to bare text."""
    assert word_ipa("السوق", "ar", stress=False).startswith("as")


# ─── defers_to_cascade: shadda is not a clitic ───────────────────────────

def test_shadda_bearing_letter_is_not_peeled_as_clitic():
    """لِسَّا is one word (li-ssa), not لِ + a waṣl-alif stem: it stays on the
    spec lattice, where ar-LB's imāla gives /lisseː/."""
    assert not defers_to_cascade("لِسَّا")
    assert word_ipa("لِسَّا", "ar-LB", stress=False) == "lisseː"


# ─── author-complete input outranks the diacritizer ──────────────────────

def test_bare_proclitic_on_marked_stem_is_complete():
    """Everything marked but a bare leading و: the author wrote the clitic the
    dialect's way (/w/, o2i's reading) and the model may not add a fatḥa."""
    assert _proclitic_complete("وكَان", [0])


def test_two_letter_word_is_not_a_proclitic_case():
    """A two-letter word may BE a closed-class lexicon entry (كي): it is not
    read as clitic + one-letter stem."""
    assert not _proclitic_complete("كي", [0])


def test_fully_bare_word_is_not_complete():
    """A word with several silent positions is the model's to vocalize."""
    assert not _author_complete("وكان", [0, 2, 3])
    assert not _proclitic_complete("وكان", [0, 2, 3])


def test_e2e_bare_waw_reads_as_cluster():
    """End to end: vocalized dialect text with a bare conjunction و keeps the
    cluster reading — /wkaːn/, not /wakaːn/ (matches raw orthography2ipa)."""
    plug = ArbtokG2PPlugin(lang="ar-KW", diacritize=True)
    out = plug.transcribe("وكَان زَين")
    assert out.split()[0].lstrip("ˈ") == "wkaːn"


# ─── iʿrāb rules are reference-register facts ────────────────────────────

def test_dialect_keeps_lexical_final_vowel_at_pause():
    """Maghrebi مْعَايَ /mʕaːja/: the final fatḥa is lexical (no iʿrāb exists
    to drop), so the IPA-level pause must not eat it."""
    ipa = Sentence("شْكُون مْعَايَ؟", lang="ar-x-maghrebi", stress=False).ipa
    assert ipa.split()[-1] == "mʕaːja"


def test_dialect_keeps_lexicalized_tanwin_adverb():
    """أَهْلًا وَسَهْلًا in a dialect is the lexical greeting /ahlan wasahlan/;
    tanwīn lengthening is a Classical pause rule, not a dialect one."""
    ipa = Sentence("أَهْلًا وَسَهْلًا.", lang="ar-SD", stress=False).ipa
    assert ipa.endswith("sahlan")


def test_msa_pausal_tanwin_still_lengthens():
    """The reference register keeps Wright I §372: written -an at a pause
    lengthens on its alif."""
    ipa = Sentence("رَأَيْتُ كِتَابًا.", lang="ar", stress=False).ipa
    assert ipa.endswith("kitaːbaː")


def test_dialect_min_keeps_its_nun():
    """idghām/iqlāb of مِن's /n/ is recitation sandhi; the dialect gold reads
    *min baʕd*, not *mim baʕd*."""
    ipa = Sentence("مِنْ بَعْد دُور", lang="ar-MR", stress=False).ipa
    assert ipa.startswith("min ")


# ─── waqf: tanwīn al-fatḥ on tāʾ marbūṭa ─────────────────────────────────

def test_pausal_tanwin_fath_on_ta_marbuta_drops():
    """مَدِينَةً at a pause is *madīna*: the tāʾ marbūṭa has no carrying alif,
    so nothing lengthens — degrading the mark to a fatḥa would voice the tāʾ
    (*madīnata*), a form no register produces (Wright I §372)."""
    assert pausal("مَدِينَةً") == "مَدِينَة"


def test_pausal_tanwin_fath_on_alif_still_lengthens():
    """The alif-carried case is untouched: كِتَابًا degrades to كِتَابَا."""
    assert pausal("كِتَابًا") == "كِتَابَا"


# ─── the register switch ─────────────────────────────────────────────────

def test_register_pausal_is_the_default():
    assert ArbtokG2PPlugin(lang="ar").pausal is True


def test_register_full_disables_waqf():
    plug = ArbtokG2PPlugin(lang="ar", register="full")
    assert plug.pausal is False
    # Full iʿrāb passthrough: the written case ending is read out.
    assert plug.transcribe("رَأَيْتُ كِتَابًا.").endswith("kiˈtaːban")


def test_register_rejects_unknown_value():
    with pytest.raises(ValueError):
        ArbtokG2PPlugin(lang="ar", register="quranic")


def test_explicit_pausal_argument_wins_over_register():
    assert ArbtokG2PPlugin(lang="ar", register="full", pausal=True).pausal is True
