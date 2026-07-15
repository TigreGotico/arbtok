# Code-switched Arabic gold set

`data/gold_code_switched/<lect>.tsv` — 20 realistic Arabic/English code-switched
sentences per lect, pinning arbtok's **loanword-nativisation** pipeline: a
Latin-script word embedded in dialectal Arabic is read as a loan and mapped into
the matrix lect's phonology out of that lect's own cited table
(`arbtok.translit`), never spliced in as raw English.

Every `ar*` spec `arbtok.supported_lects()` resolves is covered (33 lects,
including the Saudi round's `ar-SA-x-qassim`, `ar-SA-x-rijal-alma` and
`ar-SA-x-sharqiyya`), with
one deliberate exclusion: **`ar-Latn-buckwalter`**. That code is a Latin
romanisation *of* Arabic, so a mixed Arabic/Latin sentence has no stable Arabic
run to phonemise — the whole line would read as Latin. It is a machine-readable
regression anchor, not a spoken lect, and code-switching into it is undefined.

## Schema

TSV, tab-separated, UTF-8, header row:

| column | content |
|---|---|
| `id` | `<lect>-cs-NNN` |
| `sentence` | vocalised dialectal Arabic with inline Latin word(s) |
| `raw` | `sentence` stripped of ḥarakāt (what a keyboard normally produces) |
| `ipa` | `ArbtokG2PPlugin(lang, diacritize=True, nativize=True, pausal=True).transcribe(sentence)` — **pipeline output, never hand-edited** for `pinned` rows; see `pipeline_status` for the `known-wrong` / `unsupported` exceptions |
| `gloss_en` | English translation |
| `cs_words` | semicolon list of the embedded switched words |
| `notes` | domain tag + which nativisation reflex each switched word takes (refusals marked), and the cited table that fired |
| `pipeline_status` | *(optional)* `pinned` (default when absent) / `known-wrong` / `unsupported` — governs whether `validate` re-runs the pipeline on the row (see below) |

### `pipeline_status` — pinned vs. authentic-but-unpinned rows

The template files (frame-built, one reused frame set per zone) omit the column
entirely and every row is implicitly `pinned`: `validate` re-runs
`transcribe(sentence)` and asserts equality, so the file is a pure regression
gate. Hand-authored *authentic* files (e.g. `ar-EG`, written in the lect's real
code-switching register rather than the shared frames) add the column so a row
can carry IPA the pipeline does **not** produce, without hiding that fact:

- `pinned` — `ipa` **is** the pipeline output; re-run and asserted equal (the
  regression pin, and the no-Latin-leakage check). This is the only status the
  old files use, so their behaviour is unchanged.
- `known-wrong` — an Arabic-script loanword the pipeline mis-reads (e.g. Cairene
  موبايل: pipeline emits `lmuˈːbaːjil`, reading و as [uː] not the loan mid vowel
  [o]). `ipa` holds the **correct** attested loan pronunciation; the pipeline's
  wrong output and the divergence are spelled out in `notes`. Never ship wrong
  IPA as gold — the correct value is pinned and the bug is documented for a later
  `arbtok.translit` fix.
- `unsupported` — an Arabizi row (Latin-written Arabic, *3arabi/7abibi* style).
  The pipeline never sniffs a Latin run as Arabic, so it has no path for these;
  `ipa` is the derived Cairene reading of the Arabic the row spells.

`validate` (and the pytest gate) only pin `pipeline_status == "pinned"` rows;
`known-wrong` / `unsupported` rows are still schema-, `raw`- and dedup-checked
but are not re-run against `transcribe`.

## Provenance & honesty

- **Editor-authored, pipeline-verified, not native-validated.** The Arabic
  frames and the per-zone dialectal function words (`مِش`/`مُو`/`ماشِي`,
  `عَايِز`/`بِدِّي`/`أَبِي`/`بْغِيت`, `دَه`/`هَادَا`/`هَاد`, …) are written by the
  editor to be natural and are grounded in the dialectology each lect's spec
  cites, but they have **not** been checked by a native speaker. The Arabic
  spec `quality` is `research`, not `production`.
- **The `ipa` column is machine output** for `pinned` rows. `validate` (and
  `tests/test_gold_code_switched.py`) re-run the pipeline and assert equality. If
  the pipeline is wrong for a *Latin-embed* row, fix `arbtok.translit` (cited) and
  rebuild — that IPA is never hand-corrected (ground rule #3: no benchmark
  hacking). The `known-wrong` and `unsupported` rows (see `pipeline_status`) carry
  hand-authored, source-cited IPA precisely because the pipeline cannot produce
  the right value yet; they are documented, not hidden, and are not pinned.
- **Frames are reused across lects** with per-zone dialectal adaptation of the
  surrounding function words. The embedded English words and their nativised
  reflexes — the point of the set — are identical inputs across lects, so the
  files are directly comparable and every cross-lect delta is a real phonology
  difference (e.g. *manager* → Cairene `manaɡar` vs `manadʒar` elsewhere;
  *think* → Cairene `tink` by the interdental merger).

## Nativisation tables (the cited maps that fire)

Selection walks the orthography2ipa parent chain, so a leaf inherits its group's
table (`arbtok.translit.nativization_table`):

| table | keyed at | inherited by | source |
|---|---|---|---|
| Najdi | `ar-SA-x-najd` | `ar-SA-x-qassim` (its parent — Alhoody's variety *is* Qassimi) | Alhoody (2019), *Phonological Adaptation of English Loanwords into Qassimi Arabic*, PhD, Newcastle |
| Egyptian | `ar-EG` | — | Hafez (1996), *Phonological and Morphological Integration of Loanwords into Egyptian Arabic*; Watson (2002), *The Phonology and Morphology of Arabic* |
| Levantine | `ar-x-levantine` | `ar-LB`, `ar-SY`, `ar-PS`, `ar-JO` | Al-Saidat (2011), *English Loanwords in Jordanian Arabic*; Cowell (1964), *A Reference Grammar of Syrian Arabic* |
| default | `ar` | every un-tabled lect (Gulf, Iraqi, Maghrebi, Sudanic, MSA, Classical) | Watson (2002); Holes (2004), *Modern Arabic: Structures, Functions and Varieties* |

## Refusals are inventory-driven, not designed-in

`transliterate` returns `None` when the nativised form would need a phoneme the
matrix lect does **not** declare; `transcribe` then drops the word rather than
leaking an unpronounceable token. Whether a given loan refuses is therefore a
**map of the lect's inventory**, and the set reports it honestly rather than
engineering a target count:

- **Rich-inventory lects realise the whole common loan set — zero refusals.**
  The Gulf group (`ar-KW`, `ar-AE`, `ar-BH`, `ar-QA`, `ar-OM`, `ar-x-gulf`,
  `ar-SA-x-hejaz`, `ar-SA-x-qassim`, `ar-SA-x-sharqiyya`, `ar-YE`),
  Egyptian (`ar-EG`), the Iraqi *gilit* lects
  (`ar-IQ`, `ar-IQ-x-qeltu`) and the Levantine grouping node all declare /ɡ/,
  the mid long vowels /eː oː/, and /ʒ/ or /dʒ/, so *meeting* `miːtinɡ`,
  *email* `imeːl`/`imil` and *garage* `ɡaːradʒ`/`ɡaːraɡ` all pass.
- **Three-vowel / no-/ɡ/ lects refuse the /ɡ/-final and /eː/-bearing loans.**
  MSA (`ar`) and Classical (`arb`) have neither /ɡ/ nor /eː/, so *meeting*
  (needs final [ɡ]), *email* (needs [eː]) and *garage* (needs [ɡ]) are all
  refused and dropped, while *manager* still surfaces as `manadʒar`. The Najdi
  (`ar-SA-x-najd`), Maghrebi (`ar-MA`, `ar-TN`, `ar-DZ`, `ar-LY`, `ar-MR`,
  `ar-x-maghrebi`), Sudanic (`ar-SD`, `ar-TD`, `ar-NG`) and Rijāl Almaʿ
  (`ar-SA-x-rijal-alma`, the conservative /q/-retaining ʿAsīr variety) lects
  refuse *email* (no [eː]); the Levantine *leaves* `ar-LB`/`ar-SY` refuse *meeting*
  and *garage* where the grouping node does not, a genuine leaf-vs-group
  inventory difference.

Every refused word is spelled out in the row's `notes` with the exact missing
segment, e.g. `meeting REFUSED—needs [ɡ] (not in inventory), dropped`.

## Tooling

```
python scripts/gold_code_switched.py build [lect ...]     # (re)generate the TSVs
python scripts/gold_code_switched.py validate [lect ...]  # CI gate (also in pytest)
```

`tests/test_gold_code_switched.py` runs the gate in CI, parametrised per lect.
