# arbtok

Rule-based **Arabic (MSA) text→IPA** with **tashkeel** diacritization — a
downstream Arabic engine built on
[orthography2ipa](https://github.com/TigreGotico/orthography2ipa).

Word phonology is built on the **orthography2ipa shared lattice**: the
language-agnostic grapheme tokenizer (`PhonetokTokenizer`) over the `ar`
spec grapheme table produces a per-position candidate lattice. The `ar`
engine (orthography2ipa ≥ 1.70) handles the segment-local phonology
natively — gemination (shadda ّ, glides included), lam-alif / presentation
ligatures (ﻻ → `laː`), onset glides (يَ → `ja`), a hamza carrier's bare
/ʔ/ before an explicit harakah, a fatḥa + standalone alif maksūra as one
long vowel (حَتَّى → `ħattaː`), a sukūn-final **coda glide** (ظَبْي → `ðˤabj`,
رَمْي → `ramj`, while فِي stays `fiː`), and pausal tāʾ marbūṭa. The last two
were once patched by arbtok's own `MaterLectionisRescorer` /
`GlideCodaRescorer`; orthography2ipa 1.70 (upstream #251) fixed them at
source, so those rescorers are gone. The Arabic morpho-phonology that the
shared table still cannot express is layered on as composable
`LatticeRescorer`s (`arbtok/lattice.py`) rather than a private tokenizer
fork:

- **sun-letter assimilation** (idghām ash-shamsiyya) — the lām of the
  definite article ⟨ال⟩ assimilates into a following coronal (sun) letter
  (`al-šams` → `aš-šams`); moon letters keep the lām (`al-qamar`);
- **hamzat al-waṣl** elision — a word-initial prosthetic alif is silent,
  its harakah carrying the vowel (`istiqbāl`);
- **accusative-alif** silencing after tanwīn al-fatḥ (`marħaban`), and the
  bare glottal stop of a hamza carrier before a sukūn or word edge
  (`taʔθīr`).

Emphatic (pharyngealization) spreading rides on the `ar` spec's own B8
`allophone_rules`. Cross-word sandhi — clitic joining, cross-word waṣl
elision, tanwīn pausal forms, tāʾ marbūṭa, and idgham/iqlab nasal
assimilation — is orthogonal to the word lattice and lives in the
sentence-level orchestration. orthography2ipa 1.70 also added a shared
**sentence-context seam** (`orthography2ipa.sentence`: `SentenceLattice` +
`SentenceRescorer` with `prev_word`/`next_word` edge slots and
`is_phrase_final`), the sanctioned home for that cross-word layer; arbtok's
migration of its space-boundary waṣl elision and tanwīn pausal forms onto
the seam is in progress (see `docs/` and the tracking notes). Bare
(undiacritized) text is diacritized
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
