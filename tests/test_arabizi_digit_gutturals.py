"""The gate that decides Arabizi is derived from the tables that can write it.

Three sets had drifted apart: the gate matched 2 3 4 5 6 7, the skeleton mapper knew
2 3 5 7 8 9, and the docstring said 2 3 5 6 7 9. Every disagreement was reachable.

A 4 fired the gate and had no mapping, so any Latin token carrying one -- a model name,
a year, a size -- went down the Arabizi path and came back missing its letters: `X4`
read `ʔarbaʕa`, the X gone entirely. A 6 fired and could not be written either. An 8
could be written but never fired. And 9, the standard ṣād, fired in the docstring alone.

The gate is now built from the tables, so a digit fires it exactly when something can
spell the result, and `arabizi_covers` refuses a token the mapper cannot write whole.
"""
import pytest

pytest.importorskip("orthography2ipa", reason="the pipeline needs orthography2ipa")


def _plugin():
    from arbtok.plugin import ArbtokG2PPlugin
    return ArbtokG2PPlugin(lang="ar", diacritize=True, nativize=True, pausal=True)


def test_the_gate_and_the_mapper_name_the_same_digits():
    """The invariant, not the list. A hand-typed set is what drifted."""
    from arbtok.arabizi import _CONSONANTS, _GUTTURAL_DIGITS
    assert {d for d in _GUTTURAL_DIGITS if len(d) == 1} == {
        k for k in _CONSONANTS if k.isdigit()}


#: The number word each guttural digit would become if it were read as a numeral
#: instead of a consonant -- which is the regression this guards.
_AS_NUMBER = {"7": "sabʕa", "3": "θalaːθa", "9": "tisʕa", "5": "xamsa",
              "6": "sitta", "2": "iθnaːn"}


@pytest.mark.parametrize("word, expected", [
    ("7abibi", "ħaːˈbiːb"), ("3ala", "ˈʕaːlaː"), ("9abah", "qaːˈbaːh"),
    ("5alas", "xaːˈlaːs"), ("6ayyib", "tˤijˈjiːb"), ("2ana", "ˈʔaʔanaː"),
])
def test_a_genuine_arabizi_token_is_read_as_arabic(word, expected):
    """Pinned by value. An earlier version of this test asserted that the reading
    carried no ASCII letter, which no Arabic IPA string can satisfy -- b, d, k, l, m, n,
    s, t, w, z are all ASCII -- so it failed on every correct reading. The leakage gate
    in gold_code_switched says the same thing in its own docstring and I wrote the test
    it warns against."""
    from arbtok.arabizi import arabizi_covers, is_arabizi
    assert is_arabizi(word) and arabizi_covers(word), word
    got = _plugin().transcribe(word)
    assert got == expected
    assert _AS_NUMBER[word[0]] not in got, f"{word}: the guttural was read as a numeral"


@pytest.mark.parametrize("word, keeps", [
    ("X4", "iks"), ("X2", "iks"), ("A4", "a"), ("S60", "is"), ("mp4", "mb"),
])
def test_a_designator_keeps_its_letters(word, keeps):
    """These carry a digit and are not Arabizi. X2 and S60 carry a digit that IS a
    guttural, so the gate alone cannot tell -- the coverage check does, because the
    mapper cannot write the rest of the token."""
    got = _plugin().transcribe(word)
    assert keeps in got, (word, got)
    assert got.strip(), word


def test_a_letter_with_no_arabizi_value_refuses_the_path():
    """`x` has none -- Arabizi spells خ as kh or 5 -- so a token containing one is not
    reverse-transliterated, rather than transliterated with the x dropped."""
    from arbtok.arabizi import arabizi_covers
    assert not arabizi_covers("X2")
    assert not arabizi_covers("S60")
    assert arabizi_covers("7abibi")


def test_an_arabizi_token_is_not_split_into_script_runs():
    """The mixed-token splitter must not reach an Arabizi token: it would tear `7abibi`
    into `7` and `abibi` and read the seven as a number, which it did."""
    got = _plugin().transcribe("7abibi")
    assert "sabʕa" not in got, got
    assert got == _plugin().transcribe("7abibi")
