"""A lect resolves the same way under its ``ar-…`` key and under its ISO 639-3 key.

orthography2ipa may key an Arabic dialect by its ISO 639-3 code (``ar-EG`` is
``arz-EG``, ``ar-SA-x-najd`` is ``ars-SA``) and keep the older key as an exact
alias. Whichever key set the installed orthography2ipa uses, both tags must land
on the spec that ``orthography2ipa.resolve`` gives the older key, and arbtok's own
tables, which name lects by the older keys, must still reach them.
"""
import warnings

import pytest
from orthography2ipa import resolve, resolves_exactly

from arbtok import dialects, is_arabic_lang, translit
from arbtok.dialect_lexicon import DialectLexicon, available_lects, lexicon_file
from arbtok.dialects import lect_code, spec_for_lang, supported_lects
from arbtok.lattice import DEFAULT_RESCORERS
from arbtok.o2i_plugins import pipeline

PAIRS = [
    ("ar-EG", "ar-EG"), ("arz-EG", "ar-EG"),
    ("ar-MA", "ar-MA"), ("ary-MA", "ar-MA"),
    ("ar-SA-x-najd", "ar-SA-x-najd"), ("ars-SA", "ar-SA-x-najd"),
    ("ar-x-gulf", "ar-x-gulf"), ("afb", "ar-x-gulf"),
    ("ar-JO", "ar-JO"), ("ar-EG-x-saidi", "ar-EG-x-saidi"),
    ("ar-EH", "ar-DZ"), ("ar-TR", "ar-TR"),
    ("ar-x-najd", "ar-SA-x-najd"),
]


@pytest.mark.parametrize("tag, key", PAIRS)
def test_a_tag_names_the_spec_orthography2ipa_gives_its_lect(tag, key):
    """Where orthography2ipa resolves the tag exactly, that is the spec. An
    orthography2ipa that has no ISO 639-3 keys resolves ``arz-EG`` only by guessing,
    and the tag then reads as its lect's ``ar-…`` key does."""
    assert spec_for_lang(tag) == resolve(key)
    if resolves_exactly(tag):
        assert spec_for_lang(tag) == resolve(tag)


def test_a_bare_region_reads_as_orthography2ipa_reads_it():
    """A bare ``ar-`` region tag lands on the spec orthography2ipa resolves it to,
    MSA included. Turkey's specs are all private-use lects and orthography2ipa
    curates no default for ``ar-TR``, so a distance match over arbtok's lects
    would read it as whichever Turkish lect ties first."""
    regions = {code.split("-")[1] for code in dialects._arabic_codes()
               if len(code.split("-")) > 1 and len(code.split("-")[1]) == 2}
    assert "TR" in regions
    wrong = {f"ar-{region}": (spec_for_lang(f"ar-{region}"), resolve(f"ar-{region}"))
             for region in sorted(regions)
             if spec_for_lang(f"ar-{region}") != resolve(f"ar-{region}")}
    assert wrong == {}


@pytest.mark.parametrize("tag", ["ar-EG", "ar-MA", "ar-SA-x-najd", "ar-x-gulf", "ar-LB"])
def test_the_lect_is_listed_and_spoken_for(tag):
    """A re-keyed lect is listed, and arbtok's pipeline for it keeps its rescorers."""
    assert resolve(tag) in {lect.code for lect in supported_lects()}
    assert pipeline(resolve(tag)).rescore == tuple(DEFAULT_RESCORERS)


@pytest.mark.parametrize("tag", ["arz-EG", "ary-MA", "ars-SA", "apc-LB", "afb-KW",
                                 "acw-SA", "mey-MR", "ARZ-eg", "ars_SA", "ara-x-made-up"])
def test_an_iso_keyed_tag_is_arabic(tag):
    """``ara`` is the ISO 639-2 code of Arabic. Ruling: linguatag is the authority on
    which tags are Arabic, and it counts ``ara`` with any private-use subtag."""
    assert is_arabic_lang(tag)


@pytest.mark.parametrize("tag", ["arc-SY", "arn-CL", "mlt-MT"])
def test_a_lookalike_iso_keyed_tag_is_not(tag):
    assert not is_arabic_lang(tag)


@pytest.mark.parametrize("key, table", [
    ("ar-EG", translit._EGYPTIAN_MAP), ("ar-SA-x-najd", translit.SEGMENT_MAP),
    ("ar-LB", translit._LEVANTINE_MAP), ("ar-MA", translit._MAGHREBI_MAP),
    ("ar-MR", translit._DEFAULT_MAP), ("ar-KW", translit._DEFAULT_MAP),
])
def test_the_nativisation_table_follows_the_lect(key, table):
    assert translit.nativization_table(resolve(key)) is table


def test_the_bundled_lexicons_answer_to_the_installed_key():
    for name in ("ar-EG", "ar-MA", "ar-SA-x-najd", "ar-IQ", "ar-SY", "ar-TN", "ar-DZ"):
        assert resolve(name) in available_lects()
        assert lexicon_file(resolve(name)) == lexicon_file(name) is not None
        assert DialectLexicon(resolve(name)).entries == DialectLexicon(name).entries


@pytest.mark.parametrize("key, code", [("ar-EG", "arz"), ("ar-SA-x-najd", "ars"),
                                       ("ar-SA-x-hejaz", "acw"), ("ar-KW", "afb")])
def test_the_lect_code_follows_the_lect(key, code):
    assert lect_code(resolve(key)) == code


def test_a_spec_arbtok_has_no_lect_for_reads_as_msa_with_a_warning(monkeypatch):
    """orthography2ipa names ``ar-MA`` exactly. If its spec is not one arbtok carries,
    the tag must read as MSA and say so, never as the nearest other dialect: the
    Moroccan tag once came out as Libyan, with no warning."""
    moroccan = resolve("ar-MA")
    codes = [c for c in dialects._arabic_codes() if c != moroccan]
    monkeypatch.setattr(dialects, "_arabic_codes", lambda: codes)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        assert spec_for_lang("ar-MA") == dialects.DEFAULT_LANG
        assert spec_for_lang("ar-MA-x-casablanca") == dialects.DEFAULT_LANG
    messages = [str(w.message) for w in caught if issubclass(w.category, UserWarning)]
    assert any(moroccan in m and "no lect" in m for m in messages), messages


def test_a_language_that_is_not_arabic_reads_as_msa_without_a_warning():
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        assert spec_for_lang("en") == dialects.DEFAULT_LANG
        assert spec_for_lang("fr-FR") == dialects.DEFAULT_LANG


@pytest.mark.parametrize("key, zone", [("ar-EG", "eg"), ("ar-SA-x-najd", "gulf"),
                                       ("ar-LB", "lev"), ("ar-MA", "magh"), ("ar", "msa")])
def test_the_code_switched_gold_follows_the_lect(key, zone):
    """The gold files and the particle zones are named by the ``ar-…`` keys; the
    harness must still find them when the lect answers to its ISO 639-3 key."""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
    import gold_code_switched as gcs

    assert gcs._gold_path(resolve(key)) == gcs.GOLD_DIR / f"{key}.tsv"
    assert gcs._zone(resolve(key)) == zone
    assert resolve(key) in gcs._roster()


def test_the_lects_without_gold_are_lects():
    """A name in the no-gold set that stops being a lect must leave the set."""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
    import gold_code_switched as gcs

    # orthography2ipa keeps the old key of a renamed spec as an exact alias, so
    # a name still counts when it resolves exactly to a lect.
    codes = {lect.code for lect in supported_lects()}
    assert all(resolves_exactly(code) for code in gcs.NO_GOLD)
    no_gold = {resolve(code) for code in gcs.NO_GOLD}
    skip = {resolve(code) for code in gcs.SKIP}
    assert no_gold <= codes
    assert set(gcs._roster()) == codes - skip - no_gold
