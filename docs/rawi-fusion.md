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
(`text2tashkeel.Diacritizer.logits` → `(bare, logits, classes)`; the single-head
`rawi` / `rawi-v2` models expose it). So arbtok can turn the pipeline around:
instead of taking rawi's argmax and hoping it is licensed, it **enumerates the
licensed diacritizations of a word and lets rawi score them**, choosing the
highest-probability reading the orthography actually admits.

The model runs **once per sentence**. Every hypothesis is scored by indexing the
output tensor it already produced, so the search adds no model calls — only
cheap array lookups and tokenizations (`arbtok/fusion.py`).

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

Mean bare-input PER:

| arm | mean PER |
|---|---|
| current (shipped, rawi-ensemble generator) | 0.217 |
| curr-v2 (rawi-v2 generator) | 0.221 |
| **fusion (rawi-v2 scorer)** | **0.217** |

Two honest readings, both true:

- **The mechanism works.** Against its *own base model* (rawi-v2), fusion wins by
  −0.004 mean PER and is ahead on roughly two-thirds of the lects. The margin
  concentrates exactly where the dialect diverges most from MSA —
  `ar-SA-x-sharqiyya −0.026`, `ar −0.019`, `arb −0.018`, `ar-TN −0.015` — and is
  near zero on the MSA-adjacent Levantine lects, which is the signature of the
  dialect-aware licensing doing the work rather than noise.
- **Against the shipped baseline it is a wash.** current uses the stronger
  rawi-**ensemble**, and the ensemble ships as a *stitched* ONNX that folds its
  gate into the graph and exposes **no distribution to score**
  (`text2tashkeel/_models.py`, `_StitchedEnsembleBackend`). Fusion therefore has
  to run on a single head, and rawi-v2-as-scorer only *matches* rawi-ensemble-as-
  generator (0.2170 vs 0.2170).

## Disposition

Fusion ships **off by default** (`ArbtokG2PPlugin(fusion=True)`). The gate — beat
the shipped pipeline's mean bare-input PER — comes out a tie, not a decisive win,
so it does not displace the default. It is landed as a validated research
prototype: the mechanism is proven against a like-for-like model, and the one
thing standing between "proven mechanism" and "shipping win" is named below.

## The limiting factor, and what would move it

The scorer is only as good as the distribution it scores, and the best model we
have — the rawi-ensemble — hands out decisions, not distributions. Closing the
gap is a text2tashkeel task, not an arbtok one: expose per-class logits from the
stitched ensemble graph (or a two-head model's value head) so fusion can score
the flagship instead of a single head. The moment fusion scores an ensemble-grade
distribution under dialect licensing, the mechanism's proven −0.004-vs-same-model
margin lands on top of the stronger base, and the gate is a win rather than a tie.

Secondary levers, all inside arbtok: raise `lattice_weight` (currently a mild
tie-break — the soft channel rarely flips a decision today, so it is really a
hook for a stronger dialect prior); and give the spec a declared *licensed-
vocalization* table per grapheme (roadmap §T.2 / D3) so the candidate set is the
dialect's admissible vowels rather than rawi's top-`k` filtered after the fact.
