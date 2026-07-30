# Quickstart, Arabic text to IPA

`arbtok` turns Arabic script into IPA phonemes for TTS front-ends, across Modern
Standard Arabic, Classical, and 30+ regional varieties. It is **self-contained**:
the diacritizer model ships inside the wheel, so there is no external model to
download and no network call at runtime.

## 1. Install

```bash
pip install arbtok
```

That pulls the runtime deps (`numpy`, `onnxruntime`, `orthography2ipa`,
`quebra-frases`, `langcodes`, `ovos-number-parser`, `ovos-date-parser`) and the
bundled rawi diacritizer ensemble.

## 2. The one call to know

`ArbtokG2PPlugin` is the engine. Give it text, get IPA. It restores the missing
short vowels for you, so **you do not have to diacritize the input first**:

```python
from arbtok.plugin import ArbtokG2PPlugin

p = ArbtokG2PPlugin()                       # Modern Standard Arabic
print(p.transcribe("ذهب الولد الى المدرسة"))   # ˈðahab ˈalwalad ˈalaː ˈlmudrasa
```

The input here is **bare**, no ḥarakāt, the way Arabic is normally typed. arbtok
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

print(najdi.transcribe("يشرب القهوة في البيت"))  # ˈjaʃrab alˈɡahawa ˈfiː ˈlbajt
print(tunis.transcribe("يشرب القهوة في البيت"))  # ˈjaʃrab alˈqahwa ˈfiː ˈlbiːt
```

Najdi reads qāf as /ɡ/ and inserts the *gahawa* epenthetic vowel. Tunisian keeps
/q/ and monophthongizes *bayt* to /biːt/. `arbtok.supported_lects()` lists every
code you can pass. See [dialects.md](dialects.md) for the full list and the
resolution rules.

## 4. Normalize numbers, dates and units first

TTS text is rarely clean. `normalize()` expands numbers, dates, times, units and
fractions into spoken words before you phonemize:

```python
from arbtok.util import normalize
from arbtok.plugin import ArbtokG2PPlugin

spoken = normalize("عندي 3 كتب", "ar")     # عندي ثلاثة كتب
print(ArbtokG2PPlugin().transcribe(spoken))
```

For Arabic-specific number-to-words (with gender/case variants and percent
handling) reach for `num2words`:

```python
from arbtok.num2words import num2words

print(num2words("عندي 25 كتاب"))            # diacritized Arabic words
```

## 5. The low-level core (already-diacritized text)

If you have fully-diacritized Arabic and want the phonology alone, no diacritizer,
no dialect model, go straight to `Sentence`:

```python
from arbtok.tokenizer import Sentence

print(Sentence("قَالَ ٱلْمَلِكُ").ipa)        # ˈqaːla lˈmaliku
```

`Sentence` expects the vowels to be **written** as combining marks. Without them
it has nothing to voice and emits a bare consonant skeleton, which is why the
plugin diacritizes first.

## Accuracy note

The rule set and the IPA reference test set are LLM-generated and have not been
validated by a native speaker. The Arabic specs are `research` tier, not
`production`. Treat the output as a strong starting point, not gospel. If you
speak MSA or a covered dialect, pull requests are very welcome.

## Where next

- [tashkeel.md](tashkeel.md), the flagship diacritizer and its lexicons
- [rawi-fusion.md](rawi-fusion.md), how the diacritizer is scored, not just run
- [dialects.md](dialects.md), varieties, resolution, and per-lect phonology
- [arabizi.md](arabizi.md), reading Latin-script Arabic (`7abibi`, `3ala`)
- [api.md](api.md), every public class, function and important kwarg
- [advanced.md](advanced.md), token internals, espeak baseline, recipes, gotchas

---
[Home](../README.md) · [Diacritization →](tashkeel.md)
