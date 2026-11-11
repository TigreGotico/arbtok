"""Which language tags name an Arabic variety, and which rules act on the answer."""
import pytest

from arbtok import is_arabic_lang
from arbtok.dialects import spec_for_lang
from arbtok.textnorm import TtsNorm, normalize_for_tts

PERCENT = TtsNorm(speak_percent=True, cardinal_numbers=True, spoken_forms=False, canonical_unicode=False)


@pytest.mark.parametrize("tag", ["ar", "AR", "ar-SA", "ar-SA-x-najd", "ar-x-gulf", "AR-eg",
                                 "arb", "ARB", "arz", "ary", "ars", "apc", "acm", "aeb", "afb", "ayl"])
def test_an_arabic_variety_is_arabic_however_it_is_named(tag):
    assert is_arabic_lang(tag)


@pytest.mark.parametrize("tag", ["en", "en-GB", "fr-FR", "arc", "arn", "", "a", "arcadian",
                                 "fa", "ur", "und-Arab", "mt", "mlt"])
def test_a_language_that_is_not_arabic_is_not(tag):
    """``arc`` is Aramaic and ``arn`` is Mapudungun: they sort beside the Arabic codes
    and are unrelated languages. Persian, Urdu and an undetermined language are written
    in Arabic script and are not Arabic. Maltese descends from Arabic and is its own
    language."""
    assert not is_arabic_lang(tag)


@pytest.mark.parametrize("tag", ["ara", "ARA", "ara-SA", "ara_EG", "ara-x-made-up"])
def test_the_iso_639_2_code_of_arabic_is_arabic(tag):
    """``ara`` is the ISO 639-2 code of Arabic, and CLDR aliases it to ``ar``. Ruling:
    linguatag is the authority on which tags are Arabic, and it counts ``ara``."""
    assert is_arabic_lang(tag)


@pytest.mark.parametrize("tag", ["mey", "mey-MR", "mey-Arab-MR", "acy", "acy-CY", "pga", "pga-SS",
                                 "ar-Latn", "ar-Latn-x-buckwalt", "arz-Latn"])
def test_an_arabic_variety_is_arabic_in_any_script(tag):
    """Hassaniya and the Arabic varieties written in Latin script are Arabic. The
    language subtag decides, not the script."""
    assert is_arabic_lang(tag)


@pytest.mark.parametrize("tag", ["ar", "ara", "arb", "arz-EG", "mey-MR", "acy", "pga", "ar-Latn",
                                 "ar_SA", "AR-eg", "ary-x-made-up", "arc", "arn", "mt", "fa", "und-Arab",
                                 "en", "", "a", "x-ar"])
def test_linguatag_decides_which_tags_are_arabic(tag):
    """Ruling: linguatag is the authority on which tags are Arabic. arbtok asks it and
    keeps no list of its own."""
    from linguatag import is_arabic_variety
    assert is_arabic_lang(tag) is is_arabic_variety(tag)


def test_the_predicate_answers_what_the_caller_wrote_where_resolution_cannot():
    """``spec_for_lang`` resolves an unknown tag to MSA, so it says Arabic to everything."""
    assert spec_for_lang("en") == "ar"
    assert not is_arabic_lang("en")


@pytest.mark.parametrize("tag", ["arb", "arz", "ary", "ars", "apc", "AR-eg"])
def test_a_rule_that_speaks_arabic_accepts_every_arabic_variety(tag):
    assert normalize_for_tts("4.5%", tag, PERCENT) == "أربعة فاصلة خمسة في المئة"


@pytest.mark.parametrize("tag", ["en", "fr-FR", "arc"])
def test_a_rule_that_speaks_arabic_still_refuses_another_language(tag):
    with pytest.raises(ValueError, match="speak Arabic"):
        normalize_for_tts("4.5%", tag, PERCENT)


def test_every_arabic_spec_the_package_resolves_passes_the_predicate():
    from arbtok.dialects import supported_lects
    assert all(is_arabic_lang(lect.code) for lect in supported_lects())


def test_the_predicate_does_not_decide_which_specs_are_supported():
    """It reads a caller's tag. Which registry codes name an Arabic spec is a narrower
    question and stays where it was: the registry holds specs for Arabic languages that
    are not among the varieties this package ships a lect for."""
    from arbtok import dialects
    assert not dialects._is_arabic_code("arz") and is_arabic_lang("arz")


def test_the_normalizer_imports_without_the_dialect_machinery():
    import subprocess, sys
    subprocess.run([sys.executable, "-c", "import arbtok.textnorm"], check=True)
