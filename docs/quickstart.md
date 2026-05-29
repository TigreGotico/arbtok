# Quickstart — Arabic text to IPA

`arbtok` turns Arabic script into IPA phonemes for TTS front-ends, targeting
Modern Standard Arabic (MSA). If you can write a string, you can phonemize it.

## 1. Install

`arbtok` is a checkout-and-import library (no packaging metadata). Clone it and
install the runtime dependencies:

```bash
pip install -r requirements.txt
```

Runtime deps: `numpy`, `onnxruntime`, `quebra-frases`, `langcodes`,
`ovos-number-parser`, `ovos-date-parser`. The `tashkeel` diacritizer ships its
own `model.onnx` in-tree, so no model download is needed.

## 2. The one thing to understand

Everything funnels through one class: `Sentence`. You build it from raw text
and read its `.ipa` property. The phonology (definite-article assimilation,
sun/moon letters, tanwin, idgham/iqlab) is resolved from each character's
neighbours via a linked-list of tokens — you never wire that up yourself.

```python
from arbtok.tokenizer import Sentence

s = Sentence("قَالَ ٱلْمَلِكُ")   # "the king said"
print(s.ipa)                       # qaːla lmaliku
```

`Sentence` expects **diacritized** Arabic. The vowels are written as combining
marks (fatha, kasra, damma); without them the phonemizer has no vowels to emit.
If your text is undiacritized, run it through the [diacritizer](tashkeel.md)
first.

## 3. First real call

```python
from arbtok.tokenizer import Sentence

for text in ["ذَهَبَ الطَّالِبُ إِلَى الْمَدْرَسَةِ", "بَابٌ", "اَلْشَّمْس"]:
    print(text, "->", Sentence(text).ipa)
```

The definite article `ال` elides into the previous word, sun letters double, and
tanwin endings resolve by position — all from the surrounding context.

## 4. Normalize numbers, dates and units first

TTS text is rarely clean. `normalize()` expands numbers, dates, times, units and
fractions into spoken words for a given language before you phonemize:

```python
from arbtok.util import normalize

print(normalize("عندي 3 كتب", "ar"))   # عندي ثلاثة كتب
```

For Arabic-specific number-to-words (with gender/case variants and percent
handling) reach for `num2words`:

```python
from arbtok.num2words import num2words

print(num2words("عندي 25 كتاب"))       # diacritized Arabic words
```

## 5. Diacritize undiacritized text

Most real-world Arabic has no diacritics. The bundled `TashkeelDiacritizer`
restores them with an ONNX model, so the phonemizer has vowels to work with:

```python
from arbtok.tashkeel import TashkeelDiacritizer
from arbtok.tokenizer import Sentence

diac = TashkeelDiacritizer()
text = diac.diacritize("قال الملك")
print(Sentence(text).ipa)
```

## Accuracy note

This phonemizer is experimental. The rule set and the IPA reference test set are
LLM-generated and unverified; passing tests is not a guarantee of linguistic
correctness. Treat the output as a starting point, not gospel.

## Where next

- [api.md](api.md) — every public class, function and important kwarg
- [tashkeel.md](tashkeel.md) — the diacritizer subsystem in depth
- [advanced.md](advanced.md) — token internals, espeak baseline, recipes, gotchas
