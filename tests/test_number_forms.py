"""Cardinals in the words a lect uses, from the number parser and from a caller's own."""
import re

import pytest

from arbtok.dialects import lect_code
from arbtok.textnorm import KSA_VOICE_AGENT, TtsNorm, normalize_for_tts

DIALECT = TtsNorm(cardinal_numbers=True, oblique_numbers=True,
                  space_fused_hundreds=True, dialect_numbers=True,
                  spoken_forms=False, canonical_unicode=False)


@pytest.mark.parametrize("tag, code", [
    ("ar-SA-x-hejaz", "acw"), ("ar-x-hijazi", "acw"), ("ar-SA-hijazi", "acw"),
    ("ar-x-gulf", "afb"), ("ar-AE", "afb"), ("ar-KW", "afb"), ("ar-QA", "afb"), ("ar-BH", "afb"),
    ("ar-EG", "arz"), ("ar-SA", "ars"), ("ar-SA-x-najd", "ars"),
])
def test_a_tag_carries_the_code_of_the_lect_it_names(tag, code):
    """A Gulf state has no code of its own: its spec declares ar-x-gulf as its parent,
    so the code comes off the parent chain rather than off a list of states."""
    assert lect_code(tag) == code


@pytest.mark.parametrize("tag", ["ar", "arb", "ar-MA", "ar-IQ", "ar-x-levantine"])
def test_a_tag_naming_no_lect_carries_no_code(tag):
    assert lect_code(tag) is None


@pytest.mark.parametrize("tag", ["ar", "ar-SA", "ar-SA-x-najd", "ar-MA", "ar-IQ", "ar-x-levantine"])
def test_a_lect_with_no_cited_words_keeps_the_literary_ones(tag):
    """Najdi is the product's target lect and the parser has no words for it: no source
    has been read for it, and a form no source gives is not written."""
    assert normalize_for_tts("عندك 15 رسالة", tag, DIALECT) == "عندك خمسة عشر رسالة"


def test_the_classical_code_is_accepted_by_a_rule_that_speaks_arabic():
    """``arb`` is Classical Arabic and a lect this package resolves, so an Arabic-only rule
    takes it. It names no lect of its own, so the cardinal stays the literary one."""
    assert normalize_for_tts("15", "arb", DIALECT) == "خمسة عشر"
    assert normalize_for_tts("4%", "arb", TtsNorm(speak_percent=True, spoken_forms=False)) \
        == "4 في المئة"


@pytest.mark.parametrize("tag, spoken", [
    ("ar", "عندك خمسة عشر رسالة"),
    ("ar-SA-x-hejaz", "عندك خمسطعش رسالة"),
    ("ar-AE", "عندك خمسطعش رسالة"),
    ("ar-EG", "عندك خمستاشر رسالة"),
])
def test_a_teen_is_spoken_the_way_the_lect_says_it(tag, spoken):
    assert normalize_for_tts("عندك 15 رسالة", tag, DIALECT) == spoken


@pytest.mark.parametrize("tag, spoken", [
    ("ar", "السعر ثلاث مئة وخمسين ريال"),
    ("ar-SA-x-hejaz", "السعر تلت مية وخمسين ريال"),
    ("ar-AE", "السعر ثلاث مية وخمسين ريال"),
    ("ar-EG", "السعر تلت مية وخمسين ريال"),
])
def test_a_hundred_inside_a_composed_number_takes_the_lects_word(tag, spoken):
    """The parser composes and supplies the words. A colloquial hundred is spaced for the
    synthesizer the same way the standard one is."""
    assert normalize_for_tts("السعر 350 ريال", tag, DIALECT) == spoken


def test_the_three_lects_do_not_say_a_teen_alike():
    """A lect earns its code here by differing from the others as well as from MSA."""
    said = {tag: normalize_for_tts("عندك 12 رسالة", tag, DIALECT) for tag in
            ("ar", "ar-SA-x-hejaz", "ar-x-gulf", "ar-EG")}
    assert said["ar-EG"] != said["ar-SA-x-hejaz"] != said["ar"] and said["ar-EG"] != said["ar"]
    assert said["ar-EG"] == "عندك اتناشر رسالة"


def test_the_egyptian_words_are_read_for_egypt_and_not_for_its_neighbours():
    assert normalize_for_tts("عندي 100 ريال", "ar-EG", DIALECT) == "عندي مية ريال"
    for tag in ("ar-SA-x-najd", "ar-LY", "ar-x-levantine"):
        assert normalize_for_tts("عندي 100 ريال", tag, DIALECT) == "عندي مئة ريال"


def test_a_teen_inside_a_year_is_replaced_and_the_rest_is_not():
    assert normalize_for_tts("المبلغ 2018 ريال", "ar-SA-x-hejaz", DIALECT) == "المبلغ ألفين وتمنطعش ريال"


def test_digit_by_digit_readings_take_the_lects_words_too():
    assert normalize_for_tts("رقمك 0553179", "ar-SA-x-hejaz", KSA_VOICE_AGENT, dialect_numbers=True) \
        == "رقمك صفر خمسة خمسة تلاتة واحد سبعة تسعة"
    assert normalize_for_tts("رقمك 0553179", "ar", KSA_VOICE_AGENT) \
        == "رقمك صفر خمسة خمسة ثلاثة واحد سبعة تسعة"


def test_the_flag_is_off_by_default_so_every_number_on_record_is_reproduced():
    for tag in ("ar", "ar-SA-x-hejaz", "ar-AE"):
        assert normalize_for_tts("عندك 15 رسالة", tag, KSA_VOICE_AGENT) == "عندك خمسة عشر رسالة"


def test_a_callers_own_forms_are_used_with_no_lect_and_win_over_one():
    assert normalize_for_tts("عندي 100 ريال", "ar", KSA_VOICE_AGENT.with_number_forms({100: "مية"})) \
        == "عندي مية ريال"
    both = TtsNorm(cardinal_numbers=True, oblique_numbers=True, dialect_numbers=True, spoken_forms=False,
                   canonical_unicode=False).with_number_forms({15: "خمستاشر"})
    assert normalize_for_tts("عندك 15 رسالة", "ar-SA-x-hejaz", both) == "عندك خمستاشر رسالة"
    assert normalize_for_tts("عندك 115 رسالة", "ar-SA-x-hejaz", both) == "عندك مية وخمستاشر رسالة"


@pytest.mark.parametrize("forms", [{15: ""}, {15: "  "}, {15: 15}, {"15": "خمسطعش"}, {True: "واحد"}, {-1: "واحد"}])
def test_a_form_that_is_not_a_value_and_a_word_is_refused(forms):
    with pytest.raises(TypeError):
        TtsNorm().with_number_forms(forms)


def test_the_config_says_which_words_were_used():
    """The words a lect is read with are the parser's, so naming the parser names them."""
    dialect = TtsNorm(dialect_numbers=True, spoken_forms=False).describe()
    assert re.search(r"; ovos-number-parser \S+", dialect)
    assert TtsNorm().with_number_forms({100: "مية"}).describe() != \
        TtsNorm().with_number_forms({100: "ميه"}).describe()


def test_these_rules_speak_arabic_and_refuse_another_language():
    for flags in ({"dialect_numbers": True}, {}):
        config = TtsNorm(spoken_forms=False, canonical_unicode=False, **flags)
        if flags:
            with pytest.raises(ValueError, match="dialect_numbers"):
                normalize_for_tts("15", "en", config)
        else:
            assert normalize_for_tts("15", "en", config) == "15"
    with pytest.raises(ValueError, match="number_forms"):
        normalize_for_tts("15", "en", TtsNorm(spoken_forms=False).with_number_forms({15: "خمسطعش"}))
