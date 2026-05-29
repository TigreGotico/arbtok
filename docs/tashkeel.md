# Diacritization (tashkeel)

Arabic in the wild is written without short vowels. The phonemizer needs them —
no diacritics means no vowels to emit. `arbtok.tashkeel` restores diacritics
with an ONNX model bundled in-tree, so the rest of the pipeline has something to
work with.

## `TashkeelDiacritizer`

```python
from arbtok.tashkeel import TashkeelDiacritizer

diac = TashkeelDiacritizer()
print(diac.diacritize("قال الملك"))
```

Construction loads `model.onnx` and its id maps from the package directory:

```python
TashkeelDiacritizer(model_dir: Union[str, Path] = TASHKEEL_DIR)
```

`TASHKEEL_DIR` defaults to the package's own directory, so the zero-argument
constructor just works. Pass `model_dir` only if you vendor an alternative model
laid out with the same `input_id_map.json` / `target_id_map.json` /
`hint_id_map.json` files.

### `diacritize(text, taskeen_threshold=None) -> str`

Returns the input text with diacritics inserted.

```python
diac.diacritize("ذهب الطالب")
```

The optional `taskeen_threshold` is a float in roughly `0.0`–`1.0`. When set,
characters whose predicted diacritic logit exceeds the threshold get a sukoon
(silence) instead of the predicted vowel — a knob for how aggressively the model
marks unvocalized positions. Leave it `None` to take the model's raw output.

```python
diac.diacritize("كتب", taskeen_threshold=0.8)
```

`TashkeelDiacritizer` is also callable; `diac(text)` is equivalent to
`diac.diacritize(text)`.

### Limits and errors

Input is capped at `CHAR_LIMIT` (12000 characters); longer text raises
`TashkeelError`. Non-Arabic characters and digits are handled gracefully —
digits collapse to a numeral placeholder for the model and are restored, and
unknown characters pass through untouched.

```python
from arbtok.tashkeel import TashkeelError

try:
    diac.diacritize("ا" * 20000)
except TashkeelError as e:
    print("too long:", e)
```

## Putting it together

The natural pipeline is diacritize, then phonemize:

```python
from arbtok.tashkeel import TashkeelDiacritizer
from arbtok.tokenizer import Sentence

diac = TashkeelDiacritizer()

def phonemize(raw: str) -> str:
    return Sentence(diac.diacritize(raw)).ipa

print(phonemize("ذهب الطالب إلى المدرسة"))
```

The diacritizer is the heavy part of startup (it loads an ONNX session), so
build one `TashkeelDiacritizer` and reuse it across calls rather than
constructing one per sentence.

## Where next

- [quickstart.md](quickstart.md) — the full text-to-IPA path
- [api.md](api.md) — `Sentence` and the token classes
- [advanced.md](advanced.md) — espeak baseline, internals, recipes
