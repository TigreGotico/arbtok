from arbtok.tokenizer import Sentence, WordToken, CharToken,  SHADDA, SUKUN, ALIF, LAM, TANWIN_FATH, SUN_LETTERS, WAW, FATHA, KASRA


# ==============================================================================
# 1. CHARTOKEN TESTS
# ==============================================================================
def test_char_token_linking():
    """
    Ensures that characters in a word know who their neighbors are.
    In Arabic, context (neighbors) determines how a letter is pronounced.
    """
    sentence = Sentence("بِت")  # "Bit"
    word = sentence.tokens[0]
    chars = word.tokens

    assert chars[0].surface == "ب"
    assert chars[0].is_first_char is True
    assert chars[0].next_token.surface == "ِ"  # The 'i' vowel
    assert chars[-1].is_last_char is True
    assert chars[-1].prev_token.surface == "ِ"


def test_token_positional_awareness():
    """
    Tests if tokens know where they are in the 'grand scheme' of the sentence.
    """
    sentence = Sentence("قَالَ ٱلْمَلِكُ")  # "The King said"
    words = sentence.tokens

    # Word 0: 'Said'
    assert words[0].is_first_word is True
    assert words[0].is_last_word is False

    # Word 1: 'The King'
    assert words[1].is_first_word is False
    assert words[1].is_last_word is True

    # Deep check on the first character of the second word
    first_char_w2 = words[1].tokens[0]
    assert first_char_w2.is_first_char is True
    assert first_char_w2.is_first_word is False  # It's first in word, but not in sentence


def test_sun_and_moon_logic():
    """
    Arabic consonants are split into 'Sun' and 'Moon' letters.
    When 'The' (Al-) meets a Sun letter, the 'L' becomes silent and
    the Sun letter is doubled (assimilated).
    """
    # "Al-Shams" (The Sun): starts with the definite article 'Al' followed by a Sun letter.
    WORD_SUN = f"{ALIF}{LAM}شَّمْس"
    # "Al-Qamar" (The Moon): starts with 'Al' followed by a Moon letter.
    WORD_MOON = f"{ALIF}{LAM}قَمَر"


    sun_word = WordToken(surface=WORD_SUN, word_idx=0)
    # The 3rd character (index 2) is the consonant after 'Al-'
    assert sun_word.tokens[2].is_sun is True
    assert sun_word.is_sun is True

    moon_word = WordToken(surface=WORD_MOON, word_idx=1)
    assert moon_word.tokens[2].is_moon is True
    assert moon_word.is_sun is False

    for sun in SUN_LETTERS:
        sun_letter = CharToken(surface=sun, char_idx=0)
        assert sun_letter.is_sun
        assert not sun_letter.is_moon


def test_diacritic_properties():
    """
    Test if the token correctly identifies Shadda (doubling) and
    Sukun (no vowel/stop).
    """
    # Word with Shadda: بَّ (B + Shadda + Fatha)
    text = f"ب{SHADDA}{FATHA}"
    word = WordToken(surface=text, word_idx=0)
    b_char = word.tokens[0]

    assert b_char.has_shada is True
    assert b_char.has_diacritic is True
    assert b_char.has_vowel_mark is False
    assert b_char.has_sukun is False
    assert b_char.is_silent is False

    # Testing Sukun (The 'Silence' mark)
    # Word: 'Ab' (Father) with a stop on the 'b'
    text_sukun = f"أَب{SUKUN}"
    word_sukun = WordToken(surface=text_sukun, word_idx=0)
    sukun = word_sukun.tokens[3]  # The sukun character itself
    ba_sukun = word_sukun.tokens[1]  # The 'b' character

    assert sukun.surface == SUKUN
    assert ba_sukun.is_silent
    assert sukun.is_silent
    assert ba_sukun.has_sukun is True
    assert ba_sukun.has_vowel_mark is False  # Sukun is not a vowel, it's a stop
    assert ba_sukun.has_diacritic is True


# ==============================================================================
# 2. WORDTOKEN TESTS
# ==============================================================================
def test_definite_article_detection():
    """
    'Al-' (ال) is the Arabic version of 'The'.
    It is always attached to the start of the word.
    """
    # "Al-Shams" (The Sun): starts with the definite article 'Al' followed by a Sun letter.
    WORD_SUN = f"{ALIF}{LAM}شَّمْس"
    # "Al-Qamar" (The Moon): starts with 'Al' followed by a Moon letter.
    WORD_MOON = f"{ALIF}{LAM}قَمَر"

    sun_word = WordToken(surface=WORD_SUN, word_idx=0)
    moon_word = WordToken(surface=WORD_MOON, word_idx=1)
    random_word = WordToken(surface="كِتَاب", word_idx=2)  # "Book"

    assert sun_word.has_definite_article is True
    assert moon_word.has_definite_article is True
    assert random_word.has_definite_article is False


def test_definite_article_edge_cases():
    """
    Test the 'Al-' (ال) detection logic across various word lengths.
    """
    # Standard: Al-Kitab
    word_al = WordToken(surface=f"{ALIF}{LAM}كِتَاب", word_idx=0)
    assert word_al.has_definite_article is True

    # Just "Al" (2 chars) - e.g. the word "ال" on its own
    word_just_al = WordToken(surface=f"{ALIF}{LAM}", word_idx=1)
    assert word_just_al.has_definite_article is True

    # Not an article: Starts with Waw
    word_no_al = WordToken(surface=f"{WAW}{ALIF}{LAM}كِتَاب", word_idx=2)
    assert word_no_al.has_definite_article is False


def test_sun_letter_logic_with_article():
    """
    When 'Al-' is present, is_sun should check the THIRD character.
    When 'Al-' is absent, it should check the FIRST character.
    """
    # Sun Letter: Al-Shams (ش is sun)
    shams = WordToken(surface=f"{ALIF}{LAM}شَمْس", word_idx=0)
    assert shams.has_definite_article is True
    assert shams.is_sun is True

    # Moon Letter: Al-Qamar (ق is moon)
    qamar = WordToken(surface=f"{ALIF}{LAM}قَمَر", word_idx=1)
    assert qamar.is_sun is False

    # No article: Shams (starts with sun)
    just_shams = WordToken(surface="شَمْس", word_idx=2)
    assert just_shams.is_sun is True


def test_proclitic_heuristic():
    """
    Test the 1-2 character heuristic for clitics like 'and' (و), 'for' (ل), etc.
    """
    # Clitic: Wa (و)
    assert WordToken(surface=f"{WAW}", word_idx=0).is_proclitic is True
    # Clitic: 'Bi' (With/By)
    assert WordToken(surface=f"بِ", word_idx=1).is_proclitic is True
    # Clitic: Bi + Kasra (بِ)
    assert WordToken(surface=f"ب{KASRA}", word_idx=1).is_proclitic is True

    # Not Clitic: Short word but not in CLITIC_BASES (e.g., 'An' - أَنْ)
    assert WordToken(surface=f"أَنْ", word_idx=2).is_proclitic is False

    # Not Clitic: Length > 2 (e.g., 'Walad' - وَلَد)
    assert WordToken(surface="وَلَد", word_idx=3).is_proclitic is False

    # A long word like 'Library'
    assert WordToken(surface="مَكْتَبَة", word_idx=2).is_proclitic is False
    # 'Basim' (بَاسِم) - A name. Starts with 'Ba', but length is > 2.
    assert WordToken(surface="بَاسِم", word_idx=2).is_proclitic is False

    # A False Positive?
    # 'Bar' (بَر) - means 'Land'. Length 2 (Letter + Vowel).
    # This starts with 'Ba' (a clitic base) and is short.
    bar = WordToken(surface=f"بَر", word_idx=1)
    assert bar.is_proclitic is False


def test_tanwin_detection():
    """
    Tanwin is a special 'n' sound added to the end of nouns to
    indicate they are indefinite (e.g., 'a book' vs 'the book').
    """
    text = f"بَابً"  # "Baban" (A door)
    word = WordToken(surface=text, word_idx=0)
    last_char = word.tokens[-1]

    assert last_char.is_tanwin is True
    assert last_char.surface == TANWIN_FATH


# ==============================================================================
# 3. SENTENCE TESTS
# ==============================================================================

def test_sentence_token_linking_integrity():
    """
    Verify that Sentence.tokens correctly builds a bidirectional linked list
    of WordTokens.
    """
    text = "ذَهَبَ الطَّالِبُ إِلَى الْمَدْرَسَةِ"
    sentence = Sentence(text)
    tokens = sentence.tokens

    assert len(tokens) == 4

    # Check forward links
    assert tokens[0].next_word == tokens[1]
    assert tokens[1].next_word == tokens[2]

    # Check backward links
    assert tokens[3].prev_word == tokens[2]
    assert tokens[2].prev_word == tokens[1]

    # Check boundaries
    assert tokens[0].prev_word is None
    assert tokens[3].next_word is None


def test_complex_whitespace_and_punctuation_splitting():
    """
    The tokenizer should handle multiple spaces, tabs, and clusters of
    punctuation (ASCII and Arabic mixed).
    """
    # Text with double spaces, a tab, and mixed punct
    text = "قَالَ:   هَلْ\tأَنْتَ بِخَيْرٍ؟!"
    sentence = Sentence(text)

    # Expected: [قَالَ, :, هَلْ, أَنْتَ, بِخَيْرٍ, ؟, !]
    surfaces = [t.surface for t in sentence.tokens]
    assert "قَالَ" in surfaces
    assert ":" in surfaces
    assert "؟" in surfaces
    assert "!" in surfaces

    # Verify no whitespace tokens were included
    for t in sentence.tokens:
        assert not t.surface.isspace()


def test_sentence_normalization():
    """
    Ensure that normalizing the sentence also normalizes the
    constituent words and their characters.
    """
    # Word with wrong Shadda order
    text = f"يُسَب{KASRA}ّح"
    sentence = Sentence(text)

    # Check the word level
    word = sentence.tokens[0]
    assert word.normalized == f"يُسَبّ{KASRA}ح"

    # Check the sentence level normalization
    assert sentence.normalized == f"يُسَبّ{KASRA}ح"


def test_sentence_tokenization_with_punctuation():
    """
    Verify WordToken.is_punct correctly identifies individual
    punctuation marks separated by the tokenizer.
    """
    text = "هَلَا، كَيْفَ؟"  # "Hala, how?" (Hello, how [are you]?)
    sentence = Sentence(text)
    tokens = sentence.tokens

    # Expected: [Word(Hala), Punct(،), Word(Kayfa), Punct(؟)]
    assert len(tokens) == 4
    assert tokens[0].is_punct is False
    assert tokens[1].is_punct is True
    assert tokens[1].surface == "،"  # Arabic comma
    assert tokens[2].is_punct is False
    assert tokens[3].is_punct is True
    assert tokens[3].surface == "؟"  # Arabic question mark

    text = "سَلَام، كَيْفَ؟"
    tokens = Sentence(text).tokens

    # tokens[0] = سَلَام
    # tokens[1] = ،
    # tokens[2] = كَيْفَ
    # tokens[3] = ؟
    assert tokens[0].is_punct is False
    assert tokens[1].is_punct is True
    assert tokens[1].surface == "،"
    assert tokens[2].is_punct is False
    assert tokens[3].is_punct is True
    assert tokens[3].surface == "؟"