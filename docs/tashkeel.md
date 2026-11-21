# Diacritization (tashkeel)

Arabic in the wild is written without short vowels. The phonemizer needs them, no diacritics means no vowels to emit. arbtok restores diacritics with a model it
**bundles**: the rawi stitched ensemble, one 4.9 MB int8 ONNX inside the wheel
(`arbtok/_ensemble.py`, onnxruntime + numpy, no PyTorch, no network, no external
diacritization package. It also restores hamza and the dagger-alef).

The model's weights are the TigreGotico rawi family (rawi-v2 gate + rawi-v3
value head, Apache-2.0, published on PyPI in the `text2tashkeel` wheel). The
bundled re-export also emits the pre-argmax **distribution**, which is
what makes the dialect-aware fusion scorer possible
([rawi-fusion.md](rawi-fusion.md)) and lets the generator mask the classes the
writing contradicts *before* the argmax, a letter the writing spells is never
rewritten and a human's marks are never overwritten (`arbtok/orthography.py`).
`tools/build_ensemble_logits_onnx.py` reproduces the artifact and asserts that
the exposed distribution's argmax equals the graph's own decision.

## `TashkeelDiacritizer`

```python
from arbtok.tashkeel import TashkeelDiacritizer

diac = TashkeelDiacritizer()
print(diac.diacritize("قال الملك"))
```

### `diacritize(text, pausal=False) -> str`

Returns the input text with diacritics inserted.

```python
diac.diacritize("ذهب الطالب")
```

`pausal=True` drops the word-final case and mood endings (iʿrāb), leaving the
pausal (waqf) form that is spoken, the transform is deterministic and
rule-cited (`arbtok/waqf.py`. Wright I §372, Ryding §2.4):

```python
diac.diacritize("كتب", pausal=True)
```

`TashkeelDiacritizer` is also callable. `diac(text)` is equivalent to
`diac.diacritize(text)`.

## The stem lexicon

A model asked which vowels كتاب carries has to *infer* the answer, and on
high-frequency vocabulary it infers wrong (`كَتَاب` /kataːb/ for `كِتَاب`
/kitaːb/). But that is not a thing to infer, it is a thing to look up. So
`ArbtokG2PPlugin` and `LatticeDiacritizer` consult a **diacritized-stem
lexicon** before they ever call the model:

```python
from arbtok.plugin import ArbtokG2PPlugin

ArbtokG2PPlugin()                          # the default lexicon
ArbtokG2PPlugin(lexicon="/data/mine.tsv")  # a local file, a URL, or an hf:// id
ArbtokG2PPlugin(lexicon=None)              # the model, unassisted
```

The default lexicon is the Hugging Face dataset
`TigreGotico/arabic-stem-lexicon`, file `ar-stems.tsv`. The first call that
diacritizes downloads it to the Hugging Face cache. When the file is not in the
cache and the Hub is offline (`HF_HUB_OFFLINE=1`) or cannot be reached, that call
raises `arbtok.ModelUnavailableError`, a `ValueError` that names the dataset and
the file. A lexicon you name that cannot be read for another reason, such as a
missing local file, raises its base class `arbtok.lexicon.LexiconUnavailable`. The
engine does not fall back to the model. To run with no network, fetch the file
once, or pass `lexicon=None`.

The lexicon maps an **undiacritized surface form** to the most frequent
**diacritized stem** for it in a large diacritized corpus, not to IPA. The stem
is fed back through arbtok's own engine, so a looked-up word still gets emphasis
spread, gemination, stress and the pausal treatment, and the *same* entry yields
MSA under `ar` and Najdi under `ar-SA-x-najd`. A surface→IPA lexicon would freeze
one variety's pronunciation into the data and bypass all of that.

It is a *stem* because a classical corpus writes the full iʿrāb: كِتَابٌ /
كِتَابَ / كِتَابِ are one word in three syntactic positions. The case ending is
stripped before counting, waqf drops it anyway, which collapses the three into
one better-attested entry and leaves exactly the part the model gets wrong.

An entry is held to the same guards as a model proposal: it must spell the word
it was asked about, and the variety's grapheme table must license it. Data can be
wrong too.

The stem lexicon is not bundled. It is mined from a GPL-2.0 corpus and arbtok is
Apache-2.0, so it ships as a Hugging Face dataset fetched on first use. The
diacritizer's model weights are different: they ship inside the wheel.
`scripts/build_stem_lexicon.py` builds a lexicon from any diacritized corpus.

## The per-lect closed-class lexicon

The stem lexicon answers *which vowels an MSA word carries*, and that is the
right answer for the shared vocabulary the dialects inherit unchanged. It is the
wrong answer for the **closed class**, the negators, demonstratives, relatives,
interrogatives, prepositions and the handful of very-high-frequency verbs and
particles a dialect writes in the inherited orthography but vocalizes its own
way. Asked to point ⟨كي⟩ for a Maghrebi voice, the MSA model restores ⟨كَي⟩
/kaj/. The dialect says ⟨كِي⟩ /kiː/. The model is not guessing badly, it is
answering for the wrong variety, because the word it is pointing is not the word
that is spoken.

These words are few, frequent, and **written down** in every dialect grammar, so
arbtok looks them up rather than inferring them, and it looks them up *first*, a
closed-class dialect entry is a **hard prior** consulted ahead of the stem
lexicon and the model:

```python
from arbtok.plugin import ArbtokG2PPlugin

ArbtokG2PPlugin(lang="ar-x-maghrebi").transcribe("كيفاش راك اليوم")
ArbtokG2PPlugin(lang="ar-x-maghrebi", dialect_lexicon=False)  # off
```

The value is a **diacritized surface form**, not IPA, fed back through the
variety's lattice exactly like a stem entry, so a looked-up word still gets the
lect's allophony, stress and pausal treatment, and the same entry reads
correctly under every spec that shares the word. An entry is held to the same
guards as a model proposal (it must spell the word it keys, and the variety's
grapheme table must license it) and never fires on a word a human has already
vocalized, the author-complete gate runs first, and a marked surface form never
matches an undiacritized key.

Unlike the stem lexicon, this data is **hand-authored from the dialect grammars**
(Harrell, Cowell, Erwin, Ingham, Badawi & Hinds, Heath, Marçais, Singer, …) rather
than mined, so it is small, Apache-2.0-clean, and **bundled** in the wheel at
`arbtok/data/lexicons/<lect>.tsv`. Each row carries its source. A lect inherits
its ancestors' entries, `ar-MA` sees the pan-Maghrebi function words in
`ar-x-maghrebi.tsv` *and* its own Moroccan-specific ones, the more specific file
winning on a collision. See `arbtok/dialect_lexicon.py`.

`ar.tsv` (Modern Standard) and `arb.tsv` (Classical, which every dialect lect
inherits) hold function words whose bare spelling the model misreads. Bare `الي`
is `إِلَى` "to", written with ي for ى (Wright I §358 (a)), so
`ArbtokG2PPlugin().transcribe("ذهب الي البيت")` gives `ˈðahab ˈʔilaː lˈbajt`. The
Maghrebi file reads bare `الي` as the relative `الِّي` and wins there.

### Errors

Failures inside the model raise `TashkeelError` with the underlying cause
attached.

The G2P engine (`arbtok.plugin.ArbtokG2PPlugin`) raises one kind of error and
absorbs the rest. A stem lexicon that cannot be read raises
`arbtok.lexicon.LexiconUnavailable`. Its subclass `arbtok.ModelUnavailableError`,
also a `ValueError`, is raised for a file on the Hugging Face Hub that is not in
the local cache when the Hub is offline or cannot be reached. Any other
diacritization failure passes the text through: the engine transcribes whatever
diacritics the input carries.

---
[← Quickstart](quickstart.md) · [Home](../README.md) · [Rawi-lattice fusion →](rawi-fusion.md)
