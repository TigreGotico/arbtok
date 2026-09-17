"""An established loan is looked up, and the value is not put through the donor machinery.

Nativisation adapts a donor pronunciation, which is right for a nonce borrowing and
wrong for a loan that has been an Arabic word for decades. `model` adapted from modern
English gives `mudal`, which nobody says; the Arabic word is `muːdiːl`, which this
package's own Arabic lexicon carries as الْمُودِيلُ → aːlmuːdiːl.

These are VALUE tests, per lect. The gold-row test cannot stand in for them: it pins the
pipeline against its own output, so it agrees with whatever the pipeline does and moves
when the pipeline moves.
"""
import pytest

pytest.importorskip("orthography2ipa", reason="the pipeline needs orthography2ipa")

LECTS = ["ar", "ar-JO", "ar-LB", "ar-SA-x-najd", "ar-EG", "ar-x-gulf", "ar-MA", "ar-IQ"]


@pytest.mark.parametrize("lect", LECTS)
@pytest.mark.parametrize("word, expected", [
    ("model", "muːdiːl"),
    ("video", "fiːdjo"),
    ("automatic", "ʔotomatik"),
])
def test_the_settled_reading_is_the_same_on_every_lect(lect, word, expected):
    """One lexicalised form, so one reading. The per-lect fan is for words a speaker
    derives, not for a word they looked up."""
    from arbtok.translit import transliterate
    assert transliterate(word, lect) == expected


@pytest.mark.parametrize("lect", ["ar-JO", "ar-LB"])
def test_automatic_is_not_lengthened_by_the_donor_projection(lect):
    """The defect this fixed. Those 22 lects declare /oː/ and no short /o/, so the
    projection lengthened the loan to ʔoːtoːmatik; the hand-authored gold for these two
    reads ʔotomaˈtik. Both rows are marked known-wrong because the Arabic-script path
    does not reach them either -- it gives ʔuːtuːmaːˈtiːk -- so this pins the half this
    module owns.
    """
    from arbtok.translit import transliterate
    got = transliterate("automatic", lect)
    assert "oː" not in got, got
    assert got == "ʔotomatik"


@pytest.mark.parametrize("word", ["meeting", "manager", "printer", "car", "computer",
                                  "modem", "videotape", "modelling", "automation"])
def test_a_word_not_in_the_table_is_untouched(word):
    """Exact match only, and the derived forms are on the wrong side of it.

    `modelling`, `videotape` and `automation` keep the adapted reading beside their
    bases' settled one, which is an inconsistency named rather than hidden: an inflected
    or compounded loan is a different word and none of them could be cited. They are
    here so the boundary is visible and a later change to it turns this red.
    """
    from arbtok.translit import transliterate
    from arbtok.translit import ESTABLISHED_LOANS
    assert word not in ESTABLISHED_LOANS["en-GB"]
    assert transliterate(word, "ar")


def test_no_french_table_ships():
    """It held three values that were mine rather than cited, live on every lect."""
    from arbtok.translit import ESTABLISHED_LOANS
    assert set(ESTABLISHED_LOANS) == {"en-GB"}


@pytest.mark.parametrize("word", ["model", "video", "automatic"])
def test_strict_does_not_refuse_a_settled_reading(word):
    """Disclosed rather than discovered: strict=True used to return None for video and
    automatic on seven of ten lects, because the projection refused a symbol the matrix
    does not declare. A settled reading no longer goes through that, so strict returns
    it. There is nothing for strict to refuse in a word that is already Arabic.
    """
    from arbtok.translit import transliterate
    for lect in LECTS:
        assert transliterate(word, lect, strict=True) is not None, lect
