# arbtok

**Arabic text→IPA** with **dialect-aware tashkeel** diacritization, a
self-contained Arabic engine built on
[orthography2ipa](https://github.com/TigreGotico/orthography2ipa), covering MSA,
Classical, and 30+ regional varieties.

## What arbtok adds over orthography2ipa

[orthography2ipa](https://github.com/TigreGotico/orthography2ipa) (o2i) is a
language-agnostic grapheme→IPA lattice engine. For Arabic it assumes
**fully-vocalized** input: given the tashkeel, it transcribes accurately, but
real Arabic text is written **without** the short vowels, and o2i cannot invent
them, a bare skeleton transcribes incompletely wherever a vowel or gemination is
unwritten. That is the gap arbtok exists to close.

arbtok sits on o2i's lattice and adds the layer o2i deliberately leaves out:

- **A bundled neural diacritizer (rawi), extracted from
  [text2tashkeel](https://github.com/TigreGotico/text2tashkeel).** text2tashkeel
  is a diacritization library with a family of ONNX models. Arbtok takes its
  **rawi** ensemble and stitches it into a single 4.9 MB logits ONNX baked into
  the wheel (`arbtok/_ensemble.py`, built by
  `tools/build_ensemble_logits_onnx.py`). There is **no runtime dependency on
  text2tashkeel** and no network: the model rides inside the package. This is
  what lets arbtok read the undiacritized text a person actually types.
- **Dialect-aware fusion, cross-word sandhi, loanword nativization, and a waqf
  register switch**: the sentence-level, variety-specific phonology below.

The split shows up directly in the numbers. On the `arabic-dialects-gold20` set,
scored on the **undiacritized** `raw` skeleton (each lect at its own register:
full iʿrāb for MSA/Classical, pausal for the spoken varieties, using
`scripts/benchmark_gold20.py --undiac`), arbtok roughly **halves** o2i's error and
beats every dialect, while o2i-on-a-skeleton is barely better than espeak-ng:

| system | mean PER (stress-stripped) | MSA `ar` | Classical `arb` |
|---|---|---|---|
| **arbtok** (diacritizer on) | **0.147** | **0.076** | **0.055** |
| orthography2ipa (bare) | 0.302 | 0.363 | 0.444 |
| espeak-ng | 0.308 | 0.345 | 0.314 |

On the *vocalized* form of the same gold, arbtok's diacritizer is idle and it
simply matches o2i (that set does not exercise the layer). The undiacritized
per-dialect table is the benchmark that actually measures arbtok.

## Dialect-aware tashkeel

To our knowledge arbtok is the **only Arabic phonemizer whose diacritization is
dialect-aware**. Every other pipeline runs an MSA-trained diacritizer and then
phonemizes whatever it wrote. Arbtok turns that pipeline around. The bundled
rawi neural ensemble, extracted from
[text2tashkeel](https://github.com/TigreGotico/text2tashkeel) and stitched into a
4.9 MB ONNX inside the wheel (no network, no external model package), exposes
its per-character **distribution**, and arbtok
scores that distribution against **each variety's own phonological licensing**:
the orthography2ipa grapheme table and allophone rules of the target lect
(`docs/rawi-fusion.md`). The chosen tashkeel is the model's most probable
reading *that the dialect's orthography actually admits*, for all 33 supported
lects, from Najdi and Hejazi to Tunisian, Egyptian, and the qeltu Iraqi of
Mosul (`docs/dialects.md`).

So the same bare sentence receives variety-appropriate marks and IPA:

```python
from arbtok.plugin import ArbtokG2PPlugin

bare = "ذهب الولد الى المدرسة"                    # undiacritized input
ArbtokG2PPlugin(lang="ar").transcribe(bare)           # ˈðahab ˈalwalad ˈalaː ˈlmudrasa
ArbtokG2PPlugin(lang="ar-TN").transcribe(bare)        # ˈðahab ˈalwalad ˈalɛː ˈlmudrasa
ArbtokG2PPlugin(lang="ar-SA-x-najd").transcribe("يشرب القهوة في البيت")
# ˈjaʃrab alˈɡahawa ˈfiː ˈlbajt   — Najdi /g/ for qāf, epenthetic gahawa vowel
ArbtokG2PPlugin(lang="ar-TN").transcribe("يشرب القهوة في البيت")
# ˈjaʃrab alˈqahwa ˈfiː ˈlbiːt    — Tunisian monophthong /iː/ in bayt
```

Measured on the bare-input TTS gold (33 lects × 20 sentences, mean per-sentence
phoneme error rate), scoring the ensemble distribution under dialect licensing
outperforms running the same ensemble as a free generator, with the margin
concentrated on the lects that diverge most from MSA, the signature of the
licensing doing the work (`docs/rawi-fusion.md` carries the full table).

Three capabilities define the engine:

1. **Dialect-aware tashkeel**: the fusion scorer above. It is on by default
   (`fusion=False` opts out), guarded so a human's marks are never overwritten
   and a letter the writing spells is never rewritten.
2. **Per-lect cited loanword nativization**: code-switched Latin words are
   read out of the *matrix lect's own* inventory, per published loanword
   literature (Cairene `[manaɡar]` vs Najdi `[manadʒar]`, see below).
3. **Waqf / register policy**: one declared switch between the spoken pausal
   register (the TTS default) and full-iʿrāb recitation (see below).

## The lattice underneath

Word phonology is built on the **orthography2ipa shared lattice**: the
language-agnostic grapheme tokenizer (`PhonetokTokenizer`) over the `ar`
spec grapheme table produces a per-position candidate lattice. The `ar`
engine handles the segment-local phonology natively, gemination (shadda ّ,
glides included), lam-alif / presentation ligatures (ﻻ → `laː`), onset
glides (يَ → `ja`), a hamza carrier's bare /ʔ/ before an explicit harakah, a
fatḥa + standalone alif maksūra as one long vowel (حَتَّى → `ħattaː`), a
sukūn-final **coda glide** (ظَبْي → `ðˤabj`, رَمْي → `ramj`, while فِي stays
`fiː`), and pausal tāʾ marbūṭa. The Arabic morpho-phonology that the shared
grapheme table cannot express is layered on as composable
`LatticeRescorer`s (`arbtok/lattice.py`) rather than a private tokenizer
fork:

- **sun-letter assimilation** (idghām ash-shamsiyya): the lām of the
  definite article ⟨ال⟩ assimilates into a following coronal (sun) letter
  (`al-šams` → `aš-šams`). Moon letters keep the lām (`al-qamar`).
- **hamzat al-waṣl** elision: a word-initial prosthetic alif is silent,
  its harakah carrying the vowel (`istiqbāl`).
- **accusative-alif** silencing after tanwīn al-fatḥ (`marħaban`), and the
  bare glottal stop of a hamza carrier before a sukūn or word edge
  (`taʔθīr`).

Emphatic (pharyngealization) spreading rides on the `ar` spec's own B8
`allophone_rules`. Cross-word sandhi is orthogonal to the word lattice: clitic
joining, cross-word waṣl elision, tanwīn pausal forms, tāʾ marbūṭa, and
idgham/iqlab nasal assimilation all live in the sentence-level orchestration,
exposed to plain orthography2ipa through its sandhi plugin hook
(`arbtok/o2i_plugins.py`). Bare (undiacritized) text is diacritized first by
the bundled rawi ensemble (the dialect-aware fusion path above), entirely
inside the wheel.

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
Arabic pipeline. orthography2ipa stays the language-agnostic base library.

### Engine class

```python
from arbtok.tokenizer import Sentence

Sentence("اَلسَّلَامُ عَلَيْكُمْ").ipa
```

An isolated MSA word transcribes on the shared lattice directly:

```python
from arbtok.lattice import word_ipa

word_ipa("الشَّمْس")   # 'aʃˈʃams' — sun-letter assimilation as a rescorer
word_ipa("الْقَمَر")   # 'ˈalqamar' — moon-letter control (lām kept)
```

Bare text is handled by diacritizing first:

```python
from arbtok.plugin import ArbtokG2PPlugin

plugin = ArbtokG2PPlugin()
plugin.transcribe("كتاب جميل")    # auto-tashkeel + IPA
```

### Varieties

Pass a spec code as `lang=` to phonemize a variety. `arbtok.supported_lects()`
lists every code it resolves to, with the orthography2ipa quality tier of each.
Bare (undiacritized) input is restored **before** dialect allophony applies. The
model and stem lexicon are MSA artifacts, but the fusion scorer constrains the
model's distribution to the readings the *target lect's* orthography licenses
(see the flagship section above and [`docs/rawi-fusion.md`](docs/rawi-fusion.md)).
See [`docs/dialects.md`](docs/dialects.md) for the resolution rules, the
supported list, and the pinned pipeline order.

```python
import arbtok
from arbtok.plugin import ArbtokG2PPlugin

arbtok.supported_lects()[:2]                                   # [Lect('ar', 'research'), …]
ArbtokG2PPlugin(lang="ar-SA-x-najd").transcribe_word("قَهْوَة")  # 'ˈɡahawa'
```

### Waqf, the register switch (`register="pausal"`)

Read aloud, Arabic **pauses in waqf form** (Wright, *A Grammar of the Arabic
Language*, 3rd ed., I §372. Ryding, *A Reference Grammar of MSA*, CUP 2005,
§2.4): at a phrase boundary the word-final short vowel (the case/mood ending,
iʿrāb) is not pronounced, tanwīn *-un/-in* drop with their /n/, tanwīn *-an*
lengthens to /aː/ on its written seat alif, and a tāʾ marbūṭa voiced only by
its ending falls silent with it (مَدِينَةٌ. → *madiːna*). The construct-state
/at/ (an iḍāfa head pausing with its tāʾ) is **not modeled**.

The named switch is `register`: `"pausal"` (the default, the TTS register)
or `"full"` (continuous full-iʿrāb passthrough). Under `"full"` every waqf
reduction is disabled and every written ending is read out. This is the
recitation and pedagogical register, and the mode for fully-vocalized MSA
that should be read exactly as its author pointed it, including scoring
against iʿrāb-keeping gold:

```python
ArbtokG2PPlugin(register="pausal").transcribe("رَأَيْتُ كِتَابًا.")  # …kitaːbaː
ArbtokG2PPlugin(register="full").transcribe("رَأَيْتُ كِتَابًا.")    # …kitaːban
```

Under `register="pausal"`, a pause has to be **written** (a punctuation
token): no pause is invented at the edge of the input. When the diacritizer
runs on bare text it restores the pausal register throughout, since the
modern spoken register keeps no iʿrāb at all. The boolean `pausal=True/False`
is the same switch's original spelling and wins when passed explicitly.

The iʿrāb-driven reductions are facts about the MSA/Classical registers only:
a dialect lect has no case endings to drop, so its final short vowels and its
lexicalized *-an* adverbs (أَهْلًا وَسَهْلًا → *ahlan wasahlan*) are read as
written under either register.

Both modes run the same lattice and rescorers. The flag is consulted in one
place (`arbtok.sandhi`), so the transform applies exactly once.

### Foreign words (loanword nativization)

Real Arabic text is full of Latin-script words, such as *عندي meeting الساعة ٣*. A Latin
run is read as a **loanword**: phonemized with its donor spec (English by default)
and *nativized* into the matrix lect's phonology, out of that lect's own declared
inventory. The nativization table is chosen by walking the orthography2ipa parent
chain, so each lect adapts as its loanword literature says it does. Cairene reads
*manager* with the native stop ǧīm `[manaɡar]` and merges the interdental of *think*
to `[tink]`, while Najdi keeps the affricate `[manadʒar]` and the interdental
`[θink]`. A symbol the matrix lect cannot realize is refused (`None`) rather than
emitted unpronounceable.

```python
ArbtokG2PPlugin(lang="ar-EG").transcribe_word("manager")        # 'manaɡar'
ArbtokG2PPlugin(lang="ar-SA-x-najd").transcribe_word("manager") # 'manadʒar'
```

`nativize=True` is the default (a TTS voice needs a pronounceable reading). Pass
`nativize=False` for linguistic output that must not invent a pronunciation:
the Latin run is then left in place, untranscribed:

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
from arbtok.tashkeel import TashkeelDiacritizer   # the bundled rawi ensemble

TashkeelDiacritizer().diacritize("كتاب جميل")
```

### As orthography2ipa plugins

Installing arbtok registers three **named** orthography2ipa step plugins
(`normalize` / `rescore` / `sandhi`, see `arbtok/o2i_plugins.py`) so plain
orthography2ipa can transcribe **undiacritized** Arabic, which it cannot do
alone since its input contract is diacritized text. The plugin is opted into at
the call site, never applied implicitly:

```python
from orthography2ipa import G2P

G2P("ar").transcribe("كتب")                                   # 'ˈktb' — no vowels to read
G2P("ar", plugins={"normalize": "arbtok"}).transcribe("كتب")  # 'ˈkatab' — arbtok restores them
```

## Quality benchmarks

The test suite pins a gold sentence set (CER target ≤ 5% against the
reference transcriptions) and benchmarks against espeak-ng. See
`tests/test_ipa_fuzzy.py` and `docs/` for details.

For **per-lect** scoring, every resolvable variety against the orthography2ipa
Arabic TTS gold, diacritized and bare, next to espeak-ng, run
`python scripts/benchmark_stack.py --lect`. See
[`docs/benchmarks.md`](docs/benchmarks.md), which carries the full table and the
honesty note on why those figures are engine-similarity to cited-rule o2i output
rather than native-validated truth.

## Related projects

- [orthography2ipa](https://github.com/TigreGotico/orthography2ipa), the
  language-agnostic grapheme-to-IPA lattice engine arbtok builds on.
- [text2tashkeel](https://github.com/TigreGotico/text2tashkeel), the
  diacritization library that trains the rawi model family arbtok bundles.

## Documentation

[`docs/`](docs/quickstart.md) covers the diacritizer, the fusion scorer,
dialect resolution, Arabizi input, the code-switched gold set, the full API,
and advanced usage.

## License

Apache-2.0.
