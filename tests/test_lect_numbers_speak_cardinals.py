"""Asking for a lect's number words, or for your own, speaks numbers without also
having to ask for the cardinals."""
from arbtok.textnorm import TtsNorm, normalize_for_tts


def test_dialect_numbers_alone_speaks_the_lects_words():
    alone = normalize_for_tts("عندي 12 سيارة", "ar-EG", TtsNorm(dialect_numbers=True))
    both = normalize_for_tts("عندي 12 سيارة", "ar-EG", TtsNorm(dialect_numbers=True, cardinal_numbers=True))
    assert alone == both
    assert "اتناشر" in alone


def test_number_forms_alone_speaks_your_words():
    config = TtsNorm().with_number_forms({15: "خمستاشر"})
    assert "خمستاشر" in normalize_for_tts("عندي 15 سيارة", "ar", config)


def test_without_either_numbers_are_the_literary_spoken_forms():
    assert "اثنا عشر" in normalize_for_tts("عندي 12 سيارة", "ar-EG", TtsNorm())
