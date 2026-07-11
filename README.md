# arbtok

Rule-based **Arabic (MSA) text→IPA** with **tashkeel** diacritization — a
downstream Arabic engine built on
[orthography2ipa](https://github.com/TigreGotico/orthography2ipa).

Word phonology is built on the **orthography2ipa shared lattice**: the
language-agnostic grapheme tokenizer (`PhonetokTokenizer`) over the `ar`
spec grapheme table produces a per-position candidate lattice, and the
Arabic morpho-phonology that a plain table lookup cannot express is layered
on as composable `LatticeRescorer`s (`arbtok/lattice.py`) rather than a
private tokenizer fork:

- **sun-letter assimilation** (idghām ash-shamsiyya) — the lām of the
  definite article ⟨ال⟩ assimilates into a following coronal (sun) letter
  (`al-šams` → `aš-šams`); moon letters keep the lām (`al-qamar`);
- **hamzat al-waṣl** elision — a word-initial prosthetic alif is silent,
  its harakah carrying the vowel (`istiqbāl`);
- **gemination** (shadda / tashdīd), **mater-lectionis** vowel
  lengthening, hamza-carrier vowel de-duplication, and semivowel onset
  disambiguation.

Emphatic (pharyngealization) spreading rides on the `ar` spec's own B8
`allophone_rules`. Cross-word sandhi — clitic joining, cross-word waṣl
elision, tanwīn pausal forms, tāʾ marbūṭa, and idgham/iqlab nasal
assimilation — is orthogonal to the word lattice and lives in the
sentence-level orchestration. Bare (undiacritized) text is diacritized
first via [text2tashkeel](https://github.com/TigreGotico/text2tashkeel) —
a model picker over bundled ONNX diacritization models.

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

An isolated MSA word transcribes on the shared lattice directly:

```python
from arbtok.lattice import word_ipa

word_ipa("الشَّمْس")   # 'aʃʃams' — sun-letter assimilation as a rescorer
word_ipa("الْقَمَر")   # 'alqamar' — moon-letter control (lām kept)
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
