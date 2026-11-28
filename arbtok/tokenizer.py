import dataclasses
import re
import string
import unicodedata
from typing import Dict, List, Optional

# helper constants, make it more readable for non-arabic speakers (me)
# each represent an arabic grapheme that maps to a IPA phoneme in ARABIC_TO_IPA
from arbtok.constants import (B, T, DJ, X, D, R, Z, S, F, Q, K, M, N, H, LAM, WAW, YA,
                              FATHA, DAMMA, KASRA, DAGGER_ALIF, MADD, SUKUN,
                              HAMZA, ALEF_HAMZA_ABOVE, ALEF_HAMZA_BELOW, WAW_HAMZA, YA_HAMZA,
                              TANWIN_FATH, TANWIN_KASR, TANWIN_DAMM,
                              ALIF_MAKSURA,  ALIF, ALEF_MADDA,
                              HAMZAT_AL_WASL, TA_MARBUTA, SHADDA,
                              SUN_LETTERS, CLITIC_BASES, PUNCT)
from arbtok.stress import stress_words, stress_ipa, _first_segment_len
from orthography2ipa import get
from orthography2ipa import is_cliticless
from orthography2ipa import is_ipa_vowel
from arbtok.dialects import (VOWEL_MAP, ARABIC_TO_IPA_CONSONANTS, DIACRITIC_TO_IPA,
                             TANWIN_TO_IPA, WORD_EXCEPTIONS,
                             DEFAULT_LANG, consonant_ipa)

_WORD_SPLIT = re.compile(r"(\s+|[" + re.escape(PUNCT) + r"])")


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


#: ⟨مائة⟩ "hundred" and every word built on it. The alif is written and not said:
#: the word is /miʔa/, the same word as ⟨مئة⟩ (Ryding, *A Reference Grammar of Modern
#: Standard Arabic*, CUP 2005, §15.3). The pattern is a mīm (with kasra or no mark),
#: the alif, hamza-on-yāʾ, then either tāʾ marbūṭa or a tāʾ that continues into a long
#: vowel across short-vowel marks: the dual ⟨مائتان⟩, the construct ⟨مائتا⟩/⟨مائتي⟩
#: (Wright, *A Grammar of the Arabic Language*, 3rd ed., I §319). Tanwīn is not in the
#: skip class, because a hundred's tāʾ is never indefinite: ⟨مائتًا⟩ is the participle
#: "dying". The participle ⟨مائت⟩ ends at its tāʾ, and ⟨مَائِدَة⟩ "table" has no tāʾ
#: after the hamza, so both keep their alif. Unpointed ⟨مائتي⟩ and ⟨مائتاً⟩ stay
#: ambiguous without a lexicon and are read as the more frequent hundreds.
_SILENT_ALIF_MIA = re.compile(
    f"{M}({KASRA}?){ALIF}({YA_HAMZA}{FATHA}?(?:{TA_MARBUTA}|{T}(?=[َ-ْ]*[اي])))"
)


def elide_silent_alif(text: str) -> str:
    """Drop the unpronounced alif of the ⟨مائة⟩ morpheme.

    ⟨مِائَة⟩ → ⟨مِئَة⟩, ⟨ثَلَاثُمِائَة⟩ → ⟨ثَلَاثُمِئَة⟩, ⟨بِالْمِائَة⟩ → ⟨بِالْمِئَة⟩.
    Any other alif is left where it is.
    """
    return _SILENT_ALIF_MIA.sub(f"{M}\\1\\2", text)


def normalize_unicode(text: str) -> str:
    """*text* without tatweel, in NFC, with shadda before the vowel, and with
    ⟨مائة⟩ spelled as it is said (:func:`elide_silent_alif`)."""
    # Tatweel (U+0640) is a typographic stretch with no sound. Left in, it splits
    # its word in two: المـرء reads `ˈalm ˈraʔ` where المرء reads `alˈmarʔ`.
    text = text.replace("\u0640", "")
    text = unicodedata.normalize("NFC", text)
    text = _reorder_diacritics(text)
    return elide_silent_alif(text)


class _PrevTokenNeeded(Exception):
    """Raised inside CharToken._ipa when the previous token's fragment is not resolved yet."""


def _definite_article_ipa(tok: 'CharToken') -> Optional[str]:
    """The reading of one of the two characters of the definite article, or
    ``None`` for any character past them.

    Only called on a word that carries the article.
    """
    # The 'a' of al-
    if tok.is_first_char:
        # Check 1: Is current word a proclitic? (always wasl)
        if tok.word.prev_word and tok.word.prev_word.is_proclitic:
            return ""
        # Check 2: Does prev word end in a vowel? (Generalized Wasl)
        elif tok.word.prev_word and tok.word.prev_word.end_with_vowel:
            return ""
        # Alif vowel (always 'a')
        return "a"

    # is second char
    if tok.char_idx == 1:
        if tok.next_token and tok.next_token.is_moon:
            return "l"
        # Sun Letter: Assimilate 'l'
        return ""

    return None


def _alif_ipa(tok: 'CharToken', known: Dict[int, str]) -> str:
    """The reading of a bare, madda-bearing or hamza-below alif: a helper vowel,
    a length mark on the vowel before it, a long /aː/, or nothing.
    """
    s = tok.surface

    # --- Bare Alif (Sentence Initial) ---
    # If first word is bare Alif (not article), emit helper vowel 'i'
    if tok.is_first_word and tok.is_first_char and s == ALIF:
        return "i"

    # Medial: Lengthens preceding vowel (mater lectionis after fatha)
    if tok.prev_token and tok._prev_ipa(known) == "a":
        return "ː"

    # Medial ALIF after a non-'a' vowel (kasra 'i' or damma 'u') within a word:
    # this is hamzat al-wasl elision — the alif is a mere writing support and is silent
    # when preceded by a short vowel in the same orthographic word.
    # Example: وَبِاسْمِ (wa+bi+ism) → the ا of اسم is silent after 'i' of bi.
    if (not tok.is_first_char
            and tok.prev_token
            and tok._prev_ipa(known) in {"i", "u"}
            and s == ALIF):
        return ""

    # End of word: often silent or long vowel
    if tok.is_last_char:
        # Dagger alif behavior (implicit) or lengthening
        return ""

    # Default to long a
    if s == ALEF_MADDA:
        return "ʔaː"

    # Start of word: Wasla vs Hamza
    if tok.is_first_char:
        return ""

    return 'aː'


def _waw_ipa(tok: 'CharToken', known: Dict[int, str]) -> str:
    """The reading of a waw, which is any of four things: the consonant /w/, the
    glide of a diphthong, a mater lectionis lengthening the vowel before it, or
    silent in a historical spelling.
    """
    # Word-initial WAW + ALIF (Diphthong vs Glide) => /aw/ or /w/ depending on prev word
    if tok.is_first_char and tok.next_token and tok.next_token == ALIF:
        # if prev word ended in 'a' then /w/ else /aw/
        if tok.word.prev_word and tok.word.prev_word.tokens[-1].ipa.startswith('a'):
            return "w"
        else:
            return "aw"

    # A shadda proves this letter is a consonant -- see :func:`_ya_ipa`.
    if tok.has_shada:
        return "w"
    # If previous IPA ends with 'u' (short u) then WAW likely lengthens it.
    if tok.prev_token and tok._prev_ipa(known).endswith('u'):
        return "ː"

    # Default: consonant /w/
    return "w"


def _ya_ipa(tok: 'CharToken', known: Dict[int, str]) -> str:
    """The reading of a ya: a length mark on the vowel before it, or [j].

    [j] is two readings the character layer does not have to separate: the
    consonant, and the glide of a diphthong -- a ya after fatha is the second
    half of /aj/, and that glide IS [j]. Only the mater lectionis is a
    different phone, so only it needs a branch.
    """
    # A shadda proves this letter is a CONSONANT: gemination sits on a
    # consonant, never on vowel length. Without this the mater rule below
    # fires first and ⟨ـِيّ⟩ reads as `i` + `ː` (the ya) + `ː` (the shadda
    # duplicating it) -- the doubled length mark `iːː`, which is not a
    # phone and which a character-level reader cannot even see, since a
    # doubled `ː` is simply two symbols to it. The lattice path already
    # reads the same word correctly as `tijj`.
    if tok.has_shada:
        return "j"
    # Lengthening prev vowel (i -> i:)
    if tok.prev_token and tok._prev_ipa(known).endswith('i'):
        return "ː"
    return "j"


def _consonant_letter_ipa(tok: 'CharToken') -> str:
    """The reading of a consonant letter: the variety's own reflex, doubled where
    the definite article assimilated into it, or silent where it is itself an
    article lam assimilating into a sun letter.
    """
    s = tok.surface
    # Resolve the reference realization, then let the variety's own
    # spec override it. Used by every return below, so the variety's
    # reflex flows through gemination and assimilation alike.
    cons = consonant_ipa(s, tok.lang, ARABIC_TO_IPA_CONSONANTS[s])

    # 3rd position when the word has the definite article -> token to geminate
    if tok.char_idx == 2 and tok.word.has_definite_article:
        # Sun Letter: Assimilated 'l' (char_idx==1) -> double the sun letter.
        if tok.is_sun:
            return cons + cons

    # Embedded definite-article LAM assimilation:
    # In written Arabic, li+al- contracts to لِل- (the ALIF of the article is elided).
    # Pattern: KASRA + LAM(prep) + LAM(article) + SUN-LETTER(+SHADDA).
    # When a LAM is preceded by KASRA, which is preceded by another LAM,
    # and the next significant consonant is a sun letter bearing SHADDA,
    # this LAM is the article lam and assimilates into the following sun letter.
    if (s == LAM
            and tok.prev_token and tok.prev_token.surface == KASRA
            and tok.prev_token.prev_token and tok.prev_token.prev_token.surface == LAM):
        # Next consonant token (skip any intermediate diacritics)
        nxt = tok.next_token
        while nxt and nxt.surface in {FATHA, DAMMA, KASRA, SUKUN, TANWIN_FATH, TANWIN_DAMM, TANWIN_KASR}:
            nxt = nxt.next_token
        if nxt and nxt.is_sun and nxt.has_shada:
            # Article LAM assimilates: silent (sun letter doubles via SHADDA)
            return ""
        elif nxt and nxt.is_moon:
            # Article LAM before moon letter: retain 'l'
            return "l"

    return cons


def _shadda_ipa(tok: 'CharToken', known: Dict[int, str]) -> str:
    """The reading of a shadda, which duplicates the consonant before it."""
    # 4th position when the word has the definite article -> the letter before
    # it is the one the article assimilated into, and a SUN letter was already
    # doubled where it was read (see :func:`_consonant_letter_ipa`, which
    # doubles on ``is_sun``). A moon letter there was not, so its shadda still
    # has a consonant to geminate.
    if tok.char_idx == 3 and tok.word.has_definite_article and tok.prev_token.is_sun:
        return ""
    if tok.prev_token:
        prev = tok._prev_ipa(known)
        # A length mark cannot be geminated: doubling it would emit `ːː`.
        if prev.endswith("ː"):
            return ""
        return prev
    return ""


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
    def lang(self) -> str:
        """The variety realizing this char (inherited from the word)."""
        if self.word is not None:
            return self.word.lang
        return DEFAULT_LANG

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
        # A fragment can depend on the previous token's, which can depend on the one
        # before it, for as long as the run lasts. Resolved with a loop and a table
        # local to this call: a run of any length stays off the call stack, and each
        # token in it is read once instead of once per rule that asks for it.
        known: Dict[int, str] = {}
        pending = [self]
        while pending:
            tok = pending[-1]
            try:
                known[id(tok)] = tok._ipa(known)
                pending.pop()
            except _PrevTokenNeeded:
                pending.append(tok.prev_token)
        return known[id(self)]

    def _prev_ipa(self, known: Dict[int, str]) -> str:
        try:
            return known[id(self.prev_token)]
        except KeyError:
            raise _PrevTokenNeeded from None

    def _ipa(self, known: Dict[int, str]) -> str:
        """This character's fragment, given the fragments already resolved.

        A letter family at a time, in the order the rules have to fire: a
        decision that reads the previous fragment comes after the one that
        writes it.
        """
        s = self.surface

        if self.is_punct:
            return s

        # handle definite article assimilation (ال)
        if self.word.has_definite_article:
            article = _definite_article_ipa(self)
            if article is not None:
                return article

        # Hamzat al-wasl (ٱ) is context-sensitive.
        if s == HAMZAT_AL_WASL:
            if self.is_first_char and self.is_first_word:
                # emit glottal onset
                return "ʔ"
            #  Default: empty
            return ""

        # Tanwīn is always read in full here (an/un/in): the pausal form is
        # not a property of a character but of a word standing at a pause,
        # and it is applied in ONE place — the sentence-level rescorer
        # (arbtok.sandhi._pausal) — under the declared waqf policy. Idghām
        # and iqlāb of a final /n/ are the same kind of fact and sit in the
        # same place (arbtok.sandhi.NUN_ASSIMILATION, Wright I §14): a
        # character cannot see which word it is in, and مِن is a word.

        # --- Alif Rules ---
        if s == ALIF or s == ALEF_MADDA or s == ALEF_HAMZA_BELOW:
            return _alif_ipa(self, known)

        # --- Ta Marbuta (ة) ---
        if s == TA_MARBUTA:
            # Voiced /t/ only when an ending follows it; bare (word-final,
            # no ending written) it is silent. Whether a WRITTEN ending is
            # read or pausally dropped is the sandhi rescorer's decision,
            # not this character's.
            if self.next_token and self.next_token.is_vowel:
                return "t"
            return ""

        # --- Waw (و) ---
        if s == WAW:
            return _waw_ipa(self, known)

        # --- Ya (ي) ---
        if s == YA:
            return _ya_ipa(self, known)

        # --- Alif Maqsura (ى) ---
        if s == ALIF_MAKSURA:
            # - Medial + followed by explicit diacritic: short /a/ (to respect an overt vowel)
            if self.next_token and self.next_token.surface in VOWEL_MAP:
                return "a"
            # - Else: default long /aː/
            # After fatha it lengthens the 'a' vowel (ː = IPA length mark U+02D0, not ASCII colon)
            if self.prev_token and self.prev_token.surface == FATHA:
                return "ː"
            return "aː"

        # --- Vowels ---
        if s == KASRA and self.prev_token and self._prev_ipa(known) == "i":
            return ""
        if s in VOWEL_MAP:
            return VOWEL_MAP[s]

        # --- Consonants ---
        if s in ARABIC_TO_IPA_CONSONANTS:
            return _consonant_letter_ipa(self)

        if s == SHADDA:
            return _shadda_ipa(self, known)

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
    lang: str = DEFAULT_LANG

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
        """Heuristic: one or two codepoints (a clitic letter and an optional mark)
        that start with a clitic base letter."""
        s = self.normalized
        if self.is_punct or len(s) > 2:
            return False
        return s[0] in CLITIC_BASES

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
    def is_reference_register(self) -> bool:
        """True for the MSA/Classical registers, where WORD_EXCEPTIONS apply."""
        return self.lang in ("ar", "arb")

    @property
    def ipa(self) -> str:
        # Check dictionary exceptions first. These hardcode MSA-register
        # forms (silent letters, demonstrative long vowels); under another
        # variety they would bypass the spec's reflexes, so they only apply
        # to MSA/Classical. Other varieties fall through to the rule path.
        if self.is_reference_register and self.surface in WORD_EXCEPTIONS:
            return WORD_EXCEPTIONS[self.surface]

        lattice_ipa = self._lattice_ipa()
        if lattice_ipa is not None:
            return lattice_ipa
        # "idʒt" -> "ijt" is an experimentally determined cluster repair, applied on
        # both paths so they agree.
        return "".join([tok.ipa for tok in self.tokens]).replace("idʒt", "ijt").strip()

    def _lattice_ipa(self):
        """This word's IPA from the shared lattice, or ``None`` to use the cascade.

        The lattice applies the variety's ``allophone_rules``, which depend on
        syllable position (Najdi gahawa epenthesis), so a word reads the same alone
        and in a sentence. Cross-word effects, the article's waṣl elision among them,
        are left to :mod:`arbtok.sandhi`, which sees the spoken neighbours. ``None``
        for a word that needs the cascade (:func:`~arbtok.lattice.defers_to_cascade`).
        """
        from arbtok.lattice import defers_to_cascade, word_ipa

        if defers_to_cascade(self.surface):
            return None
        ipa = word_ipa(self.surface, self.lang, stress=False)
        if not ipa:
            return None
        return ipa.replace("idʒt", "ijt")

    def __eq__(self, other) -> bool:
        if isinstance(other, str):
            return self.surface == other
        return super().__eq__(other)


@dataclasses.dataclass
class Sentence:
    surface: str
    lang: str = DEFAULT_LANG
    #: Mark the stressed syllable of each prosodic word. Stress is applied AFTER
    #: assembly, so a proclitic and its host — joined in connected speech — take
    #: one mark between them, which is what they are: one phonological word.
    stress: bool = True
    #: The waqf policy (Wright I §372): ``True`` (TTS default) renders a word
    #: at a written pause in its pausal form — final short vowels and tanwīn
    #: -un/-in dropped, tanwīn -an lengthened to -aː, tāʾ marbūṭa /a/;
    #: ``False`` reads the full iʿrāb as written. See arbtok.sandhi._pausal.
    pausal: bool = True
    #: The spoken form of the word before this text, when the text continues an
    #: utterance (a nativized loanword before it). The article onset reads it.
    preceding: Optional[str] = None

    @property
    def normalized(self) -> str:
        return normalize_unicode(self.surface)

    @property
    def tokens(self) -> List[WordToken]:
        """The words, split on whitespace, with each ASCII or Arabic punctuation
        character as a token of its own."""
        pieces = [p for p in _WORD_SPLIT.split(self.normalized) if p and not p.isspace()]

        tokens: List[WordToken] = []
        for idx, piece in enumerate(pieces):
            wt = WordToken(
                surface=piece,
                word_idx=idx,
                prev_word=tokens[idx - 1] if idx > 0 else None,
                lang=self.lang,
            )
            if idx > 0:
                tokens[idx - 1].next_word = wt
            tokens.append(wt)
        return tokens

    @property
    def ipa(self) -> str:
        """The sentence's IPA: each word's own reading, then the cross-word rules of
        :mod:`arbtok.sandhi` (waṣl elision, idghām, pausal forms), then stress."""
        from arbtok.sandhi import apply_cross_word, _has_article
        tokens = self.tokens
        pieces = apply_cross_word(
            [(w.ipa, w.surface, w.is_punct) for w in tokens],
            pausal=self.pausal, lang=self.lang, preceding=self.preceding)

        # A waṣl-elided definite article is proclitic — unstressed, outside its
        # host's stress domain. When the article's seat vowel has been elided
        # (the piece now opens on the article consonant, not on ``a``), hold that
        # consonant out of the host's stress so الْيَوم is *lˈjawm*, not *ˈljawm*
        # (see arbtok.stress.stress_ipa). Aligned to the spoken (non-punct) words.
        spoken_tokens = [w for w in tokens if not w.is_punct]
        onsets = [
            (_first_segment_len(p)
             if (_has_article(w.surface) and p and not is_ipa_vowel(p[0]))
             else 0)
            for w, p in zip(spoken_tokens, pieces)
        ]

        # An assimilated مِن stays its own word (*mim baʕd*, not *mimbaʕd*): this
        # transcription is read word by word by the aligner and the label builder.
        ipa_str = " ".join(pieces).replace(" ː", "ː ").strip()
        if not self.stress:
            return ipa_str

        words = ipa_str.split(" ")
        if len(words) == len(onsets):
            # A declared prosodic clitic (a preposition, a vocative particle) leans
            # on its host and carries no word stress, as in the o2i engine.
            spec = get(self.lang)
            return " ".join(
                w if is_cliticless(t.surface, spec)
                else stress_ipa(w, self.lang, proclitic_onset=o)
                for w, o, t in zip(words, onsets, spoken_tokens))
        # The words no longer align with the spoken tokens, so each word is
        # stressed without its article onset.
        return stress_words(ipa_str, self.lang)

    def __eq__(self, other) -> bool:
        if isinstance(other, str):
            return self.surface == other
        return super().__eq__(other)

