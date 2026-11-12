"""The public list of resolvable varieties tracks the o2i registry.

``supported_lects()`` is enumerated from orthography2ipa, so it cannot drift
from the installed data set the way a hand-kept table would. orthography2ipa may
key a lect by its ISO 639-3 code (``arz-EG``, ``ars-SA``, ``afb``) and keep the
older ``ar-…`` key as an alias; the list must hold under either key set.
"""
from pathlib import Path

import langcodes
from orthography2ipa import available_codes, get, resolve

import arbtok
from arbtok.dialects import Lect, spec_for_lang

#: The lects arbtok listed when orthography2ipa keyed every Arabic dialect ``ar-…``.
#: Each key stays an exact alias in orthography2ipa, so each still names a listed lect.
AR_KEYS = (
    "ar", "ar-AE", "ar-BH", "ar-BH-x-baharna", "ar-DZ", "ar-EG", "ar-EG-x-bedawi",
    "ar-EG-x-fayyum", "ar-EG-x-saidi", "ar-IQ", "ar-IQ-x-qeltu", "ar-JO", "ar-KW",
    "ar-LB", "ar-LY", "ar-Latn-buckwalter", "ar-MA", "ar-MR", "ar-NG", "ar-OM",
    "ar-OM-x-dhofari", "ar-PS", "ar-QA", "ar-SA-x-dawasir", "ar-SA-x-hejaz",
    "ar-SA-x-janubi", "ar-SA-x-najd", "ar-SA-x-qassim", "ar-SA-x-rijal-alma",
    "ar-SA-x-shamali", "ar-SA-x-sharqiyya", "ar-SA-x-tihama-qahtan", "ar-SD", "ar-SY",
    "ar-TD", "ar-TN", "ar-TR-x-cukurova", "ar-TR-x-kinderib", "ar-YE",
    "ar-YE-x-highland", "ar-YE-x-manakha", "ar-x-gulf", "ar-x-levantine",
    "ar-x-maghrebi", "ar-x-mashriqi", "ar-x-peninsular", "arb",
)


def _registry_arabic_languages():
    """``ara`` and the languages the IANA subtag registry lists under the macrolanguage
    ``ar``, read from the copy langcodes ships, plus Hassaniya ``mey``, which the registry
    lists outside it and orthography2ipa files under Maghrebi Arabic."""
    path = Path(langcodes.__file__).parent / "data" / "language-subtag-registry.txt"
    members = {"ara", "mey"}
    for record in path.read_text(encoding="utf-8").split("%%"):
        fields = dict(line.split(": ", 1) for line in record.strip().splitlines()
                      if ": " in line)
        if fields.get("Macrolanguage") == "ar":
            members.add(fields["Subtag"])
    return members


def _declared_language(code):
    spec = get(code)
    while spec.iso639_3 is None and spec.parent:
        spec = get(spec.parent)
    return spec.iso639_3


def _arabic_codes():
    """A spec whose lineage declares no language is the language its key's primary
    subtag names; ``ar`` is the registry's two-letter subtag of the macrolanguage."""
    languages = _registry_arabic_languages() | {"ar"}
    return {c for c in available_codes()
            if resolve(c) == c
            and (_declared_language(c) or c.split("-")[0]) in languages}


def test_the_subtag_registry_lists_the_arabic_languages():
    """The oracle below reads real data, not an empty file."""
    languages = _registry_arabic_languages()
    assert {"arb", "arz", "ary", "ars", "apc", "afb", "acw", "shu"} <= languages
    assert not {"arc", "arn", "mlt", "jrb"} & languages


def test_supported_lects_matches_the_registry():
    codes = {lect.code for lect in arbtok.supported_lects()}
    assert codes == _arabic_codes()
    assert len(arbtok.supported_lects()) == len(_arabic_codes())


def test_every_ar_key_still_names_a_listed_lect():
    """A lect orthography2ipa re-keys by its ISO 639-3 code stays on the list."""
    codes = {lect.code for lect in arbtok.supported_lects()}
    assert {resolve(key) for key in AR_KEYS} <= codes
    assert len({resolve(key) for key in AR_KEYS}) == len(AR_KEYS)


def test_supported_lects_excludes_the_lookalike_languages():
    """arc (Aramaic) and arn (Mapudungun) sort next to Arabic but are not it. Maltese
    descends from ``ar`` in orthography2ipa and declares a language of its own."""
    codes = {lect.code for lect in arbtok.supported_lects()}
    assert not {"arc", "arn", "mt"} & codes


def test_a_spec_that_declares_no_language_is_named_by_its_key():
    """orthography2ipa keys Babalia Creole Arabic ``bbz`` with ``iso639_3: bbz``, or
    ``ar-TD-x-babalia`` with no declared language under a clade parent. The primary
    language subtag of the key names it Arabic, so it stays on the list either way."""
    codes = {lect.code for lect in arbtok.supported_lects()}
    assert resolve("bbz") in codes


def test_a_key_without_an_arabic_subtag_or_language_is_not_arabic():
    """The clade above Babalia declares no language, and its key names none."""
    from arbtok.dialects import _is_arabic_code

    assert not _is_arabic_code("x-clade-afro1255")


def test_every_listed_code_actually_resolves_to_itself():
    """A code the list advertises must be one ``lang=`` honours exactly."""
    for lect in arbtok.supported_lects():
        assert spec_for_lang(lect.code) == lect.code


def test_lects_are_sorted_and_carry_a_known_tier():
    lects = arbtok.supported_lects()
    assert lects == sorted(lects, key=lambda lect: lect.code)
    known = {"stub", "skeleton", "research", "production"}
    assert all(isinstance(lect, Lect) and lect.tier in known for lect in lects)


def test_msa_is_research_tier():
    assert next(l.tier for l in arbtok.supported_lects() if l.code == "ar") == "research"
