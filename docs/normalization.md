# Text normalization

Speech work needs text cleaned in two opposite directions, and arbtok has one
function for each.

| You have | You want | Use |
| --- | --- | --- |
| what a recognizer wrote | text a program can act on, or compare | `normalize_asr` |
| what an author wrote | the words that are actually spoken | `normalize_for_tts` |

```python
from arbtok import AsrNorm, TtsNorm, normalize_asr, normalize_for_tts
```

Both live in `arbtok.textnorm`, which imports only the standard library until a
function needs more.

## `normalize_asr`: from recognizer output to usable text

A recognizer writes what it hears in the script it was trained on. A brand name
comes back in Arabic letters, a number comes back as words, and the same word
comes back with or without its hamza from one utterance to the next. None of
that is an error, and all of it gets in the way of whatever reads the transcript
next.

Every rule is a boolean that is off unless you ask for it. With nothing on, the
text comes back unchanged. Both functions take a `str` and raise `TypeError` for
anything else, `None` included: a missing reference is the caller's to decide
about, and scoring it as an empty one hides it.

### Intent parsing and slot filling

An intent parser matches on surface text, so give it the text a person would
have typed: terms in their own script, numbers as digits, one spelling per word.

```python
LEXICON = {"بي إم دبليو": "BMW", "اكس فايف": "X5", "اكس": "X"}

heard = "ابغى احجز صيانة لسيارتي بي ام دبليو اكس فايف موديل الفين وثلاثة وعشرين"
normalize_asr(heard, AsrNorm().with_lexicon(LEXICON), unify_alef=True, spoken_numbers_to_digits=True)
# 'ابغى احجز صيانة لسيارتي BMW X5 موديل 2023'
```

The **lexicon** maps a spelling to the term it stands for. It is part of the
config, set with `with_lexicon`, and cannot be passed beside it: whatever config
a text was normalized under then says everything that was done to it. A spelling matches
whole words only and the longest one wins, so `اكس فايف` is `X5` before `اكس` is
`X`. The spelling and the text are both read under the character rules that are
on: above, the lexicon writes `إم` and the recognizer wrote `ام`, and they meet
because `unify_alef` is on. Punctuation around a match stays where it was, and
punctuation inside a spelling prevents the match. A prefixed form such as
`والاكس فايف` is a different spelling and needs its own entry.

**`spoken_numbers_to_digits`** reads number words in the language given by
`lang=` (default `"ar"`), pointed or not, and leaves text without numbers alone.
It runs after the lexicon, so a term that is spelled with a number word is a
term first.

A phone number read aloud arrives one digit at a time. `join_dictated_digits`
joins seven or more single digits into one run and leaves shorter runs apart,
because two small numbers side by side are two numbers:

```python
heard = "جوالي صفر خمسة خمسة ثلاثة واحد سبعة تسعة اثنين اربعة خمسة"
normalize_asr(heard, spoken_numbers_to_digits=True)
# 'جوالي 0 5 5 3 1 7 9 2 4 5'
normalize_asr(heard, spoken_numbers_to_digits=True, join_dictated_digits=True)
# 'جوالي 0553179245'
```

**`fix_asr_errors`** repairs what a recognizer writes that is not the Arabic
that was said. In Saudi and Gulf speech the conjunction و "and" is said u- before
a vowel, and a recognizer writes that u- as the word او, which is "or". Inside a
spoken number the repair writes it و again, in one shape only: a hundreds word
alone, perhaps after a larger part of the same number, then tens or units that
the thousands word multiplies with it. Every other او stays "or".

A recognizer also writes the Saudi hundred as ماية, a spelling written Arabic
uses for "water". Inside a number the repair writes it مية: fused to a unit
(`اربعماية`), after a unit (`ست ماية`), before the thousands word (`ماية الف`), or
after و that follows a number (`الف وماية`). Anywhere else, as in `كباية ماية`, it
stays as written:

```python
normalize_asr("اربعماية الف", fix_asr_errors=True, spoken_numbers_to_digits=True)
# '400000'
normalize_asr("ست مية او عشرة الف", fix_asr_errors=True)
# 'ست مية وعشرة الف'
normalize_asr("ست مية او عشرة الف", fix_asr_errors=True, spoken_numbers_to_digits=True)
# '610000'
normalize_asr("الف او خمسمية", fix_asr_errors=True, spoken_numbers_to_digits=True)
# '1000 او 500'
```

Text the number rule finds nothing in comes back exactly as it went in. Text it
changes keeps the whitespace at its ends, and its words come back single-spaced
with any Arabic-Indic digits written in ASCII.

A lexicon of car makes and models ships with the package, built from the Arabic
spellings that Saudi maker, distributor and marketplace sites publish. A name
has an entry for every spelling published for it, since a recognizer may write
any of them:

```python
from arbtok.textnorm import bundled_asr_lexicon

normalize_asr("عندي سوناتا جديدة، هيونداي.", AsrNorm().with_lexicon(bundled_asr_lexicon()))
# 'عندي SONATA جديدة، Hyundai.'
```

Every row of `arbtok/data/term_lexicons/cars-sa.tsv` carries the page the
spelling was read from and the day. `scripts/build_term_lexicon.py` builds the
file and takes only spellings a public page published.

**`unify_spoken_variants`** writes one spoken form that is spelled several ways as
one spelling. The Gulf and Saudi closing `في أمان الله` is said as a single run,
and a transcriber may write it as one word, `فمان الله` or `فمانيلا`, where a
recognizer writes the three words. The rule gives the three words, with or without
the hamza on `أمان`. It reads unpointed spelling, so the mark rules run first, and
it takes only the spellings with no space between `ف` and `مان`: `في مانيلا` is
"in Manila" and stays. `CER_NORM` and `CER_NORM_MARKS_FIRST` have it on.

```python
normalize_asr("شكرا فمانيلا", unify_spoken_variants=True)
# 'شكرا في أمان الله'
```

Other rules that help a parser: `fold_digits` turns `١٢` into `12`,
`strip_controls` drops zero-width and bidirectional characters, `strip_harakat`
and its siblings drop marks, `fold_case` lowers Latin text.

### Comparing transcripts: CER and WER

Whether two transcripts are "the same" depends on what the comparison is for, so
the bundles of rules in production use have names. Apply the same bundle to both
sides.

| Bundle | For |
| --- | --- |
| `TRUTH_CHECK` | checking a transcript against a re-transcription, and code-switch detection: marks and letter forms only, digits and punctuation pass through |
| `CER_STRIP` | the TTS bake-off CER instrument: punctuation blanked, then harakat and tatweel dropped |
| `CER_NORM` | `CER_STRIP` with letter forms unified, a word-final bare hamza dropped and spoken variants unified |
| `CER_MARKS_FIRST` | references that carry diacritics or transcriber markup: markup dropped, every mark dropped, then punctuation |
| `CER_NORM_MARKS_FIRST` | `CER_MARKS_FIRST` with letter forms unified, a word-final bare hamza dropped and spoken variants unified |
| `INTELLIGIBILITY_GATE` | intelligibility of synthetic speech: marks dropped, letter forms unified, everything outside the Arabic block blanked |
| `CER_CANONICAL` | a written text against a recognizer's reading of it, or two readings of one recording: `CER_NORM_MARKS_FIRST` with numbers, codes, terms, dialect spellings and clitics each written one way |

```python
from arbtok.textnorm import CER_NORM, TRUTH_CHECK

normalize_asr("مَرْحَبًا بِكُمْ، يا أَحْمَد!", TRUTH_CHECK)
# 'مرحبا بكم، يا احمد!'

ref_tokens = normalize_asr(reference, CER_NORM).split()
hyp_tokens = normalize_asr(hypothesis, CER_NORM).split()
```

### Scoring synthetic speech against the text it was given

A voice is given `السعر 400,000 ريال` and a recognizer writes back `السعر اربع مية
الف ريال`. Nothing was said wrong, and `CER_NORM_MARKS_FIRST` charges most of the
digits. `CER_CANONICAL` brings both sides to one form, so that what remains between
them is what was said differently:

```python
from arbtok.textnorm import CER_CANONICAL

normalize_asr("السعر 400,000 ريال", CER_CANONICAL)          # 'السعر 400000 ريال'
normalize_asr("السعر اربع مية الف ريال", CER_CANONICAL)     # 'السعر 400000 ريال'
normalize_asr("موديل 2026", CER_CANONICAL)                  # 'موديل 2026'
normalize_asr("موديل عشرين ستة وعشرين", CER_CANONICAL)      # 'موديل 2026'
normalize_asr("متوفر عندنا X5", CER_CANONICAL)              # 'متوفر عندنا اكس 5'
normalize_asr("متوفر عندنا اكس فايف", CER_CANONICAL)        # 'متوفر عندنا اكس 5'
normalize_asr("سيارة LAND ROVER", CER_CANONICAL)            # 'سياره لاند روفر'
```

A different thing said still differs: `خمسة ونص` is `5.5` and `خمسة خمسة` is `5 5`,
since the decimal mark survives the punctuation rule; `اكس سيفن` is not `X5`.

Each equivalence has one of two kinds, and the rules hold only these:

- **Spelling.** The same sounds written two ways: `400,000` and `400000`, `مية` and
  `مئة`, `ايوا` and `ايوه`, `احجزلك` and `احجز لك`, `ڤ` and `ف`. These merge freely.
- **Pronunciation, one meaning.** Two sayings of one word or one quantity: `ونص` and
  `والنصف` are both a half, `عشرين ستة وعشرين` and `ألفين وستة وعشرين` are both 2026,
  `فايف` and `خمسة` are both the 5 of a code, `هذي` and `هذه` are both "this". These
  merge because they name the same thing; a dialect-fidelity measure must not use this
  bundle.

Every dialect pair in `unify_dialect_spellings` is one that two recognizers wrote both
ways for the same audio. The terms are those of `canonical_term_lexicon()`: every
Latin name and Arabic spelling in the bundled `cars-sa`, `common-en` and `spoken-sa` tables, each
written as `bundled_tts_lexicon` spells it. A term outside those tables stays in
Latin and is charged against an Arabic reading of it; extend the lexicon with
`CER_CANONICAL.with_lexicon({**canonical_term_lexicon(), **more})`.

`CER_STRIP` and `CER_NORM` blank punctuation before they drop marks. A combining
mark is not a word character, so in that order each mark becomes a space and a
pointed word breaks into letters:

```python
normalize_asr("مَرْحَبا", CER_STRIP)        # 'م ر ح با'
normalize_asr("مَرْحَبا", CER_MARKS_FIRST)  # 'مرحبا'
```

Figures already on record were produced in that order, which is why it is kept,
as the flag `punctuation_before_marks`. Use a `MARKS_FIRST` bundle when the
references are pointed.

`strip_event_markup` removes what a transcriber wrote and no recognizer can
produce, and keeps speech that markup wraps:

```python
normalize_asr("قال [noise] نعم [french: au moins] شيء", CER_MARKS_FIRST)
# 'قال نعم au moins شيء'
```

A bundle takes overrides and a lexicon:

```python
normalize_asr(text, TRUTH_CHECK, fold_digits=True)
normalize_asr(text, CER_NORM.with_lexicon(LEXICON))
```

### Record what you used

Two error rates are comparable only when the same rules produced both.
`describe()` returns a stable string to store beside the number. A lexicon is
named in it by its entry count and a digest of its entries, and the number
parser by its version when numbers are read.

```python
CER_NORM.with_lexicon(LEXICON).describe()
# 'arbtok-asr-norm <rule set>: punctuation_before_marks,strip_harakat,strip_tatweel,
#  unify_alef,unify_ta_marbuta,unify_alef_maqsura,unify_hamza_carriers,
#  blank_punctuation,drop_word_final_hamza,collapse_whitespace;
#  lexicon 3 entries sha256:a44661c91a5bc932'
```

The name after `arbtok-asr-norm` is `ASR_NORM_VERSION`: a digest of the flags in
their order and of every pattern and table the rules use. It changes when a rule
or the order changes, and nobody sets it by hand. `TTS_NORM_VERSION` is computed
the same way.

**Record the `describe()` string, not the version alone.** The version names the
rules. What a config carries as values is configuration and is outside it: which
flags are on, a lexicon, and for `normalize_for_tts` the phone regions, phone
shapes, phone prefixes and identifier words (`ARAB_PHONE_REGIONS`,
`IDENTIFIER_WORDS` or your own). `describe()` names each of those, the tuples and
the lexicon by a digest of their content, so two runs that differ in any of them
describe themselves differently while sharing one version. If the number parser's
version cannot be read, `describe()` says `ovos-number-parser unknown` and still
returns.

### Every rule

Rules run in this order. A lexicon is applied after the mark rules and before
`fix_asr_errors`.

| Flag | Rule |
| --- | --- |
| `nfc` | Unicode NFC |
| `strip_event_markup` | drop bracketed non-speech labels, timestamps and language tags; unwrap `[french: ...]` to the speech inside |
| `strip_controls` | drop zero-width and bidirectional control characters |
| `punctuation_before_marks` | run `blank_punctuation` ahead of the mark rules |
| `strip_harakat` | U+064B–U+0652 |
| `strip_extended_marks` | U+0653–U+065F and the dagger alif U+0670 |
| `strip_quranic_marks` | U+0610–U+061A, U+06D6–U+06ED |
| `strip_tatweel` | U+0640 |
| `split_term_proclitics` | a proclitic written onto a Latin word is written apart, `وMINI` as `و MINI`, and a lexicon spelling matches after a proclitic, `وام جي` (Arabic only) |
| `fix_asr_errors` | recognizer spellings that are not the Arabic said are repaired: inside a spoken number, `ماية` becomes the hundred `مية` and `او` becomes the conjunction `و` (Arabic only) |
| `unify_spoken_variants` | one spoken form written several ways is written one way: `فمانيلا`, `فمان الله` and `في مان الله` become the three words `في أمان الله` (Arabic only) |
| `unify_dialect_spellings` | a word recognizers write two ways for the same audio is written one way: `هذي` as `هذه`, `معاك` as `معك` (Arabic only) |
| `number_forms` | numbers written or said several ways are written one way: thousands separators, dates, percent, decimals, colloquial number words and years; `.` `:` `/` `%` inside a number survive `blank_punctuation` |
| `spoken_numbers_to_digits` | number words become digits |
| `join_dictated_digits` | seven or more single digits in a row become one run |
| `spell_codes` | a code is written as its letter names and digits, `X5` as `اكس 5`, and English digit names in a run of letter names are digits (Arabic only) |
| `unify_alef` | آ أ إ ٱ become ا |
| `unify_ta_marbuta` | ة becomes ه |
| `unify_alef_maqsura` | ى becomes ي |
| `unify_hamza_carriers` | ئ becomes ي, ؤ becomes و |
| `unify_loan_letters` | ڤ پ گ چ ڨ become ف ب ك ج ق |
| `fold_digits` | Arabic-Indic and Extended Arabic-Indic digits become ASCII |
| `fold_case` | `str.lower()` |
| `arabic_block_only` | blank everything outside U+0600–U+06FF |
| `blank_punctuation` | blank what is neither a word character nor whitespace |
| `drop_word_final_hamza` | drop a bare ء that ends a word |
| `join_clitics` | a lone و joins the next word, ل with its pronoun joins the word before, and عبد with the name after it, ان شا الله, الحمد لله, يا رب and ما في are one word each (Arabic only) |
| `collapse_whitespace` | one space between words, ends trimmed |

`arabic_block_only` also blanks Latin text, including a term the lexicon just
wrote. `INTELLIGIBILITY_GATE` is built that way on purpose; do not combine it
with a lexicon and expect the terms to survive.

## `normalize_for_tts`: from written text to the words that are spoken

```python
normalize_for_tts("السعر 45000 ريال")
# 'السعر خمسة وأربعون ألف ريال'
```

The rules are booleans on a `TtsNorm`, the way `normalize_asr`'s are on an
`AsrNorm`; pass a config, flags, or a config with flags that override it. With
no config it runs `spoken_forms` and `canonical_unicode`, which is what the G2P
plugin runs.

`spoken_forms` writes dates, times, numbers and units as words in `lang`.
`canonical_unicode` drops tatweel, applies NFC, orders shadda before its vowel
and settles the spellings of مائة, which is the form the tokenizer reads.
`strip_controls`, off by default, drops zero-width and bidirectional characters
that would otherwise reach the tokenizer as characters with no reading.

```python
normalize_for_tts("المـرء عنده 3 كتب", spoken_forms=False)
# 'المرء عنده 3 كتب'
```

Diacritization is not part of it. That is a model, and it lives in
`arbtok.vocalize` and in `ArbtokG2PPlugin(diacritize=True)`.

### Latin terms: a lexicon, and spelling out codes

A synthesizer trained on Arabic does badly with `BMW X5`, and a phonemizer has
no reading for it at all. Two inputs put Arabic in its place.

A lexicon, set on the config with `with_lexicon`, maps a term to the way it is
said. It is applied before anything else, the longest term first and without regard to case. A term ends where a
Latin letter or digit ends, so an Arabic prefix written against it stays
attached, and a tatweel written between the two, `للـNissan`, is dropped once the
term is read in Arabic: `للنيسان`. A spelled code drops it the same way. A digit
written against the letters of a reading, the bundled `أتش1` for `H1`, is read apart
from them by its English name, as a spelled code's digit is: `أتش وَنْ`, where the
cardinals would otherwise fuse it to the letters as `أتشواحد`.

`spell_out_codes=True` reads what the lexicon did not claim and is a code, one
character at a time. A code is a run of capitals and digits with at least one of
each, such as `X5` or `GV70`, or a run of two or more capitals with no vowel among
them, such as `BMW`, `GMC` or `MG`: those spell no word, so they are initialisms.
A number on its own is not a code and goes to the number rules; a lowercase word is
left for the loanword path; and a run of capitals that spells a word is a word.
`TOYOTA`, `FORD`, `KIA`, `AUDI` and `LAND ROVER DEFENDER` are read, not spelled.

The vowel is what the rule has to go on, and it is not always right. `SUV`, `VIN`
and `ABS` are initialisms that carry a vowel, so the rule reads them as words and
leaves them whole. Spelling one is what the lexicon is for: `{"SUV": "إِسْ يُو فِي"}`
is applied before the code reading and gives the letters their names.

Four unit symbols are written in capitals often enough that the capitals say nothing
about a code: `KM`, `KG`, `KW` and `HP`. After a number each of them is the unit, so
`50 KM` is read as kilometres, and so is any symbol the unit table itself capitalises,
`2 GB`. Every other symbol is read in the case it is written in, because there the
capitals are the evidence of a code: `3 mg` is milligrams where `3 MG` is the make,
and `2 ev` is electronvolts where `2 EV` is a car and is left as written.

A code written with a space between its letters and its digits, `MG 4` or `X 5`,
is joined and read as the joined code. `spell_out_codes` joins one to three
capitals and one or two digits standing alone before the lexicon runs, and reads
`MG 4` as `MG4` and `X 5` as the lexicon's `X5`. The cited case is `MG 4`: German
Wikipedia's page for the name opens "MG4 oder MG 4 steht für:" and lists the car
as "MG 4 EV, Pkw-Modell"
([revision 236735370](https://de.wikipedia.org/w/index.php?oldid=236735370)). That
every model code written with a space names its joined code is this package's
generalisation from that case. One small letter may lead, as in BMW's `iX 3`, and the code is joined in capitals,
`IX3`, since only capitals are spelled. Written joined, `iX3` is read the same way.
BMW's `i4` to `i7`, a small i before one or two digits, are read as `I4` is. One of BMW's
small suffix letters after two or three digits, `520i`, `330e`, `320d`, `M340i` or, after
the long wheelbase's L, `740Li`, is part of the code too, and is read in capitals with the rest:
`فَيْفْ تُو زِيرُو آيْ`. Every code is spelled one character at a time with the English
digit names, so `LX600` is "six zero zero" and `520i` "five two zero i"; a
consumer that wants the spoken hundreds, `خمس مية وعشرين آي`, puts the term in its
lexicon, which is applied first. With `spell_out_codes` off and the cardinals on, a
code written with a hyphen, `CX-5`, stays whole as `CX5` does, rather than its digit
becoming `CX-خمسة`. Three cases are not joined, because their digits are not a code's:

| written | why it stays |
|---|---|
| `BMW 5 SERIES`, `BMW 5 سيريز`, `BMW 5 سيريس` | the digit numbers the series |
| `MG 4,500` | the digit is part of a larger figure |
| `SAR 50`, `SR 50`, `KM 20` | a currency code or abbreviation, or a capitalised unit symbol, makes the number an amount |

The currency codes are the ISO 4217 codes of the bundled CLDR table. `SR` is not
one, and is guarded because English Wikipedia's "Saudi riyal" gives the riyal's
symbol as "SAR, SR, ر.س"
([revision 1252604873](https://en.wikipedia.org/w/index.php?oldid=1252604873)).
A Latin plate written with a space, `ABC 12`, is joined too, and reads letter by
letter with English digits. So is a paper size, `ورق A 4`, which reads as `A4`
already did. The currency codes, the abbreviations and the unit symbols are part of
`TTS_NORM_VERSION`, so a change to the bundled tables moves the version.

The lexicon comes first either way. A published reading of a name or of a whole
model, `BMW 7 Series` among them, belongs in the lexicon, which is applied before
the code reading and overrides it.

A run of 8 to 17 of those characters with at least one digit is a vehicle
identification number, or a fragment of one, and is read as an identifier: the
letters take the same English names, and the digits take the Arabic words a phone
number or a booking reference is read with, one at a time, in the lect's words
under `dialect_numbers`. ISO 3779 fixes the VIN at 17 capitals and digits, without
I, O and Q. The floor of eight is a design choice that takes the fragments an agent
reads back ("the last eight are L457L680") and leaves every model code of seven
characters or fewer, such as `X5` or `GLE450`, with the English digit names. A
shorter run right after a word that names the VIN (`رقم الهيكل`, `الشاصي`, `VIN`, with
up to two Arabic words between) is the end of one and is read as a VIN is:
`رقم الهيكل ينتهي بـ ABC1234` takes the Arabic digit words.

A VIN is not always written as one run of capitals. A whole VIN written with small
letters, `jtdkb20u793456789`, is read in capitals. A VIN written in groups is joined
before any other code rule reads a group on its own: groups joined by hyphens when
together they make seventeen characters, `JTDKB20U7-93456789`, and groups joined by
hyphens or single spaces right after a word that names the VIN when together they make
eight to seventeen, `رقم الهيكل WBA 7F2 C51 JG`.

A run of letters and digits with a capital in it is read whole or character by
character, never part by part. With `spell_out_codes` off it reaches the synthesizer
as it was written: `L809UPZ3V361` stays `L809UPZ3V361`, where a number rule reading
the digit runs inside it gives a code no listener can write back down. A run without
a capital is not a code: `15h01` is a time and `7abibi` is Arabizi.

So a run of capitals is read in one of three ways. With a digit in it, it is an
identifier: spelled out under `spell_out_codes`, and left exactly as written
without it. With no digit and no vowel, it is an initialism and is spelled out.
With no digit and a vowel, it is a word and is never spelled.

```python
normalize_for_tts("رقم الهيكل WBA7F2C51JG", "ar", TtsNorm(spell_out_codes=True))
# 'رقم الهيكل دَبَلْيُو بِي إِي سبعة إِفْ اثنين سِي خمسة واحد جِيْ جِي'
```

```python
SAID = {"BMW": "بِي إِمْ دَبَلْيُو", "7 Series": "سِفَنْ سِيرِيزْ"}

normalize_for_tts("عندنا بالBMW X5 و 7 Series موديل 2023", "ar", TtsNorm(spell_out_codes=True).with_lexicon(SAID))
# 'عندنا بالبِي إِمْ دَبَلْيُو إِكْسْ فَيْفْ و سِفَنْ سِيرِيزْ موديل ألفان وثلاثة وعشرون'
```

**Give the spoken form fully pointed.** The diacritizer supplies the short vowels
of an unpointed word from the sentence around it, and for a borrowed word it has
nothing to go on: the same spelling gets different vowels in different
sentences. A pointed word it leaves alone, so the reading is the one the entry
gives.

```python
Sentence("اكس فايف", stress=False).ipa        # 'ʔiks faːjf'
Sentence("إِكْسْ فَيْفْ", stress=False).ipa   # 'ʔiks fajf'
```

The names `spell_out_codes` uses are in `spelled_codes()`: the 26 English letter
names and the ten digit words, pointed.

**No part of that table has been checked by a human speaker of Arabic.**

A letter's consonant skeleton is the spelling Arabic writing attests for that
letter. Each was read from an ar.wikipedia page that prints the spelling beside
the Latin initialism it spells, and the page is named in the table below. The
vowels are the English letter name's, taken from the pronunciation the page on
the English alphabet (أبجدية إنجليزية) gives, and written as the nearest Arabic
rendering the tokenizer reads. The two sources answer different questions: the
first says which letters an Arabic writer uses for a letter name, the second says
how that name is said.

That matters where one skeleton serves two letters. `جي` is written for both G
and J, so G takes the vowels of "gee" and J those of "jay"; `كي` is written for K,
which takes "kay" and so is not heard as C. **A letter must be heard apart from
every other, and a test says so.** B and P are the one exception: Arabic has no
/p/, the sources give `بي` for both, and the table keeps the collision rather
than invent a spelling for it.

| Letter | Spelling | Read from | Pointed | Says |
|---|---|---|---|---|
| A | `إيه` | واي إم سي إيه (أغنية) | `إِيهْ` | ay /eɪ/ |
| B | `بي` | USB | `بِي` | bee /biː/ |
| C | `سي` | CNN | `سِي` | cee /siː/ |
| D | `دي` | DVD | `دِي` | dee /diː/ |
| E | `إي` | ESPN | `إِي` | ee /iː/ |
| F | `إف` | KFC | `إِفْ` | ef /ɛf/ |
| G | `جي` | LG | `جِي` | gee /dʒiː/ |
| H | `إتش` | HBO | `إِتْشْ` | aitch /eɪtʃ/ |
| I | `آي` | IBM | `آيْ` | i /aɪ/ |
| J | `جي` | J. K. Rowling | `جَيْ` | jay /dʒeɪ/ |
| K | `كي` | KFC | `كَيْ` | kay /keɪ/ |
| L | `إل` | LG | `إِلْ` | el /ɛl/ |
| M | `إم` | MTV | `إِمْ` | em /ɛm/ |
| N | `إن` | CNN | `إِنْ` | en /ɛn/ |
| O | `أو` | HBO | `أُو` | o /oʊ/ |
| P | `بي` | ESPN | `بِي` | pee /piː/ |
| Q | `كيو` | QGIS | `كْيُو` | cue /kjuː/ |
| R | `آر` | R&B | `آرْ` | ar /ɑːr/ |
| S | `إس` | USB | `إِسْ` | ess /ɛs/ |
| T | `تي` | MTV | `تِي` | tee /tiː/ |
| U | `يو` | USB | `يُو` | u /juː/ |
| V | `في` | DVD | `فِي` | vee /viː/ |
| W | `دبليو` | BMW | `دَبَلْيُو` | double-u /ˈdʌbəljuː/ |
| X | `إكس` | Xbox | `إِكْسْ` | ex /ɛks/ |
| Y | `واي` | واي إم سي إيه (أغنية) | `وَايْ` | wy /waɪ/ |
| Z | `زد` | DF-ZF | `زِدْ` | zed /zɛd/ |

Three rows are weaker than the rest and say so here. `X` is `إكس` from the page
on the Xbox, which is a word rather than the letter; the vowels are the English
name's as everywhere else. `Z` is `زد` from DF-ZF; `زي` is attested too, on the
page for Jay-Z, and is not what this table uses. `A` is told apart from `E` by one
consonant and nothing else: `إِيهْ` reads /ʔiːh/ where `E` reads /ʔiː/. The
English name is /eɪ/, which the inventory has no vowel for, so the final ه of the
attested spelling carries the whole distinction. A listener who misses it hears E.

The pairing for both `A` and `Y` is printed on the page for the song,
واي إم سي إيه (أغنية), not on the organisation's own page, which does not spell
the letters out.

The digit words have a different basis, unchanged: each is the English word's
pronunciation from the bundled donor lexicon, carried into Arabic by
`arbtok.translit.nativize`, with the glottal onset Arabic gives a word that
starts with a vowel. A test holds every digit row to that.

A caller who wants a letter said another way puts its own spelling in the
lexicon, which is applied first.

The bundled car lexicon also reads in this direction, one published spelling per
name, the maker's own site before its distributor's before a marketplace. The
maker publishes the name it wants said; a marketplace publishes the one buyers
search for, and where the two differ the table takes the maker's:

```python
from arbtok.textnorm import bundled_tts_lexicon

normalize_for_tts("سيارة Hyundai Sonata", "ar", TtsNorm().with_lexicon(bundled_tts_lexicon()))
# 'سيارة هيونداي سوناتا'
```

Those spellings are as published, which is unpointed. They replace Latin letters
with Arabic ones, and their short vowels are still the diacritizer's to supply.

A second bundled lexicon, `common-en`, holds a little over fifty English terms in
everyday use: `WiFi`, `Bluetooth`, `Apple`, `CarPlay`, `Online`, `WhatsApp`,
`Cruise Control` and the rest. Each has its conventional Arabic spelling and a
pointed one:

```python
said = bundled_tts_lexicon("common-en")
normalize_for_tts("فيها WiFi و Apple CarPlay", "ar", TtsNorm().with_lexicon(said))
# 'فيها وَايْ فَايْ و أَبِلْ كَارْبْلَايْ'

bundled_tts_lexicon("common-en", pointed=False)["WiFi"]    # 'واي فاي'
normalize_asr("فيها واي فاي", AsrNorm().with_lexicon(bundled_asr_lexicon("common-en")))
# 'فيها WiFi'
```

The spellings are the ones Arabic text conventionally uses. The pointing is this
package's own and cites no source; every row of
`arbtok/data/term_lexicons/common-en.tsv` says `authored`, and records the
reading the tokenizer gives the pointed form so that a change to it is seen.
Lexicons combine with `{**cars, **common, **yours}`, later entries winning.

Four more bundled lexicons come from Unicode CLDR, pinned to one release, every row
carrying the release file it was read from, that file's digest and the licence:
`units-cldr` (unit names), `currencies-cldr` (names and ISO codes, so `SAR` reads
`ريال سعودي`), `territories-cldr` and `languages-cldr`. The loader keeps only names
a voice can say, since CLDR gives some units a symbol or a Latin abbreviation as
their Arabic name, and leaves out CLDR's pseudo-locales. These tables read one way:
`bundled_asr_lexicon` refuses them, because read backwards they would translate
Arabic words into English.

```python
money = bundled_tts_lexicon("currencies-cldr")
normalize_for_tts("السعر 500 SAR", "ar", TtsNorm().with_lexicon(money))
```

`ر.س`, the riyal's Arabic symbol, has no Latin letter for a lexicon to find. Where the
cardinals speak numbers it is said `ريال` after a number, written with a space before it
or against the digits: `1,200 ر.س` is `ألف ومئتين ريال`.

A unit symbol is read only where it follows a number, because `in` and `m` in running
text are not units. `spoken_forms` does that for Arabic from the same CLDR table
(`cldr_units()`): `المسافة 5 km` becomes `المسافة خمسة كيلومتر`. The unit takes its
CLDR display name; it is not inflected for the number before it.

A voice agent that speaks its numbers through the cardinals, with `spoken_forms` off,
reads no unit symbol this way. For the kilometre, the unit its replies carry most,
`colloquial_units` says it the way Saudi agents do, `كيلو`, written `km` or `كم`:
`الصيانة كل 10000 كم` becomes `الصيانة كل عشرة آلاف كيلو`. Without it, `كم` after a
number reads as the word "how much". `كم` stays the question wherever it can be one: before
a question mark or a noun, and after a year or a Latin model name, so `كامري 2024 كم؟` and
`عندي 3 كم سؤال` are left alone; it is the kilometre before the end of the text, other
punctuation, or a word that follows a distance (من, في, بس, كل, و and the like).

The post office box is written `ص ب`, `ص.ب` or `ص. ب.` before its number. Read as it
stands it is two letter names or the word ص, so wherever the cardinals speak the number
it is read `صندوق بريد`: `ص ب 1234` becomes `صندوق بريد ألف ومئتين وأربعة وثلاثين`. The rule skips `ص ب` after
another single letter, where the two letters end a plate (`ح ص ب 1234`), and after a
number, where ص is the morning.

### Licence plates in Arabic script

A licence plate written in Arabic script is read by the letters' names and digit by
digit. Left bare, its letters are spoken as a word, `س ع د` as the name سعد, and its
digits as one cardinal. `spell_out_plates` is off by default, as `spell_out_codes`
is, and applies to Arabic only; a voice agent turns it on.

```python
normalize_for_tts("أ ب ج ١٢٣٤", "ar", spell_out_plates=True)
# 'ألف باء جيم واحد اثنين ثلاثة أربعة'
normalize_for_tts("هـ و ى ١٢٣٤", "ar", spell_out_plates=True)
# 'هاء واو ياء واحد اثنين ثلاثة أربعة'
```

A Saudi plate carries three letters, and "There are only 17
Arabic letters used on the registration plates"
([Vehicle registration plates of Saudi Arabia](https://en.wikipedia.org/wiki/Vehicle_registration_plates_of_Saudi_Arabia)):
ا ب ح د ر س ص ط ع ق ك ل م ن هـ و ى. The plate prints ه with a tatweel, `هـ`, and
carries "three letters and up to four numbers"; a personalised or older plate "may
contain one, two or three numbers" (the same article,
[revision 1352834674](https://en.wikipedia.org/w/index.php?oldid=1352834674)).
The rule takes three single letters, each optionally followed by a tatweel, separated
by one space, and then, after one space, a dash or nothing, one to four digits in
either script, optionally spaced: `أ ب ج1234` is a plate too. Three or four digits written first and the three letters
after them, `١٢٣٤ أ ب ج`, are a plate too and are read in the order written. The
first letter starts the text or follows whitespace or opening punctuation, so
`(أ ب ج ١٢٣٤)` and `«أ ب ج ١٢٣٤»` are read whole. It takes any letter that has a
name, since running text writes the plate's ا as أ.

Reading each letter by its name, as the alphabet names it (أ إ آ ا are all ألف), is
the convention a speaker follows for a spelled sequence; the plate
standard does not prescribe it. The digits take the words of a digit-by-digit
reading, the lect's under `dialect_numbers` and yours under `number_forms`. ى is named
ياء: on the plate it is the letter ي printed without its dots, which the plate's Latin
row writes V and the article transliterates ỳ, not the alif maqsura that ends a word.

The plate's Latin row is three of the capitals the plate maps its letters to,
A B J D R S X T E G K L Z N H U V, written in either case, and up to four digits. After a word that names a
plate (لوحة, اللوحة, لوحتها, with at most one word between), it is read by the
capitals' names from `spelled_codes()` and digit by digit, in the order written:
`اللوحة XTR 6477` is `اللوحة إِكْسْ تِي آرْ ستة أربعة سبعة سبعة`. Elsewhere three capitals
and a number are a model name or a price, and the code rules read them.

What is not a plate reads as it does without the rule: a single letter before a
number, which is a label or a particle (`الباقة أ 1450 ريال`, `و 1500 ريال`); two
letters, which are an abbreviation (`ص ب 1234` is a post office box); four letters
or more; letters spaced unevenly; five digits, a decimal, or a second group of
digits. A plate does not start right after another single letter or a
tatweel, with one exception: the conjunction و, so `أ ب ج ١٢٣٤ و د ر س ٥٦٧٨` is two
plates. A letter's name is a word, so a reading is never read again
as a plate: `ألف ١٢٣٤` is a cardinal. The rule runs before the lexicon, so a term
made only of digits, a model number such as `530`, cannot take a plate's digits.

### Numbers a voice agent reads out

A reply holds prices, phone numbers and booking references, and a plain
"numbers to words" pass reads all of them as quantities. These rules tell them
apart. A voice agent turns them on with the numbering plans of every Arab League
member:

```python
from arbtok.textnorm import ARAB_PHONE_REGIONS, IDENTIFIER_WORDS, TtsNorm, normalize_for_tts

VOICE_AGENT = TtsNorm(speak_percent=True, keep_code_digits=True, phone_regions=ARAB_PHONE_REGIONS,
                      long_digit_runs=True, identifier_words=IDENTIFIER_WORDS, cardinal_numbers=True,
                      leave_unspeakable_numbers=True, oblique_numbers=True, space_fused_hundreds=True,
                      spoken_forms=False, canonical_unicode=False)

normalize_for_tts("السعر النهائي 355,000 ريال", "ar", VOICE_AGENT)
# 'السعر النهائي ثلاث مئة وخمسة وخمسين ألف ريال'
normalize_for_tts("خلني أسجل رقمك 0551234567", "ar", VOICE_AGENT)
# 'خلني أسجل رقمك صفر خمسة خمسة واحد اثنين ثلاثة أربعة خمسة ستة سبعة'
normalize_for_tts("اتصل على 010 01234567", "ar", VOICE_AGENT)
# 'اتصل على صفر واحد صفر صفر واحد اثنين ثلاثة أربعة خمسة ستة سبعة'
normalize_for_tts("كود العرض 4471 صالح", "ar", VOICE_AGENT)
# 'كود العرض أربعة أربعة سبعة واحد صالح'
normalize_for_tts("نسبة التمويل 4.5%", "ar", VOICE_AGENT)
# 'نسبة التمويل أربعة فاصلة خمسة في المئة'
```

Every rule of `normalize_for_tts`, in the order they run; a lexicon is applied after
`strip_controls` and `spell_out_plates`:

| Flag | Rule |
| --- | --- |
| `strip_controls` | drop zero-width and bidirectional control characters |
| `spell_out_plates` | a licence plate in Arabic script, three single letters and one to four digits, is read by the letters' names and digit by digit: `أ ب ج ١٢٣٤` is `ألف باء جيم واحد اثنين ثلاثة أربعة`; the plate's Latin row after a word that names a plate, `اللوحة XTR 6477`, by the capitals' names and digit by digit; Arabic only |
| `spell_out_codes` | read `X5`-shaped codes character by character from `spelled_codes()`, after the lexicon; a run of 8 to 17 with a digit is a VIN, its digits read as Arabic words, and so is a shorter run after a word that names the VIN; a VIN in small letters or in groups is read as one |
| `speak_percent` | `4.5%` becomes `4.5 في المئة`, then the number is spoken; so does `%4.5`, the sign written first |
| `keep_code_digits` | up to four digits beside a Latin word, `MG 5` or `7 Series`, belong to the name and are kept from every number rule; a number beside a currency code, `500 SAR` or `SR 50`, is an amount and is spoken |
| `phone_shapes` | patterns of a phone number in running text; a match is read digit by digit |
| `phone_regions` | ISO 3166-1 regions whose numbering plans are recognised; a valid number of one of them, written with `+` or `00` and the country code, with the region's trunk prefix, or after an identifier word, is read digit by digit |
| `long_digit_runs` | eleven or more digits are a reference, read digit by digit |
| `phone_prefixes` | patterns a bare digit run matches whole when it is a phone number; a run written with `+` is one too |
| `identifier_words` | words after which a number is a reference: `الكود 4729`, `برقم الحجز 3401`. A proclitic may be attached and one other word may stand between |
| `cardinal_numbers` | speak Arabic-Indic and ASCII numbers as cardinals ahead of `spoken_forms`, so the next three flags apply. A whole number directly after a rank noun is the ordinal agreeing with it: `الطابق 3` is `الطابق الثالث`, `الفئة 5` is `الفئة الخامسة`. This holds from 1 to 99; from 100 the number stays a cardinal. The nouns, their genders and their sources are in `arbtok/data/rank_ordinals.tsv`. A date written in digits, day, month and year or an ISO year first, is read as its day, its month by name and its year: `10/6/2026` is `عشرة يونيو ألفين وستة وعشرين`. A number from 3 to 10 before a plural whose singular is feminine takes its short form, `5 سنوات` is `خمس سنوات`, and a number written against the Arabic word after it is read apart from it, `45,000ريال` as `45,000 ريال` |
| `colloquial_clock` | where a clock time is spoken, it is read as Saudi speech says it: `9:30` is `الساعة تسعة ونص`, `14:00` is `الساعة اثنين الظهر`; the hour a cardinal, `وربع` and `ونص` for the quarter and the half, and the part of the day by its common word where the text gives the period |
| `colloquial_years` | a year from 2020 to 2099 after سنة, عام, موديل, موديلات or a month name is read as Saudi speech says it: `موديل 2026` is `موديل عشرين ستة وعشرين`, and a second year after و is read the same way on its own; an earlier year, or a four-digit number with no such word before it, stays a cardinal |
| `colloquial_units` | a kilometre after a number in digits, `km`, `km/h` or `كم`, is said as Saudi speech says it: `10000 كم` is `عشرة آلاف كيلو` and `120 km/h` is `مئة وعشرين كيلو بالساعة`; a lexicon term for the symbol keeps its reading (Arabic only) |
| `leave_unspeakable_numbers` | a number that cannot be spoken is left as written and the rest is still read; otherwise the error is raised |
| `oblique_numbers` | cardinals in the oblique case, the one connected speech uses |
| `space_fused_hundreds` | in those cardinals `ثلاثمئة` becomes `ثلاث مئة`; a synthesizer keeps the spaced form and garbles the fused one |
| `dialect_numbers` | the cardinals and the digit-by-digit readings take the words the lect `lang` names uses, asked of the number parser under that lect's ISO 639-3 code |
| `number_forms` | your own words for values, `{100: "مية"}`, over the lect's or instead of them; set with `with_number_forms` |
| `month_names` | your own words for the twelve months, January first, said wherever a month name is written and for a date in digits the cardinals read: with `جون` for June, `15 يونيو` is `15 جون`; a date `spoken_forms` alone reads keeps the date parser's month; Arabic only |
| `spoken_forms` | dates, times, numbers and units as words in `lang`; on by default. A time written with a dot after `الساعة`, `الساعة 9.30`, is a time, as it is under `cardinal_numbers`, unless an amount of money follows it: `سعر الساعة 12.50 ريال` is a decimal |
| `canonical_unicode` | tatweel dropped, NFC, shadda before its vowel, the spellings of مائة settled; on by default |
| `drop_false_starts` | a two- or three-letter word ending in tatweel is dropped with the whitespace after it where the next word begins the same way: `الـ السيارة` becomes `السيارة`; a one-letter fragment is kept, since it is also how a detached clitic is written; Arabic only, on by default |
| `plain_orthography` | the output in the orthography speech-recognition transcripts use: no harakat, tatweel or Quranic marks, alef without hamza, a dagger alef written ا where the standard spelling has it, ڤ as ف, and ة, ى, ؤ and ئ kept, so `بِي إِمْ دَبَلْيُو` is `بي ام دبليو` and `ألف` is `الف`; the last rule, over the whole text |

### Numbers in the words a lect actually uses

A number spoken in Standard Arabic is not what a lect says: where the literary
reading is `خمسة عشر` for 15, Jidda and Abu Dhabi both say `خمسطعش`, and where it
is `ثلاثمئة` Jidda says `تلتمية` and Abu Dhabi `ثلاثمية`. `dialect_numbers` asks
the number parser for the lect's own words, under that lect's ISO 639-3 code.

```python
normalize_for_tts("السعر 350 ريال", "ar", VOICE_AGENT)
# 'السعر ثلاث مئة وخمسين ريال'
normalize_for_tts("السعر 350 ريال", "ar-SA-x-hejaz", VOICE_AGENT, dialect_numbers=True)
# 'السعر تلت مية وخمسين ريال'
```

The words are the parser's, quoted there from a published grammar with its page,
and it composes the number the same way whichever lect it speaks: a lect differs
in its words and not in its arithmetic. It has words for Hijazi `acw`, Gulf `afb`,
Najdi `ars` and Cairene Egyptian `arz`. What arbtok adds is the translation from the tag you
passed to that code, `arbtok.lect_code`, which walks the orthography2ipa parent
chain, so Kuwaiti and Qatari take the Gulf code from the node they descend from.
**A lect the parser has no cited words for keeps the literary ones**: a form no
source gives is not written. `ar-SA` resolves to Najdi and takes its words.

**The noun is the author's.** Arabic makes the counted noun agree with the number,
and the dialects covered agree in the same direction: two to ten take a plural noun
and eleven upwards a singular. The noun is left as written, because the text around
the number is the author's; write it the way the number you passed in requires.

The number agrees with the noun where the noun after it shows how. A number from 3 to
10 written right before a plural whose singular is feminine takes its short form, as
Standard Arabic and Saudi speech both say it: `5 سنوات` is `خمس سنوات`, `6 ثواني` is
`ست ثواني` and `8 سيارات` is `ثماني سيارات`, eight taking its construct before the
noun. `3 أيام` keeps `ثلاثة`, since يوم is masculine. The plurals and the source of
each are in `arbtok/data/feminine_counted_nouns.tsv`; a plural not listed there keeps
the long form. Your own word for a value, from `number_forms`, is said as you gave it.
Two hundred before ألف, مليون or مليار is in construct and drops its nun: `200,000` is
`مئتي ألف`, `مئتا ألف` in the nominative.

The flag is off everywhere by default, so a number keeps its literary words
unless you ask for a lect. `with_number_forms` gives your own words for values,
with or without a lect under them, and `describe()` names the parser and digests
your words, so a run records which words it used.

A price and a phone number cannot be told apart by length, so nothing here
guesses from length alone below eleven digits: a phone number is known by its
prefix or by the word before it, and a colon may follow that word, `الكود: 4729`.
`موديل 4729` stays a quantity because `موديل` is not an identifier word.
`ARAB_PHONE_REGIONS` and `IDENTIFIER_WORDS` are plain tuples; pass your own for another vocabulary. `phone_shapes` and `phone_prefixes`
take your own patterns for numbers the bundled plans do not cover; no preset sets
them.

`phone_regions` names the regions whose numbering plans are read, and
`ARAB_PHONE_REGIONS` lists the 22 members of the Arab League. The plans are bundled
in `arbtok/data/phone_plans.json`: for each region its country code, its trunk
prefix and, for each number type, the pattern and lengths of a national number, and
the digits a number of that type starts with, each with the lengths such a number has.
The table is built by `scripts/build_phone_plans.py` from `resources/PhoneNumberMetadata.xml`
of Google's libphonenumber (https://github.com/google/libphonenumber), and its
`source` field names the release tag and the sha256 of the file it read.

A run of 7 to 15 digits, in groups split by spaces or hyphens, is read digit by digit
when it is a valid number and it also says it is a phone number. A run that starts
with `+` or `00` names its country, and is read when the rest is a number of that
country in the bundled plans, whichever regions are configured. Otherwise the plans
of `phone_regions` are tried, and the run is read when it starts with a three-digit
country code and a mobile number (`966 50 123 4567`), or with the region's trunk
prefix (`0` in most of them), or when it is a toll-free, shared-cost or unified
number of eight digits or more (`8001000341`, `920012345`), whose first digits say
what it is, or when it follows an identifier word. So `اتصل على 010 01234567` is an
Egyptian mobile, while a bare Kuwaiti
`50012345` stays a quantity until it follows a word such as `رقمي`: in the Gulf and
the Maghreb there is no trunk prefix, and eight digits are a price as often as a
phone number. A run whose first groups are a date, `05-06-2024`, is never read this
way unless it starts with `+` or `00`, and a run that touches another digit across a
comma, a point, a slash or a colon is part of a longer number, a date or a time.

A run that says it is a phone number is read digit by digit even when the plans do
not hold it as a valid number, so a short or a long number is still read out:

- a run led by `+` with five digits or more, the `+` dropped (`+9665012345`);
- a run led by `00` and a country code of the plans, with five digits or more after
  the `00`;
- a run of seven digits or more after an identifier word (`الموحد 9200012345`);
- a run of nine digits or more that starts with a three-digit country code of
  `phone_regions` and a digit that region's mobile numbers start with (`966501234`);
- a run of 8 to 11 digits that starts with the first three digits of a toll-free,
  shared-cost or unified number of `phone_regions`, at a length the plan gives numbers
  that start with them.

So `السعر 92000123 ريال` stays a price: it starts with 920, but a Saudi unified
number has nine digits, and no word before it says it is a phone number. When a run
of groups holds a valid number, the longest valid number is read and the rest of the
run keeps its own reading.

The rules from `speak_percent` to `identifier_words`, and `dialect_numbers` and
`number_forms` with them, write Arabic words, so they raise `ValueError` for a
`lang` that is not Arabic.

`VOICE_AGENT` leaves `spoken_forms` and `canonical_unicode` off, because its
cardinals speak the numbers. `TtsNorm.describe()` gives the string to record, as
`AsrNorm.describe()` does.

### Before synthesis

This is the preparation `ArbtokG2PPlugin.normalize` runs before it diacritizes,
so text that goes through the plugin already has it. Call it yourself when you
hand text to a synthesizer that does not go through the plugin, so the model is
never asked to read a digit.

### Before CER on a read-back

A TTS evaluation synthesizes a reference, recognizes the audio and scores the
transcript against the reference. When the reference holds `45000`, the voice
says words and the recognizer writes words, and a character comparison charges
the system for a difference in notation that nobody could hear. Put the
reference into its spoken form first, then normalize both sides the same way:

```python
spoken_ref = normalize_for_tts("السعر 45000 ريال")
normalize_asr(spoken_ref, CER_NORM)                      # 'السعر خمسه واربعون الف ريال'
normalize_asr("السعر خمسه واربعون الف ريال", CER_NORM)   # 'السعر خمسه واربعون الف ريال'
```

The other direction also works: leave the reference in digits and turn the
transcript's number words into digits with `spoken_numbers_to_digits`. Pick one
direction per evaluation and record it. Words on both sides keeps every spoken
word in the score; digits on both sides forgives a number read in a different
but valid way.

### Before phone alignment

A forced aligner places the phones of a text on audio, and it can only place
phones for words that were said. Phonemize the spoken form, never the written
one: the tokenizer passes a `3` through as the character `3`, which is not a
phone, and the syllables the speaker produced are left with nothing to align to.

```python
from arbtok.tokenizer import Sentence

text = normalize_for_tts(transcript_of_record)
phones = Sentence(text).ipa
```

## Where next

- [api.md](api.md), signatures
- [advanced.md](advanced.md), internals and recipes

---
[← Advanced](advanced.md) · [Home](../README.md) · [API →](api.md)
