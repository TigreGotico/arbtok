# Arabizi input

*Arabizi*, also **3arabi**, **Franco-Arabic**, **chat Arabic**, is Arabic written
in the Latin letters and digits a keyboard offers, with numerals standing in for the
consonants Latin has no glyph for: `7abibi` is حبيبي, `3ala` is على, `5alid` is خالد.
It is Arabic, not English, and it is everywhere in real code-switched text.

arbtok reads it. A Latin run detected as Arabizi is **reverse-transliterated to an
unpointed Arabic skeleton** and fed through the normal pipeline, the same diacritize
+ lect-phonology stack that runs on native Arabic script. The Arabizi supplies the
skeleton. [fusion](rawi-fusion.md) restores the vocalism, dialect-aware.

## Why it is a separate path from loanword nativization

A Latin run in Arabic text has two very different sources, and they need opposite
treatment:

* a **foreign loanword**, `meeting`, `manager`, `email`, is *nativized*: read
  through an English G2P and mapped into the matrix lect's phonology out of that
  lect's cited loanword table (see [`arbtok/translit.py`](../arbtok/translit.py)).
  `meeting` → `miːtinɡ`.
* **Arabizi**, `7abibi`, `3ala`, is *Arabic*, and must be read as Arabic. Sent to
  the loanword path it would be run through an English G2P (`3ala` → `ala`), which is
  exactly the failure `translit.py` warns about: "this is how ⟨Arabizi⟩ gets read as
  English."

Telling the two apart is the job of the detection gate.

## The digit map

The digit conventions are the stable, well-documented core of Arabizi. The shapes of
the digits echo the mirrored Arabic letters.

| token | Arabic | letter |
|-------|--------|--------|
| `2`   | ء      | hamza / glottal stop |
| `3`   | ع      | ʿayn |
| `5`   | خ      | ḫāʾ (also `kh`) |
| `6`   | ط      | emphatic ṭāʾ |
| `7`   | ح      | ḥāʾ |
| `8`   | غ      | ġayn (also `gh`). Regionally ≈ ق |
| `9`   | ق      | qāf (also `q`) |
| `3'`  | غ      | ʿayn + prime = ġayn |
| `7'`  | خ      | ḥāʾ + prime = ḫāʾ |
| `6'`  | ظ      | ṭāʾ + prime = ẓāʾ |

Consonant digraphs (`kh gh sh ch th dh`) and emphatic capitals (`S D T Z` → ص ض ط ظ)
round out the consonants. Long vowels, doubled `aa ee oo` and the diphthong digraphs
`ai ay ei aw ou`, become matres lectionis. Single vowels are written as their most
likely mater too, because Arabizi (unlike Arabic script) *spells its vowels*, `habibi` is written, not `hbb`, so keeping the mater preserves the word shape for the
diacritizer instead of collapsing it to an unreadable consonant cluster.

Sources: Yaghan, M. A. (2008), "Arabizi: A Contemporary Style of Arabic Slang",
*Design Issues* 24(2), 39-52 (digit-guttural inventory, table p. 44). Bies, A. et al.
(2014), "Transliteration of Arabizi into Arabic Orthography", *EMNLP 2014 Workshop on
Arabic NLP*, 11-20 (the many-to-many, context-dependent nature of the mapping, one
Arabizi form spells several skeletons, and the vowels are the ambiguous part).

## The detection gate is conservative, and honestly so

`is_arabizi()` fires on exactly two signals:

1. an **explicit hint**, a caller that has language-tagged its input passes
   `arabizi=True`/`False`, and that always wins.
2. a **digit-guttural** (`2 3 5 6 7 9` and the primed forms). No English word
   contains one, so their presence is strong, low-false-positive evidence of
   Arabic-in-Latin.

The gate deliberately does **not** sniff all-alphabetic Arabizi (`habibi`, `inta`)
apart from English by morphology or lexicon. That call is real but error-prone, and a
wrong "yes" silently corrupts a genuine English embed, so the gate refuses it unless
the caller hints. This is the honest ambiguity: `habibi` with no hint stays on the
loanword path. Two conventions are also genuinely ambiguous and take a documented
default: `g` → ق (the Gulf/Bedouin qāf reflex, not the Egyptian ǧīm) and `ch` → ش
(Levantine/Maghrebi, not the Gulf چ).

## Usage

```python
from arbtok.plugin import ArbtokG2PPlugin

p = ArbtokG2PPlugin(lang="ar-EG")           # arabizi=True by default
p.transcribe("3andi maw3ed el sa3a sab3a")  # digit-guttural → read as Arabic
p.transcribe("عِنْدِي meeting مَعَ manager") # digit-free English → nativized loans
p.transcribe("habibi", arabizi=True)         # force the Arabizi reading of a run
p.transcribe("3ala", arabizi=False)          # force the loanword reading
ArbtokG2PPlugin(lang="ar-EG", arabizi=False) # disable the path entirely
```

## What the path does and does not achieve

The input path is **sound and complete**: detection routes Arabizi to Arabic and
leaves English embeds nativized, reverse-transliteration produces a plausible Arabic
skeleton, and it flows through the real diacritize + phonology stack for every lect.

It does **not** reproduce the hand-derived dialectal gold in
`data/gold_code_switched/*.tsv` (the 99 Arabizi rows carried there as
`unsupported`). Two independent limits, measured honestly:

* **The skeleton is under-determined.** Arabizi does not encode vowel *length* or,
  reliably, hamza/tāʾ-marbūṭa, so a mechanical skeleton diverges from the exact
  dialectal spelling a human writes (≈29 % token-level agreement with the
  hand-spelt Arabic in the row notes).
* **The diacritizer is the real ceiling.** Fed the *perfect* hand-spelt Arabic for
  each row, the fusion diacritizer + lect phonology reproduces the hand-derived IPA
  at only **1.2 % exact / 47 % token**, because that gold was authored precisely
  *because* the pipeline does not produce it (dialectal monophthongization,
  kashkasha, emphatic spread the diacritizer does not model).

End-to-end the Arabizi path reaches **0 % exact / 12.6 % token** on those 99 rows.
The rows are therefore held as `unsupported`: overwriting citation-backed hand gold
with demonstrably-inferior pipeline output would launder a regression, not fix one.
The ceiling is the diacritizer and the dialect phonologies, not the input path. The
rows stand as the acceptance test the pipeline has to earn.

---
[← Varieties](dialects.md) · [Home](../README.md) · [Code-switched gold →](gold-code-switched.md)
