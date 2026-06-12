# Dialect zones

`arbtok` reads **diacritized MSA orthography** and can realize it with the
reflexes of a broad regional zone instead of the standard register. This is
*zone realization*, not micro-dialect modelling: the cascade swaps the sounds a
grapheme maps to (and applies a few context-conditioned rules), but it does not
model the lexical, morphological, or syntactic differences that spoken
varieties actually carry.

> The reflex data here is **model-generated from documented reflexes and is
> pending native-speaker validation**, in the same spirit as the rest of the
> repo's gold data. Passing tests is not a guarantee of linguistic accuracy.

## Zones

| Zone | Enum | Region tags |
| --- | --- | --- |
| Modern Standard Arabic | `MSA` (default) | `ar`, `arb` |
| Classical Arabic | `CLA` | — |
| Egyptian | `EGYPTIAN` | `ar-EG` |
| Levantine | `LEVANTINE` | `ar-SY`, `ar-LB`, `ar-JO`, `ar-PS` |
| Gulf | `GULF` | `ar-AE`, `ar-BH`, `ar-KW`, `ar-OM`, `ar-QA`, `ar-SA` |
| Maghrebi | `MAGHREBI` | `ar-MA`, `ar-DZ`, `ar-TN`, `ar-LY` |

`MSA` and `CLA` are the reference registers: they apply **no** reflex
overrides, so their output is byte-identical to the standard rule cascade.

## Reflex table

Cells show the IPA each grapheme is realized as; a dash means the MSA
realization is kept unchanged.

| Grapheme | MSA | Egyptian | Levantine | Gulf | Maghrebi |
| --- | --- | --- | --- | --- | --- |
| ق (qāf) | q | ʔ | ʔ | g | q (kept) |
| ج (jīm) | dʒ | g | ʒ | j | ʒ |
| ث (thāʾ) | θ | t | t | — (θ) | t |
| ذ (dhāl) | ð | d | d | — (ð) | d |
| ظ (ẓāʾ) | ðˤ | dˤ | dˤ | — (ðˤ) | dˤ |

Worked examples:

| Word | MSA | Egyptian | Levantine | Gulf | Maghrebi |
| --- | --- | --- | --- | --- | --- |
| قَلْب (heart) | qalb | ʔalb | ʔalb | galb | qalb |
| جَمِيل (beautiful) | dʒamiːl | gamiːl | ʒamiːl | jamiːl | ʒamiːl |
| ثَلَاثَة (three) | θalaːθa | talaːta | talaːta | θalaːθa | talaːta |
| ظُهْر (noon) | ðˤuhr | dˤuhr | dˤuhr | ðˤuhr | dˤuhr |

## Usage

```python
from arbtok.tokenizer import Sentence
from arbtok.dialects import ArabicDialect

Sentence("قَلْب جَمِيل", dialect=ArabicDialect.GULF).ipa      # 'galb jamiːl'
Sentence("قَلْب جَمِيل", dialect=ArabicDialect.EGYPTIAN).ipa  # 'ʔalb gamiːl'
Sentence("قَلْب جَمِيل").ipa                                  # 'qalb dʒamiːl' (MSA)
```

Through the G2P plugin, a BCP-47 tag picks the zone (per call or as a default):

```python
from arbtok.plugin import ArbtokG2PPlugin
from orthography2ipa.g2p_plugin import WordContext

ArbtokG2PPlugin(dialect=ArabicDialect.LEVANTINE).transcribe("قلب")  # 'ʔalb'
ArbtokG2PPlugin().transcribe_word("قلب", WordContext(lang="ar-SA")) # 'galb'
```

A per-call `context.lang` region subtag takes precedence over the construction
default; bare `ar` or an unmapped region resolves to MSA.

## What is approximated

- **Maghrebi short-vowel reduction.** Maghrebi's signature reduction and
  elision of short vowels operates below the orthography the cascade reads —
  CVCVC spellings carry no stress or syllable cues. `arbtok` applies a
  conservative stand-in: a short `a`/`i`/`u` in a *non-initial, non-final, open*
  syllable is centralized to schwa (e.g. بَقَرَة `baqara` → `baqəra`). Long
  vowels and vowels in closed or word-edge syllables are left untouched. This is
  an approximation of the pattern, not a syllabifier or stress model.

- **Competing reflexes.** Where a grapheme has more than one common
  realization, the override commits to the most widely cited urban default and
  records the variability:
  - Egyptian ث/ذ/ظ → inherited stops `t`/`d`/`dˤ` (ظ merges with ض). The
    sibilant reflexes (ث→`s`, ذ→`z`, ظ→`zˤ`) are the borrowed/literary forms and
    are lexically conditioned, so they are not modelled from orthography.
  - Levantine ث/ذ → stops `t`/`d` (the sibilant reflexes `s`/`z` surface in
    learned vocabulary); ظ → `dˤ` is inferred to match that merger.
  - Gulf ج → `j` for the zone label (yodization); the affricate `dʒ` is the
    broader pan-Gulf default and remains common.
  - Maghrebi ق → `q` kept (the `g` reflex also occurs).

## Out of scope

- **Sub-zone variation.** Each zone is one broad default; it does not branch
  into city/rural/Bedouin sub-dialects (e.g. Druze qāf retention, Cairene vs.
  Saʿidi Egyptian, Najdi vs. coastal Gulf).
- **Lexically conditioned reflexes.** Learned/loaned words that take a different
  reflex from the zone default (Egyptian ث→s, ذ→z) are not modelled — they are
  unknowable from orthography alone.
- **Phonological processes beyond consonant reflexes and the Maghrebi schwa
  approximation:** Gulf kashkasha/affrication, gahawa epenthesis, imāla, full
  vowel-quality shifts, and code-switching.
- **Lexical and morphological dialect content.** The input is and remains MSA
  orthography; only its *realization* changes.
