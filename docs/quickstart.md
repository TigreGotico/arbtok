# Quickstart, Arabic text to IPA

<!-- agent-hint
covers: how to install arbtok and phonemize a bare Arabic sentence, in a dialect and after normalization
source: pyproject.toml, arbtok/plugin.py, arbtok/textnorm.py:normalize_for_tts, arbtok/tokenizer.py
generated: no
verify: .venv/bin/python scripts/check_docs_examples.py docs/quickstart.md
see: tashkeel.md, dialects.md, normalization.md, api.md
-->

`arbtok` turns Arabic script into IPA phonemes for TTS front-ends, across Modern
Standard Arabic, Classical, and 30+ regional varieties. The diacritizer model
ships inside the wheel, so there is no external model to download. The default
stem lexicon is a Hugging Face dataset: the first call that diacritizes downloads
it to the Hugging Face cache. Pass `lexicon=None` to run with no network call (see
[tashkeel.md](tashkeel.md#the-stem-lexicon)).

## 1. Install

```bash
pip install --pre arbtok
```

That pulls the runtime deps (`numpy`, `onnxruntime`, `orthography2ipa`,
`quebra-frases`, `linguatag`, `ovos-number-parser`, `numtag`, `ovos-date-parser`, `chronologia`,
`unicode-rbnf`, `ovos-utils`, `ovos-config`, `huggingface_hub`) and the bundled rawi diacritizer
ensemble. `arbtok.__version__` is the installed version.

`pip install arbtok` without `--pre` gives the latest stable release, which can
lag behind the features that these pages describe.

The diacritizer model ships inside the wheel. The default stem lexicon does not.
If the file is not cached and the Hub cannot be reached, the first call that
diacritizes raises `arbtok.ModelUnavailableError`. A lexicon that cannot be read
for any other reason raises its base class, `arbtok.lexicon.LexiconUnavailable`.

## 2. The one call to know

`ArbtokG2PPlugin` is the engine. Give it text, get IPA. It restores the missing
short vowels for you, so **you do not have to diacritize the input first**:

```python
from arbtok.plugin import ArbtokG2PPlugin

p = ArbtokG2PPlugin()
print(p.transcribe("ذهب الولد الى المدرسة"))  # ˈðahab ˈalwalad ˈʔilaː lˈmudrasa
```

```python
print(p.transcribe("كتاب جميل"))   # kiˈtaːb dʒaˈmiːl
```

`ArbtokG2PPlugin()` with no argument transcribes Modern Standard Arabic. The input here is **bare**, no ḥarakāt, the way Arabic is normally typed. arbtok
diacritizes it internally (the flagship dialect-aware tashkeel, see
[tashkeel.md](tashkeel.md) and [rawi-fusion.md](rawi-fusion.md)) and then
phonemizes the result. If your text already carries diacritics, they are honored
as written and never overwritten.

## 3. Pick a dialect

Pass a variety code as `lang=`. The *same bare sentence* gets variety-appropriate
vowels and reflexes, because the diacritizer's choice is constrained to what that
variety's orthography actually admits:

```python
from arbtok.plugin import ArbtokG2PPlugin

najdi = ArbtokG2PPlugin(lang="ar-SA-x-najd")
tunis = ArbtokG2PPlugin(lang="ar-TN")

print(ArbtokG2PPlugin(lang="ar").transcribe("ذهب الولد الى المدرسة"))  # ˈðahab ˈalwalad ˈʔilaː lˈmudrasa
print(ArbtokG2PPlugin(lang="ar-TN").transcribe("ذهب الولد الى المدرسة"))  # ˈðahab ˈalwalad ˈʔilɛː lˈmudrasa
print(najdi.transcribe("يشرب القهوة في البيت"))  # ˈjaʃrab alˈɡahawa fiː lˈbeːt
print(tunis.transcribe("يشرب القهوة في البيت"))  # ˈjaʃrab alˈqahwa fiː lˈbiːt
```

Najdi reads qāf as /ɡ/ and inserts the *gahawa* epenthetic vowel. Tunisian keeps
/q/ and monophthongizes *bayt* to /biːt/. `arbtok.supported_lects()` lists every
variety you can pass, by its canonical code. See [dialects.md](dialects.md) for the full list and the
resolution rules.

## 4. Normalize numbers, dates and units first

TTS text is rarely clean. `normalize_for_tts()` expands numbers, dates, times,
units and fractions into spoken words before you phonemize, and it is what the
plugin runs on the way in:

```python
from arbtok import normalize_for_tts
from arbtok.plugin import ArbtokG2PPlugin

spoken = normalize_for_tts("عندي 3 كتب")
print(spoken)  # عندي ثلاثة كتب
print(ArbtokG2PPlugin().transcribe(spoken))  # ˈʕindiː θaˈlaːθa ˈkatab
```

A reply that reads out prices, phone numbers and booking references needs those
told apart from quantities, and a lect says its cardinals its own way. Both are
config on a `TtsNorm`; see [normalization.md](normalization.md).

## 5. The low-level core (already-diacritized text)

If you have fully-diacritized Arabic and want the phonology alone, no diacritizer,
no dialect model, go straight to `Sentence`:

```python
from arbtok.tokenizer import Sentence

print(Sentence("قَالَ ٱلْمَلِكُ").ipa)        # ˈqaːla lˈmaliku
print(Sentence("اَلسَّلَامُ عَلَيْكُمْ").ipa)  # assaˈlaːmu ʕaˈlajkum
```

`Sentence` expects the vowels to be **written** as combining marks. Without them
it has nothing to voice and emits a bare consonant skeleton, which is why the
plugin diacritizes first.

## Accuracy note

The rule set and the IPA reference test set are LLM-generated and have not been
validated by a native speaker. The Arabic specs are `research` or `stub` tier,
none `production`. Treat the output as a strong starting point, not gospel. If you
speak MSA or a covered dialect, pull requests are very welcome.

## Where next

- [overview.md](overview.md), what arbtok adds over orthography2ipa
- [tashkeel.md](tashkeel.md), the flagship diacritizer and its lexicons
- [rawi-fusion.md](rawi-fusion.md), how the diacritizer is scored, not just run
- [dialects.md](dialects.md), varieties, resolution, and per-lect phonology
- [arabizi.md](arabizi.md), reading Latin-script Arabic (`7abibi`, `3ala`)
- [api.md](api.md), every public class, function and important kwarg
- [advanced.md](advanced.md), token internals, espeak baseline, recipes, gotchas

---
[Home](index.md) · [Overview →](overview.md)
