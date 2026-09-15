# Donor lexicons

## en-GB.tsv — the English donor lexicon

This is the **donor** lexicon, read by `orthography2ipa`'s lexicon overlay when a
code-switched English word is phonemized before `arbtok.translit` adapts it into
the matrix language. See `arbtok/donor_lexicon.py` for why it ships here when
orthography2ipa deliberately bundles none, and how a caller's own registration
takes precedence over it.

**Provenance.** Derived from misaki's `gb_gold.json` (Apache-2.0), a British
English gold lexicon — the same RP convention the `en-GB` spec targets, where
the CMUdict-derived pilot in orthography2ipa is General American. Its
single-letter phoneme shorthands are expanded to IPA at build time and
part-of-speech variants are dropped rather than guessed, since the overlay is a
word-to-IPA map with no part-of-speech channel. Rebuild with
`scripts/build_donor_lexicon.py`.
