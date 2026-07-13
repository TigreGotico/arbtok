# Varieties

A variety is an **orthography2ipa spec**, named by its code:

```python
from arbtok.plugin import ArbtokG2PPlugin

ArbtokG2PPlugin(lang="ar-SA-x-najd").transcribe_word("قَهْوَة")   # 'ɡahawa'
ArbtokG2PPlugin(lang="ar-SA-x-hejaz").transcribe_word("بَيْت")    # 'beːt'
ArbtokG2PPlugin().transcribe_word("قَهْوَة")                      # 'qahwa'  (MSA)
```

The variety may also ride on `WordContext.lang` per call, which overrides the
instance default. A tag that names no Arabic spec narrows a subtag at a time
(`ar-SA-x-najd` → `ar-SA` → `ar`) and ultimately falls back to the `ar` leaf, so
an unknown region is MSA rather than an error.

Any Arabic spec orthography2ipa carries can be named — `ar`, `arb` (Classical),
the proto nodes (`ar-x-peninsular`, `ar-x-gulf`, `ar-x-levantine`,
`ar-x-maghrebi`, `ar-x-mashriqi`), and the leaves (`ar-SA-x-najd`,
`ar-SA-x-hejaz`, `ar-EG`, `ar-IQ`, `ar-MA`, …).

## Where a variety's phonology comes from

Two layers, both read from the spec:

**The grapheme table** gives each letter its realization — the qāf reflex
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
| Hejazi | monophthongization /aj/ → [eː] (Omar 1975; Abdoh 2010) | بَيْت → `beːt` |
| Gulf | kashkasha /k/ → [tʃ] by a high front vowel | كِتَاب → `tʃitaːb` |
| all Peninsular | emphatic spreading (Watson 2002) | صَبْر → `sˤɑbr` |

Saudi is not one variety, and it is not Gulf: Najdi affricates /k/ to **[ts]**,
Gulf to **[tʃ]**, and Hejazi keeps **/k/**.

## Known limits

- The **sentence cascade has no allophone pass** — it reads the grapheme layer
  only. Word-level transcription (`transcribe_word`, `arbtok.lattice.word_ipa`)
  is where a variety's rules fire.
- A diphthong **split across slots** is not one segment, so a rule targeting it
  cannot see it: يَوْم tokenizes as يَ|وْ|م = `ja|w|m`, and Hejazi
  monophthongization targets an /aw/ atom, so it does not fire (بَيْت works —
  ⟨َي⟩ is a single digraph slot).
- Spec `quality` is `research`, not `production`, for the Arabic varieties, and
  their gold has not been validated by a native speaker.
