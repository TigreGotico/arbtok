# Diacritization (tashkeel)

Arabic in the wild is written without short vowels. The phonemizer needs them —
no diacritics means no vowels to emit. `arbtok.tashkeel` restores diacritics
via [text2tashkeel](https://github.com/TigreGotico/text2tashkeel), a model
picker over bundled ONNX diacritization models (no PyTorch, offline by
default; the flagship ensemble also restores hamza and the dagger-alef).

## `TashkeelDiacritizer`

```python
from arbtok.tashkeel import TashkeelDiacritizer

diac = TashkeelDiacritizer()
print(diac.diacritize("قال الملك"))
```

Pass a text2tashkeel model name to pick a specific accuracy/speed/size
trade-off:

```python
TashkeelDiacritizer("rawi-v2-int8")   # small int8 variant
```

### `diacritize(text, pausal=False) -> str`

Returns the input text with diacritics inserted.

```python
diac.diacritize("ذهب الطالب")
```

`pausal=True` rewrites the word-final case vowels (fatha/damma/kasra and the
damm/kasr tanwīn) to sukūn — the pausal form used when citing isolated words,
which is how dictionary lexicons transcribe them:

```python
diac.diacritize("كتب", pausal=True)
```

`TashkeelDiacritizer` is also callable; `diac(text)` is equivalent to
`diac.diacritize(text)`.

## The stem lexicon

A model asked which vowels كتاب carries has to *infer* the answer, and on
high-frequency vocabulary it infers wrong (`كَتَاب` /kataːb/ for `كِتَاب`
/kitaːb/). But that is not a thing to infer — it is a thing to look up. So
`ArbtokG2PPlugin` and `LatticeDiacritizer` consult a **diacritized-stem
lexicon** before they ever call the model:

```python
from arbtok.plugin import ArbtokG2PPlugin

ArbtokG2PPlugin()                          # the default lexicon
ArbtokG2PPlugin(lexicon="/data/mine.tsv")  # a local file, a URL, or an hf:// id
ArbtokG2PPlugin(lexicon=None)              # the model, unassisted
```

The lexicon maps an **undiacritized surface form** to the most frequent
**diacritized stem** for it in a large diacritized corpus — not to IPA. The stem
is fed back through arbtok's own engine, so a looked-up word still gets emphasis
spread, gemination, stress and the pausal treatment, and the *same* entry yields
MSA under `ar` and Najdi under `ar-SA-x-najd`. A surface→IPA lexicon would freeze
one variety's pronunciation into the data and bypass all of that.

It is a *stem* because a classical corpus writes the full iʿrāb: كِتَابٌ /
كِتَابَ / كِتَابِ are one word in three syntactic positions. The case ending is
stripped before counting — waqf drops it anyway — which collapses the three into
one better-attested entry and leaves exactly the part the model gets wrong.

An entry is held to the same guards as a model proposal: it must spell the word
it was asked about, and the variety's grapheme table must license it. Data can be
wrong too.

Nothing is bundled. The lexicon is mined from a GPL-2.0 corpus and arbtok is
Apache-2.0, so it ships as a Hugging Face dataset fetched on first use, exactly
as the diacritizer's model weights are. `scripts/build_stem_lexicon.py` builds
one from any diacritized corpus.

### Errors

Failures inside the model raise `TashkeelError` with the underlying cause
attached. The G2P engine (`arbtok.plugin.ArbtokG2PPlugin`) degrades
gracefully: when diacritization is unavailable it transcribes whatever
diacritics are present in the input.
