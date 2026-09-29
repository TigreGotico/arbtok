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

**Rhotic.** RP is non-rhotic and the source gold speaks RP, so it gives *car* as
`kˈɑː` and *manager* as `mˈænɪdʒə`. That is a true statement about English and the
wrong input to loanword adaptation into Arabic, which has /r/ and writes these loans
with the rāʾ: كارت, كارد, برنتر, تشارجر, كونسرت. The readings are rhoticised on the
way out — `scripts/build_donor_lexicon.py --rhoticise <tsv>` performs the transform
and reproduces this file byte-for-byte from its unrhoticised predecessor.

Checked against misaki's `us_gold.json`, which is General American and therefore an
independent rhotic reference: of the 66,431 words in both, the rhotic count agrees on
**66,278 (99.77%)**. Of the 153 that differ, most are loans and rarities whose two
varieties genuinely disagree (*atelier*, *dossier*, *chitterlings*). Two classes are
real limits of a spelling-driven rule, and neither can be fixed without aligning
graphemes to phonemes:

* a **silent ⟨r⟩** gets one restored — *forecastle* is `fˈəʊksəl`, and the rule makes
  it `fˈəʊksəɹl`;
* an /r/ with **no ⟨r⟩ to license it** is never restored — *colonel* stays `kˈɜːnəl`
  where rhotic English has `kˈɜːɹnəl`.

**What this file actually is.** Measured against misaki 0.7.4, not remembered: of the
words it shares with `gb_gold`, 55,031 readings match `gb_gold` exactly, 13 match
`us_gold`, and 31 match neither. So the readings are `gb_gold`. But **1,487 of its
74,300 entries appear in no `gb_gold` from misaki 0.6.7 through 0.7.4** — 896 of them
are in `us_gold` (*aluminum*, *analog*, *aging*) and 591 are in neither (the `-ise`
family: *accessorise*, *acclimatise*, *agonise*). Their origin is not established.
Rebuilding from `gb_gold` alone would therefore drop those 1,487 words, which is why
the rhoticisation was applied in place rather than by a rebuild.

## fr-FR.tsv — the French closed-class donor lexicon

Maghrebi Arabic switches into French the way Gulf Arabic switches into English, and
the French words that recur in every such sentence are the grammatical ones: *les*,
*des*, *et*, *est*, *déjà*, *voilà*, *dix*. French spelling leaves their final
consonants silent or sounded word by word, so a rule system reads *les* as `l`,
*déjà* as `deʒ` and *dix* as `di`. This file gives those words their dictionary
reading. It holds the closed classes only — articles, prepositions, conjunctions,
pronouns, determiners, negation, common adverbs, discourse words, the forms of
*être*, *avoir*, *aller*, *faire*, *pouvoir*, *vouloir*, *devoir*, *savoir* and
*falloir* that a conversation uses, and the numbers — because those are a finite list
that can be checked by eye, and an open-class French dictionary is not.

**Provenance.** Every reading is a pronunciation the French MFA dictionary v3.0.0
(McAuliffe and Sonderegger 2024) gives for the word, distributed under CC BY 4.0. It is the
dictionary's highest-probability pronunciation, except for a word with sandhi forms:
variants that differ only by a final consonant, which French sounds or drops by what
follows. *six* is [si] before a consonant, [siz] before a vowel and [sis] before a pause,
and the dictionary ranks [si] first. A lexicon consulted one word at a time reads each word
as if it stood alone, which is before a pause, so among such variants the one written is
the one the dictionary most often puts before a pause: the largest product of the
pronunciation probability and the dictionary's probability that a pause follows the word.
That rule gives *six* `sis` and keeps the first-ranked reading of every other word, including *dix* `dis`, *huit* `ɥit`, *cinq* `sɛ̃k` and *neuf* `nœf`, which the
dictionary already ranks first in their sounded form. A final schwa is not a sandhi
consonant, so *quatre* stays `katʁə`. The rule assumes a word is said alone, which holds for
a numeral (*il en a six*). It does not hold for *tous*, which is `tu` as a determiner (*tous
les jours*, *tous les deux*) and `tus` only as the stressed pronoun (*ils sont tous là*). A
word-to-IPA map cannot tell the two apart, so *tous* is named as an exception in the build
script and keeps `tu`, the determiner reading, because that is the common case.

`fr-FR.sources.tsv` records, for each word, its class, the reading written here, the
dictionary's own phone string, the probability it carries and the probability that a pause
follows it, so every row can be traced to the line it came from. Rebuild both files with
`scripts/build_french_donor_lexicon.py <french_mfa.dict> <out_dir>`; the word list is in
that script, grouped by class.

**Phones.** The dictionary writes the fronted allophones of /k/ and /ɡ/ before front
vowels as `c` and `ɟ`, a palatalised `mʲ`, and `ʎ` for the *li* of *lieu*. These are
written back to `k`, `ɡ`, `m` and `lj`, which is the phonemic inventory the `fr-FR`
spec and the adaptation maps in `arbtok.translit` are stated in. Nothing else is
changed.

**Elided forms.** orthography2ipa looks a word up in the lexicon by its whole written form,
apostrophe included, so the elided forms are entries of their own: *c'est* `sɛ`, *qu'il*
`kil`, *n'est* `nɛ`, *jusqu'à* `ʒyska`, and the bare clitics *l'*, *d'*, *qu'*, *c'* and
the rest. Read by rule, *c'est* is `sɛs` and *qu'il* is `kyil`. The keys are written with
the ASCII apostrophe; a word typed with the typographic apostrophe U+2019 (*c’est*) misses
them and is read by rule. orthography2ipa's sentence path splits a word at the apostrophe
before the lookup, so this applies to single-word readings such as the ones
`arbtok.translit.transliterate` asks for. *là-bas* and *peut-être* are not in the dictionary
and are left out.

**What the file changes.** It holds 217 entries. Read by the `fr-FR` rules alone, 157 of them
already come out as the dictionary gives them. Of the other 60, three are overridden by the spec
(below), so 57 entries change the donor reading, and 56 change what
`transliterate(word, "ar-MA", donor="fr-FR")` returns (*euh* changes from `ø` to `œ`, which
Moroccan Arabic adapts to the same vowel).

The `fr-FR` spec's own inline word readings outrank any lexicon. For these entries the spec's
reading is what is spoken, not the dictionary's: *le*, *me*, *hier*.
