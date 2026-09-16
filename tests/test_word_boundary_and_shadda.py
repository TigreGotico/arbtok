"""Two defects that only a phone-level reader can see.

Both were invisible to a character-level check: a doubled length mark is simply
two symbols to a character split, and a deleted word boundary changes no
character at all. They were found by tokenising IPA into phones and counting.
"""
import pytest

from arbtok.plugin import ArbtokG2PPlugin


@pytest.fixture(scope="module")
def msa():
    return ArbtokG2PPlugin(lang="ar")


# ---------------------------------------------------------------------------
# A word boundary survives assimilation
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("text, expected", [
    ("من بعد", "mim ˈbaʕd"),      # iqlāb: n -> m before b
    ("من رب", "mir ˈrabb"),       # idghām into r
    ("من يوم", "mij ˈjawm"),      # idghām into j
    ("من لحمك", "mil laˈħamk"),   # idghām into l
])
def test_assimilation_keeps_the_word_boundary(msa, text, expected):
    """مِن takes the shape of what follows it and stays its own word.

    Four blind substring replacements used to delete the space afterwards, so
    مِن بَعْد came out as the single token *mimbaʕd*. The transcription is read
    per word — by the aligner, whose targets are word-aligned, and by the label
    builder, which pairs five lect tables word by word — so a merged pair cannot
    be sited at all.
    """
    assert msa.transcribe(text) == expected


@pytest.mark.parametrize("text", ["كامل لبن", "عامل لحم", "كامل يوم", "سليم تمر"])
def test_an_ordinary_word_pair_is_never_merged(msa, text):
    """The guard that fails loudest on the old code. Those replacements matched
    on letters rather than on مِن, so any word ending in them was caught:
    كامل لبن ("whole milk") became the single token *kaːˈmillaban*."""
    out = msa.transcribe(text)
    assert len(out.split()) == len(text.split()), out


# ---------------------------------------------------------------------------
# A shadda geminates a consonant; it never doubles a length mark
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("word, expected", [
    ("اسباجتي", "ʔisbaːdʒˈtijj"),   # nisba -iyy
    ("باشتي", "biʃˈtijj"),          # same ending, but reaches the cascade path
    ("قوة", "ˈquwwa"),              # waw geminate
    ("عدو", "ʕaˈduww"),
])
def test_a_shadda_on_a_glide_geminates_the_consonant(msa, word, expected):
    """⟨ـِيّ⟩ is `ijj`. Gemination sits on a consonant, never on vowel length, so
    a shadda proves its letter is consonantal — the mater-lectionis reading must
    not fire first. It used to: the ya gave `ː` and the shadda duplicated it,
    producing `iːː`, a doubled length mark that is not a phone."""
    assert msa.transcribe(word) == expected


@pytest.mark.parametrize("word", ["اسباجتي", "باشتي", "قوة", "عدو", "لانجويني"])
def test_no_doubled_length_mark_is_ever_emitted(msa, word):
    assert "ːː" not in msa.transcribe(word)


def test_a_length_mark_never_lands_on_a_consonant(msa):
    """The other shape the same defect took: `ː` after a consonant, which is
    gemination written as length where this engine writes it as a doubled
    consonant everywhere else."""
    long_vowels = {"aː", "iː", "uː", "eː", "oː", "ɑː", "ɪː", "ʊː"}
    for word in ("اسباجتي", "باشتي", "قوة", "عدو", "حقي", "راعي"):
        ipa = msa.transcribe(word)
        for i, ch in enumerate(ipa):
            if ch == "ː":
                assert i and ipa[i - 1] + ch in long_vowels, (word, ipa)
