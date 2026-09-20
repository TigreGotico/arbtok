"""Idghām and iqlāb belong to مِن and مَن, not to a run of three characters.

The character cascade carried its own copy of the rule, guarded on a nūn whose
two preceding characters were a kasra and a mīm. That is the spelling of مِن --
and also the spelling of the middle of اسْمِنَا, of مُؤْمِنُونَ, of any word at
all that happens to run م ِ ن. The word-level rule in :mod:`arbtok.sandhi` asks
whether the WORD is مِن or مَن, which is what the rule is about.
"""
import pytest

from arbtok.tokenizer import Sentence


@pytest.mark.parametrize("text, expected", [
    ("بِاسْمِنَا رَبِّنَا", "ˈbisminaː ˈrabbinaː"),   # not *bismiraː
    ("بِاسْمِنَا يَوْمَ", "ˈbisminaː ˈjawma"),        # not *bismijaː
    ("بِاسْمِنَا لَيْلًا", "ˈbisminaː ˈlajlan"),      # not *bismilaː
    ("بِاسْمِنَا بَعْدَ", "ˈbisminaː ˈbaʕda"),        # not *bismimaː
])
def test_a_word_that_merely_spells_min_keeps_its_nun(text, expected):
    """بِاسْمِنَا is "in our name" and its nūn is word-medial. The character
    guard read the next word's first letter and wrote it over that nūn, so the
    phrase changed shape with whatever followed it."""
    assert Sentence(text, lang="ar").ipa == expected


@pytest.mark.parametrize("text, expected", [
    ("مِنْ رَبِّهِمْ", "ˈmir ˈrabbihim"),   # idghām into r
    ("مِنْ بَيْتِكَ", "ˈmim ˈbajtika"),     # iqlāb before b
    ("مَنْ يَقُولُ", "ˈmaj jaˈquːlu"),      # idghām into j -- مَن, which the character guard never saw
    ("مَنْ لَهُ", "ˈmal ˈlahu"),            # idghām into l
])
def test_the_words_the_rule_is_about_still_assimilate(text, expected):
    assert Sentence(text, lang="ar").ipa == expected


@pytest.mark.parametrize("text, expected", [
    ("بِاسْمِنَا رَبِّنَا", "ˈbisminaː ˈrabbinaː"),
    ("مِنْ بَعْدِ", "ˈmin ˈbaʕdi"),
])
def test_a_dialect_reads_its_nun_as_written(text, expected):
    """Idghām of مِن is Classical recitation sandhi: the dialect gold reads
    *min baʕd*. The word-level rule is gated to the reference register; the
    character guard was not gated at all."""
    assert Sentence(text, lang="ar-EG").ipa == expected
