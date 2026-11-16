"""Tag resolution: linear work on long tags, non-Arabic tags, extlang forms and
retired codes. Each expected lect comes from linguatag, langcodes (CLDR), the
ISO 639-3 tables or orthography2ipa, never from arbtok."""
import langcodes
import pytest
from linguatag import standardize_lang
from orthography2ipa import WordContext, available_codes, resolve

from arbtok import dialects, lect_code, spec_for_lang
from arbtok.plugin import ArbtokG2PPlugin


def _letters(n):
    """n distinct four-letter alphabetic subtags: aaaa, aaab, ..."""
    alphabet = "abcdefghijklmnopqrstuvwxyz"
    return ["".join(alphabet[(i // 26 ** k) % 26] for k in (3, 2, 1, 0)) for i in range(n)]


@pytest.fixture
def exact_calls(monkeypatch):
    calls = []
    real = dialects._exact_spec

    def counted(tag, codes):
        calls.append(tag)
        return real(tag, codes)

    monkeypatch.setattr(dialects, "_exact_spec", counted)
    return calls


LONG = 128


def test_a_long_tag_costs_work_in_proportion_to_its_length(exact_calls):
    """An ill-formed tag of 128 four-letter subtags after the script. Step 3 tries
    each shorter tag once, so the exact lookups grow with the length, not its square."""
    spec_for_lang("-".join(["acm", "Latn", *_letters(LONG)]))
    assert len(exact_calls) <= 2 * LONG + 10


def test_a_long_tag_reads_as_its_language():
    """The subtags after the script name nothing, so the tag reads as ``acm``."""
    assert spec_for_lang("-".join(["acm", "Latn", *_letters(LONG)])) == resolve("acm")


def test_cldr_reads_und_latn_ma_as_french_so_it_has_no_arabic_lect():
    assert langcodes.Language.get("und-Latn-MA").maximize().language == "fr"
    for tag in ("und-Latn-MA", "und_Latn_MA"):
        with pytest.raises(ValueError):
            spec_for_lang(tag)


@pytest.mark.parametrize("tag", ["fi", "en", "fr-FR", "mt", "ckb-IQ", "he-IL"])
def test_a_tag_that_is_not_arabic_raises(tag):
    with pytest.raises(ValueError, match="not an Arabic variety"):
        spec_for_lang(tag)
    assert lect_code(tag) is None


def test_a_plugin_for_another_language_raises():
    with pytest.raises(ValueError):
        ArbtokG2PPlugin(lang="fi")


def test_a_word_in_another_language_keeps_the_plugin_lect():
    plugin = ArbtokG2PPlugin(lang="arz-EG", diacritize=False)
    assert plugin._resolve_lang(WordContext(lang="en")) == "arz-EG"


@pytest.mark.parametrize("tag", ["ar-arz", "ar-arz-EG", "ar-acm", "ar_arz"])
def test_the_extlang_form_names_the_language_it_stands_for(tag):
    """RFC 5646 section 4.5: an extlang is replaced by its Preferred-Value."""
    language = standardize_lang(tag)
    assert language in ("arz", "arz-EG", "acm")
    assert spec_for_lang(tag) == resolve(language)


@pytest.mark.parametrize("region", ["JO", "PS", "LB", "SY"])
@pytest.mark.parametrize("script", ["", "Arab-"])
def test_a_retired_ajp_tag_reads_as_apc(region, script):
    """ISO 639-3 retirements: ajp (South Levantine Arabic) merged into apc,
    effective 2023-01-20. Each apc-<region> is an orthography2ipa spec key."""
    assert f"apc-{region}" in available_codes()
    assert spec_for_lang(f"ajp-{script}{region}") == f"apc-{region}"


def test_a_bare_ajp_tag_keeps_its_jordanian_lect():
    """orthography2ipa keys bare ajp to apc-JO. That is not MSA, so the tag is
    not read again as apc, whose bare form is the region-less apc lect."""
    assert resolve("ajp") == "apc-JO"
    assert spec_for_lang("ajp") == "apc-JO"
