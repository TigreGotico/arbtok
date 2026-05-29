# API reference

Every public symbol, with real signatures and return shapes. `arbtok` is a
checkout-and-import library; import paths are module-qualified.

## `arbtok.tokenizer`

The phonemization core. Three dataclasses form a three-level hierarchy —
`Sentence` holds `WordToken`s, each `WordToken` holds `CharToken`s — linked
bidirectionally so phonology can read neighbours.

### `Sentence(surface: str)`

The main entry point. Build it from raw (diacritized) Arabic text.

```python
from arbtok.tokenizer import Sentence

s = Sentence("قَالَ ٱلْمَلِكُ")
```

| Member | Type | Description |
| --- | --- | --- |
| `surface` | `str` | The original text you passed in. |
| `normalized` | `str` | NFC-normalized text with diacritics reordered (consonant → shadda → vowel). |
| `tokens` | `List[WordToken]` | Words and punctuation as linked `WordToken`s; whitespace is dropped, punctuation kept as its own token. |
| `ipa` | `str` | The IPA transcription of the whole sentence. **This is what you want.** |

```python
print(s.ipa)              # "qaːla lmaliku"
print(len(s.tokens))      # word + punctuation tokens
```

`Sentence` compares equal to its surface string (`Sentence("x") == "x"`).

### `WordToken(surface: str, word_idx: int, prev_word=None, next_word=None)`

One word (or one punctuation mark). You rarely construct these directly — read
them off `Sentence.tokens` — but the properties are useful for inspection.

| Member | Type | Description |
| --- | --- | --- |
| `surface` | `str` | The word text. |
| `word_idx` | `int` | Position in the sentence. |
| `prev_word` / `next_word` | `Optional[WordToken]` | Neighbours in the linked list. |
| `tokens` | `List[CharToken]` | The word's characters as linked `CharToken`s (cached). |
| `normalized` | `str` | NFC-normalized surface. |
| `is_punct` | `bool` | True if the surface is a punctuation token. |
| `is_first_word` / `is_last_word` | `bool` | Sentence boundary checks (last accounts for trailing punctuation). |
| `has_definite_article` | `bool` | Starts with `ال` (alif + lam). |
| `is_proclitic` | `bool` | Short clitic heuristic (1–2 chars starting with a clitic base, e.g. `و`, `بِ`). |
| `is_sun` | `bool` | First real letter (after any article) is a sun letter. |
| `end_with_vowel` | `bool` | Final char's IPA is a vowel — used for wasl elision. |
| `ipa` | `str` | IPA for this word (consults `WORD_EXCEPTIONS` first). |

```python
word = Sentence("الْمَدْرَسَةِ").tokens[0]
print(word.has_definite_article)   # True
print(word.ipa)                    # IPA for the word
```

### `CharToken(surface, char_idx, prev_token=None, next_token=None, word=None)`

One character — a letter, a diacritic, or punctuation. The IPA of a character
depends on its neighbours, so these are linked both ways and back to their
`word`.

Boolean properties: `is_first_char`, `is_last_char`, `is_first_word`,
`is_last_word`, `is_punct`, `is_vowel`, `is_sun`, `is_moon`, `is_silent`,
`is_tanwin`, `has_diacritic`, `has_shada`, `has_sukun`, `has_vowel_mark`.

| Member | Type | Description |
| --- | --- | --- |
| `surface` | `str` | The single character. |
| `char_idx` | `int` | Position within its word. |
| `normalized` | `str` | NFC-normalized character. |
| `ipa` | `str` | Context-sensitive IPA fragment for this character. |

```python
chars = Sentence("بِت").tokens[0].tokens
print(chars[0].surface, chars[0].is_first_char)   # ب True
print(chars[-1].is_last_char)                      # True
```

### Module-level normalization helpers

```python
from arbtok.tokenizer import normalize_unicode

normalize_unicode(text: str) -> str
```

NFC-normalizes and enforces consonant → shadda → vowel ordering. Both `Sentence`
and the token classes use it internally via their `.normalized` property.

The module also re-exports named grapheme constants (`ALIF`, `LAM`, `SHADDA`,
`SUKUN`, `FATHA`, `KASRA`, `WAW`, `TANWIN_FATH`, `SUN_LETTERS`, …) for readable
rule code — see `arbtok/constants.py`.

## `arbtok.util`

### `normalize(text: str, lang: str) -> str`

Expand contractions, titles, numbers, dates, times, units and fractions into
spoken words for the given locale tag (`"ar"`, `"en"`, `"en-US"`, `"pt"`, …).
Date/time normalization is attempted and silently skipped where unsupported.

```python
from arbtok.util import normalize

normalize("عندي 3 كتب", "ar")          # "عندي ثلاثة كتب"
normalize("I'm Dr. 3/3", "en")          # "I am Doctor three thirds"
```

### `match_lang(target_lang, valid_langs) -> Tuple[str, int]`

Find the closest supported language tag. Returns `(lang, distance)`; returns
`("und", 10000)` when nothing matches well.

```python
from arbtok.util import match_lang

match_lang("ar-EG", ["ar", "en"])      # ("ar", <distance>)
```

Public helper: `is_fraction(word: str) -> bool` (e.g. `"3/4"` → `True`).
`pronounce_date(date_obj, full_lang)` and `pronounce_time(time_string,
full_lang)` wrap the OVOS date parser.

## `arbtok.num2words`

### `num2words(text, handle_percent=True, apply_tashkeel=True) -> str`

Convert digit sequences in `text` to Arabic words. With `apply_tashkeel=True`
the inserted words are diacritized; `handle_percent` replaces `%` with the
spoken percent word.

```python
from arbtok.num2words import num2words

num2words("عندي 25 كتاب")              # diacritized Arabic number words
num2words("50%", apply_tashkeel=False) # undiacritized + spoken percent
```

## `arbtok.dialects`

Phoneme maps and the dialect enum.

| Symbol | Type | Description |
| --- | --- | --- |
| `ArabicDialect` | `Enum` | `MSA`, `CLA`. Only MSA maps are populated. |
| `ARABIC_TO_IPA_CONSONANTS` | `dict[str, str]` | Grapheme → IPA consonant. |
| `VOWEL_MAP` | `dict[str, str]` | Vowel grapheme → IPA. |
| `DIACRITIC_TO_IPA` | `dict[str, str]` | Diacritic → IPA. |
| `TANWIN_TO_IPA` | `dict[str, str]` | Tanwin marks → IPA. |
| `WORD_EXCEPTIONS` | `dict[str, str]` | Whole-word IPA overrides consulted before rule-based phonemization. |

```python
from arbtok.dialects import ArabicDialect, ARABIC_TO_IPA_CONSONANTS

print(ArabicDialect.MSA.value)         # "MSA"
print(ARABIC_TO_IPA_CONSONANTS["ب"])   # "b"
```

## `arbtok.tashkeel`

See [tashkeel.md](tashkeel.md). Key symbols: `TashkeelDiacritizer`,
`TashkeelError`.

## `arbtok.espeak_wrapper`

A baseline phonemizer that shells out to the `espeak-ng` binary, for comparison
against the rule-based path. See [advanced.md](advanced.md#espeak-baseline).
Key symbols: `EspeakPhonemizer`, `EspeakError`.

## Where next

- [quickstart.md](quickstart.md) — install and the core idea
- [tashkeel.md](tashkeel.md) — the diacritizer subsystem
- [advanced.md](advanced.md) — internals, espeak baseline, recipes, gotchas
