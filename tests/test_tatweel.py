"""Tatweel is a stretch, not a letter.

U+0640 (kashida) elongates a joining stroke for justification. It has no sound and no
letter identity. Left in the string it is not a letter the tokenizer knows, so it breaks
its word in two: المـرء read `ˈalm ˈraʔ` where المرء reads `alˈmarʔ`. All five lect
tables agreed on the split, so the label builder's disagreement guard never saw it, and
two rows of the read register were dropped as unphonemisable with no reason visible.
"""
import pytest

pytest.importorskip("orthography2ipa", reason="the pipeline needs orthography2ipa")

TATWEEL = "ـ"


def _plugin():
    from arbtok.plugin import ArbtokG2PPlugin
    return ArbtokG2PPlugin(lang="ar", diacritize=True, nativize=True, pausal=True)


@pytest.mark.parametrize("stretched, plain", [
    ("المـرء", "المرء"),
    ("أفشـى", "أفشى"),
    ("بلسانـه", "بلسانه"),
    ("سـره", "سره"),
    ("الــكتاب", "الكتاب"),          # more than one, and consecutive
    (f"كتاب{TATWEEL}", "كتاب"),      # trailing
    (f"{TATWEEL}كتاب", "كتاب"),      # leading
])
def test_a_stretched_word_reads_as_the_plain_one(stretched, plain):
    p = _plugin()
    assert p.transcribe(stretched) == p.transcribe(plain)


def test_a_stretched_word_is_still_one_word():
    """The failure was a word count, which is what the label builder joins on."""
    p = _plugin()
    assert len(p.transcribe("المـرء").split()) == 1


def test_the_read_register_line_that_exposed_it():
    p = _plugin()
    got = p.transcribe("إذا المـرء أفشـى سـره بلسانـه")
    assert len(got.split()) == 5, got
    assert got == p.transcribe("إذا المرء أفشى سره بلسانه")


def test_normalize_unicode_drops_it_before_anything_else_looks():
    from arbtok.tokenizer import normalize_unicode
    assert TATWEEL not in normalize_unicode(f"ال{TATWEEL}كتاب")


def test_a_bare_latin_letter_is_read_as_its_name():
    """X was `z` -- the grapheme value of <x>, not the letter's name. The donor lexicon
    now carries the twenty-six letter names, so a letter in Arabic text is said."""
    from arbtok.translit import transliterate
    assert transliterate("x", "ar") == "iks"
    assert transliterate("b", "ar") == "biː"
