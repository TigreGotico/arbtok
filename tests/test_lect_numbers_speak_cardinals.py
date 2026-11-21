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
    # سيارة ends in taa' marbuuTa and is feminine (Ryding 2005, p. 121), and twelve before a
    # feminine noun is اثنتا عشرة (Ryding 2005, pp. 339-345).
    assert "اثنتا عشرة" in normalize_for_tts("عندي 12 سيارة", "ar-EG", TtsNorm())


def test_a_lect_the_parser_does_not_serve_reads_the_literary_numbers():
    """The number parser has no words for Hassaniya, ``mey``, and refuses the code. A lect
    with no words of its own keeps the literary ones, as ``dialect_numbers`` documents."""
    config = TtsNorm(dialect_numbers=True, spoken_forms=False, canonical_unicode=False)
    for lang in ("mey-MR", "mey"):
        assert normalize_for_tts("عندي 4 كتب و 13 قلم", lang, config) == "عندي أربعة كتب و ثلاثة عشر قلم"
