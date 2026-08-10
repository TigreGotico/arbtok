"""The hundreds, and the alif that is written but not said.

⟨مائة⟩ "hundred" is spelled with an alif that no one pronounces: the word is
/miʔa/, not */miaːʔa/. The spelling is a survival of an old scribal convention
that kept the alif to keep ⟨مائة⟩ apart from ⟨منه⟩ in unpointed script, and
both spellings — the etymological ⟨مائة⟩ and the phonetic ⟨مئة⟩ — are in
current use for the same word.

  - Wright, *A Grammar of the Arabic Language*, 3rd ed., I §319 (the numerals
    100–900 and the writing of مائة).
  - Ryding, *A Reference Grammar of Modern Standard Arabic*, CUP 2005, §15.3.
  - https://en.wikipedia.org/wiki/Arabic_numerals#Arabic_numeral_words
  - https://ar.wiktionary.org/wiki/مائة

arbtok used to know this for the bare word only, through a whole-word entry in
``WORD_EXCEPTIONS``. Every word that *contains* the morpheme — the fused
hundreds ⟨ثلاثمائة⟩ … ⟨تسعمائة⟩, the dual ⟨مائتان⟩, and ⟨بالمائة⟩ "percent" —
missed that entry, fell through to the lattice, and read the silent alif as a
long /aː/: ⟨ثَلَاثُمِائَة⟩ came out *θalaːθuˈmiaːʔa*. That is what a TTS voice
then says.

The rule is orthographic, so it is fixed orthographically (see
:func:`arbtok.tokenizer.elide_silent_alif`): the two spellings are made to
transcribe identically, everywhere the morpheme appears. The tests below are
written as that equality plus the exact string, so neither half can drift.

The alif of ⟨مَائِدَة⟩ "table" is a real alif and must survive — it is the
regression guard on the rule being too greedy.
"""
import os
import re

import pytest

from arbtok.tokenizer import Sentence, normalize_unicode


def ipa(text: str) -> str:
    return Sentence(text).ipa


# ─── the fused hundreds: ⟨…مائة⟩ must read exactly like ⟨…مئة⟩ ────────────
# key: (alif spelling, phonetic spelling, expected IPA)
FUSED_HUNDREDS = [
    ("ثَلَاثُمِائَة", "ثَلَاثُمِئَة", "θalaːˈθumiʔa"),      # 300
    ("أَرْبَعُمِائَة", "أَرْبَعُمِئَة", "ʔarbaˈʕumiʔa"),     # 400
    ("خَمْسُمِائَة", "خَمْسُمِئَة", "xamˈsumiʔa"),          # 500
    ("سِتُّمِائَة", "سِتُّمِئَة", "sitˈtumiʔa"),             # 600
    ("سَبْعُمِائَة", "سَبْعُمِئَة", "sabˈʕumiʔa"),          # 700
    ("ثَمَانُمِائَة", "ثَمَانُمِئَة", "θamaːˈnumiʔa"),      # 800
    ("تِسْعُمِائَة", "تِسْعُمِئَة", "tisˈʕumiʔa"),          # 900
]


@pytest.mark.parametrize("alif,phonetic,expected", FUSED_HUNDREDS)
def test_fused_hundred_alif_spelling(alif, phonetic, expected):
    assert ipa(alif) == expected


@pytest.mark.parametrize("alif,phonetic,expected", FUSED_HUNDREDS)
def test_fused_hundred_phonetic_spelling(phonetic, alif, expected):
    assert ipa(phonetic) == expected


# ─── the base word and the words built on it ──────────────────────────────
@pytest.mark.parametrize("word,expected", [
    ("مِائَة", "ˈmiʔa"),            # 100, etymological spelling
    ("مِئَة", "ˈmiʔa"),             # 100, phonetic spelling
    ("مِائَتَان", "miʔaˈtaːn"),      # 200, nominative dual
    ("مِئَتَان", "miʔaˈtaːn"),
    ("مِائَتَيْن", "miʔaˈtajn"),      # 200, oblique dual
    ("مِئَتَيْن", "miʔaˈtajn"),
    ("بِالْمِائَة", "ˈbilmiʔa"),      # "per cent"
    ("بِالْمِئَة", "ˈbilmiʔa"),
])
def test_hundred_base_forms(word, expected):
    assert ipa(word) == expected


# ─── the alif that IS pronounced must not be touched ──────────────────────
@pytest.mark.parametrize("word,expected", [
    ("مَائِدَة", "ˈmaːʔida"),    # "table" — a real, pronounced alif
    ("هَيْئَة", "ˈhajʔa"),        # hamza on yāʾ, no alif in sight
])
def test_real_alif_survives(word, expected):
    assert ipa(word) == expected


# ─── the near-miss: ⟨مائت⟩ "dying/mortal" is not ⟨مائة⟩ ───────────────────
# ⟨مائت⟩ (active participle of ماتَ يموتُ "to die") is spelled مīm + alif +
# hamza-on-yāʾ + tāʾ — exactly the shape the ⟨مائة⟩ rule looks for, up to the
# tāʾ. The discriminator is what comes AFTER that tāʾ: the hundreds paradigm
# always carries it into a long vowel (the dual -ā-, the oblique -ay-, Wright
# I §319); the participle's tāʾ ends the word, or takes a short-vowel
# inflection of its own (⟨مائتة⟩ fem., ⟨مائتون⟩ masc. pl.), never a following
# long vowel on that same tāʾ. Values pinned from origin/dev (unaffected by
# this bug, since dev predates ``elide_silent_alif`` entirely).
@pytest.mark.parametrize("word,expected", [
    ("مَائِت", "ˈmaːʔit"),          # "dying/mortal" (masc. sg.)
    ("ٱلْمَائِت", "alˈmaːʔit"),      # "the dying/mortal"
    ("بِمَائِت", "biˈmaːʔit"),       # "with a dying/mortal (one)"
    ("مَائِتَة", "ˈmaːʔita"),        # "dying/mortal" (fem. sg.)
    ("مَائِتُونَ", "maːʔiˈtuːna"),   # "dying/mortal" (masc. pl.)
])
def test_dying_participle_alif_survives(word, expected):
    assert ipa(word) == expected


# ─── the other near-miss: tanwīn on the tāʾ is never a hundred ────────────
# ⟨مائتًا⟩ is the participle's indefinite accusative — tāʾ + tanwīn fatḥ +
# the bare alif that spells /-an/ — and superficially matches the pattern's
# skip-then-long-vowel shape (something, then an alif, after the tāʾ). But a
# hundred's tāʾ is never indefinite: it is always either the tāʾ marbūṭa of
# the bare/construct form or the plain tāʾ of the dual, never a tāʾ carrying
# its own tanwīn. Excluding tanwīn from the diacritics the lookahead skips
# over is what keeps this word out.
def test_tanwin_on_mait_tanwin_not_collapsed():
    word = "مائتًا"
    assert normalize_unicode(word) == word, (
        f"{word}: normalize_unicode collapsed the tanwīn-bearing تًا of the "
        "مائت participle as if it were a hundred's تا"
    )


# ─── sweep: every ⟨مائت⟩-family form in the CER gold set keeps its alif ───
# tests/ar_test.txt scores an aggregate CER, which hid this defect: the
# regex that collapses ⟨مائة⟩'s silent alif used to match ⟨مائت⟩ too, on
# undiacritized input where no kasra separates the hamza from the tāʾ, and
# silently ate the vowel (⟨بمائت⟩ → ⟨بمئت⟩, losing /i/). Assert directly on
# normalize_unicode, ahead of everything downstream, that the alif is never
# touched for this whole clitic paradigm.
# Derived from the corpus itself, not hardcoded, so the sweep never goes
# stale if tests/ar_test.txt grows or shrinks its مائت entries: every word
# column that contains the bare morpheme (undiacritized, so ``مائت`` alone,
# not ``مِائَة``/``مِئَة``/etc.). Pinned to today's count of 22 so silent
# corpus drift — the list quietly becoming shorter or longer — still fails
# loudly instead of just narrowing or widening coverage unnoticed.
_AR_TEST_PATH = os.path.join(os.path.dirname(__file__), "ar_test.txt")
with open(_AR_TEST_PATH, encoding="utf-8") as _f:
    MAIT_FORMS = sorted({
        line.split("\t", 1)[0]
        for line in _f.read().splitlines()
        if "\t" in line and re.search(r"مائت", line.split("\t", 1)[0])
    })

assert MAIT_FORMS, "no مائت forms found in tests/ar_test.txt — corpus regenerated?"
assert len(MAIT_FORMS) == 22, (
    f"tests/ar_test.txt now has {len(MAIT_FORMS)} مائت forms, not the 22 this "
    "sweep was written against — update the pin after checking whether the "
    "corpus changed on purpose"
)


@pytest.mark.parametrize("word", MAIT_FORMS)
def test_mait_family_alif_untouched_by_normalization(word):
    assert "ائت" in normalize_unicode(word), (
        f"{word}: normalize_unicode ate the alif of the مائت morpheme"
    )


# ─── the rest of the closed class, pinned so the rule cannot disturb it ───
@pytest.mark.parametrize("word,expected", [
    # ones, masculine
    ("وَاحِد", "ˈwaːħid"),
    ("اِثْنَان", "ʔiθˈnaːn"),
    ("ثَلَاثَة", "θaˈlaːθa"),
    ("أَرْبَعَة", "ˈʔarbaʕa"),
    ("خَمْسَة", "ˈxamsa"),
    ("سِتَّة", "ˈsitta"),
    ("سَبْعَة", "ˈsabʕa"),
    ("ثَمَانِيَة", "θaˈmaːnija"),
    ("تِسْعَة", "ˈtisʕa"),
    ("عَشَرَة", "ˈʕaʃara"),
    # ones, feminine
    ("وَاحِدَة", "ˈwaːħida"),
    ("ثَلَاث", "θaˈlaːθ"),
    ("أَرْبَع", "ˈʔarbaʕ"),
    ("خَمْس", "ˈxams"),
    ("سِتّ", "ˈsitt"),
    ("سَبْع", "ˈsabʕ"),
    ("ثَمَان", "θaˈmaːn"),
    ("تِسْع", "ˈtisʕ"),
    ("عَشْر", "ˈʕaʃr"),
    # tens, nominative
    ("عِشْرُون", "ʕiʃˈruːn"),
    ("ثَلَاثُون", "θalaːˈθuːn"),
    ("أَرْبَعُون", "ʔarbaˈʕuːn"),
    ("خَمْسُون", "xamˈsuːn"),
    ("سِتُّون", "sitˈtuːn"),
    ("سَبْعُون", "sabˈʕuːn"),
    ("ثَمَانُون", "θamaːˈnuːn"),
    ("تِسْعُون", "tisˈʕuːn"),
    # tens, oblique
    ("عِشْرِين", "ʕiʃˈriːn"),
    ("ثَلَاثِين", "θalaːˈθiːn"),
    ("أَرْبَعِين", "ʔarbaˈʕiːn"),
    ("خَمْسِين", "xamˈsiːn"),
    ("سِتِّين", "sitˈtiːn"),
    ("سَبْعِين", "sabˈʕiːn"),
    ("ثَمَانِين", "θamaːˈniːn"),
    ("تِسْعِين", "tisˈʕiːn"),
    # the larger bases
    ("أَلْف", "ˈʔalf"),
    ("أَلْفَان", "ʔalˈfaːn"),
    ("مِلْيُون", "milˈjuːn"),
])
def test_closed_class_unchanged(word, expected):
    assert ipa(word) == expected


# ─── sentences ────────────────────────────────────────────────────────────
@pytest.mark.parametrize("sentence,expected", [
    # "Three hundred books are on the table."
    ("ثَلَاثُمِائَةِ كِتَابٍ عَلَى الطَّاوِلَة.",
     "θalaːθuˈmiʔati kiˈtaːbin ˈʕalaː tˤˈtˤɑːwila"),
    ("ثَلَاثُمِئَةِ كِتَابٍ عَلَى الطَّاوِلَة.",
     "θalaːθuˈmiʔati kiˈtaːbin ˈʕalaː tˤˈtˤɑːwila"),
])
def test_numeral_in_sentence(sentence, expected):
    assert ipa(sentence) == expected
