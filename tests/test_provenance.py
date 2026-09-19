"""Every word carries the stage that decided it, and the categories are distinct.

The field exists because licensing is a veto over letters, not a preference over
readings: a well-formed MSA vocalization passes it untouched, so ``model`` means the
lect contributed nothing but a veto that could not fire. These tests pin that the
categories say what they mean, because a provenance that lumps two causes together is
worse than none — a caller filters on it.
"""
import pytest

import arbtok
from arbtok.diacritize import PROVENANCE, DiacritizedText, LatticeDiacritizer


def test_the_text_matches_what_diacritize_returns():
    """The record path and the string path are the same pipeline, not two."""
    d = LatticeDiacritizer(lang="ar-EG")
    text = "كتاب جديد مع الاستاذ"
    assert d.diacritize_text(text).text == d.diacritize(text)


def test_every_word_gets_a_known_provenance():
    out = arbtok.vocalize("كتاب جديد مع الاستاذ", "ar-EG")
    assert out.words
    for w in out.words:
        assert w.provenance in PROVENANCE
        assert w.surface and w.output


def test_a_latin_embed_is_not_a_refusal():
    """The whole reason `not-arabic` is separate.

    On the code-switched gold every refusal in ar-EG was an English embed — the
    words that set exists to carry. A caller filtering `refused` for failures got a
    pile of English, so the two are different categories now.
    """
    out = arbtok.vocalize("عندي meeting مهم", "ar-EG")
    by = {w.surface: w for w in out.words}
    assert by["meeting"].provenance == "not-arabic"
    assert by["meeting"].is_failure is False
    assert by["meeting"].output == "meeting"


def test_lect_constrained_excludes_the_model():
    """`model` means the MSA prior decided unopposed; it must never read as
    lect-constrained, which is the distinction the field is for."""
    from arbtok.diacritize import DiacritizedWord
    assert DiacritizedWord("x", "x", "model").lect_constrained is False
    assert DiacritizedWord("x", "x", "model-repaired").lect_constrained is False
    assert DiacritizedWord("x", "x", "closed-class").lect_constrained is True


def test_whitespace_keeps_its_place_and_carries_no_record():
    out = arbtok.vocalize("كتاب  جديد", "ar-EG")
    assert len(out.words) == 2
    assert "  " in out.text


def test_by_provenance_groups_the_surfaces():
    out = arbtok.vocalize("عندي meeting مهم", "ar-EG")
    assert "meeting" in out.by_provenance["not-arabic"]


def test_the_public_name_survives_importing_the_submodule():
    """`arbtok.diacritize` is the module. Binding a function of that name at package
    level works until something imports the submodule and rebinds the attribute, which
    is why the entry point is `vocalize`."""
    import arbtok.diacritize  # noqa: F401  — the rebinding case
    assert callable(arbtok.vocalize)
    assert isinstance(arbtok.vocalize("كتاب", "ar-EG"), DiacritizedText)
