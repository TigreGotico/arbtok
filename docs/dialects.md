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
the orthography2ipa `quality` tier of its spec, so the list tracks the installed
data set rather than a table in arbtok. Ask the code rather than a page: a spec
shipped upstream joins the roster without arbtok changing, which is what makes a
written-out list here wrong within a release or two.

```python
import arbtok

for lect in arbtok.supported_lects():
    print(lect.code, lect.tier)
```

The roster runs from MSA `ar` and Classical `arb` through the grouping nodes
(`ar-x-gulf`, `ar-x-levantine`, `ar-x-maghrebi`, `ar-x-mashriqi`,
`ar-x-peninsular`) to the national leaves (`ar-EG`, `ar-IQ`, `ar-MA`, …) and the
sub-lects below them (`ar-SA-x-najd`, `ar-IQ-x-qeltu`, `ar-BH-x-baharna`, …),
with the Buckwalter romanization `ar-Latn-buckwalter` among them as a
machine-readable anchor. Most sit at `research` tier and a handful at `stub`,
where the grapheme layer resolves but the allophone rule set has not been taken
as far. The tier is a property of the installed orthography2ipa spec, not of
arbtok's cascade.

## The ISO 639-3 code a tag names

A spec code is a BCP-47 tag, and some things a variety needs are keyed by the ISO
639-3 code of the individual Arabic language instead — the number parser's
cardinals are, because a region is not a lect and mapping one to the other is a
linguistic claim a number parser has no source for. `arbtok.lect_code` makes that
claim and nothing else: it reads the code off the spec's parent chain, so a leaf
takes its group's code and the answer follows orthography2ipa's genealogy rather
than a list of countries.

```python
from arbtok import lect_code

lect_code("ar-SA-x-hejaz")   # 'acw' — Hijazi
lect_code("ar-KW")           # 'afb' — Gulf, from the ar-x-gulf node it descends from
lect_code("ar-SA")           # 'ars' — Najdi, which ar-SA resolves to
lect_code("ar")              # None  — the macrolanguage names no lect
```

Whether anything is said differently under the code is the answer of whoever
holds the data: the parser speaks a lect's cardinals only for the lects it has
read a source for, and `ars` is not among them.

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

| table | keyed at | source |
|---|---|---|
| Najdi | `ar-SA-x-najd` | Alhoody (2019) |
| Egyptian | `ar-EG` | Hafez (1996). Watson (2002) |
| Levantine | `ar-x-levantine` | Al-Saidat (2011). Cowell (1964) |
| Maghrebi | `ar-x-maghrebi` | Kenstowicz & Louriz (2009). Ziadna (2018). Oueslati (2021). Heath (2020) |
| default | `ar` | Watson (2002). Holes (2004) |

Which leaves inherit which table is not listed here, and deliberately. The answer
comes from orthography2ipa's genealogy, so it changes whenever that package ships
a spec — `ar-SA-x-shamali` and three `ar-EG-x-*` lects exist on newer releases than
this repository's floor pin and would already have made a written-out list wrong.
Ask the code:

```python
from arbtok.translit import nativization_table, SEGMENT_MAP
nativization_table("ar-SA-x-qassim") is SEGMENT_MAP   # True — inherits Najdi
```

Two leaves are held out of their group's table by naming the default ahead of
their parent: `ar-LY`, whose donor is Italian rather than French (Benkato 2020),
and `ar-MR`, whose Hassaniya declares /ʁ/ where the Maghrebi table would rewrite
it.

```python
ArbtokG2PPlugin(lang="ar-EG").transcribe_word("manager")         # 'maniɡar'  (Cairene stop ǧīm)
ArbtokG2PPlugin(lang="ar-SA-x-najd").transcribe_word("manager")  # 'manidʒar' (Najdi affricate)
ArbtokG2PPlugin(lang="ar-EG").transcribe_word("think")           # 'tink'     (interdental merger)
```

### The Maghreb borrows from French

The donor is still guessed from the script, so a Latin run defaults to English
everywhere. Name the donor to read a French loan as one:

```python
from arbtok.translit import transliterate
transliterate("garage", "ar-MA", donor="fr-FR")     # 'ɡaraʒ'
transliterate("bureau", "ar-MA", donor="fr-FR")     # 'biro'
transliterate("chauffeur", "ar-MA", donor="fr-FR")  # 'ʃofur'
```

French spelling does not say which final consonants are silent, and the words that
recur in every switched sentence are the ones it gets wrong. A closed-class French
lexicon ships with the package and is registered when `fr-FR` is the donor, so
these are read from a dictionary rather than from their letters:

```python
transliterate("déjà", "ar-MA", donor="fr-FR")    # 'deʒa'   (spelling alone: 'deʒ')
transliterate("voilà", "ar-MA", donor="fr-FR")   # 'vwala'  (spelling alone: 'vwal')
transliterate("dix", "ar-MA", donor="fr-FR")     # 'dis'    (spelling alone: 'di')
```

It covers articles, prepositions, conjunctions, pronouns, determiners, negation,
common adverbs, discourse words, the conversational forms of nine verbs and the
numbers; open-class words are still read by rule. Its source and its limits are in
`arbtok/data/donor_lexicons/README.md`. A lexicon you register for `fr-FR` yourself
takes its place.

The Maghrebi table diverges from the pan-Arabic default on four segments and
carries no rule for two more. French /ʁ/ becomes **[r]**, not the [ɣ] a feature
metric picks — these lects declare /ɣ/ and do not use it for a French rhotic. The
ǧīm **[ʒ] is retained**, where the default maps it to [dʒ] for the stated reason
that MSA and Gulf have no /ʒ/. The front rounded vowels go **/y/ → [i]**, **/ø/ →
[u]**, **/œ/ → [u]**.

**/p/ and /v/ carry no rule**, deliberately. Substitution to [b] and [f] is the
majority outcome in every corpus — 59 of 74 /p/ tokens in Ziadna's Algerian data —
but the conditioning is loan age and the speaker's access to French, and neither is
recoverable from an input string. The specs declare both segments, so
they pass through. This path fires on a *Latin-script* run, which is a code-switch
or a recent loan, the register where retention is reported; the established
stratum is written in Arabic letters and never reaches here.

Two limits. **Nasal vowels are not unpacked**: *camion* comes out `kamjo`,
denasalized, which is one documented outcome but not the dominant one — unpacking
to a vowel plus a nasal is uncontested, the vowel quality is not (Moroccan
/ɛ̃/ → [an], Tunisian → [in]). And **`ar-LY` and `ar-MR` are held out**: Libya
borrows from Italian rather than French (Benkato 2020), and Mauritanian Hassaniya
declares /ʁ/, so the table would rewrite a segment it actually has.

Whatever a table emits must be realizable in the matrix lect's inventory, and a
symbol the lect does not declare never reaches the output. By default it is
**projected** onto the nearest sound the lect does declare, because loanword
adaptation does not drop a word — a speaker says *something*. So Najdi's `[-inɡ]`
reading of *meeting* comes out `miːtink` for MSA, which has no /ɡ/, and the
Egyptian interdental merger is what lets *think* be realized at all in `ar-EG`,
which has no /θ/.

`strict=True` refuses that projection instead, returning `None`, for a linguistic
caller for whom a nearest-sound guess is worse than no answer:

```python
transliterate("meeting", "ar")                # 'miːtink'  — /ɡ/ projected onto /k/
transliterate("meeting", "ar", strict=True)   # None       — MSA declares no /ɡ/
transliterate("meeting", "ar-SA-x-najd")      # 'miːtinɡ'  — Najdi declares it
```

`strict` governs that one decision and nothing else. `None` also comes back,
whatever `strict` says, when the donor produces no reading at all — an empty
string, digits, punctuation.

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
- Spec `quality` is `research`, not `production`, for the Arabic varieties, and
  their gold has not been validated by a native speaker.

---
[← Rawi-lattice fusion](rawi-fusion.md) · [Home](../README.md) · [Arabizi →](arabizi.md)

## Diacritizing without phonemizing, and knowing who decided

`arbtok.vocalize(text, lect)` returns the diacritized text and a record per word:

```python
import arbtok

out = arbtok.vocalize("عندي meeting مهم", "ar-EG")
str(out)                                        # the vocalized string
[(w.surface, w.provenance) for w in out.words]  # who decided each word
```

Each `DiacritizedWord` carries `surface`, `output` and `provenance` — one of
`author`, `closed-class`, `stem-lexicon`, `proclitic`, `model`, `model-repaired`,
`refused`, `not-arabic`.

### Why the provenance is the point

The orthography licenses **letters, not readings**. `_is_licensed` asks whether every
letter and mark in a proposal is declared by the variety's spec, and every Arabic spec
declares every ḥaraka — so a well-formed Modern Standard vocalization passes the check
untouched, whatever variety was asked for. Measured: six MSA vocalizations against
`ar-EG`, `ar-SA-x-najd`, `ar-MA` and `ar-x-gulf`, zero rejections.

So `provenance == "model"` means the model's MSA prior decided that word with nothing
from the lect opposing it. That is not a bug report; it is the shape of the cascade, and
the field is what lets a caller see it. `w.lect_constrained` excludes `model` and
`model-repaired` for exactly this reason.

The veto is not inert, and the distinction matters. Over the 636 model-path words of the
shipped gold, **5 carry a reading at least one lect in the roster would reject** — the
narrower Omani and southern Saudi specs among them. So `model` means the lect *did not*
object, not that it *could not*; the mechanism has teeth.

Five is enough to refute "the veto never fires on a model reading" and **not enough to
say how often it does**: a numerator of 5 over 636, on one gold, is not a rate, and
quoting it as one would give it a precision the sample cannot carry. Not objecting is
weaker evidence than choosing, which is what the exclusion records.

Measured over the shipped code-switched gold, 4,687 words across 46 lects:

| provenance | share |
|---|---|
| `not-arabic` | 32.3% |
| `stem-lexicon` | 30.7% |
| `author` | 20.6% |
| `model` | 13.0% |
| `closed-class` | 2.8% |
| `model-repaired` | 0.6% |
| `refused` | 0.04% |

Two readings worth taking from that. The closed-class lexicon — the only mechanism that
supplies a *dialectal reading* rather than permitting one — decides fewer than three
words in a hundred, and ranges from 22% (`ar-TN`) to none at all in most lects,
the grouping nodes among them. And genuine refusals are two words in 4,687: the
cascade does not fail, it defaults.

### `not-arabic` is not a failure

A token with no Arabic letter — a Latin embed, a number, punctuation — never had a
diacritization to attempt. It is separated from `refused` because the two are
different events and a caller filtering `refused` for failures would otherwise read a
page of English. Both refusals on this gold are an Arabic article written against a
Latin word, `الـcharger` and `الـprinter`, where the skeleton guard cannot put the
written letters back. Use `w.is_failure`, which counts only `refused`.

### Filtering a corpus

A corpus filtered to words the lect actually constrained is a different corpus from one
filtered on the lect label:

```python
kept = [w for w in out.words if w.lect_constrained]
```

## Which generator answers a word nobody has written down

Two exist. `LatticeDiacritizer` tokenizes one constrained-argmax guess from rawi and
refuses it when the variety's grapheme table does not license it. `FusionDiacritizer`
enumerates the licensed readings and lets rawi **score** them, so an unlicensed argmax
loses to the best licensed alternative rather than throwing the whole distribution away.

`ArbtokG2PPlugin` runs fusion (`fusion=False` opts out, see
[rawi-fusion.md](rawi-fusion.md)). The orthography2ipa `normalize` step plugin, which
answers for callers who reached arbtok through plain orthography2ipa, runs the lattice
instead, and **that default is a measurement rather than an inheritance**. Over 881
rows across 44 lects of the code-switched gold, scored per character position against
the editor-authored vocalization:

| generator | rows unscorable | positions | DER |
|---|---|---|---|
| rawi alone | 67 (7.6%) | 21,292 | 0.1757 |
| lattice | 11 (1.2%) | 22,802 | **0.0989** |
| fusion | 11 (1.2%) | 22,809 | 0.1012 |

Fusion is 52 positions in 22,800 behind the simpler path, about one standard error
before within-sentence correlation widens the interval — this gold cannot separate them,
and a tie goes to the cheaper path.

Read the rawi-alone row carefully. An unscorable row is one whose bare skeleton does not
match the reference's, so the two cannot be aligned position by position — and those rows
are *excluded* from that system's DER, which means rawi is scored on the rows it did not
disturb and the gap above understates the guard.

What the disturbance actually is, measured: **66 of the 67 differ only in hamza
carriers**, and they are the model adding a hamza the writing does not have —
وايد → وأيد, التاير → التأير. One row differs for some other reason.

That is not letter mangling and it is not free either. The orthographic mask permits
hamza restoration on purpose (restoring it to a defectively-spelled alif is a documented
part of the task), but on dialectal and loan spellings the permission is usually wrong:
وايد is Gulf *wayed* and التاير is a tyre, and neither takes a hamza. `repair_skeleton`
in the lattice path is what puts the written letter back, which is why 7.6% becomes
1.2%.

So the lattice's advantage over the bare model on this gold is mostly **undoing spurious
hamza restoration**, not correcting ḥarakāt. A mask that knew the variety could refuse
the restoration where the orthography does not use it, and would not need the repair.

```bash
ARBTOK_DIACRITIZER=fusion   # the step plugin's generator; ArbtokG2PPlugin takes fusion=
```

A value that is neither raises rather than falling back: a typo that silently kept the
default reads exactly like the setting working, and a comparison run that way would
compare one path with itself.
