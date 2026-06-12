# arbtok

Rule-based **Arabic (MSA) text→IPA** with **tashkeel** diacritization — a
downstream Arabic engine built on
[orthography2ipa](https://github.com/TigreGotico/orthography2ipa).

A context-sensitive token tree (sentence → words → characters) implements the
morpho-phonological rules that table lookups cannot express: sun-letter
assimilation, hamzat al-waṣl elision, tanwīn pausal forms, tāʾ marbūṭa,
mater-lectionis vowel lengthening, definite-article waṣl, and idgham/iqlab
nasal assimilation. Bare (undiacritized) text is diacritized first via
[text2tashkeel](https://github.com/TigreGotico/text2tashkeel) — a model
picker over bundled ONNX diacritization models.

> Honesty note: the gold IPA reference set was LLM-generated and has not been
> validated by a native MSA speaker. If you speak MSA, pull requests are very
> welcome.

## Installation

```bash
pip install arbtok
```

## Usage

arbtok is built **on** [orthography2ipa](https://github.com/TigreGotico/orthography2ipa)
(spec data and the shared `G2PPlugin`/`WordContext` base types) and owns the
Arabic pipeline — orthography2ipa stays the language-agnostic base library.

### Engine class

```python
from arbtok.tokenizer import Sentence

Sentence("اَلسَّلَامُ عَلَيْكُمْ").ipa
```

Bare text is handled by diacritizing first:

```python
from arbtok.plugin import ArbtokG2PPlugin

plugin = ArbtokG2PPlugin()
plugin.transcribe("كتاب جميل")    # auto-tashkeel + IPA
```

### Diacritization only

```python
from arbtok.tashkeel import TashkeelDiacritizer   # wraps text2tashkeel

TashkeelDiacritizer().diacritize("كتاب جميل")
```

## Quality benchmarks

The test suite pins a gold sentence set (CER target ≤ 5% against the
reference transcriptions) and benchmarks against espeak-ng. See
`tests/test_ipa_fuzzy.py` and `docs/` for details.
