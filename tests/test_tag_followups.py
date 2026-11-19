"""Tag resolution: linear work on long tags, non-Arabic tags, extlang forms and
retired codes. Each expected lect comes from linguatag, langcodes (CLDR), the
ISO 639-3 tables or orthography2ipa, never from arbtok."""
import langcodes
import pytest
from linguatag import standardize_lang
from orthography2ipa import WordContext, available_codes, get, resolve

from arbtok import dialects, lect_code, spec_for_lang, supported_lects
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


@pytest.mark.parametrize("tag", ["ajp", "AJP", "ar-ajp", "AR_AJP", "ajp-Arab",
                                 "ar-ajp-Arab", "ajp-Latn", "ajp-x-cairo"])
def test_a_bare_ajp_tag_keeps_its_jordanian_lect(tag):
    """orthography2ipa keys bare ajp to apc-JO, and the tag keeps that lect, where
    bare apc is the region-less apc lect. RFC 5646 section 3.1.7: the extlang form
    ar-ajp and ajp are the same tag. A script the lect reads changes nothing, and a
    private-use subtag that names no dialect is ignored."""
    assert resolve("ajp") == "apc-JO"
    assert spec_for_lang(tag) == "apc-JO"


@pytest.mark.parametrize("tag", ["ara", "ara-Latn", "ara-Arab", "ara-EG", "ara-Latn-EG"])
def test_the_three_letter_code_of_ar_reads_as_ar(tag):
    """``ara`` is the ISO 639-2 code of ``ar``. RFC 5646 section 2.2.1 registers only
    the two-letter subtag for such a language, and linguatag reads ``ara`` as ``ar``,
    so both spellings name the same lect."""
    assert spec_for_lang(tag) == spec_for_lang("ar" + tag[3:])


@pytest.mark.parametrize("script", ["Hebr", "Cyrl"])
def test_a_script_the_jordanian_lect_does_not_read_reads_as_apc_does(script):
    """apc-JO reads Arabic script, and Latin script as Arabizi, and no other."""
    assert spec_for_lang(f"ajp-{script}") == spec_for_lang(f"apc-{script}") != "apc-JO"


@pytest.mark.parametrize("tag, lect", [("ajp-x-najdi", "ar-SA-x-najd"),
                                       ("ajp-x-gulf", "ar-x-gulf")])
def test_a_dialect_named_after_a_retired_code_wins(tag, lect):
    """A dialect named in a subtag names its lect, after a retired code as after
    any other language subtag."""
    assert spec_for_lang(tag) == resolve(lect)


def test_a_retired_code_whose_spec_reads_no_arabic_script_reads_as_its_successor():
    """ISO 639-3 retirements: ajt (Judeo-Tunisian Arabic) merged into aeb,
    effective 2022-01-20, and RFC 5646 section 4.5 replaces the subtag with its
    Preferred-Value. orthography2ipa keeps an ajt spec for Hebrew script, which
    reads no Arabic text, so it is not a lect and the tag reads as Tunisian
    Arabic."""
    assert get("ajt").script == "Hebrew"
    assert "ajt" not in {lect.code for lect in supported_lects()}
    for tag in ("ajt", "AJT", "ajt-x-cairo", "ajt_u_nu_latn", "ajt-Arab", "ajt-TN"):
        assert spec_for_lang(tag) == "aeb-TN", tag
