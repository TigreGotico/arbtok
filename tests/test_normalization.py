from arbtok.tokenizer import normalize_unicode, SHADDA, FATHA, KASRA, DAMMA


def test_normalization_shadda_ordering():
    """
    In Arabic, the 'Shadda' (which doubles a consonant) should technically
    come BEFORE the vowel.
    Input: 'B' + 'Fatha' (a) + 'Shadda' (double)
    Output: 'B' + 'Shadda' (double) + 'Fatha' (a)
    """
    # Character 'Ba' (ب)
    ba = '\u0628'
    # Input has vowel BEFORE Shadda (Incorrect sequence)
    incorrect_order = f"{ba}{FATHA}{SHADDA}"
    # Expected: Shadda then Vowel
    expected_order = f"{ba}{SHADDA}{FATHA}"
    assert normalize_unicode(incorrect_order) == expected_order

    word_wrong_order = f"يُسَب{KASRA}{SHADDA}ح"
    word_correct_order = f"يُسَب{SHADDA}{KASRA}ح"
    assert normalize_unicode(word_wrong_order) == word_correct_order

    # Check Shadda swap logic with all three primary short vowels.
    vowels = [FATHA, DAMMA, KASRA]
    for v in vowels:
        input_str = f"{ba}{v}{SHADDA}"
        expected = f"{ba}{SHADDA}{v}"
        assert normalize_unicode(input_str) == expected


def test_unicode_decomposition_nfc():
    """
    Unicode allows some Arabic characters to be written in two ways:
    1. As a single pre-composed character (NFC).
    2. As a base letter + a separate hamza mark (NFD).
    Normalization should force them to be identical.
    """
    # Alef with Hamza Above (أ)
    # Method 1: Single code point \u0623
    combined = "\u0623"
    # Method 2: Alef \u0627 + Hamza mark \u0654 (Decomposed)
    decomposed = "\u0627\u0654"

    assert normalize_unicode(combined) == normalize_unicode(decomposed)


def test_no_change_on_clean_text():
    """
    Ensure that text that is already correctly formatted doesn't break.
    """
    clean_text = "كِتَابٌ"  # 'Kitabun' (A book)
    assert normalize_unicode(clean_text) == clean_text

