"""A guest vowel with no counterpart in the matrix lands on its own quality.

`segment_distance` returns one constant for every candidate when the guest's quality
is absent from the matrix altogether. `min` over that tie returns whichever sorts
first, which is alphabetical -- so [o] landed on [a] and *video* came out `fidiaː` on
every lect declaring no /o/, the pan-Arabic default among them.
"""
import pytest

from arbtok import translit


@pytest.mark.parametrize("segment, expected", [
    ("o", "u"), ("oː", "uː"), ("ɔ", "ʊ"),
])
def test_a_mid_back_vowel_raises_rather_than_lowering(segment, expected):
    """[o] is one step from [u] and three from [a]; the metric cannot see it."""
    assert translit._project(segment, "ar") == expected


@pytest.mark.parametrize("lect", [
    "ar", "ar-SA-x-najd", "ar-EG", "ar-LB", "ar-x-gulf", "ar-MA", "ar-IQ", "ar-YE",
])
def test_no_lect_lowers_a_mid_back_vowel_to_a_low_one(lect):
    """Whatever a lect declares, [o] must not come out as [a].

    Asserted on the projection rather than on a transliterated word: the reading of
    a word also depends on which donor lexicon is registered, so a word-level
    assertion here would be testing two things and would move when either changed.
    """
    for segment in ("o", "oː"):
        got = translit._project(segment, lect)
        assert got is not None, f"{lect}: {segment} projects nowhere"
        assert got[0] not in "aɑæ", f"{lect}: {segment} -> {got}"


def test_a_lect_that_declares_the_quality_is_untouched():
    """The tie-break fires only on a tie: ar-SA-x-najd declares /o/ and keeps it."""
    assert translit._project("o", "ar-SA-x-najd") == "o"
    assert translit._project("oː", "ar-EG") == "oː"


# ---------------------------------------------------------------------------
# A cited table beats the metric, whether or not the metric was undecided
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("lect", ["ar-MA", "ar-DZ"])
def test_an_interdental_lands_where_the_citations_put_it(lect):
    """ð on a lect declaring neither interdental.

    The metric has a UNIQUE answer here and it is [dʒ], so this is not a tie and the
    tie-break never saw it: `the`, `this`, `mother`, `father` read dʒa, dʒis, madʒar,
    faːdʒar on Moroccan and Algerian -- 445 lexicon entries a lect -- while their own
    parent ar-x-maghrebi says [d] and every cited table naming ð says [d].
    """
    assert translit._project("ð", lect) == "d"
    assert translit._project("θ", lect) == "t"


@pytest.mark.parametrize("word, expected", [
    ("the", "da"), ("this", "dis"), ("mother", "madar"), ("father", "faːdar"),
])
def test_the_words_that_showed_it(word, expected):
    for lect in ("ar-MA", "ar-DZ", "ar-x-maghrebi"):
        assert translit.transliterate(word, lect) == expected, lect


def test_the_maghrebi_parent_keeps_its_own_reading():
    """The tripwire for #85's undisclosed ð→d on ar-x-maghrebi, 450 lexicon words.

    It moved no gold row, so nothing in the corpus pins it; without this the next
    projection change could move it back and no test would notice.
    """
    assert translit._project("ð", "ar-x-maghrebi") == "d"


@pytest.mark.parametrize("lect", ["ar", "ar-TN", "ar-LY"])
def test_a_lect_that_declares_the_interdentals_keeps_them(lect):
    """Only a lect that does not declare the segment reaches the projection at all."""
    assert translit.transliterate("think", lect) == "θink"
    assert translit.transliterate("mother", lect).count("ð") == 1


# ---------------------------------------------------------------------------
# No tie is decided by sort order
# ---------------------------------------------------------------------------

def _lect_codes():
    from pathlib import Path
    root = Path(__file__).resolve().parents[1] / "data" / "gold_code_switched"
    return sorted(p.stem for p in root.glob("*.tsv"))


def test_no_reachable_tie_resolves_by_alphabetical_order():
    """The invariant, over every lect and every segment the donor lexicon can produce.

    A tie means the metric returned the same distance for every candidate, so `min`
    falls back to sort order -- which is how [o] landed on [a] and started this. The
    residue was ɜ: 35 of the 71 reachable ties, one per lect, resolving to [a] because
    `a` sorts first and agreeing with the citations only by luck. Every cited table maps
    its long counterpart ɜː to [a], so the short one now follows that, derived rather
    than typed.

    Counted rather than asserted: 71 ties over 7 segments across 35 lects, and none of
    them alphabetical.
    """
    from orthography2ipa import G2P
    from orthography2ipa.distance import segment_distance
    from arbtok import translit
    from pathlib import Path

    lexicon = (Path(__file__).resolve().parents[1]
               / "arbtok" / "data" / "donor_lexicons" / "en-GB.tsv")
    donor = set()
    with lexicon.open(encoding="utf-8") as fh:
        for line in fh:
            _, _, ipa = line.rstrip("\n").partition("\t")
            donor.update(translit.segment_ipa(ipa))
    donor -= {"ˈ", "ˌ", "ː"}

    alphabetical, ties = [], 0
    for lect in _lect_codes():
        try:
            table = translit.nativization_table(lect)
            targets = translit._targets(lect)
        except Exception:
            continue
        for seg in sorted(donor):
            cited = table.get(seg)
            for piece in (translit.segment_ipa(cited) if cited is not None else [seg]):
                if piece in targets:
                    continue
                scored = [(segment_distance(piece, t), t) for t in targets]
                best = min(d for d, _ in scored)
                if sum(1 for d, _ in scored if d == best) < 2:
                    continue
                ties += 1
                got = translit._project(piece, lect)
                if any(tb.get(piece) == got for tb in translit._BORROWABLE_TABLES):
                    continue
                if not piece.endswith("ː") and any(
                        (tb.get(piece + "ː") or "").rstrip("ː") == got
                        for tb in translit._BORROWABLE_TABLES):
                    continue
                base = piece[:-1] if piece.endswith("ː") else piece
                raised = translit._RAISED.get(base)
                if raised and got and got.startswith(raised):
                    continue
                alphabetical.append((lect, piece, got))

    assert ties > 0, "the enumeration found no ties at all, so it proves nothing"
    assert not alphabetical, f"{len(alphabetical)} of {ties} ties fell to sort order: " \
                             f"{alphabetical[:5]}"
