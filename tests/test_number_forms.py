"""Cardinals in the words a lect uses, from the bundled tables and from a caller's own."""
import re
from pathlib import Path

import pytest

from arbtok import number_forms as nf
from arbtok.textnorm import KSA_VOICE_AGENT, TtsNorm, normalize_for_tts

DIALECT = TtsNorm(cardinal_numbers=True, oblique_numbers=True,
                  space_fused_hundreds=True, dialect_numbers=True,
                  spoken_forms=False, canonical_unicode=False)
ARABIC = re.compile(r"[ء-ي ]+")


def _rows(code):
    path = Path(nf.__file__).parent / "data" / "number_forms" / f"{code}.tsv"
    return [line.split("\t") for line in path.read_text(encoding="utf-8").splitlines()
            if line and not line.startswith("#")]


def test_a_table_ships_for_the_lects_named_and_for_no_others():
    assert nf.bundled_lects() == ["ar-SA-x-hejaz", "ar-x-gulf"]


@pytest.mark.parametrize("code", ["ar-SA-x-hejaz", "ar-x-gulf"])
def test_every_row_is_a_value_a_speakable_word_and_a_source(code):
    rows = _rows(code)
    assert len(rows) > 15
    for value, word, source in rows:
        assert value.isdigit() and ARABIC.fullmatch(word), (value, word)
        assert len(source.split()) >= 3 and re.search(r"\b(p\.|pp\.)\s*\d", source), (value, source)
    assert len({int(value) for value, _, _ in rows}) == len(rows)


def test_a_row_without_a_source_is_refused(tmp_path):
    table = tmp_path / "ar-XX.tsv"
    table.write_text("13\tتلاطعش\n", encoding="utf-8")
    with pytest.raises(ValueError, match="value, form and source"):
        nf._read(table)
    table = tmp_path / "ar-YY.tsv"
    table.write_text("13\tتلاطعش\t \n", encoding="utf-8")
    with pytest.raises(ValueError, match="value, form and source"):
        nf._read(table)


def test_a_value_named_twice_is_refused(tmp_path):
    table = tmp_path / "ar-ZZ.tsv"
    table.write_text("13\tتلاطعش\tsomewhere p. 1\n13\tثلاطعش\tsomewhere p. 2\n", encoding="utf-8")
    with pytest.raises(ValueError, match="has a form already"):
        nf._read(table)


@pytest.mark.parametrize("tag, table", [
    ("ar-SA-x-hejaz", "hejaz"), ("ar-x-hijazi", "hejaz"), ("ar-SA-hijazi", "hejaz"),
    ("ar-x-gulf", "gulf"), ("ar-AE", "gulf"), ("ar-KW", "gulf"), ("ar-QA", "gulf"), ("ar-BH", "gulf"),
])
def test_a_lect_reads_its_own_table_or_its_groups(tag, table):
    forms = nf.number_forms(tag)
    assert forms[15] == "خمسطعش"
    assert forms[13] == ("تلاطعش" if table == "hejaz" else "ثلاطعش")


@pytest.mark.parametrize("tag", ["ar", "ar-SA", "ar-SA-x-najd", "ar-EG", "ar-MA", "ar-IQ", "ar-x-levantine"])
def test_a_lect_with_no_cited_table_has_no_forms(tag):
    """Najdi is the product's target lect and has no table: no source has been read for it,
    and a form no source gives is not written."""
    assert nf.number_forms(tag) == {}
    assert normalize_for_tts("عندك 15 رسالة", tag, DIALECT) == "عندك خمسة عشر رسالة"


def test_the_classical_code_is_accepted_by_a_rule_that_speaks_arabic():
    """``arb`` is Classical Arabic and a lect this package resolves, so an Arabic-only rule
    takes it. It has no number table of its own, so the cardinal stays the parser's."""
    assert normalize_for_tts("15", "arb", DIALECT) == "خمسة عشر"
    assert normalize_for_tts("4%", "arb", TtsNorm(speak_percent=True, spoken_forms=False)) \
        == "4 في المئة"


@pytest.mark.parametrize("tag, spoken", [
    ("ar", "عندك خمسة عشر رسالة"),
    ("ar-SA-x-hejaz", "عندك خمسطعش رسالة"),
    ("ar-AE", "عندك خمسطعش رسالة"),
])
def test_a_teen_is_spoken_the_way_the_lect_says_it(tag, spoken):
    assert normalize_for_tts("عندك 15 رسالة", tag, DIALECT) == spoken


@pytest.mark.parametrize("tag, spoken", [
    ("ar", "السعر ثلاث مئة وخمسين ريال"),
    ("ar-SA-x-hejaz", "السعر تلت مية وخمسين ريال"),
    ("ar-AE", "السعر ثلاث مية وخمسين ريال"),
])
def test_a_hundred_inside_a_composed_number_takes_the_lects_word(tag, spoken):
    """The parser composes; the table supplies the words. A colloquial hundred is spaced
    for the synthesizer the same way the standard one is."""
    assert normalize_for_tts("السعر 350 ريال", tag, DIALECT) == spoken


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


def test_a_callers_own_forms_are_used_with_no_table_and_win_over_one():
    assert normalize_for_tts("عندي 100 ريال", "ar", KSA_VOICE_AGENT.with_number_forms({100: "مية"})) \
        == "عندي مية ريال"
    both = TtsNorm(cardinal_numbers=True, oblique_numbers=True, dialect_numbers=True, spoken_forms=False,
                   canonical_unicode=False).with_number_forms({15: "خمستاشر"})
    assert normalize_for_tts("عندك 15 رسالة", "ar-SA-x-hejaz", both) == "عندك خمستاشر رسالة"


@pytest.mark.parametrize("forms", [{15: ""}, {15: "  "}, {15: 15}, {"15": "خمسطعش"}, {True: "واحد"}, {-1: "واحد"}])
def test_a_form_that_is_not_a_value_and_a_word_is_refused(forms):
    with pytest.raises(TypeError):
        TtsNorm().with_number_forms(forms)


def test_the_config_says_which_tables_and_which_words_were_used():
    plain = TtsNorm(cardinal_numbers=True, spoken_forms=False).describe()
    dialect = TtsNorm(cardinal_numbers=True, dialect_numbers=True, spoken_forms=False).describe()
    assert "number tables" not in plain and f"number tables {nf.tables_digest()}" in dialect
    assert TtsNorm().with_number_forms({100: "مية"}).describe() != \
        TtsNorm().with_number_forms({100: "ميه"}).describe()


def test_the_tables_digest_follows_the_files():
    digest = nf.tables_digest()
    assert re.fullmatch(r"[0-9a-f]{12}", digest)
    assert digest == nf.tables_digest()


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
