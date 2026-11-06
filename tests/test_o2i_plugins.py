"""arbtok, as steps orthography2ipa can run.

arbtok is an engine built ON orthography2ipa, not a plugin to it. But the pieces
it owns are exactly the steps o2i made pluggable, and there is no reason to keep
them locked inside one package.

Registered, they let plain orthography2ipa transcribe UNDIACRITIZED Arabic — which
it cannot do alone, and by design: its input contract is diacritized text and it
ships no weights.
"""
import pytest

from orthography2ipa import G2P

from arbtok.o2i_plugins import ArbtokSandhi
from arbtok.sandhi import apply_cross_word

ARBTOK = {"normalize": "arbtok", "sandhi": "arbtok"}


# ─── the plugin is NAMED, not merely installed ──────────────────────────

def test_installing_arbtok_does_not_change_what_o2i_says():
    """The safeguard. arbtok is installed in this environment — and o2i still
    reads كتب as a bare skeleton, because nobody asked it not to."""
    assert G2P("ar").transcribe("كتب") == "ˈktb"


def test_naming_it_puts_the_vowels_back():
    """`pip install arbtok` must not silently change what o2i says about Arabic.
    The caller asks, in code, where anyone reading the call site can see that a
    model is putting the vowels in."""
    assert G2P("ar", plugins={"normalize": "arbtok"}).transcribe("كتب") == "ˈkatab"


# ─── cross-word phonology, which no word-level engine can see ───────────

@pytest.mark.parametrize("text,expected,rule", [
    ("مِنْ رَبِّهِمْ", "ˈmir ˈrabbihim", "idghām: n → r"),
    ("مَنْ يَقُولُ", "ˈmaj jaˈquːl", "idghām: n → j"),
    ("مِنْ بَيْتِكَ", "ˈmim ˈbajtik", "iqlāb: n → m before b"),
])
def test_the_sandhi_plugin_assimilates_across_words(text, expected, rule):
    """o2i's SandhiPlugin contract marks the end of input as pausal, so the
    LAST word here also takes its pausal form under arbtok's declared waqf
    policy (Wright I §372): the mood -u of يَقُولُ and the suffix vowel -a of
    بَيْتِكَ are dropped at the pause. The assimilation under test is
    unaffected."""
    assert G2P("ar", plugins=ARBTOK).transcribe(text) == expected, rule


@pytest.mark.parametrize("text,expected,why", [
    ("قَلَمٌ", "ˈqalam", "the pause removes the case ending"),
    ("مَدِينَةٌ", "maˈdiːna", "…and takes the tāʾ with it — it was only voiced by the ending"),
    ("كِتَابًا", "kiˈtaːbaː", "tanwīn al-fatḥ lengthens rather than vanishing"),
    ("مُؤْمِن", "ˈmuʔmin", "-in here is the WORD, not an ending"),
])
def test_the_pause_removes_only_a_case_ending(text, expected, why):
    """orthography2ipa strips punctuation during word splitting, so the plugin is
    TOLD where the pause is. It could not find it otherwise."""
    assert G2P("ar", plugins=ARBTOK).transcribe(text) == expected, why


def test_the_stress_mark_survives_sandhi():
    """o2i places stress per word BEFORE sandhi runs, so the plugin sees `ˈmin`,
    not `min` — and the mark sits INSIDE the word, so it has to go back where it
    was rather than on the front."""
    assert G2P("ar", plugins=ARBTOK).transcribe("مَدِينَةٌ") == "maˈdiːna"


@pytest.mark.parametrize("text,expected", [
    ("قَلَمٌ، كِتَابٌ.", "ˈqalam kiˈtaːb"),
    ("مِنْ رَبِّهِمْ، مِنْ بَيْتِكَ", "ˈmir ˈrabbihim ˈmim ˈbajtik"),
])
def test_a_pause_inside_the_sentence(text, expected):
    """Each clause reads as it reads alone, in the rows above."""
    assert G2P("ar", plugins=ARBTOK).transcribe(text) == expected


def test_the_plugin_returns_what_apply_cross_word_returns():
    words = ["qalamun", "kitaːbun", "waladun"]
    surfaces = ["قَلَمٌ", "كِتَابٌ", "وَلَدٌ"]
    rows = [(words[0], surfaces[0], False), ("", "", True),
            (words[1], surfaces[1], False), ("", "", True),
            (words[2], surfaces[2], False)]

    assert ArbtokSandhi().apply(words, surfaces, [True, True, False], "ar") \
        == apply_cross_word(rows, lang="ar")


# ─── and a variety's own phonology still fires ──────────────────────────

def test_a_variety_keeps_its_own_phonology():
    """Najdi's gahawa epenthesis, through plain o2i."""
    assert G2P("ar-SA-x-najd", plugins=ARBTOK).transcribe("قَهْوَة") == "ˈɡahawa"


# ─── the same steps as one Pipeline ─────────────────────────────────────

from orthography2ipa import Pipeline  # noqa: E402

from arbtok.o2i_plugins import _keep_letters, pipeline  # noqa: E402


def test_pipeline_puts_the_vowels_back():
    assert G2P("ar", pipeline=pipeline("ar")).transcribe("كتب") == "ˈkatab"


def test_pipeline_holds_every_arbtok_step():
    p = pipeline("ar")
    assert isinstance(p, Pipeline)
    assert p.expand is not None and p.mark is not None
    assert p.rescore and isinstance(p.sandhi, ArbtokSandhi)


@pytest.mark.parametrize("original, proposed, expected", [
    ("كتب", "كَتَبَ", "كَتَبَ"),             # marks only
    ("اكل", "أَكَلَ", "أَكَلَ"),             # a hamza on the written alif is a mark
    ("مدرسه", "مَدْرَسَة", "مَدْرَسَه"),     # ة for ه swaps a letter: the written one returns
    ("علي", "عَلَى", "عَلَي"),               # ى for ي, the same
    ("كتاب", "كتب", "كتاب"),                 # letters that do not align: the word stays as written
])
def test_keep_letters(original, proposed, expected):
    assert _keep_letters(original, proposed) == expected


def test_pipeline_mark_keeps_the_written_letters(monkeypatch):
    """A diacritizer that swaps ⟨ه⟩ for ⟨ة⟩ would make orthography2ipa raise. The
    pipeline puts the written letter back, so the sentence reads as its marked
    form with ⟨ه⟩."""
    from arbtok.o2i_plugins import ArbtokDiacritizer

    monkeypatch.setattr(ArbtokDiacritizer, "normalize",
                        lambda self, text, lang: "هَذِهِ مَدْرَسَةٌ")
    assert (G2P("ar", pipeline=pipeline("ar")).transcribe("هذه مدرسه")
            == G2P("ar", pipeline=Pipeline(sandhi=ArbtokSandhi(), rescore=pipeline("ar").rescore,
                                           expand=pipeline("ar").expand)).transcribe("هَذِهِ مَدْرَسَهٌ"))
