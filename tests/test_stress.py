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
    """Connected speech joins a proclitic to its host into one unit, and one unit
    takes one mark. فِي is a cliticless preposition (unstressed, per the ar spec's
    ``stress.cliticless_words``; Watson 2002 ch.3) and the definite article is
    proclitic, so the host noun carries the phrase's only stress."""
    out = ArbtokG2PPlugin().transcribe("فِي الْبَيْتِ")
    assert out == "fiː lˈbajti"
    assert out.count("ˈ") == 1  # فِي unstressed; بيت + proclitic article share one


def test_punctuation_is_not_a_word():
    """It has no syllable to stress and no phonology, so it does not survive into
    the IPA — orthography2ipa emits none either. It is still read as a *pause*,
    which is why the tanwīn al-fatḥ here lengthens (utterance-final waqf)."""
    out = Sentence("مَرْحَبًا!").ipa
    assert "!" not in out
    assert not out.endswith("ˈ")
    assert out == "ˈmarħabaː"  # utterance-final: tanwīn al-fatḥ lengthens


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


# ─── cross-word phonology (arbtok.sandhi) ───────────────────────────────

@pytest.mark.parametrize("text,expected,rule", [
    ("مِنْ رَبِّهِمْ", "mir rabbihim", "idghām: n → r"),
    ("مَنْ يَقُولُ", "maj jaquːlu", "idghām: n → j"),
    ("مِنْ بَيْتِكَ", "mim bajtika", "iqlāb: n → m before b"),
])
def test_nun_assimilates_to_what_follows(text, expected, rule):
    """A final /n/ is written, and it is not pronounced — it takes the shape of
    the next word's onset. No word-level engine can see this."""
    from arbtok.plugin import ArbtokG2PPlugin
    assert ArbtokG2PPlugin(stress=False).transcribe(text) == expected, rule


@pytest.mark.parametrize("text,expected,why", [
    ("قَلَمٌ", "qalamun", "no pause is written, so the ending stands"),
    ("مَدِينَةٌ.", "madiːna", "at a pause the tanwīn goes, and the tāʾ with it"),
    ("قَهْوَةً.", "qahwa", "the tāʾ was only voiced by the ending that just left"),
    ("كِتَابًا.", "kitaːbaː", "tanwīn al-fatḥ lengthens rather than vanishing"),
    ("مُؤْمِن", "muʔmin", "-in here is the WORD, not a case ending"),
    ("مِنْ لَبَن", "millaban", "…and so is the -an of laban"),
])
def test_the_pause_removes_only_a_case_ending(text, expected, why):
    """Driven by the spelling. A tanwīn is written; guessing it from the last two
    characters of the IPA confuses an ending with a stem and eats the word."""
    from arbtok.plugin import ArbtokG2PPlugin
    assert ArbtokG2PPlugin(stress=False).transcribe(text) == expected, why


def test_a_word_and_a_sentence_agree_on_a_varietys_phonology():
    """The gahawa epenthesis fired in the word lattice and not in the cascade, so
    the same word had two transcriptions depending on how you asked for it."""
    from arbtok.plugin import ArbtokG2PPlugin
    p = ArbtokG2PPlugin(lang="ar-SA-x-najd", stress=False)
    assert p.transcribe_word("قَهْوَة") == "ɡahawa"
    assert p.transcribe("قَهْوَة") == "ɡahawa"
    assert p.transcribe("أُرِيدُ قَهْوَة").endswith("ɡahawa")
