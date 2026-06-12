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
TashkeelDiacritizer("rawi-v2-int8")   # fastest & smallest
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

### Errors

Failures inside the model raise `TashkeelError` with the underlying cause
attached. The G2P engine (`arbtok.plugin.ArbtokG2PPlugin`) degrades
gracefully: when diacritization is unavailable it transcribes whatever
diacritics are present in the input.
