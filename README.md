# arbtok

**Arabic text→IPA** with **dialect-aware tashkeel** diacritization — a
self-contained Arabic engine built on
[orthography2ipa](https://github.com/TigreGotico/orthography2ipa), covering MSA,
Classical, and 30+ regional varieties.

## Dialect-aware tashkeel — the flagship

To our knowledge arbtok is the **only Arabic phonemizer whose diacritization is
dialect-aware**. Every other pipeline runs an MSA-trained diacritizer and then
phonemizes whatever it wrote; arbtok turns that pipeline around. The bundled
rawi neural ensemble (a 4.9 MB stitched ONNX inside the wheel — no network, no
external model package) exposes its per-character **distribution**, and arbtok
scores that distribution against **each variety's own phonological licensing**:
the orthography2ipa grapheme table and allophone rules of the target lect
(`docs/rawi-fusion.md`). The chosen tashkeel is the model's most probable
reading *that the dialect's orthography actually admits* — for all 33 supported
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
concentrated on the lects that diverge most from MSA — the signature of the
licensing doing the work (`docs/rawi-fusion.md` carries the full table).

Three capabilities define the engine:

1. **Dialect-aware tashkeel** — the fusion scorer above; on by default
   (`fusion=False` opts out), guarded so a human's marks are never overwritten
   and a letter the writing spells is never rewritten.
2. **Per-lect cited loanword nativization** — code-switched Latin words are
   read out of the *matrix lect's own* inventory, per published loanword
   literature (Cairene `[manaɡar]` vs Najdi `[manadʒar]`; see below).
3. **Waqf / register policy** — one declared switch between the spoken pausal
   register (the TTS default) and full-iʿrāb recitation (see below).

## The lattice underneath

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
(undiacritized) text is diacritized first by the bundled rawi ensemble —
the dialect-aware fusion path above — entirely inside the wheel.

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
Bare (undiacritized) input is restored **before** dialect allophony applies; the
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

### Waqf — the pausal register (`pausal=True`)

Read aloud, Arabic **pauses in waqf form** (Wright, *A Grammar of the Arabic
Language*, 3rd ed., I §372; Ryding, *A Reference Grammar of MSA*, CUP 2005,
§2.4): at a phrase boundary the word-final short vowel (the case/mood ending,
iʿrāb) is not pronounced, tanwīn *-un/-in* drop with their /n/, tanwīn *-an*
lengthens to /aː/ on its written seat alif, and a tāʾ marbūṭa voiced only by
its ending falls silent with it (مَدِينَةٌ. → *madiːna*). The construct-state
/at/ (an iḍāfa head pausing with its tāʾ) is **not modeled**.

`pausal=True` is the default — the TTS register. A pause has to be **written**
(a punctuation token): no pause is invented at the edge of the input. When the
diacritizer runs on bare text it restores the pausal register throughout,
since the modern spoken register keeps no iʿrāb at all. Pass `pausal=False`
for the full-iʿrāb passthrough (recitation/pedagogical register, and the mode
to use against iʿrāb-keeping gold):

```python
ArbtokG2PPlugin(pausal=True).transcribe("رَأَيْتُ كِتَابًا.")   # …kitaːbaː
ArbtokG2PPlugin(pausal=False).transcribe("رَأَيْتُ كِتَابًا.")  # …kitaːban
```

Both modes run the same lattice and rescorers; the flag is consulted in one
place (`arbtok.sandhi`), so the transform applies exactly once.

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
from arbtok.tashkeel import TashkeelDiacritizer   # the bundled rawi ensemble

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
