# What arbtok adds over orthography2ipa

<!-- agent-hint
covers: the gap arbtok closes in orthography2ipa, the three capabilities of the engine, the word lattice underneath and the sibling projects
source: arbtok/plugin.py, arbtok/lattice.py, arbtok/sandhi.py, arbtok/o2i_plugins.py, arbtok/_ensemble.py, tools/build_ensemble_logits_onnx.py, scripts/benchmark_gold20.py
generated: no
verify: .venv/bin/python scripts/check_docs_examples.py docs/overview.md
see: tashkeel.md, rawi-fusion.md, dialects.md, waqf.md
-->

[orthography2ipa](https://github.com/TigreGotico/orthography2ipa) (o2i) is a
language-agnostic grapheme-to-IPA lattice engine. For Arabic it assumes
**fully vocalized** input. Given the tashkeel, it transcribes accurately. Real
Arabic text is written **without** the short vowels, and o2i cannot invent them:
a bare skeleton transcribes incompletely wherever a vowel or a gemination is
unwritten. arbtok closes that gap.

arbtok sits on the o2i lattice and adds the layer that o2i leaves out:

- **A bundled neural diacritizer (rawi).** The rawi ensemble comes from
  [text2tashkeel](https://github.com/TigreGotico/text2tashkeel), a diacritization
  library with a family of ONNX models. arbtok stitches the ensemble into one
  4.9 MB logits ONNX file inside the wheel (`arbtok/_ensemble.py`, built by
  `tools/build_ensemble_logits_onnx.py`). arbtok has no runtime dependency on
  text2tashkeel, and the model needs no network. This lets arbtok read the
  undiacritized text that a person types.
- **Dialect-aware fusion, cross-word sandhi, loanword nativization and a waqf
  register switch.** These are the sentence-level, variety-specific phonology
  that the sections below describe.

## The split in numbers

The table scores the `arabic-dialects-gold20` set on the **undiacritized**
`raw` skeleton. Each lect runs at its own register: full iʿrāb for MSA and
Classical, pausal for the spoken varieties. The command is
`python scripts/benchmark_gold20.py --undiac`. The script pulls the gold from
Hugging Face at run time, so the figures follow the gold. The table gives the
mean PER with stress stripped, over the seven lects that the script scores.

| system | mean PER | MSA `ar` | Classical `arb` |
|---|---|---|---|
| **arbtok** (diacritizer on) | **0.119** | **0.048** | **0.047** |
| orthography2ipa (bare) | 0.318 | 0.363 | 0.444 |
| espeak-ng | 0.297 | 0.345 | 0.314 |

arbtok scores a lower PER than o2i and espeak-ng on every lect of the set.
o2i on a skeleton scores about the same as espeak-ng.

On the vocalized form of the same gold, the diacritizer has no work to do and
arbtok matches o2i. That set does not exercise the layer. The undiacritized
table is the benchmark that measures arbtok. See
[benchmarks.md](benchmarks.md) for the per-lect scores.

## Three capabilities

1. **Dialect-aware tashkeel.** The fusion scorer is on by default (`fusion=False`
   opts out). It never overwrites the marks of a human, and it never rewrites a
   letter that the writing spells. See [rawi-fusion.md](rawi-fusion.md).
2. **Per-lect cited loanword nativization.** The engine reads a code-switched
   Latin word out of the inventory of the *matrix lect*, as the published
   loanword literature describes it. Cairene reads *manager* as `[maniɡar]`,
   and Najdi reads it as `[manidʒar]`. See
   [dialects.md](dialects.md#foreign-words-per-lect-nativization).
3. **Waqf and register policy.** One declared switch chooses between the spoken
   pausal register, the TTS default, and full-iʿrāb recitation. See
   [waqf.md](waqf.md).

## The lattice underneath

Word phonology rests on the **orthography2ipa shared lattice**. The
language-agnostic grapheme tokenizer (`PhonetokTokenizer`) runs over the
grapheme table of the `ar` spec and produces a candidate lattice for each
position. The `ar` engine handles the segment-local phonology natively:

- gemination (shadda), glides included.
- lam-alif and presentation ligatures.
- onset glides.
- the bare /ʔ/ of a hamza carrier before an explicit harakah.
- a fatḥa followed by a standalone alif maksūra, read as one long vowel.
- a sukūn-final coda glide, where `فِي` stays `fiː`.
- pausal tāʾ marbūṭa.

```python
from arbtok.tokenizer import Sentence

print(Sentence("ظَبْي").ipa)    # ˈðˤɑbj
print(Sentence("رَمْي").ipa)    # ˈramj
print(Sentence("فِي").ipa)      # fiː
print(Sentence("حَتَّى").ipa)    # ˈħattaː
print(Sentence("ﻻ").ipa)       # ˈlaː
print(Sentence("يَ").ipa)       # ˈja
```

The Arabic morpho-phonology that the shared grapheme table cannot express is
layered on as composable `LatticeRescorer` classes (`arbtok/lattice.py`), not as
a private tokenizer fork:

- **Sun-letter assimilation** (idghām ash-shamsiyya). The lām of the definite
  article assimilates into a following coronal (sun) letter. Moon letters keep
  the lām.
- **Hamzat al-waṣl elision.** A word-initial prosthetic alif is silent, and its
  harakah carries the vowel.
- **Accusative-alif silencing** after tanwīn al-fatḥ, and the bare glottal stop
  of a hamza carrier before a sukūn or a word edge.

```python
from arbtok.lattice import word_ipa

print(word_ipa("الشَّمْس"))      # aʃˈʃams
print(word_ipa("الْقَمَر"))      # ˈalqamar
print(word_ipa("اِسْتِقْبَال"))   # istiqˈbaːl
print(word_ipa("مَرْحَبًا"))      # ˈmarħaban
print(word_ipa("تَأْثِير"))       # taʔˈθiːr
```

Emphatic (pharyngealization) spreading uses the `allophone_rules` of the `ar`
spec. Cross-word sandhi is separate from the word lattice. Clitic joining,
cross-word waṣl elision, tanwīn pausal forms, tāʾ marbūṭa and the idgham and
iqlab nasal assimilation all live in the sentence-level orchestration. The
`sandhi` field of the o2i `Pipeline` exposes them to plain orthography2ipa
(`arbtok/o2i_plugins.py`, see [api.md](api.md)). The bundled rawi ensemble
diacritizes bare text first, inside the wheel.

## Related projects

- [orthography2ipa](https://github.com/TigreGotico/orthography2ipa), the
  language-agnostic grapheme-to-IPA lattice engine that arbtok builds on. It
  provides the spec data and the shared `G2PPlugin` and `WordContext` base
  types. arbtok owns the Arabic pipeline.
- [text2tashkeel](https://github.com/TigreGotico/text2tashkeel), the
  diacritization library that trains the rawi model family that arbtok bundles.

---
[← Quickstart](quickstart.md) · [Home](index.md) · [Diacritization →](tashkeel.md)
