"""The Maghreb reads a French loan out of its own phonology.

These lects had no nativisation table and fell back to the pan-Arabic default,
which is built for Gulf and MSA and states its own reasons in terms of what those
lects lack. Applied to the Maghreb it rewrote /ʒ/ -- a segment every Maghrebi spec
declares -- to [dʒ], and the feature metric sent French /ʁ/ to [ɣ], which three
corpora across three countries say it never becomes. *garage* came out `ɡaɣadʒ`.
"""
import pytest

from arbtok import translit
from arbtok.translit import nativization_table, transliterate

MAGHREB = ["ar-MA", "ar-DZ", "ar-TN"]


@pytest.mark.parametrize("lect", MAGHREB + ["ar-x-maghrebi", "ary", "arq", "aeb"])
def test_the_maghreb_has_its_own_table(lect):
    """Attached at the group node, so the ISO codes inherit it too."""
    assert nativization_table(lect) is translit._MAGHREBI_MAP


@pytest.mark.parametrize("lect", ["ar-LY", "ar-MR"])
def test_the_two_held_out_lects_keep_the_default(lect):
    """Libya borrows from Italian, not French (Benkato 2020), and Mauritania's
    Hassaniya declares /ʁ/, which the table would rewrite on no source at all.
    Both are held out by naming the default ahead of their parent."""
    assert nativization_table(lect) is translit._DEFAULT_MAP


@pytest.mark.parametrize("lect", MAGHREB)
def test_the_french_rhotic_is_a_trill_not_a_velar_fricative(lect):
    """Kenstowicz & Louriz 2009; Ziadna 2018 p.185; Oueslati 2021 p.101. Each lect
    declares /ɣ/ and does not use it for a French rhotic, which is why the metric
    gets it wrong. [ɣ] is attested as the socially feminine variant (Ziadna p.185);
    the table holds the unmarked value because register is not in the input."""
    got = translit.nativize("ɡaʁaʒ", lect, donor="fr-FR")
    assert "ɣ" not in got, got
    assert got.count("r") == 1, got


@pytest.mark.parametrize("lect", MAGHREB)
def test_the_maghrebi_jim_is_retained(lect):
    """The default maps /ʒ/ to [dʒ] because MSA and Gulf have no /ʒ/. These do."""
    assert "ʒ" in translit._targets(lect)
    assert translit.nativize("ʒ", lect, donor="fr-FR") == "ʒ"


@pytest.mark.parametrize("segment, expected", [("y", "i"), ("ø", "u"), ("œ", "u")])
@pytest.mark.parametrize("lect", MAGHREB)
def test_the_front_rounded_vowels(lect, segment, expected):
    """Heath 2020 p.217; Kenstowicz & Louriz 2009 pp.53-54; Ziadna 2018 pp.196-197;
    Oueslati 2021 pp.101-102."""
    assert translit.nativize(segment, lect, donor="fr-FR") == expected


@pytest.mark.parametrize("segment", ["p", "v"])
@pytest.mark.parametrize("lect", MAGHREB)
def test_p_and_v_carry_no_rule(lect, segment):
    """Substitution is the majority outcome in every corpus and is conditioned on
    loan age and the speaker's French, neither visible here. The specs declare both,
    so the table stays out of it and they pass through."""
    assert segment not in translit._MAGHREBI_MAP
    assert translit.nativize(segment, lect, donor="fr-FR") == segment


@pytest.mark.parametrize("lect, expected", [
    ("ar-MA", "ɡaraʒ"), ("ar-DZ", "ɡaraʒ"), ("ar-TN", "ɡaraʒ"),
])
def test_garage(lect, expected):
    """The word the whole thing was found on. Ziadna 2018 p.196 has Algerian
    [gɑːrˤɑːʤ]. The affrication there is his own Setifian (p.58); the EMPHASIS is
    not a dialect trait but his general rule for a rhotic beside a non-high vowel
    (p.185), and encoding it needs a context rule rather than a table entry."""
    assert transliterate("garage", lect, donor="fr-FR") == expected


# ---------------------------------------------------------------------------
# The table must not answer for anybody else
# ---------------------------------------------------------------------------

def test_the_table_is_not_borrowable_by_other_lects():
    """`_project` scans tables for a cited value when the matrix's own is silent.
    Scanning ALL of them hands one lect's cited adaptation to another, which the
    module's docstring says the per-lect design exists to prevent."""
    assert translit._MAGHREBI_MAP not in translit._BORROWABLE_TABLES


@pytest.mark.parametrize("lect", ["ar", "ar-LB", "ar-EG", "ar-SA-x-najd", "ar-KW",
                                  "ar-IQ", "ar-JO", "ar-x-gulf", "ar-SD"])
@pytest.mark.parametrize("segment", ["ʁ", "y", "ø", "œ"])
def test_a_non_maghrebi_lect_is_not_given_the_maghrebi_reading(lect, segment):
    """These four segments are named by no other table, so while the projector
    scanned every table the Maghrebi value was the only candidate and won on 32
    lects: `ar-LB`'s *chauffeur* moved on a source about Moroccan.

    Asserted as "not the Maghrebi value" rather than as a fixed reading, because
    what the metric answers instead is a separate question with its own tests, and
    pinning it here would make this test move when that one does.
    """
    assert translit._project(segment, lect) != translit._MAGHREBI_MAP[segment], (
        f"{lect}: {segment} took the Maghrebi table's value")


def test_an_english_code_switch_is_untouched_by_the_french_segments():
    """The donor is still chosen by script, so `service` on a Maghrebi lect is read
    from English. What changes there is /p/ and /v/, which is the point."""
    assert transliterate("service", "ar-MA") == "sarvis"
    assert transliterate("laptop", "ar-DZ") == "laptup"
    assert transliterate("service", "ar-EG") == "sarfis"
