"""With dialect_numbers off, numbers are the literary words whatever lect the tag names."""
import pytest

from arbtok.textnorm import TtsNorm, normalize_for_tts

LITERARY = normalize_for_tts("عندي 12 سيارة و 15 باص", "ar")


@pytest.mark.parametrize("lang", ["arz", "ar-EG", "acw", "ar-SA-x-hejaz", "afb", "ar-x-gulf", "ars", "ar-SA"])
def test_a_lect_tag_reads_the_literary_numbers_by_default(lang):
    assert normalize_for_tts("عندي 12 سيارة و 15 باص", lang) == LITERARY


@pytest.mark.parametrize("code, tag", [("arz", "ar-EG"), ("acw", "ar-SA-x-hejaz")])
def test_a_code_and_its_tag_read_alike_with_lect_numbers_on(code, tag):
    config = TtsNorm(cardinal_numbers=True, dialect_numbers=True)
    assert normalize_for_tts("عندي 12 سيارة", code, config) == normalize_for_tts("عندي 12 سيارة", tag, config)


# 4 before كتب, whose singular كتاب is masculine, takes the form with ة, and 13 before a
# masculine noun is ثلاثة عشر: Ryding, A Reference Grammar of Modern Standard Arabic
# (2005), ch. 15, gender polarity of 3 to 10 and of the unit in 13 to 19.
@pytest.mark.parametrize("lang", ["ary", "ary-MA", "aeb-TN", "apc-SY", "arz", "arz-EG", "acw", "mey-MR"])
def test_the_cardinals_read_the_literary_numbers_with_lect_numbers_off(lang):
    config = TtsNorm(cardinal_numbers=True, spoken_forms=False, canonical_unicode=False)
    assert normalize_for_tts("عندي 4 كتب و 13 قلم", lang, config) == "عندي أربعة كتب و ثلاثة عشر قلم"
