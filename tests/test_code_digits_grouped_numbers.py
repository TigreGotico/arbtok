"""Digits kept beside a Latin word are a name's digits, never a piece of a grouped number."""
import pytest

from arbtok.textnorm import TtsNorm, normalize_for_tts

KEEP = TtsNorm(keep_code_digits=True, cardinal_numbers=True, oblique_numbers=True, space_fused_hundreds=True,
               spoken_forms=False, canonical_unicode=False)


@pytest.mark.parametrize("written", ["cash price 99,999", "cash price 12,500 ريال", "price 1,250.50",
                                     "السعر 99,999 cash", "price ٩٩٬٩٩٩", "price ١٢٣٤٥"])
def test_a_grouped_number_after_a_latin_word_is_spoken_whole(written):
    said = normalize_for_tts(written, "ar", KEEP)
    assert not any(c.isdigit() for c in said), said


def test_a_models_digits_are_still_kept():
    assert normalize_for_tts("سيارة MG 5 بسعر 70,000", "ar", KEEP) == "سيارة MG 5 بسعر سبعين ألف"
    assert normalize_for_tts("7 Series موديل 2024", "ar", KEEP).startswith("7 Series ")
