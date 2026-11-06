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
