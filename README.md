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

### Varieties

Pass a spec code as `lang=` to phonemize a variety; `arbtok.supported_lects()`
lists every code it resolves to, with the orthography2ipa quality tier of each.
Bare (undiacritized) input is restored on MSA orthography **before** dialect
allophony applies — the diacritizer and stem lexicon are MSA artifacts. See
[`docs/dialects.md`](docs/dialects.md) for the resolution rules, the supported
list, and the pinned pipeline order.

```python
import arbtok
from arbtok.plugin import ArbtokG2PPlugin

arbtok.supported_lects()[:2]                                   # [Lect('ar', 'research'), …]
ArbtokG2PPlugin(lang="ar-SA-x-najd").transcribe_word("قَهْوَة")  # 'ˈɡahawa'
```

### Foreign words (loanword nativization)

Real Arabic text is full of Latin-script words — *عندي meeting الساعة ٣*. A Latin
run is read as a **loanword**: phonemized with its donor spec (English by default)
and *nativized* into the matrix lect's phonology, out of that lect's own declared
inventory. The nativization table is chosen by walking the orthography2ipa parent
chain, so each lect adapts as its loanword literature says it does — Cairene reads
*manager* with the native stop ǧīm `[manaɡar]` and merges the interdental of *think*
to `[tink]`, where Najdi keeps the affricate `[manadʒar]` and the interdental
`[θink]`. A symbol the matrix lect cannot realize is refused (`None`) rather than
emitted unpronounceable.

```python
ArbtokG2PPlugin(lang="ar-EG").transcribe_word("manager")        # 'manaɡar'
ArbtokG2PPlugin(lang="ar-SA-x-najd").transcribe_word("manager") # 'manadʒar'
```

`nativize=True` is the default (a TTS voice needs a pronounceable reading). Pass
`nativize=False` for linguistic output that must not invent a pronunciation — the
Latin run is then left in place, untranscribed:

```python
ArbtokG2PPlugin(lang="ar-SA-x-najd", nativize=False).transcribe("عندي meeting")
# 'ˈʕindiː meeting'
```

Cited tables ship for Najdi (`ar-SA-x-najd`, Alhoody 2019), Egyptian (`ar-EG`,
Hafez 1996 / Watson 2002) and Levantine (`ar-x-levantine`, Al-Saidat 2011 / Cowell
1964). A lect with no table of its own (e.g. `ar-KW`) falls back to a conservative
pan-Arabic default.

### Diacritization only

```python
from arbtok.tashkeel import TashkeelDiacritizer   # wraps text2tashkeel

TashkeelDiacritizer().diacritize("كتاب جميل")
```

## Quality benchmarks

The test suite pins a gold sentence set (CER target ≤ 5% against the
reference transcriptions) and benchmarks against espeak-ng. See
`tests/test_ipa_fuzzy.py` and `docs/` for details.

For **per-lect** scoring — every resolvable variety against the orthography2ipa
Arabic TTS gold, diacritized and bare, next to espeak-ng — run
`python scripts/benchmark_stack.py --lect` and see
[`docs/benchmarks.md`](docs/benchmarks.md), which carries the full table and the
honesty note on why those figures are engine-similarity to cited-rule o2i output
rather than native-validated truth.
