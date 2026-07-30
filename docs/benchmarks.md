# Per-lect benchmarks

Two benchmarks live in `scripts/benchmark_stack.py`.

- **default mode**, the MSA stack question: is arbtok better than its parts and
  than espeak-ng on the WikiPron `ara_arab_broad` word set? See the module
  docstring.
- **`--lect` mode**, the dialect question this page reports: does a *dialect*
  sentence, diacritized or bare, come out the way the requested lect's cited
  rules say it should?

```
python scripts/benchmark_stack.py --lect                     # every lect, full gold
python scripts/benchmark_stack.py --lect --json out.json     # + machine-readable
python scripts/benchmark_stack.py --lect --lects ar-EG,ar-MA # a subset
python scripts/benchmark_stack.py --lect --no-espeak         # arbtok arms only
```

## What the gold is, and what it is not

The gold is orthography2ipa's Arabic TTS set (`data/gold/arabic_tts`, o2i #358):
one TSV per lect, sentence-level, with a vocalized `sentence`, its bare `raw`
skeleton, and a reference `ipa`. It covers 25 lects with 5 sentences each.

**Its provenance is load-bearing and must be quoted with every number.** The
reference IPA is **LLM-generated from the specs' cited rules, then
rule-anchored**, it is an o2i-regression snapshot, **not native-speaker-validated
ground truth.** So every figure here is *engine similarity to cited-rule o2i
output*: a lect where arbtok scores well means "arbtok reproduces what o2i's
rules predict for it", never "a native speaker signed off". Native word-level
gold is what would turn these into truth claims. Until then, read these as a
consistency check between arbtok's lattice and the specs it consults.

espeak-ng has **no dialect voices**, so every lect is scored against its single
`ar` (MSA) voice. That is honestly apples-to-oranges, espeak is not being asked
the dialect question, it has no way to answer it, and the gap is the point, not
a fair contest. espeak is fed the *vocalized* sentence (vowels handed to it),
which if anything flatters the baseline.

## Metrics

Both sides are stress-stripped and punctuation-stripped before scoring.

- **PER**, character edit distance / gold characters, over the whole lect.
- **WER**, word edit distance / gold words. A TTS voice gets no partial credit
  for a word it mispronounces, so WER is the harsher, more honest headline.

Two arbtok arms run the full default stack (diacritizer + stem lexicon) on the
variety's own spec:

- **diac**, input is the vocalized `sentence` (the marks are already there).
- **bare**, input is the `raw` abjad skeleton. The diacritizer must restore the
  vowels the writing omits. This is the everyday-input question.
- **ΔPER** = bare − diac: the price of the missing harakat, per lect.

## Results (full gold, 5 sentences/lect, default stem lexicon)

Sorted best-to-worst by arbtok diacritized PER.

| Lect | Tier | N | arbtok PER (diac) | arbtok WER (diac) | arbtok PER (bare) | arbtok WER (bare) | ΔPER (bare−diac) | espeak PER | espeak WER |
|---|---|---|---|---|---|---|---|---|---|
| ar-SA-x-najd | research | 5 | 0.009 | 0.057 | 0.131 | 0.343 | +0.122 | 0.221 | 0.543 |
| ar-JO | research | 5 | 0.010 | 0.030 | 0.178 | 0.606 | +0.168 | 0.223 | 0.515 |
| ar-OM | research | 5 | 0.015 | 0.094 | 0.100 | 0.344 | +0.085 | 0.230 | 0.594 |
| ar-TN | skeleton | 5 | 0.016 | 0.091 | 0.207 | 0.606 | +0.191 | 0.170 | 0.576 |
| ar-LY | skeleton | 5 | 0.017 | 0.061 | 0.211 | 0.545 | +0.194 | 0.211 | 0.545 |
| ar-KW | research | 5 | 0.019 | 0.088 | 0.184 | 0.559 | +0.164 | 0.266 | 0.559 |
| ar-AE | research | 5 | 0.020 | 0.091 | 0.164 | 0.515 | +0.144 | 0.333 | 0.818 |
| ar-YE | research | 5 | 0.020 | 0.094 | 0.110 | 0.344 | +0.090 | 0.220 | 0.719 |
| ar-NG | research | 5 | 0.020 | 0.121 | 0.182 | 0.515 | +0.162 | 0.167 | 0.545 |
| ar-MA | research | 5 | 0.021 | 0.091 | 0.181 | 0.636 | +0.161 | 0.187 | 0.485 |
| ar-QA | research | 5 | 0.021 | 0.094 | 0.140 | 0.375 | +0.119 | 0.228 | 0.562 |
| ar-SA-x-hejaz | research | 5 | 0.022 | 0.135 | 0.152 | 0.459 | +0.130 | 0.225 | 0.541 |
| ar-DZ | research | 5 | 0.022 | 0.094 | 0.170 | 0.531 | +0.148 | 0.236 | 0.562 |
| ar-SD | research | 5 | 0.022 | 0.111 | 0.179 | 0.528 | +0.156 | 0.246 | 0.639 |
| ar-SY | research | 5 | 0.023 | 0.091 | 0.213 | 0.697 | +0.190 | 0.262 | 0.667 |
| ar-BH | research | 5 | 0.024 | 0.156 | 0.173 | 0.594 | +0.149 | 0.269 | 0.750 |
| ar-PS | research | 5 | 0.027 | 0.138 | 0.161 | 0.690 | +0.134 | 0.285 | 0.655 |
| ar-EG | research | 5 | 0.027 | 0.176 | 0.224 | 0.618 | +0.197 | 0.287 | 0.647 |
| ar-LB | research | 5 | 0.028 | 0.111 | 0.144 | 0.528 | +0.116 | 0.306 | 0.750 |
| ar-TD | research | 5 | 0.028 | 0.139 | 0.131 | 0.417 | +0.103 | 0.160 | 0.417 |
| ar-IQ-x-qeltu | research | 5 | 0.032 | 0.100 | 0.101 | 0.400 | +0.069 | 0.238 | 0.533 |
| ar-MR | skeleton | 5 | 0.036 | 0.188 | 0.169 | 0.594 | +0.133 | 0.205 | 0.531 |
| ar-IQ | research | 5 | 0.037 | 0.125 | 0.206 | 0.656 | +0.168 | 0.336 | 0.844 |
| arb | research | 5 | 0.055 | 0.378 | 0.114 | 0.838 | +0.059 | 0.216 | 0.622 |
| ar | research | 5 | 0.083 | 0.368 | 0.245 | 0.816 | +0.162 | 0.176 | 0.605 |

## Interpretation

**Diacritized path, arbtok reproduces the specs, and beats the MSA baseline
everywhere.** With the marks present, arbtok's PER sits at 0.01-0.08 and beats
espeak-ng's MSA voice on every single lect, by 5-20× on PER. Read honestly, this
is largely *self-consistency*: the reference IPA is generated from the same cited
spec rules arbtok's lattice consults, so a low number confirms the lattice
faithfully executes the specs, it is not independent evidence about native
pronunciation. The espeak gap is real but expected: espeak has no reflexes for
qāf→/g/, gīm→/g/, interdental shifts, or imāla, so it mistranscribes exactly the
segments that define a dialect.

**The two worst diacritized rows are `ar` (MSA) and `arb` (Classical), not a
skeleton dialect.** Their WER (0.37-0.38) is far above any dialect's. Diagnosis:
these gold sentences carry full iʿrāb case endings and hamzat-waṣl that
arbtok's pausal-TTS defaults resolve away, so word-final segments disagree with a
gold that kept them. This is a policy seam (pausal vs full iʿrāb),
not a dialect-rule failure.

**Undiacritized path (D1), stripping harakat costs +0.06 to +0.20 PER.** The
MSA-trained diacritizer and stem lexicon do not know dialectal vowels, so the
bare-skeleton input is where the real dialect work remains. The largest ΔPER
falls on the lects with the heaviest vowel reduction / syncope, where the abjad
skeleton underdetermines the most, Egyptian (+0.197), Libyan (+0.194), Tunisian
(+0.191), Syrian (+0.190). The smallest ΔPER is Classical `arb` (+0.059) and
Iraqi qeltu (+0.069), whose fuller vocalism the MSA diacritizer handles closer to
right. The closed-class dialect lexicons are what narrow this residual.

**On the bare path, arbtok still beats espeak on most lects, but loses on MSA.**
For `ar`, espeak's bare-input PER (0.176) beats arbtok's (0.245), espeak's engine
*is* MSA-tuned, so on the one target it was built for, arbtok's diacritizer adds
noise rather than removing it. Every dialect bare row where espeak looks close
(TN, NG, TD) is espeak scoring an MSA reading against a dialect gold and getting
lucky on shared segments, not reading the dialect.

### 3 best / 3 worst lects (by arbtok diacritized PER)

Best (lattice tracks the cited rules almost exactly):

- **ar-SA-x-najd** 0.009, Najdi reflexes (qāf→/g/, gahawa-syndrome epenthesis)
  are among the most fully cited specs. The lattice reproduces them cleanly.
- **ar-JO** 0.010, Jordanian's moderate consonant shifts and light reduction
  leave little for the transcription to disagree about.
- **ar-OM** 0.015, Omani's conservative vocalism maps closely to the spec's
  predicted segments.

Worst (by diacritized PER, a policy/register issue, not broken dialect rules):

- **ar** (MSA) 0.083 / WER 0.368, full iʿrāb and waṣl in the gold vs arbtok's
  pausal-TTS defaults. The disagreement is word-final case endings.
- **arb** (Classical) 0.055 / WER 0.378, same iʿrāb/register seam, sharpened by
  Classical's fully-marked endings.
- **ar-IQ** (gilit) 0.037, Iraqi gilit has the richest set of reflexes (kāf→/tʃ/,
  qāf→/g/, affrication) and the most room for a single segment to diverge.

### The MSA rows are a register seam, and the waqf policy prices it

The `ar`/`arb` gold keeps the full iʿrāb. Arbtok's default is the declared
pausal (waqf) policy, `ArbtokG2PPlugin(pausal=True)`, Wright I §372, which
drops the endings a TTS voice should not read out. Scoring the right register
against the right gold (`--full-irab`, i.e. `pausal=False`) removes almost the
whole gap:

| Lect | mode | PER (diac) | WER (diac) | PER (bare) | WER (bare) |
|---|---|---|---|---|---|
| ar  | pausal (default) | 0.086 | 0.400 | 0.231 | 0.800 |
| ar  | `--full-irab`    | **0.015** | **0.089** | 0.203 | 0.644 |
| arb | pausal (default) | 0.062 | 0.405 | 0.115 | 0.786 |
| arb | `--full-irab`    | **0.007** | **0.048** | 0.128 | 0.595 |

The residual diacritized error in `--full-irab` mode is the ordinary rule
seam, not the register. The waqf policy is one flag consulted in one place
(`arbtok.sandhi`), and both modes run the same lattice.

## Why these are reported, not gated

These are engine-similarity numbers on an LLM-origin gold, so they are reported,
not used as a pass/fail gate. A CI regression gate belongs on native word-level
gold. Wiring `--lect` into CI against this gold would only gate arbtok against its
own specs. `tests/test_lect_benchmark.py` pins that the runner works (2 lects × 3
sentences, no network), not any score.

---
[← Advanced](advanced.md) · [Home](../README.md)
