"""The donor's length mark survives projection onto a lect's declared inventory.

Donor segmentation cuts ``əː`` into ``ə | ː``. The mark is a modifier of the vowel
before it, so it must come out attached to whatever that vowel is projected to,
whether or not the matrix inventory lists a bare ``ː`` token.
"""
import pytest

from arbtok.translit import nativize

PASSWORD = "pˈɑːswəːɹd"


@pytest.mark.parametrize("lect", ["abv-BH", "ar", "apc", "arz-EG", "acm-IQ"])
def test_donor_length_mark_stays_on_projected_vowel(lect):
    assert nativize(PASSWORD, lect) == "baːswaːrd"
