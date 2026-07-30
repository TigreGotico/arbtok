# Varieties

A variety is an **orthography2ipa spec**, named by its code, and each variety's
spec does more than allophony: its grapheme table is the **licensing filter**
that makes arbtok's tashkeel dialect-aware (the fusion scorer picks the model's
most probable reading the variety's orthography admits, see
[rawi-fusion.md](rawi-fusion.md)):

```python
from arbtok.plugin import ArbtokG2PPlugin

ArbtokG2PPlugin(lang="ar-SA-x-najd").transcribe_word("قَهْوَة")   # 'ˈɡahawa'
ArbtokG2PPlugin(lang="ar-SA-x-hejaz").transcribe_word("بَيْت")    # 'ˈbeːt'
ArbtokG2PPlugin().transcribe_word("قَهْوَة")                      # 'ˈqahwa'  (MSA)
```

The variety may also ride on `WordContext.lang` per call, which overrides the
instance default. A tag that names no Arabic spec narrows a subtag at a time
(`ar-SA-x-najd` → `ar-SA` → `ar`) and ultimately falls back to the `ar` leaf, so
an unknown region is MSA rather than an error.

Any Arabic spec orthography2ipa carries can be named, `ar`, `arb` (Classical),
the proto nodes (`ar-x-peninsular`, `ar-x-gulf`, `ar-x-levantine`,
`ar-x-maghrebi`, `ar-x-mashriqi`), and the leaves (`ar-SA-x-najd`,
`ar-SA-x-hejaz`, `ar-EG`, `ar-IQ`, `ar-MA`, …).

## What `lang=` resolves to

`arbtok.supported_lects()` enumerates every variety `lang=` accepts, each with
the orthography2ipa `quality` tier of its spec, so the list tracks the
installed data set rather than a table in arbtok. The tier reports how far the
spec's cited rule set has been taken (`research` vs `skeleton`/`stub`), not a
promise about arbtok's cascade.

```python
import arbtok

for lect in arbtok.supported_lects():
    print(lect.code, lect.tier)
```

| code | tier | code | tier |
|---|---|---|---|
| `ar` | research | `ar-QA` | research |
| `arb` | research | `ar-SA-x-najd` | research |
| `ar-EG` | research | `ar-SA-x-hejaz` | research |
| `ar-SD` | research | `ar-YE` | research |
| `ar-SY` | research | `ar-MA` | research |
| `ar-LB` | research | `ar-x-gulf` | research |
| `ar-JO` | research | `ar-x-levantine` | research |
| `ar-PS` | research | `ar-Latn-buckwalter` | research |
| `ar-IQ` | research | `ar-DZ` | skeleton |
| `ar-IQ-x-qeltu` | research | `ar-TN` | skeleton |
| `ar-KW` | research | `ar-LY` | skeleton |
| `ar-BH` | research | `ar-MR` | skeleton |
| `ar-AE` | research | `ar-TD` | skeleton |
| `ar-OM` | research | `ar-NG` | skeleton |
| | | `ar-x-maghrebi` | skeleton |
| | | `ar-x-mashriqi` | skeleton |
| | | `ar-x-peninsular` | skeleton |

(The `skeleton`-tier grouping nodes and Maghrebi/Sudanic leaves resolve and read
their grapheme layer, but their allophone rule sets are not at research tier. The
tier is a property of the installed orthography2ipa spec, not of arbtok.)

## Pipeline order: MSA restoration before dialect allophony

The stem lexicon and the tashkeel diacritizer are **MSA artifacts**, and
dialect text is *written* in MSA orthography. So when the input is bare
(undiacritized), the pipeline restores the short vowels on the MSA-shaped
orthography **first**, and the word lattice applies the target variety's
allophony **after** that, on the resulting segments:

```
normalize → diacritize (MSA model, guarded by the lattice) → word lattice
          → structural rescorers → the spec's allophone rules
```

The order is observable. Bare `قلم`:

```python
from arbtok.plugin import ArbtokG2PPlugin

ArbtokG2PPlugin(lang="ar", diacritize=True).transcribe("قلم")          # 'ˈqalam'
ArbtokG2PPlugin(lang="ar-SA-x-najd", diacritize=True).transcribe("قلم") # 'ˈɡalam'
ArbtokG2PPlugin(lang="ar-SA-x-najd", diacritize=False).transcribe("قلم") # 'ɡlm'
```

`ˈɡalam` carries both the restored MSA vowels *and* the Najdi qāf → /ɡ/ reflex:
it can only exist if the MSA diacritizer ran first (it supplied the vowels the
bare skeleton lacked) and the Najdi allophony ran after it (it supplied the
/ɡ/). Reversing the stages would hand the MSA diacritizer a string the lattice
had already turned to IPA. `tests/test_pipeline_order.py` pins this.

## Where a variety's phonology comes from

Two layers, both read from the spec:

**The grapheme table** gives each letter its realization, the qāf reflex
(MSA /q/, Najdi and Hejazi /ɡ/, Cairene /ʔ/), the interdental treatment, the
jīm. Both the word lattice and the sentence cascade read this.

**The `allophone_rules`** give the context-conditioned phonology, and they fire
in the word lattice, where arbtok's structural rescorers run first (they resolve
*which segment* a slot is) and the rule-compiled rescorer then realizes those
segments in context:

| variety | rule | example |
|---|---|---|
| Najdi | velar affrication /k/ → [ts] by a front vowel (Ingham 1994) | كِتَاب → `tsitaːb` |
| Najdi | gahawa-syndrome epenthesis after a guttural coda (Ingham 1994) | قَهْوَة → `ɡahawa` |
| Hejazi | monophthongization /aj/ → [eː] (Omar 1975. Abdoh 2010) | بَيْت → `beːt` |
| Gulf | kashkasha /k/ → [tʃ] by a high front vowel | كِتَاب → `tʃitaːb` |
| all Peninsular | emphatic spreading (Watson 2002) | صَبْر → `sˤɑbr` |

Saudi is not one variety, and it is not Gulf: Najdi affricates /k/ to **[ts]**,
Gulf to **[tʃ]**, and Hejazi keeps **/k/**.

## Foreign words: per-lect nativization

A Latin-script (or other non-Arabic) run is read as a **loanword**: phonemized
with its donor spec (English by default) and *nativized* into the matrix lect's
phonology, out of that lect's own declared inventory (`arbtok.translit`). A lect
adapts a loan as its own loanword literature says it does, so the nativization
table is chosen by walking the orthography2ipa **parent chain**, no hardcoded
lang→zone map, and the first ancestor carrying a table wins:

| table | keyed at | inherited by | source |
|---|---|---|---|
| Najdi | `ar-SA-x-najd` |, | Alhoody (2019) |
| Egyptian | `ar-EG` |, | Hafez (1996). Watson (2002) |
| Levantine | `ar-x-levantine` | `ar-LB`, `ar-SY`, `ar-PS`, `ar-JO` | Al-Saidat (2011). Cowell (1964) |
| default | `ar` | every un-tabled lect (e.g. `ar-KW` → `ar-x-gulf` → `ar-x-peninsular` → …) | Watson (2002). Holes (2004) |

```python
ArbtokG2PPlugin(lang="ar-EG").transcribe_word("manager")         # 'manaɡar'  (Cairene stop ǧīm)
ArbtokG2PPlugin(lang="ar-SA-x-najd").transcribe_word("manager")  # 'manadʒar' (Najdi affricate)
ArbtokG2PPlugin(lang="ar-EG").transcribe_word("think")           # 'tink'     (interdental merger)
```

Whatever a table emits must be realizable in the matrix lect's inventory. A symbol
the lect does not declare is **refused** (`transliterate` returns `None`) rather
than emitted as an unpronounceable token. So Najdi's `[-inɡ]` reading of *meeting*
is refused for MSA (which has no /ɡ/), and the Egyptian interdental merger is what
lets *think* be realized at all in `ar-EG` (which has no /θ/).

`nativize=True` is the TTS default. `nativize=False` leaves a Latin run in place,
untranscribed, for linguistic output that must not invent a pronunciation:

```python
ArbtokG2PPlugin(lang="ar-SA-x-najd", nativize=False).transcribe("عندي meeting")
# 'ˈʕindiː meeting'
```

## Known limits

- The **sentence cascade has no allophone pass**, it reads the grapheme layer
  only. Word-level transcription (`transcribe_word`, `arbtok.lattice.word_ipa`)
  is where a variety's rules fire.
- A diphthong **split across slots** is not one segment, so a rule targeting it
  cannot see it: يَوْم tokenizes as يَ|وْ|م = `ja|w|m`, and Hejazi
  monophthongization targets an /aw/ atom, so it does not fire (بَيْت works, ⟨َي⟩ is a single digraph slot).
- Spec `quality` is `research`, not `production`, for the Arabic varieties, and
  their gold has not been validated by a native speaker.

---
[← Rawi-lattice fusion](rawi-fusion.md) · [Home](../README.md) · [Arabizi →](arabizi.md)
