# Code-switched Arabic gold set

`data/gold_code_switched/<lect>.tsv`, twenty or so realistic Arabic/English
code-switched sentences per lect, pinning arbtok's **loanword-nativization**
pipeline: a Latin-script word embedded in dialectal Arabic is read as a loan and
mapped into the matrix lect's phonology out of that lect's own cited table
(`arbtok.translit`), never spliced in as raw English.

Every `ar*` spec `arbtok.supported_lects()` resolves is covered, the Saudi,
Bahraini and Yemeni sub-lects among them. The roster is not a number kept here:
it is whatever the installed orthography2ipa resolves, so a spec added upstream
is a missing gold file until `scripts/gold_code_switched.py build <lect>` is run,
and `tests/test_gold_code_switched.py` is what says so. One deliberate exclusion:
**`ar-Latn-buckwalter`**. That code is a Latin
romanization *of* Arabic, so a mixed Arabic/Latin sentence has no stable Arabic
run to phonemise, the whole line would read as Latin. It is a machine-readable
regression anchor, not a spoken lect, and code-switching into it is undefined.

## Schema

TSV, tab-separated, UTF-8, header row:

| column | content |
|---|---|
| `id` | `<lect>-cs-NNN` |
| `sentence` | vocalized dialectal Arabic with inline Latin word(s) |
| `raw` | `sentence` stripped of ḥarakāt (what a keyboard normally produces) |
| `ipa` | `ArbtokG2PPlugin(lang, diacritize=True, nativize=True, pausal=True).transcribe(sentence)`, **pipeline output, never hand-edited** for `pinned` rows. See `pipeline_status` for the `known-wrong` / `unsupported` exceptions |
| `gloss_en` | English translation |
| `cs_words` | semicolon list of the embedded switched words |
| `notes` | domain tag + which nativization reflex each switched word takes (refusals marked), and the cited table that fired |
| `pipeline_status` | *(optional)* `pinned` (default when absent) / `known-wrong` / `unsupported`, governs whether `validate` re-runs the pipeline on the row (see below) |

### `pipeline_status`, pinned vs. authentic-but-unpinned rows

A file that omits the column entirely is implicitly `pinned` throughout:
`validate` re-runs `transcribe(sentence)` and asserts equality, so the file is a
pure regression gate. A file carrying rows the pipeline does **not** produce adds
the column, so that fact is on the row rather than hidden:

- `pinned`, `ipa` **is** the pipeline output. Re-run and asserted equal (the
  regression pin, and the no-Latin-leakage check). This is the status the
  frame-built template files carry throughout.
- `known-wrong`, an Arabic-script loanword the pipeline mis-reads (e.g. Cairene
  موبايل: pipeline emits `lmuˈːbaːjil`, reading و as [uː] not the loan mid vowel
  [o]). `ipa` holds the **correct** attested loan pronunciation. The pipeline's
  wrong output and the divergence are spelled out in `notes`. Never ship wrong
  IPA as gold, the correct value is pinned and the bug is documented for a later
  `arbtok.translit` fix.
- `unsupported`, an Arabizi row (Latin-written Arabic, *3arabi/7abibi* style),
  three to a file. The pipeline sniffs a Latin run as Arabic only on a
  digit-guttural or an explicit hint, so it has no path for most of these. `ipa`
  is the derived reading, in the file's own lect, of the Arabic the row spells.

`validate` (and the pytest gate) only pin `pipeline_status == "pinned"` rows.
`known-wrong` / `unsupported` rows are still schema-, `raw`- and dedup-checked
but are not re-run against `transcribe`.

## A file has to distinguish its lect to be worth running

A gold file for a sub-lect that reproduces its parent's output on every row keeps the
roster complete and the pipeline exercised, but it would not catch a regression that
reverted the sub-lect's spec. What makes it worth running is a frame that puts the
sub-lect's own reflex in the environment that fires it.

`ar-SA-x-shamali` is the case that shows what that takes. Northern Najdi's only delta
from its parent is /k/ affrication before a central vowel, so a frame has to carry a
word in that environment: كَلْب → ˈtsalb against Najdi's ˈkalb, مَكَان → maˈtsaːn
against maˈkaːn, كَاتِب → ˈtsaːtib against ˈkaːtib. كِتَاب and دِيك discriminate
nothing, because the front-vowel rule both varieties share already fires there. And
سَكَن is a trap: it reads ˈsakan under both specs, since orthography2ipa withdraws the
word-medial cell the source does not attest, so a row built on it would say nothing.

`ar-BH-x-baharna` distinguishes itself the same way against `ar-BH`: ˈhaðaː → ˈhadaː
on the dhāl and ˈnʃuːfak → naˈʃuːfatʃ on the kāf.

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
  rebuild, that IPA is never hand-corrected (ground rule #3: no benchmark
  hacking). The `known-wrong` and `unsupported` rows (see `pipeline_status`) carry
  hand-authored, source-cited IPA precisely because the pipeline cannot produce
  the right value yet. They are documented, not hidden, and are not pinned.
- **A core of loans recurs in almost every file**, *meeting*, *laptop*, *email*,
  *manager*, *password* and a dozen more, each embedded in the lect's own
  dialectal frame rather than a shared one. Those recurring words are the
  comparable inputs: a cross-lect delta on one of them is a real phonology
  difference (e.g. *manager* → Cairene `maniɡar` vs `manidʒar` elsewhere.
  *think* → Cairene `tink` by the interdental merger).

## Nativization tables (the cited maps that fire)

Selection walks the orthography2ipa parent chain, so a leaf inherits its group's
table (`arbtok.translit.nativization_table`):

| table | keyed at | inherited by | source |
|---|---|---|---|
| Najdi | `ar-SA-x-najd` | `ar-SA-x-qassim` and the other Najdi leaves (Alhoody's variety *is* Qassimi) | Alhoody (2019), *Phonological Adaptation of English Loanwords into Qassimi Arabic*, PhD, Newcastle |
| Egyptian | `ar-EG` | the Egyptian leaves | Hafez (1996), *Phonological and Morphological Integration of Loanwords into Egyptian Arabic*. Watson (2002), *The Phonology and Morphology of Arabic* |
| Levantine | `ar-x-levantine` | `ar-LB`, `ar-SY`, `ar-PS`, `ar-JO` | Al-Saidat (2011), *English Loanwords in Jordanian Arabic*. Cowell (1964), *A Reference Grammar of Syrian Arabic* |
| Maghrebi | `ar-x-maghrebi` | `ar-MA`, `ar-TN`, `ar-DZ` | Kenstowicz & Louriz (2009). Ziadna (2018). Oueslati (2021). Heath (2020) |
| default | `ar` | every un-tabled lect (Gulf, Iraqi, Sudanic, MSA, Classical), and `ar-LY` and `ar-MR`, which name it ahead of their Maghrebi parent | Watson (2002). Holes (2004), *Modern Arabic: Structures, Functions and Varieties* |

## What a loan comes out as is a map of the lect's inventory

A nativized form that would need a phoneme the matrix lect does **not** declare is
projected onto the nearest sound it does, because loanword adaptation does not drop a
word — a speaker says *something*. So the reading a lect gives a common loan is a map
of its inventory, and the set reports what each one does rather than engineering a
target count:

- **Rich-inventory lects realise the whole common loan set unaltered.** The Gulf
  group (`ar-KW`, `ar-AE`, `ar-BH`, `ar-QA`, `ar-OM`, `ar-x-gulf`,
  `ar-SA-x-hejaz`, `ar-SA-x-qassim`, `ar-SA-x-sharqiyya`, `ar-YE`), Egyptian
  (`ar-EG`), the Iraqi lects (`ar-IQ`, `ar-IQ-x-qeltu`) and the whole Levantine
  branch declare /ɡ/, the mid long vowels /eː oː/, and /ʒ/ or /dʒ/, so *meeting*
  `miːtinɡ`, *email* `iːmeːl` and *garage* `ɡaraːdʒ`/`ɡaraːɡ` all come out whole.
- **Three-vowel / no-/ɡ/ lects show the projection instead.** MSA (`ar`) and
  Classical (`arb`) have neither /ɡ/ nor /eː/, so *meeting* reads `miːtink`,
  *garage* `karaːdʒ` and *email* `iːmiːl`, while *manager* needs nothing they lack
  and surfaces as `manidʒar`. Najdi (`ar-SA-x-najd`), Mauritanian (`ar-MR`), the
  Sudanic lects (`ar-TD`, `ar-NG`) and Rijāl Almaʿ (`ar-SA-x-rijal-alma`, the
  conservative /q/-retaining ʿAsīr variety) raise *email* to `iːmiːl` for want of
  [eː]; the Maghrebi leaves (`ar-MA`, `ar-TN`, `ar-DZ`) read it `iːmel` on their
  own short mid vowel.

Each row's `notes` name the reflex every switched word takes and the table it came
from, and say where a segment was projected rather than realized, e.g.
`meeting→miːtink: final /ŋ/→[nk] — MSA has no /ɡ/`.

`transliterate(word, lect, strict=True)` refuses the projection instead and returns
`None`, for a linguistic caller for whom a nearest-sound guess is worse than no
answer.

## Tooling

```
python scripts/gold_code_switched.py build [lect ...]     # (re)generate the TSVs
python scripts/gold_code_switched.py validate [lect ...]  # CI gate (also in pytest)
```

`tests/test_gold_code_switched.py` runs the gate in CI, parameterized per lect.

---
[← Arabizi](arabizi.md) · [Home](../README.md) · [API reference →](api.md)
