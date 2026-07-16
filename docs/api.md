# API reference

Every public symbol, with real signatures and return shapes. Import paths are
module-qualified (`from arbtok.plugin import ArbtokG2PPlugin`).

## `arbtok.plugin`

The primary entry point — the full engine, including automatic diacritization,
dialects, loanword nativization, and Arabizi.

### `ArbtokG2PPlugin(lang="ar", diacritize=True, stress=True, lexicon=..., dialect_lexicon=True, nativize=True, arabizi=True, pausal=True, fusion=True)`

Constructs an Arabic G2P engine. Every argument is a policy switch:

| kwarg | default | meaning |
| --- | --- | --- |
| `lang` | `"ar"` | The variety: any orthography2ipa Arabic spec code (`ar`, `arb`, `ar-EG`, `ar-SA-x-najd`, …). Resolves by narrowing subtags, falling back to `ar`. |
| `diacritize` | `True` | Restore the marks bare text omits before transcribing. |
| `stress` | `True` | Mark the stressed syllable (quantity-sensitive, read off the transcription). |
| `lexicon` | default HF id | Diacritized-stem lexicon consulted before the model — a path, URL, `hf://` id, or `None`. |
| `dialect_lexicon` | `True` | Consult the lect's closed-class lexicon (function words) as a hard prior. |
| `nativize` | `True` | Read a Latin-script run as a loanword, nativized into the lect's phonology. |
| `arabizi` | `True` | Read a digit-guttural Latin run (`7abibi`) as Arabic (see [arabizi.md](arabizi.md)). |
| `pausal` | `True` | The waqf/pausal (TTS) register; `False` for full-iʿrāb passthrough. |
| `fusion` | `True` | Score the diacritizer distribution under dialect licensing (see [rawi-fusion.md](rawi-fusion.md)); `False` for the plain generator. |

```python
from arbtok.plugin import ArbtokG2PPlugin

p = ArbtokG2PPlugin(lang="ar-EG")
```

| Method | Returns | Description |
| --- | --- | --- |
| `transcribe(text, arabizi=None)` | `str` | Full-sentence IPA, with clitic joining and cross-word sandhi. Latin runs are read as loanwords or Arabizi. `arabizi` overrides the instance default per call. |
| `transcribe_word(word, context=None)` | `str` | IPA for one isolated word on the shared lattice (the variety's grapheme table + allophone rules). |
| `normalize(text)` | `str` | The lifecycle step: speech normalization, Unicode/diacritic reordering, and (if `diacritize`) tashkeel restoration. |
| `language_codes` | `List[str]` | `["ar", "arb"]`. |

```python
p.transcribe("ذهب الولد الى المدرسة")            # bare input, auto-diacritized
p.transcribe_word("قَهْوَة")                      # single word
p.transcribe("عِنْدِي meeting", arabizi=False)    # force the loanword reading
```

Diacritization degrades gracefully: if the model cannot load, the engine
transcribes whatever diacritics are already present rather than raising.

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

## `arbtok.o2i_plugins` — the orthography2ipa step plugins

arbtok is an engine built *on* orthography2ipa, but the pieces it owns are exactly
the steps orthography2ipa made pluggable. Installing arbtok registers three
entry-point plugins so plain orthography2ipa can transcribe **undiacritized**
Arabic — which it cannot do alone, since its input contract is diacritized text:

| entry-point group | class | contribution |
| --- | --- | --- |
| `orthography2ipa.normalize` | `ArbtokDiacritizer` | restore tashkeel, guarded by the lattice |
| `orthography2ipa.rescore` | `ArbtokRescorers` | sun-letter assimilation, hamzat al-waṣl, hamza carrier, accusative alif |
| `orthography2ipa.sandhi` | `ArbtokSandhi` | cross-word idghām/iqlāb, pausal case-ending drop, waṣl |

The plugin is **named**, not implicit — installing arbtok does not silently change
what orthography2ipa says about Arabic; the caller opts in at the call site:

```python
from orthography2ipa import G2P

G2P("ar").transcribe("كتب")                                   # 'ˈktb' — no vowels to read
G2P("ar", plugins={"normalize": "arbtok"}).transcribe("كتب")  # 'ˈkatab' — arbtok restores them
```

## Where next

- [quickstart.md](quickstart.md) — install and the core idea
- [tashkeel.md](tashkeel.md) — the diacritizer subsystem
- [rawi-fusion.md](rawi-fusion.md) — the fusion scorer
- [dialects.md](dialects.md) — varieties and per-lect phonology
- [advanced.md](advanced.md) — internals, espeak baseline, recipes, gotchas
