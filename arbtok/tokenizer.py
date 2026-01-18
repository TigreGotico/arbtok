import dataclasses
import re
import string
import unicodedata
from typing import List, Optional, Set, Tuple

# helper constants, make it more readable for non-arabic speakers (me)
# each represent an arabic grapheme that maps to a IPA phoneme in ARABIC_TO_IPA
from arbtok.constants import (B, T, DJ, X, D, R, Z, S, F, Q, K, M, N, H, LAM, WAW, YA,
                              FATHA, DAMMA, KASRA, DAGGER_ALIF, MADD, SUKUN,
                              HAMZA, ALEF_HAMZA_ABOVE, ALEF_HAMZA_BELOW, WAW_HAMZA, YA_HAMZA,
                              TANWIN_FATH, TANWIN_KASR, TANWIN_DAMM,
                              ALIF_MAKSURA,  ALIF, ALEF_MADDA,
                              HAMZAT_AL_WASL, TA_MARBUTA, SHADDA,
                              SUN_LETTERS, CLITIC_BASES, PUNCT)
from arbtok.dialects import VOWEL_MAP, ARABIC_TO_IPA_CONSONANTS, DIACRITIC_TO_IPA, TANWIN_TO_IPA, WORD_EXCEPTIONS


def _reorder_diacritics(text: str) -> str:
    """
    Ensure Shadda (gemination) always precedes vowels.
    Incorrect input: Consonant + Kasra + Shadda
    Correct output:  Consonant + Shadda + Kasra
    """
    chars = list(text)
    i = 0
    while i < len(chars) - 1:
        curr = chars[i]
        next_char = chars[i + 1]

        # If current is vowel (Short Vowels) and next is Shadda -> Swap
        if curr in {FATHA, DAMMA, KASRA} and next_char == SHADDA:
            chars[i], chars[i + 1] = chars[i + 1], chars[i]
            i += 1  # Skip next since we just swapped into it
        i += 1
    return "".join(chars)


def normalize_unicode(text: str) -> str:
    """
    Normalize unicode to NFC (Normalization Form Canonical Composition).

    Note on Diacritic Order:
    In Arabic, the canonical order for stacking diacritics is usually:
    Base Char + Shadda + Vowel.
    NFC normalization generally handles this correctly, ensuring that
    a Shadda + Fatha sequence is combined or ordered consistently.
    This tokenizer relies on this standard order.
    """
    # 1. Standard Unicode normalization (NFC)
    text = unicodedata.normalize("NFC", text)
    # 2. Enforce Consonant -> Shadda -> Vowel order
    return _reorder_diacritics(text)


@dataclasses.dataclass
class CharToken:
    """
    Represents a single character in the text (letter, diacritic, or punctuation).
    Stores pointers to neighbors to allow context-aware IPA generation.
    """
    surface: str
    char_idx: int
    prev_token: Optional['CharToken'] = None
    next_token: Optional['CharToken'] = None
    word: Optional['WordToken'] = None

    @property
    def is_first_char(self) -> bool:
        return self.prev_token is None

    @property
    def is_first_word(self) -> bool:
        return self.word.prev_word is None and self.is_first_char

    @property
    def is_last_char(self) -> bool:
        return self.next_token is None

    @property
    def is_last_word(self) -> bool:
        return self.word.is_last_word and self.is_last_char

    @property
    def is_punct(self) -> bool:
        return self.surface in PUNCT

    @property
    def normalized(self) -> str:
        return normalize_unicode(self.surface)

    @property
    def is_vowel(self) -> bool:
        """Check if the produced IPA is a vowel."""
        # Note: 'j' and 'w' are semivowels/consonants in IPA, not vowels.
        return self.surface in VOWEL_MAP

    @property
    def has_diacritic(self) -> bool:
        return self.has_shada or self.has_sukun or self.has_vowel_mark

    @property
    def has_shada(self) -> bool:
        return self.next_token and self.next_token.surface == SHADDA

    @property
    def has_sukun(self) -> bool:
        return (self.next_token and self.next_token.surface == SUKUN) or \
            (self.next_token and self.next_token.next_token and self.next_token.next_token.surface == SUKUN)

    @property
    def has_vowel_mark(self) -> bool:
        return self.next_token and self.next_token.surface in DIACRITIC_TO_IPA

    @property
    def is_sun(self) -> bool:
        """Check if this is a Sun letter (assimilates definite article)."""
        return self.surface in SUN_LETTERS

    @property
    def is_moon(self) -> bool:
        return not self.is_sun

    @property
    def is_silent(self) -> bool:
        if self.has_sukun:
            return True
        return self.ipa == ""

    @property
    def is_tanwin(self) -> bool:
        return self.surface in TANWIN_TO_IPA

    @property
    def ipa(self) -> str:
        """
        Return an IPA fragment for this single character token.
        Context-sensitive adjustments that span *words* are handled in WordToken.
        Context-sensitive adjustments between *chars* (like Alif lengthening) happen here.
        """
        s = self.surface

        if self.is_punct:
            return s

        # handle definite article assimilation (ال)
        if self.word.has_definite_article:
            # The 'a' of al-
            if self.is_first_char:
                # Check 1: Is current word a proclitic? (always wasl)
                if self.word.prev_word and self.word.prev_word.is_proclitic:
                    return ""
                # Check 2: Does prev word end in a vowel? (Generalized Wasl)
                elif self.word.prev_word and self.word.prev_word.end_with_vowel:
                    return ""
                # Alif vowel (always 'a')
                return "a"

            # is second char
            if self.char_idx == 1:
                if self.next_token and self.next_token.is_moon:
                    return "l"
                # Sun Letter: Assimilate 'l'
                return ""

        # Hamzat al-wasl (ٱ) is context-sensitive.
        if s == HAMZAT_AL_WASL:
            if self.is_first_char and self.is_first_word:
                # emit glottal onset
                return "ʔ"
            #  Default: empty
            return ""

        # --- Tanwin Rules ---
        is_pausal = self.word.next_word and self.word.next_word.is_punct
        # Pausal: 'an' becomes long 'a' at end
        if s == TANWIN_FATH and is_pausal:
            return "aː"
        # Pausal: 'un' becomes silent at end
        elif s == TANWIN_DAMM and is_pausal:
            return ""

        # Assimilation of n + r/j/l/m
        if self.word.next_word and s == N and \
                self.prev_token and self.prev_token.surface == KASRA and \
                self.prev_token.prev_token and self.prev_token.prev_token.surface == M:

            # Idgham (n assimilation)
            if self.word.next_word.tokens[0] == R:
                # Assimilation n+r -> rr
                return "r"
            if self.word.next_word.tokens[0] == YA:
                # Assimilation n+j -> jj
                return "j"
            if self.word.next_word.tokens[0] == LAM:
                # Assimilation n+l -> ll
                return "l"

            # Iqlab: n becomes 'm' before 'b'
            if self.word.next_word.tokens[0] == B:
                return "m"


        # --- Alif Rules ---
        if s == ALIF or s == ALEF_MADDA or s == ALEF_HAMZA_BELOW:

            # --- Bare Alif (Sentence Initial) ---
            # If first word is bare Alif (not article), emit helper vowel 'i'
            if self.is_first_word and self.is_first_char and s == ALIF:
                return "i"

            # Medial: Lengthens preceding vowel
            if self.prev_token and self.prev_token.ipa == "a":
                return "ː"

            # End of word: often silent or long vowel
            if self.is_last_char:
                # Silent Alif in plural verbs (e.g., Katabu كتبوا)
                #if self.prev_token and self.prev_token.surface == WAW:
                #    return ""
                # Dagger alif behavior (implicit) or lengthening
                return ""

            # Default to long a
            if s == ALEF_MADDA:
                return "ʔaː"

            # Start of word: Wasla vs Hamza
            if self.is_first_char:
                return ""

            return 'aː'

        # --- Ta Marbuta (ة) ---
        if s == TA_MARBUTA:

            # If pause (followed by nothing or non-diacritic), it is silent (or /h/).
            if is_pausal:
                pass

            # If connected (followed by vowel/tanwin), it is /t/.
            elif self.next_token and self.next_token.is_vowel:
                return "t"

            # In pause, standard pronunciation often drops it entirely or implies 'h'
            return ""

        # --- Waw (و) ---
        if s == WAW:
            # Heuristics for multiple behaviors of Waw:
            # 1) Consonantal /w/
            # 2) Glide in diphthongs (aw)
            # 3) Mater lectionis (long vowel) when it lengthens a preceding vowel
            # 4) Silent in certain historical/orthographic contexts

            # Word-initial WAW + ALIF (Diphthong vs Glide) => /aw/ or /w/ depending on prev word
            if self.is_first_char and self.next_token and self.next_token == ALIF:
                # if prev word ended in 'a' then /w/ else /aw/
                if self.word.prev_word and self.word.prev_word.tokens[-1].ipa.startswith('a'):
                    return "w"
                else:
                    return "aw"

            # If previous IPA ends with 'u' (short u) then WAW likely lengthens it.
            if self.prev_token and self.prev_token.ipa.endswith('u'):
                return "ː"

            # Default: consonant /w/
            return "w"

        # --- Ya (ي) ---
        if s == YA:
            # 1) Lengthening prev vowel (i -> i:)
            if self.prev_token and self.prev_token.ipa.endswith('i'):
                return "ː"
            # 2) Diphthong: FATHA + YA -> /aj/ glide
            if self.prev_token and self.prev_token.surface == FATHA and (not self.next_token or self.next_token.surface not in VOWEL_MAP):
                return "j"
            # 3) Consonantal /j/
            return "j"

        # --- Alif Maqsura (ى) ---
        if s == ALIF_MAKSURA:
            # - Medial + followed by explicit diacritic: short /a/ (to respect an overt vowel)
            if self.next_token and self.next_token.surface in VOWEL_MAP:
                return "a"
            # - Else: default long /aː/
            if self.prev_token and self.prev_token.surface == FATHA:
                return ":"
            return "aː"

        # --- Vowels ---
        if self.prev_token and self.prev_token.ipa == "i" and s == KASRA:
            return ""
        if s in VOWEL_MAP:
            return VOWEL_MAP[s]

        # --- Consonants ---
        if s in ARABIC_TO_IPA_CONSONANTS:
            # 3rd position when self.word.has_definite_article -> token to geminate
            if self.char_idx == 2 and self.word.has_definite_article:
                # Sun Letter: Assimilated 'l' (char_idx==1) -> double the sun letter.
                if self.is_sun:
                    return ARABIC_TO_IPA_CONSONANTS[s] + ARABIC_TO_IPA_CONSONANTS[s]
            return ARABIC_TO_IPA_CONSONANTS[s]

        if s == SHADDA:
            # Shadda duplicates the previous consonant.
            # 4th position when self.word.has_definite_article -> already geminated in previous check
            if self.char_idx == 3 and self.word.has_definite_article:
                return ""
            # Return the IPA of the previous token.
            if self.prev_token:
                return self.prev_token.ipa
            return ":"

        # --- Non-Arabic fallback ---
        # For maintainability and to avoid losing non-Arabic characters, return ASCII letters/digits/punct as-is.
        if s.isascii() and (s.isalnum() or s in string.punctuation or s.isspace()):
            return s

        # Fallback for unhandled characters
        return ""

    def __eq__(self, other) -> bool:
        if isinstance(other, str):
            return self.surface == other
        return super().__eq__(other)


@dataclasses.dataclass
class WordToken:
    """
    Represents a distinct word (sequence of characters).
    Handles intra-word phonology like Sun-letter assimilation and Shadda application.
    """
    surface: str
    word_idx: int
    prev_word: Optional['WordToken'] = None
    next_word: Optional['WordToken'] = None

    def __post_init__(self):
        self._tokens_cache: Optional[List[CharToken]] = None

    @property
    def is_punct(self) -> bool:
        return self.surface in PUNCT

    @property
    def is_first_word(self) -> bool:
        return self.prev_word is None

    @property
    def is_last_word(self) -> bool:
        return self.next_word is None or (self.next_word.is_punct and self.next_word.next_word is None)

    @property
    def end_with_vowel(self) -> bool:
        return self.tokens[-1].ipa in {'a', 'u', 'i', 'aː', 'uː', 'iː', 'ː', 'an', 'un', 'in'}

    @property
    def normalized(self) -> str:
        return normalize_unicode(self.surface)

    @property
    def tokens(self) -> List[CharToken]:
        """Convert surface string into linked CharTokens."""
        if self._tokens_cache is not None:
            return self._tokens_cache
        s = list(self.normalized)
        tokens: List[CharToken] = [CharToken(surface=ch, char_idx=i) for i, ch in enumerate(s)]
        for i, t in enumerate(tokens):
            t.word = self
            t.prev_token = tokens[i - 1] if i > 0 else None
            t.next_token = tokens[i + 1] if i < len(tokens) - 1 else None
        self._tokens_cache = tokens
        return self._tokens_cache

    @property
    def has_definite_article(self) -> bool:
        """Checks for 'Al-' (Alif + Lam) at the start. orthographic "ال" """
        return len(self.tokens) >= 2 and self.tokens[0].surface == ALIF and self.tokens[1].surface == LAM

    @property
    def is_proclitic(self) -> bool:
        """
        Heuristic: short surface (1-2 chars) and starts with a clitic base letter.
        Many Arabic proclitics are a single consonant optionally carrying a diacritic.
        """
        s = self.normalized
        # treat punctuation/non-words as non-clitics
        if self.is_punct:
            return False
        # typical clitics are very short: 1 or 2 codepoints (letter + optional diacritic)
        if len(s) > 2:
            return False
        # first character must be one of known clitic letters
        first = s[0]
        if first in CLITIC_BASES:
            return True
        return False

    @property
    def is_sun(self) -> bool:
        """Determines if the word starts with a Sun letter (ignoring 'Al-')."""
        t = self.tokens
        if self.has_definite_article and len(t) > 2:
            return t[2].is_sun
        if t:
            return t[0].is_sun
        return False

    @property
    def ipa(self) -> str:
        # Check dictionary exceptions first
        if self.surface in WORD_EXCEPTIONS:
            return WORD_EXCEPTIONS[self.surface]

        ipa = "".join([tok.ipa for tok in self.tokens])
        # HACK: Normalize double length markers if they occur
        # TODO: improve CharToken.ipa to avoid these mistakes in the first place
        # experimentally determined to reduce CER
        replacements = {
            #"dˤdˤ": "ðˤ", # debatable
            "idʒt": "ijt",
        }
        for k, v in replacements.items():
            ipa = ipa.replace(k, v)
        return ipa.strip()

    def __eq__(self, other) -> bool:
        if isinstance(other, str):
            return self.surface == other
        return super().__eq__(other)


@dataclasses.dataclass
class Sentence:
    surface: str

    @property
    def normalized(self) -> str:
        return normalize_unicode(self.surface)

    @property
    def tokens(self) -> List[WordToken]:
        """
        Split text into words, keeping punctuation separate.
        This tokenizer:
          - splits on whitespace
          - treats ASCII and Arabic punctuation as separate tokens
          - preserves diacritics attached to letters
        """
        # pattern: split on whitespace OR any punctuation character (ASCII + Arabic)
        punct_class = re.escape(PUNCT)
        # Split by whitespace OR punctuation
        pattern = r'(\s+|[' + punct_class + r'])'
        pieces = [p for p in re.split(pattern, self.normalized) if p and not p.isspace()]

        tokens: List[WordToken] = []
        for idx, piece in enumerate(pieces):
            wt = WordToken(
                surface=piece,
                word_idx=idx,
                prev_word=tokens[idx - 1] if idx > 0 else None
            )
            if idx > 0:
                tokens[idx - 1].next_word = wt
            tokens.append(wt)
        return tokens

    @property
    def ipa(self) -> str:
        """
        Produce IPA for sentence while propagating hamzat/wasl effects across clitics.
        Specifically:
          - Common proclitics (وَ، فَ، بِ، لِ، كَ، سَ) attach to the following word in connected speech;
            we therefore concatenate their IPA with the next word's IPA (no separating space).
          - When concatenating into a following definite article 'ال', drop the article's initial 'a'
            (the short article vowel) to model wasl-elision: e.g. "بِ الْمَدِينَة" -> "bi lmadiːna" (not "bi almadiːna").
        """
        ipa_str = " ".join([w.ipa for w in self.tokens]).replace(" ː", "ː ").strip()

        # HACK: experimentally determined
        # TODO - handle remove whitespaces better
        ipa_str = ipa_str.replace("mij j", "mijj")
        ipa_str = ipa_str.replace("mil l", "mill")
        ipa_str = ipa_str.replace("mim baʕ", "mimbaʕ")
        ipa_str = ipa_str.replace("min t", "mint")

        return ipa_str

    def __eq__(self, other) -> bool:
        if isinstance(other, str):
            return self.surface == other
        return super().__eq__(other)

