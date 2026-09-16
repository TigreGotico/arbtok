"""The bundled English donor lexicon is rhotic, because Arabic loans are.

RP is non-rhotic and the lexicon's source gold speaks RP, so left alone it gives
`car` as kˈɑː. That is a true statement about English and the wrong input to loanword
adaptation into Arabic, which has /r/ and writes these loans with the rāʾ: كارت,
كارد, برنتر, تشارجر, كونسرت. Unrhoticised, the adapter produced `kaː` for car and
`brinta` for printer.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LEXICON = ROOT / "arbtok" / "data" / "donor_lexicons" / "en-GB.tsv"


def _builder():
    spec = importlib.util.spec_from_file_location(
        "build_donor_lexicon", ROOT / "scripts" / "build_donor_lexicon.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.mark.parametrize("word, ipa, expected", [
    ("car", "kˈɑː", "kˈɑːɹ"),
    ("card", "kˈɑːd", "kˈɑːɹd"),
    ("printer", "pɹˈɪntə", "pɹˈɪntəɹ"),          # one /r/ already there, one missing
    ("charger", "tʃˈɑːdʒə", "tʃˈɑːɹdʒəɹ"),       # both missing
    ("barber", "bˈɑːbə", "bˈɑːɹbəɹ"),
    ("father", "fˈɑːðə", "fˈɑːðəɹ"),             # PALM ɑː is not r-coloured; only the ə
    ("surprise", "səpɹˈaɪz", "səɹpɹˈaɪz"),       # the missing one is not the last nucleus
    ("password", "pˈɑːswəː", "pˈɑːswəːɹ"),       # after the length mark, not inside it
    ("stirring", "stˈɜːɹɪŋ", "stˈɜːɹɪŋ"),        # <rr> spells one /r/, already present
    ("sofa", "sˈəʊfə", "sˈəʊfə"),                # no <r> to restore
    ("idea", "aɪdˈɪə", "aɪdˈɪə"),                # NEAR without an <r>
])
def test_rhoticise_restores_what_the_spelling_has(word, ipa, expected):
    assert _builder().rhoticise(word, ipa) == expected


#: Cases that tell this rule apart from the obvious wrong one — "rhoticise every
#: eligible nucleus" rather than only the deficit. Most single-/r/ words cannot: with
#: one eligible nucleus both rules agree, so they cover spelling classes without
#: testing the positional logic. These have two or more eligible nuclei and a deficit
#: smaller than that, so filling from the right is the only thing that gets them right.
DISCRIMINATING = [
    ("father", "fˈɑːðə", "fˈɑːðəɹ"),            # naive: fˈɑːɹðəɹ — PALM ɑː is not r-coloured
    ("password", "pˈɑːswəː", "pˈɑːswəːɹ"),      # naive: pˈɑːɹswəːɹ
    ("catarrh", "kətˈɑː", "kətˈɑːɹ"),           # naive: kəɹtˈɑːɹ — <rr> spells one /r/
    ("abattoir", "ˈæbətwɑː", "ˈæbətwɑːɹ"),      # naive: ˈæbəɹtwɑːɹ
    ("theatre", "θˈɪətə", "θˈɪətəɹ"),           # naive: θˈɪəɹtəɹ — NEAR without an <r>
    ("massacre", "mˈæsəkə", "mˈæsəkəɹ"),        # naive: mˈæsəɹkəɹ
    ("rhythm", "ɹˈɪðəm", "ɹˈɪðəm"),             # naive: ɹˈɪðəɹm — the <rh> onset already has it
]

#: Spelling classes the rule must not mangle. These do not discriminate against the
#: naive rule — one eligible nucleus each, so both rules agree — and they are here for
#: the classes, not for the logic.
CLASSES = [
    ("iron", "ˈaɪən", "ˈaɪəɹn"),                # <r> before a consonant, not word-final
    ("cupboard", "kˈʌbəd", "kˈʌbəɹd"),          # compound with a reduced second element
    ("fireproof", "fˈaɪəpɹuːf", "fˈaɪəɹpɹuːf"),  # compound, the deficit is medial
    ("corps", "kˈɔː", "kˈɔːɹ"),
    ("mortgage", "mˈɔːɡɪdʒ", "mˈɔːɹɡɪdʒ"),
    ("myrrh", "mˈɜː", "mˈɜːɹ"),                 # <rrh>
    ("centre", "sˈɛntə", "sˈɛntəɹ"),            # -re ending
    ("write", "ɹˈaɪt", "ɹˈaɪt"),                # <wr> onset, already rhotic
    ("hierarchy", "hˈaɪəɹɑːki", "hˈaɪəɹɑːɹki"),  # one /r/ present, one missing
    ("aardvark", "ˈɑːdvɑːk", "ˈɑːɹdvɑːɹk"),     # deficit of two
    ("governor", "ɡˈʌvənə", "ɡˈʌvəɹnəɹ"),
]


@pytest.mark.parametrize("word, ipa, expected", DISCRIMINATING + CLASSES)
def test_rhoticise_on_adversarial_spellings(word, ipa, expected):
    assert _builder().rhoticise(word, ipa) == expected


@pytest.mark.parametrize("word, ipa, expected", [
    # A silent <r> gets one restored, and an /r/ with no <r> to license it does not.
    # Both need grapheme-to-phoneme alignment to fix and neither is fixed; they are
    # pinned so the limits are visible and a later rule has something to beat.
    ("forecastle", "fˈəʊksəl", "fˈəʊksəɹl"),   # wrong: the <r> of fore- is silent
    ("colonel", "kˈɜːnəl", "kˈɜːnəl"),          # wrong: rhotic English has kˈɜːɹnəl
])
def test_the_known_limits_of_a_spelling_driven_rule(word, ipa, expected):
    assert _builder().rhoticise(word, ipa) == expected


def test_the_shipped_lexicon_is_rhotic():
    """The shipped file, not just the function."""
    want = {"car": "kˈɑːɹ", "card": "kˈɑːɹd", "manager": "mˈænɪdʒəɹ",
            "printer": "pɹˈɪntəɹ", "charger": "tʃˈɑːɹdʒəɹ"}
    got = {}
    with LEXICON.open(encoding="utf-8") as fh:
        for line in fh:
            w, _, ipa = line.rstrip("\n").partition("\t")
            if w in want:
                got[w] = ipa
    assert got == want


def test_the_adapted_loans_keep_their_r():
    """End to end, on the matrix that has no cited table of its own."""
    from arbtok.translit import transliterate
    for word, expected in (("car", "kaːr"), ("card", "kaːrd"),
                           ("printer", "brintar"), ("concert", "kunsart")):
        assert transliterate(word, "ar") == expected, word
