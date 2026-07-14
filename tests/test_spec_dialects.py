"""Varieties are read from their orthography2ipa specs, not a zone table.

The word lattice takes a spec code (``ar-SA-x-najd``, ``ar-EG``, …) and builds
its rescorer chain from that spec: arbtok's structural rescorers, then the
rescorer compiled from the spec's own ``allophone_rules``. So a variety's
declared phonology — Najdi affrication and gahawa epenthesis, Hejazi
monophthongization, the qāf reflexes, emphatic spreading — actually fires,
where the five-zone table could only swap consonants and bucketed all of Saudi
into Gulf.
"""
import pytest

from arbtok.dialects import spec_for_lang
from arbtok.lattice import word_ipa
from arbtok.plugin import ArbtokG2PPlugin
from orthography2ipa import WordContext


# ─── the allophone rules of a variety fire ──────────────────────────────

@pytest.mark.parametrize("word,expected,why", [
    # Najdi qāf → /ɡ/ (Ingham 1994).
    ("قَلَم", "ˈɡalam", "qāf → ɡ"),
    # Velar affrication /k/ → [ts] before a front vowel (Ingham 1994 pp.13-14).
    ("كِتَاب", "tsiˈtaːb", "/k/ → [ts] before a front vowel"),
    # Gahawa syndrome: epenthetic /a/ after a guttural in a coda after a low
    # vowel (Ingham 1994 pp.15-16) — gahwa → gahawa.
    ("قَهْوَة", "ˈɡahawa", "gahawa-syndrome epenthesis"),
    ("لَحْم", "ˈlaħam", "gahawa-syndrome epenthesis after ħ"),
])
def test_najdi(word, expected, why):
    assert word_ipa(word, "ar-SA-x-najd") == expected, why


@pytest.mark.parametrize("word,expected,why", [
    ("قَلَم", "ˈɡalam", "qāf → ɡ (Omar 1975)"),
    # Urban Hejazi monophthongization /aj/ → [eː] (Omar 1975; Abdoh 2010).
    ("بَيْت", "ˈbeːt", "/aj/ → [eː]"),
    # Hejazi keeps /k/ — no affrication, unlike Najdi and Gulf.
    ("كِتَاب", "kiˈtaːb", "no velar affrication"),
])
def test_hejazi(word, expected, why):
    assert word_ipa(word, "ar-SA-x-hejaz") == expected, why


def test_saudi_varieties_are_distinct_from_each_other_and_from_gulf():
    """The whole point: Saudi is not one thing, and it is not Gulf.

    Gulf kashkasha affricates /k/ → [tʃ]; Najdi → [ts]; Hejazi keeps /k/. The
    legacy zone table mapped every Saudi tag to GULF, so all three collapsed
    onto the [tʃ] reading.
    """
    assert word_ipa("كِتَاب", "ar-SA-x-najd") == "tsiˈtaːb"
    assert word_ipa("كِتَاب", "ar-SA-x-hejaz") == "kiˈtaːb"
    assert word_ipa("كِتَاب", "ar-x-gulf") == "tʃiˈtaːb"


def test_msa_is_unchanged_by_the_variety_machinery():
    """The default path must not move."""
    assert word_ipa("قَلَم") == "ˈqalam"
    assert word_ipa("كِتَاب") == "kiˈtaːb"
    assert word_ipa("قَهْوَة") == "ˈqahwa"


def test_msa_emphatic_spreading_fires():
    """The ar spec's own AR_EMPH_BACK_* rules reach the lattice.

    Before the spec's allophone rules were compiled into the chain, arbtok
    dropped them silently: /a/ next to an emphatic stayed [a] here while
    orthography2ipa's own G2P produced [ɑ] (Watson 2002, ch. Emphasis).
    """
    assert word_ipa("صَبْر") == "ˈsˤɑbr"
    assert word_ipa("طَالِب") == "ˈtˤɑːlib"


# ─── orthographic readings survive in every variety ─────────────────────

@pytest.mark.parametrize("lang", [
    "ar", "ar-SA-x-najd", "ar-SA-x-hejaz", "ar-x-gulf", "ar-EG", "ar-MA",
])
@pytest.mark.parametrize("word,expected", [
    ("أَمِير", "ʔaˈmiːr"),      # hamza carrier is a bare /ʔ/ before a harakah
    ("مَدْرَسَة", "ˈmadrasa"),   # pausal tāʾ marbūṭa
])
def test_msa_orthography_is_read_correctly_in_every_variety(lang, word, expected):
    """A variety is *written* in MSA orthography, so it must read it.

    These assert the orthography, not the phonology — none of the varieties
    here change these segments, so every one must agree with MSA. (Guards the
    upstream fix that pointed the dialect grapheme layer at `ar` rather than
    Classical `arb`, which carries none of these readings.)
    """
    assert word_ipa(word, lang) == expected


# ─── language-tag resolution ────────────────────────────────────────────

@pytest.mark.parametrize("tag,expected", [
    ("ar-SA-x-najd", "ar-SA-x-najd"),   # exact spec code
    ("ar-sa-x-najd", "ar-SA-x-najd"),   # case-insensitive
    ("ar_SA_x_najd", "ar-SA-x-najd"),   # underscore separators
    ("ar-EG", "ar-EG"),
    ("ar-x-gulf", "ar-x-gulf"),
    ("ar", "ar"),
    ("ar-SA", "ar"),                    # a region with no spec narrows to ar
    ("ar-ZZ", "ar"),                    # unknown region → MSA, never raises
    ("en", "ar"),                       # not Arabic at all → MSA, never raises
    ("", "ar"),
    (None, "ar"),
])
def test_spec_for_lang(tag, expected):
    assert spec_for_lang(tag) == expected


# ─── the plugin surface ─────────────────────────────────────────────────

def test_plugin_lang_selects_the_variety():
    assert ArbtokG2PPlugin(lang="ar-SA-x-najd").transcribe_word("قَهْوَة") == "ˈɡahawa"
    assert ArbtokG2PPlugin(lang="ar-SA-x-hejaz").transcribe_word("بَيْت") == "ˈbeːt"
    assert ArbtokG2PPlugin().transcribe_word("قَهْوَة") == "ˈqahwa"


def test_plugin_context_lang_overrides_the_instance_default():
    plugin = ArbtokG2PPlugin()
    ctx = WordContext(lang="ar-SA-x-najd")
    assert plugin.transcribe_word("كِتَاب", ctx) == "tsiˈtaːb"
    assert plugin.transcribe_word("كِتَاب") == "kiˈtaːb"


@pytest.mark.parametrize("lang", [
    "ar", "arb", "ar-SA-x-najd", "ar-SA-x-hejaz", "ar-x-gulf",
    "ar-x-levantine", "ar-x-maghrebi", "ar-EG",
])
def test_every_variety_transcribes_through_the_cascade_too(lang):
    """The sentence path resolves consonants from the same specs.

    The cascade has no allophone pass yet (that lives in the word lattice), but
    it must at least read each variety's grapheme layer and not raise.
    """
    plugin = ArbtokG2PPlugin(lang=lang)
    assert plugin.transcribe("كِتَاب جَمِيل")


@pytest.mark.xfail(
    reason="A diphthong split across slots (glide onset + coda glide) is not "
           "one segment, so the monophthongization rule cannot see it: يَوْم "
           "tokenizes as يَ|وْ|م = ja|w|m, and the rule targets an /aw/ atom. "
           "بَيْت works because ⟨َي⟩ is a single digraph slot. Needs a "
           "cross-slot rescorer or a spec digraph.",
    strict=True,
)
def test_hejazi_monophthongizes_a_split_diphthong():
    assert word_ipa("يَوْم", "ar-SA-x-hejaz") == "joːm"
