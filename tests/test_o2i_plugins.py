"""arbtok, as steps orthography2ipa can run.

arbtok is an engine built ON orthography2ipa, not a plugin to it. But the pieces
it owns are exactly the steps o2i made pluggable, and there is no reason to keep
them locked inside one package.

Passed in a Pipeline, they let plain orthography2ipa transcribe UNDIACRITIZED
Arabic — which it cannot do alone, and by design: its input contract is diacritized
text and it ships no weights.

The expected strings are what the named entry points
(``plugins={"normalize": "arbtok", "sandhi": "arbtok"}``) give for the same input.
"""
import subprocess
import sys

import pytest

from orthography2ipa import G2P, Pipeline, who_answers

from arbtok.o2i_plugins import ArbtokSandhi, _keep_letters, pipeline
from arbtok.sandhi import apply_cross_word


# ─── the steps are PASSED, not merely installed ─────────────────────────

def test_installing_arbtok_does_not_change_what_o2i_says():
    """The safeguard. arbtok is installed in this environment — and o2i still
    reads كتب as a bare skeleton, because nobody asked it not to."""
    assert G2P("ar").transcribe("كتب") == "ˈktb"


def test_passing_the_pipeline_puts_the_vowels_back():
    """`pip install arbtok` must not silently change what o2i says about Arabic.
    The caller asks, in code, where anyone reading the call site can see that a
    model is putting the vowels in."""
    assert G2P("ar", pipeline=pipeline("ar")).transcribe("كتب") == "ˈkatab"


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
    assert G2P("ar", pipeline=pipeline("ar")).transcribe(text) == expected, rule


@pytest.mark.parametrize("text,expected,why", [
    ("قَلَمٌ", "ˈqalam", "the pause removes the case ending"),
    ("مَدِينَةٌ", "maˈdiːna", "…and takes the tāʾ with it — it was only voiced by the ending"),
    ("كِتَابًا", "kiˈtaːbaː", "tanwīn al-fatḥ lengthens rather than vanishing"),
    ("مُؤْمِن", "ˈmuʔmin", "-in here is the WORD, not an ending"),
])
def test_the_pause_removes_only_a_case_ending(text, expected, why):
    """orthography2ipa strips punctuation during word splitting, so the plugin is
    TOLD where the pause is. It could not find it otherwise."""
    assert G2P("ar", pipeline=pipeline("ar")).transcribe(text) == expected, why


def test_the_stress_mark_survives_sandhi():
    """o2i places stress per word BEFORE sandhi runs, so the plugin sees `ˈmin`,
    not `min` — and the mark sits INSIDE the word, so it has to go back where it
    was rather than on the front."""
    assert G2P("ar", pipeline=pipeline("ar")).transcribe("مَدِينَةٌ") == "maˈdiːna"


@pytest.mark.parametrize("text,expected", [
    ("قَلَمٌ، كِتَابٌ.", "ˈqalam kiˈtaːb"),
    ("مِنْ رَبِّهِمْ، مِنْ بَيْتِكَ", "ˈmir ˈrabbihim ˈmim ˈbajtik"),
])
def test_a_pause_inside_the_sentence(text, expected):
    """Each clause reads as it reads alone, in the rows above."""
    assert G2P("ar", pipeline=pipeline("ar")).transcribe(text) == expected


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
    lect = "ar-SA-x-najd"
    assert G2P(lect, pipeline=pipeline(lect)).transcribe("قَهْوَة") == "ˈɡahawa"


# ─── the steps as one Pipeline ──────────────────────────────────────────

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


# ─── the named entry points, until orthography2ipa 8.0.0 ────────────────

def test_the_entry_points_still_answer_plugins():
    """``plugins=`` warns and still runs arbtok until orthography2ipa 8.0.0, and the
    resolver checks no base class."""
    with pytest.warns(DeprecationWarning, match="plugins="):
        g2p = G2P("ar", plugins={"normalize": "arbtok", "sandhi": "arbtok"})
    assert g2p.transcribe("كتب") == "ˈkatab"
    assert who_answers("ar")["rescore"] == [
        "arbtok.o2i_plugins.ArbtokRescorers (priority 50)"]


def test_the_steps_run_without_the_stage_base_classes():
    """orthography2ipa 8.0.0 removes ``NormalizePlugin`` and ``RescorerPlugin``.
    With both names gone, the module imports and its pipeline transcribes."""
    code = (
        "import orthography2ipa.plugins as p, orthography2ipa.rescorer_plugin as r\n"
        "del p.NormalizePlugin, r.RescorerPlugin\n"
        "from orthography2ipa import G2P\n"
        "from arbtok.o2i_plugins import pipeline\n"
        "print(G2P('ar', pipeline=pipeline('ar')).transcribe('كتب'))\n"
    )
    run = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert run.returncode == 0, run.stderr
    assert run.stdout.strip() == "ˈkatab"
