"""Where the stress falls, asserted precisely.

arbtok's reference gold is a segment gold — it carries no stress marks — so
stress is tested here rather than smeared across 140 gold entries. That keeps
both honest: the gold measures phonemes, and this measures prosody.

Arabic stress is quantity-sensitive: it lands on a syllable because that syllable
is *heavy*, and weight is a property of the transcription, not the spelling. So it
can only be placed once the IPA exists, which is why arbtok — driving the
orthography2ipa tokenizer directly — did not emit it at all until now.
"""
import pytest

from arbtok.lattice import word_ipa
from arbtok.plugin import ArbtokG2PPlugin
from arbtok.stress import stress_ipa, stress_words
from arbtok.tokenizer import Sentence


# ─── the cascade (Ryding 2005 §2.3; Watson 2002 ch.3) ───────────────────

@pytest.mark.parametrize("word,expected,why", [
    ("كِتَاب", "kiˈtaːb", "superheavy final CVːC takes it"),
    ("مُدَرِّس", "muˈdarris", "otherwise a heavy penult CVC"),
    ("مَدْرَسَة", "ˈmadrasa", "otherwise the antepenult"),
    ("كَتَبَ", "ˈkataba", "all light → antepenult"),
    ("قَهْوَة", "ˈqahwa", "two syllables, heavy penult"),
])
def test_the_weight_cascade(word, expected, why):
    assert word_ipa(word) == expected, why


# ─── it is read off the IPA, so a variety's phonology feeds it ──────────

def test_a_varietys_own_reflexes_are_stressed():
    """Najdi affricates and epenthesizes; the stress lands on the result."""
    assert word_ipa("كِتَاب", "ar-SA-x-najd") == "tsiˈtaːb"
    assert word_ipa("قَهْوَة", "ar-SA-x-najd") == "ˈɡahawa"


# ─── one phonological word, one primary stress ──────────────────────────

def test_each_word_of_an_utterance_is_stressed():
    assert ArbtokG2PPlugin().transcribe("كِتَاب جَمِيل") == "kiˈtaːb dʒaˈmiːl"


def test_a_proclitic_and_its_host_share_one_stress():
    """Connected speech joins them into one unit, and one unit takes one mark."""
    out = ArbtokG2PPlugin().transcribe("فِي الْبَيْتِ")
    assert out.count("ˈ") == 2  # fiː + the clitic-joined article+noun


def test_punctuation_is_not_a_word():
    """It has no syllable to stress. Marking it leaves a mark floating."""
    out = Sentence("مَرْحَبًا!").ipa
    assert "!" in out
    assert not out.endswith("ˈ")
    assert out.replace(" !", "") == "ˈmarħabaː"  # utterance-final: tanwīn al-fatḥ lengthens


# ─── it can be turned off ───────────────────────────────────────────────

def test_stress_can_be_turned_off():
    """A consumer scoring against stress-free gold needs the segments alone."""
    assert word_ipa("كِتَاب", stress=False) == "kitaːb"
    assert ArbtokG2PPlugin(stress=False).transcribe("كِتَاب جَمِيل") == "kitaːb dʒamiːl"


def test_the_word_and_sentence_paths_agree():
    """A word transcribed alone and in an utterance must be stressed the same.

    They are different engines — the word lattice and the sentence cascade — and
    an inconsistency here is exactly the kind of thing that silently ships.
    """
    assert ArbtokG2PPlugin().transcribe("كِتَاب") == word_ipa("كِتَاب")


# ─── the helpers ────────────────────────────────────────────────────────

def test_stress_ipa_needs_a_vowel():
    assert stress_ipa("") == ""
    assert stress_ipa("!") == "!"
    assert stress_ipa("kitaːb") == "kiˈtaːb"


def test_stress_words_marks_each_word():
    assert stress_words("kitaːb dʒamiːl") == "kiˈtaːb dʒaˈmiːl"
