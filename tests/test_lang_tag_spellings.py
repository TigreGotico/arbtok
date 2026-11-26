"""A language tag reads the same in every spelling linguatag standardizes it from."""
import datetime

import pytest
from ovos_date_parser import nice_date
from ovos_number_parser import pronounce_number

from arbtok.espeak_wrapper import EspeakPhonemizer
from arbtok.textnorm import cldr_units, normalize_for_tts, spelled_codes
from arbtok.util import normalize


@pytest.mark.parametrize("tag", ["en_US", "EN-us", "en_us", "eng-US", "en-Latn-US"])
def test_american_english_in_any_spelling_writes_the_month_first(tag):
    expected = nice_date(datetime.date(2024, 12, 3), "en-US")
    assert expected in normalize("on 12/03/2024", tag)


@pytest.mark.parametrize("tag", ["en", "en-GB", "EN_gb", "en-AU"])
def test_other_english_writes_the_day_first(tag):
    expected = nice_date(datetime.date(2024, 3, 12), "en-GB")
    assert expected in normalize("on 12/03/2024", tag)


@pytest.mark.parametrize("tag", ["pt_BR", "PT-br", "pt_pt", "por", "PT"])
def test_portuguese_in_any_spelling_reads_a_comma_as_the_decimal_point(tag):
    assert pronounce_number(1234.56, "pt-BR") in normalize("Paguei 1.234,56", tag)


@pytest.mark.parametrize("tag", ["ara", "AR", "ar_SA", "AR_sa", "ar-arz-EG", "arz-EG"])
def test_an_arabic_tag_in_any_spelling_reads_the_arabic_tables(tag):
    assert cldr_units(tag) == cldr_units("ar")
    assert spelled_codes(tag) == spelled_codes("ar")


@pytest.mark.parametrize("tag", ["ara", "AR", "ar_SA", "AR_sa"])
def test_modern_standard_arabic_in_any_spelling_reads_like_ar(tag):
    assert normalize("5 km", tag) == normalize("5 km", "ar")
    assert "كيلومتر" in normalize("5 km", tag)


@pytest.mark.xfail(raises=AssertionError, strict=True, reason="TigreGotico/arbtok#373: normalize reads a counted unit "
                   "in the singular; CLDR ar gives the few form for 3 to 10")
def test_a_counted_unit_takes_its_cldr_plural():
    assert normalize("5 km", "ar") == "خمسة كيلومترات"


@pytest.mark.parametrize("tag", ["fa", "en", "arc", "arn", "mt"])
def test_a_tag_that_is_not_arabic_has_no_arabic_tables(tag):
    with pytest.raises(ValueError):
        cldr_units(tag)
    with pytest.raises(ValueError):
        spelled_codes(tag)


@pytest.mark.parametrize("tag", ["en_GB", "EN-gb", "en_gb", "eng-GB"])
def test_british_english_in_any_spelling_names_the_rp_voice(tag):
    assert EspeakPhonemizer.get_lang(tag) == "en-gb-x-rp"


# The voices are espeak-ng's own names (ESPEAK_LANGS).
@pytest.mark.parametrize("tag,voice", [
    ("pt_BR", "pt-br"), ("PT_br", "pt-br"), ("por-BR", "pt-br"), ("pt-BR", "pt-br"),
    ("fr_BE", "fr-be"), ("fr_CH", "fr-ch"), ("es_419", "es-419"), ("es_MX", "es-419"),
    ("ru_LV", "ru-lv"), ("de-DE", "de"), ("pt", "pt"),
])
def test_a_tag_in_any_spelling_names_its_regional_voice(tag, voice):
    assert EspeakPhonemizer.get_lang(tag) == voice


@pytest.mark.parametrize("tag", ["arz-EG", "AR_sa", "ary", "apc"])
def test_spelling_out_codes_reads_every_arabic_lect(tag):
    spelled = normalize_for_tts("الرمز AB12 صحيح", tag, spell_out_codes=True)
    assert "AB12" not in spelled
    assert spelled == normalize_for_tts("الرمز AB12 صحيح", "ar", spell_out_codes=True)


@pytest.mark.parametrize("tag,diacritized", [
    ("ar", True), ("AR_sa", True), ("ara", True), ("arz-EG", True), ("ary", True),
    ("arc", False), ("arn", False), ("en", False),
])
def test_only_an_arabic_variety_is_diacritized(tag, diacritized):
    class Spy:
        def diacritize(self, text, pausal):
            return "diacritized"

    phonemizer = EspeakPhonemizer()
    phonemizer._tashkeel = Spy()
    assert (phonemizer.add_diacritics("نص", tag) == "diacritized") is diacritized
