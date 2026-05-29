# Advanced

Token internals, the espeak baseline, recipes, and the sharp edges.

## Inspecting the token tree

`Sentence.ipa` hides a three-level linked structure. When a transcription looks
wrong, drop down a level and read where each phoneme came from.

```python
from arbtok.tokenizer import Sentence

s = Sentence("الْمَدْرَسَةِ")
word = s.tokens[0]
print("definite article:", word.has_definite_article)
for ch in word.tokens:
    print(repr(ch.surface), "->", repr(ch.ipa),
          "sun" if ch.is_sun else "moon")
```

Each `CharToken` decides its IPA from neighbours: the article's `ل` assimilates
before sun letters and doubles them, tanwin resolves to `aː`/silence in pausal
position, and `ن` undergoes idgham/iqlab before `ر ي ل م ب`. None of this is
configurable — it is the rule set — but reading `.ipa` per character tells you
exactly which rule fired.

## Sun vs moon letters

The classic assimilation case. `is_sun` on a `WordToken` looks at the first real
letter, skipping the definite article:

```python
from arbtok.tokenizer import Sentence

print(Sentence("الشَّمْس").ipa)    # sun letter: the ل assimilates, ش doubles
print(Sentence("الْقَمَر").ipa)    # moon letter: the ل is pronounced
```

## Wasl and clitics across word boundaries

The article's initial `a` elides after a vowel or a proclitic, modelling
connected speech. Proclitics (`و`, `بِ`, `لِ`, `كَ`, …) are detected by
`WordToken.is_proclitic` and joined to the following word's IPA:

```python
from arbtok.tokenizer import Sentence

print(Sentence("قَالَ ٱلْمَلِكُ").ipa)   # "qaːla lmaliku" — article 'a' gone
```

## Normalizing real TTS input

Raw sentences carry numbers, dates, units and percent signs. Run `normalize`
(language-aware) and, for Arabic numerals specifically, `num2words` before
phonemizing:

```python
from arbtok.util import normalize
from arbtok.num2words import num2words
from arbtok.tokenizer import Sentence

raw = "عندي 3 كتب و 50%"
spoken = num2words(normalize(raw, "ar"))
print(spoken)
print(Sentence(spoken).ipa)
```

`normalize` also serves other languages (`"en"`, `"pt"`, `"es"`, `"fr"`, `"de"`)
for contractions, titles and locale-aware decimal separators — handy when the
same front-end handles mixed-language metadata.

## espeak baseline

`EspeakPhonemizer` shells out to the `espeak-ng` binary to produce a comparison
transcription. It is a baseline, not the primary path, and it requires
`espeak-ng` on `PATH`.

```python
import shutil
from arbtok.espeak_wrapper import EspeakPhonemizer, EspeakError

if shutil.which("espeak-ng"):
    esp = EspeakPhonemizer()
    print(esp.phonemize("قال الملك", "ar"))   # list[list[str]] grouped by sentence
    print(esp.phonemize_string("قال الملك", "ar"))
else:
    print("espeak-ng not installed; skipping baseline")
```

Key methods:

- `phonemize(text, lang="ar") -> list[list[str]]` — chunks text, phonemizes each
  chunk, returns phonemes grouped by sentence. For Arabic it diacritizes first
  via the bundled tashkeel model.
- `phonemize_string(text, lang) -> str` — raw espeak IPA string.
- `phonemize_to_list(text, lang="ar") -> List[str]` — that string as a char list.
- `add_diacritics(text, lang="ar") -> str` — diacritize Arabic input (pass-through
  for other langs).
- `get_lang(target_lang) -> str` — closest supported espeak voice.

`EspeakError` wraps a missing binary or a non-zero espeak exit.

## Gotchas

- **Diacritics are mandatory for vowels.** `Sentence` reads vowels from combining
  marks. Undiacritized text phonemizes to a consonant skeleton — diacritize first
  (see [tashkeel.md](tashkeel.md)).
- **Accuracy is experimental and unverified.** The rule set and the IPA gold set
  (`arbtok.test.ALL_TEST_CASES`) are LLM-generated. Many gold cases are marked
  failing. Passing tests is not linguistic correctness.
- **Reuse the diacritizer.** `TashkeelDiacritizer()` loads an ONNX session; build
  one and keep it, don't construct per sentence.
- **Vendored deps.** `arbtok.pyarabic` and `arbtok.tashkeel` are vendored copies;
  import them from `arbtok`, not from a system package.
- **No packaging metadata.** There is no `pip install .`; consumers import from a
  checkout with the repo root on `PYTHONPATH`.

## Where next

- [quickstart.md](quickstart.md) — the core path
- [api.md](api.md) — full public surface
- [tashkeel.md](tashkeel.md) — diacritizer details
