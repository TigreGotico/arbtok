# Rawi–lattice fusion: the diacritizer as a scorer, not a generator

## The problem

arbtok restores tashkeel with a model (rawi, via text2tashkeel) and then
phonemizes the result with orthography2ipa's lattice. The shipped pipeline runs
these in strict sequence: rawi writes **one** vocalized string, the lattice
**checks** it, and a word whose single guess the variety's orthography refuses is
dropped back to its bare skeleton — an underdetermined reading
(`arbtok/diacritize.py`). The model proposes once; when that one proposal is
unlicensed, its whole distribution is discarded with it. The lattice's
constraints never reach *back* to inform the choice — they can only veto it after
the fact.

That is a one-way street, and rawi is trained on MSA. When the target is a
dialect, the diacritizer is guessing vowels for a variety it has never seen,
and the only thing that knows the dialect — the spec's grapheme table and its
allophone rules — is downstream of the decision it would most like to shape.

## The mechanism

rawi is a char-level classifier with an accessible per-character distribution
(`(bare, logits, classes)`). arbtok reads that distribution from the **flagship
ensemble** directly: it bundles a stitched `rawi-v2 + rawi-v3` ONNX that, unlike
the argmax-only flagship text2tashkeel ships, also emits `gated_logits` — the
ensemble's decision *as a distribution* (`arbtok/_ensemble.py`; the artifact is
built by `tools/build_ensemble_logits_onnx.py`). So arbtok can turn the pipeline
around:
instead of taking rawi's argmax and hoping it is licensed, it **enumerates the
licensed diacritizations of a word and lets rawi score them**, choosing the
highest-probability reading the orthography actually admits.

The model runs **once per sentence**. Every hypothesis is scored by indexing the
output tensor it already produced, so the search adds no model calls — only
cheap array lookups and tokenizations (`arbtok/fusion.py`).

### Scoring the ensemble, not a single head

The distribution fusion scores is the flagship ensemble's, exposed as one extra
ONNX output. text2tashkeel's stitched flagship folds its gate into the graph and
returns `gated_cls`, an argmax, only — no distribution to score. arbtok bundles a
re-export of that same graph with a second output, `gated_logits`: the rawi-v3
value-head logits with class 0 lifted just above the row max at every position the
rawi-v2 gate zeroes. So `argmax(gated_logits)` is byte-identical to the ensemble's
own `gated_cls` decision — the correctness gate the artifact is built and tested
against — while every other class keeps the value head's real log-probability, so
the scorer sees which mark the flagship preferred, not just the one it picked.
This is read straight from the bundled ONNX with onnxruntime (`arbtok/_ensemble.py`),
so the scoring path takes no text2tashkeel model dependency.

Per word (only where the writing is silent — a fully-marked word is never
touched, and a word in the stem lexicon is answered from it first):

1. **Enumerate, constrained.** For each letter, take the top-`k` diacritic
   classes from rawi's distribution. The classes rawi exposes are pure combining
   marks — it cannot propose a class that rewrites the consonant — so every
   hypothesis carries the word's skeleton. A beam of width `beam` keeps the
   search bounded.
2. **Score.** A hypothesis's score is the sum of the log-probabilities rawi
   assigns to its per-character classes. This is monotone: swapping any position
   for a higher-logit class raises the score.
3. **License, then rank.** A hypothesis survives only if the variety's grapheme
   table licenses it (it tokenizes with no `UNKNOWN` segment). Among the
   survivors the highest-scoring wins, with a small lattice-cost tie-break
   (`lattice_weight`) so a phonotactically cleaner reading is preferred when two
   are near-equal in the model's eyes.
4. **Pausal / per-lect prior.** With `waqf` on (the TTS register) the chosen
   reading is reduced to its pausal form, dropping the iʿrāb-style final short
   vowels the dialect targets would drop at pause anyway.

### The math

For a word of `n` letters, hypothesis `h = (c₁,…,cₙ)` assigns class `cᵢ` to
letter `i`. rawi's log-softmax at position `i` is
`ℓᵢ(c) = logits[i,c] − logsumexp(logits[i,·])`. The score is

```
S(h) = Σᵢ ℓᵢ(cᵢ)  −  λ · latticeCost(render(h))
```

subject to the hard constraint `licensed(render(h))`. The emitted reading is
`argmax_h S(h)` over the licensed beam. With `λ = 0` this is the maximum-
likelihood licensed reading; the `render` step recomposes the classes to NFC and
applies the pausal transform.

## Why the lattice is a *second scorer*, not just a filter

This is the point of doing it in arbtok. rawi is one voice; the pick is
`argmax` over a set two other, **dialect-aware** voices have shaped:

- **The licensing filter (hard).** The candidate set is whatever the *variety's
  own* grapheme table admits. rawi is MSA-trained and has never seen the dialect;
  the spec has. This is a per-position constraint distinct from text2tashkeel's
  own generic orthographic mask, so fusion and the shipped generator diverge on
  real dialect words even when neither is "wrong" — e.g. Tunisian `العايلة` comes
  out `الْعَائِلَة` (hamza-carrier) under o2i licensing where the generator's
  generic mask leaves `الْعَايِلَة`.
- **The lattice cost (soft).** `latticeCost` is summed from the variety's
  *allophone-rescored* lattice — sun-letter assimilation, waṣl, emphatic backing,
  Najdi affrication, Hejazi monophthongization. A reading that yields a cleaner
  path *in that dialect* can outrank rawi's MSA-favoured argmax.

A free generator hears neither of these until it is too late to change its mind.

## The measured result (empirical gate)

`scripts/benchmark_fusion.py` scores three arms on the bare (`raw`) column of the
Fable-corrected TTS gold (33 lects × 20 sentences), reference = the `ipa` column,
metric = mean per-sentence PER:

- `current` — the shipped stack (rawi-**ensemble** generator);
- `curr-v2` — the same generator pipeline forced to **rawi-v2** (fusion's model),
  isolating the *mechanism* from the ensemble→single-head model swap;
- `fusion` — rawi-v2 **scoring** the licensed readings.

Mean bare-input PER (33 lects × 20 sentences):

| arm | mean PER |
|---|---|
| shipped (rawi-ensemble generator) | 0.217 |
| **fusion (rawi-ensemble scorer)** | **0.214** |

Fusion scoring the ensemble distribution beats the shipped pipeline by −0.003
mean PER, and the win concentrates exactly where the dialect diverges most from
MSA — the signature of the dialect-aware licensing doing the work rather than
noise, and the same signature the single-head prototype showed against its own
base model:

| lect | Δ PER | | lect | Δ PER |
|---|---|---|---|---|
| ar-TN | −0.021 | | ar (leaf) | −0.013 |
| ar-SA-x-sharqiyya | −0.018 | | ar-SA-x-najd | −0.013 |
| ar-SA-x-qassim | −0.017 | | ar-MR | −0.013 |
| ar-LY | −0.013 | | ar-YE | −0.011 |

The MSA-adjacent lects (Levantine, Gulf koinés) move by at most +0.009, so the
mean is a real dialect win, not a wash. The earlier single-head prototype
(rawi-v2 as scorer) only *matched* the shipped rawi-ensemble generator (0.217 vs
0.217), because it had to score a weaker model than the pipeline generated from;
scoring the ensemble's own distribution is what turns the proven mechanism into a
measured win.

## Disposition

Fusion scores the flagship ensemble's distribution under the variety's own
licensing and beats the shipped generator's mean bare-input PER (0.214 vs 0.217),
with the margin on the dialect-divergent lects it was built for. The mechanism the
section below once described as the limiting factor — the flagship exposing only a
decision, not a distribution — is resolved: arbtok bundles the ensemble as a
scorable ONNX. Clearing that gate is what flips fusion **on by default**
(`ArbtokG2PPlugin(fusion=False)` to opt out).

## The resolved limiting factor, and what is left to move

The scorer is only as good as the distribution it scores, and for a while the best
model we had — the rawi-ensemble — handed out decisions, not distributions. That
was the whole gap: fusion had to score a single head weaker than the pipeline's
own generator. It is closed here. arbtok bundles a re-export of the stitched
ensemble graph that additionally emits `gated_logits` (the gate folded into the
value-head logits as a bias on class 0), and reads it directly with onnxruntime
(`arbtok/_ensemble.py`, built by `tools/build_ensemble_logits_onnx.py`). Scoring
that ensemble-grade distribution under dialect licensing is what lands the proven
mechanism on top of the stronger base — the measured 0.214-vs-0.217 win above.

Secondary levers, still open, all inside arbtok: raise `lattice_weight` (currently a mild
tie-break — the soft channel rarely flips a decision today, so it is really a
hook for a stronger dialect prior); and give the spec a declared *licensed-
vocalization* table per grapheme (roadmap §T.2 / D3) so the candidate set is the
dialect's admissible vowels rather than rawi's top-`k` filtered after the fact.
