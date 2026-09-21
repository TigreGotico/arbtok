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
| `CER_NORM` | `CER_STRIP` with letter forms unified and a word-final bare hamza dropped |
| `CER_MARKS_FIRST` | references that carry diacritics or transcriber markup: markup dropped, every mark dropped, then punctuation |
| `CER_NORM_MARKS_FIRST` | `CER_MARKS_FIRST` with letter forms unified and a word-final bare hamza dropped |
| `INTELLIGIBILITY_GATE` | intelligibility of synthetic speech: marks dropped, letter forms unified, everything outside the Arabic block blanked |

```python
from arbtok.textnorm import CER_NORM, TRUTH_CHECK

normalize_asr("مَرْحَبًا بِكُمْ، يا أَحْمَد!", TRUTH_CHECK)
# 'مرحبا بكم، يا احمد!'

ref_tokens = normalize_asr(reference, CER_NORM).split()
hyp_tokens = normalize_asr(hypothesis, CER_NORM).split()
```

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
`spoken_numbers_to_digits`.

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
| `spoken_numbers_to_digits` | number words become digits |
| `join_dictated_digits` | seven or more single digits in a row become one run |
| `unify_alef` | آ أ إ ٱ become ا |
| `unify_ta_marbuta` | ة becomes ه |
| `unify_alef_maqsura` | ى becomes ي |
| `unify_hamza_carriers` | ئ becomes ي, ؤ becomes و |
| `fold_digits` | Arabic-Indic and Extended Arabic-Indic digits become ASCII |
| `fold_case` | `str.lower()` |
| `arabic_block_only` | blank everything outside U+0600–U+06FF |
| `blank_punctuation` | blank what is neither a word character nor whitespace |
| `drop_word_final_hamza` | drop a bare ء that ends a word |
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
attached.

`spell_out_codes=True` reads what the lexicon did not claim and is written in
capitals and digits with at least one capital, such as `X5` or `GV70`, one
character at a time. A number on its own is not a code and goes to the number
rules; a lowercase word is left for the loanword path.

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
names and the ten digit words, pointed. Each is the English pronunciation from
the bundled donor lexicon, carried into Arabic by `arbtok.translit.nativize`,
with the glottal onset Arabic gives a word that starts with a vowel; a test
holds every row to that. Two consequences of the standard inventory are worth
knowing before reading a registration plate or a VIN aloud: it has no /eː/, so
A and E come out alike and so do G and J, and it has no /tʃ/, so H ends in /ʃ/.
Put your own spellings for those letters in the lexicon when they must differ.

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

A unit symbol is read only where it follows a number, because `in` and `m` in running
text are not units. `spoken_forms` does that for Arabic from the same CLDR table
(`cldr_units()`): `المسافة 5 km` becomes `المسافة خمسة كيلومتر`. The unit takes its
CLDR display name; it is not inflected for the number before it.

### Numbers a voice agent reads out

A reply holds prices, phone numbers and booking references, and a plain
"numbers to words" pass reads all of them as quantities. These rules tell them
apart. `KSA_VOICE_AGENT` turns them on with the numbering plans of every Arab
League member:

```python
from arbtok.textnorm import KSA_VOICE_AGENT

normalize_for_tts("السعر النهائي 355,000 ريال", "ar", KSA_VOICE_AGENT)
# 'السعر النهائي ثلاث مئة وخمسة وخمسين ألف ريال'
normalize_for_tts("خلني أسجل رقمك 0551234567", "ar", KSA_VOICE_AGENT)
# 'خلني أسجل رقمك صفر خمسة خمسة واحد اثنين ثلاثة أربعة خمسة ستة سبعة'
normalize_for_tts("اتصل على 010 01234567", "ar", KSA_VOICE_AGENT)
# 'اتصل على صفر واحد صفر صفر واحد اثنين ثلاثة أربعة خمسة ستة سبعة'
normalize_for_tts("كود العرض 4471 صالح", "ar", KSA_VOICE_AGENT)
# 'كود العرض أربعة أربعة سبعة واحد صالح'
normalize_for_tts("نسبة التمويل 4.5%", "ar", KSA_VOICE_AGENT)
# 'نسبة التمويل أربعة فاصلة خمسة في المئة'
```

Every rule of `normalize_for_tts`, in the order they run; a lexicon is applied after
`strip_controls`:

| Flag | Rule |
| --- | --- |
| `strip_controls` | drop zero-width and bidirectional control characters |
| `spell_out_codes` | read `X5`-shaped codes character by character from `spelled_codes()`, after the lexicon |
| `speak_percent` | `4.5%` becomes `4.5 في المئة`, then the number is spoken |
| `keep_code_digits` | up to four digits beside a Latin word, `MG 5` or `7 Series`, belong to the name and are kept from every number rule |
| `phone_shapes` | patterns of a phone number in running text; a match is read digit by digit |
| `phone_regions` | ISO 3166-1 regions whose numbering plans are recognised; a valid number of one of them, written with `+` or `00` and the country code, with the region's trunk prefix, or after an identifier word, is read digit by digit |
| `long_digit_runs` | eleven or more digits are a reference, read digit by digit |
| `phone_prefixes` | patterns a bare digit run matches whole when it is a phone number; a run written with `+` is one too |
| `identifier_words` | words after which a number is a reference: `الكود 4729`, `برقم الحجز 3401`. A proclitic may be attached and one other word may stand between |
| `cardinal_numbers` | speak Arabic-Indic and ASCII numbers as cardinals ahead of `spoken_forms`, so the next three flags apply |
| `leave_unspeakable_numbers` | a number that cannot be spoken is left as written and the rest is still read; otherwise the error is raised |
| `oblique_numbers` | cardinals in the oblique case, the one connected speech uses |
| `space_fused_hundreds` | in those cardinals `ثلاثمئة` becomes `ثلاث مئة`; a synthesizer keeps the spaced form and garbles the fused one |
| `dialect_numbers` | the cardinals and the digit-by-digit readings take the words the lect `lang` names uses, asked of the number parser under that lect's ISO 639-3 code |
| `number_forms` | your own words for values, `{100: "مية"}`, over the lect's or instead of them; set with `with_number_forms` |
| `spoken_forms` | dates, times, numbers and units as words in `lang`; on by default |
| `canonical_unicode` | tatweel dropped, NFC, shadda before its vowel, the spellings of مائة settled; on by default |

### Numbers in the words a lect actually uses

A number spoken in Standard Arabic is not what a lect says: where the literary
reading is `خمسة عشر` for 15, Jidda and Abu Dhabi both say `خمسطعش`, and where it
is `ثلاثمئة` Jidda says `تلتمية` and Abu Dhabi `ثلاثمية`. `dialect_numbers` asks
the number parser for the lect's own words, under that lect's ISO 639-3 code.

```python
normalize_for_tts("السعر 350 ريال", "ar", KSA_VOICE_AGENT)
# 'السعر ثلاث مئة وخمسين ريال'
normalize_for_tts("السعر 350 ريال", "ar-SA-x-hejaz", KSA_VOICE_AGENT, dialect_numbers=True)
# 'السعر تلت مية وخمسين ريال'
```

The words are the parser's, quoted there from a published grammar with its page,
and it composes the number the same way whichever lect it speaks: a lect differs
in its words and not in its arithmetic. It has words for Hijazi `acw`, Gulf `afb`
and Cairene Egyptian `arz`. What arbtok adds is the translation from the tag you
passed to that code, `arbtok.lect_code`, which walks the orthography2ipa parent
chain, so Kuwaiti and Qatari take the Gulf code from the node they descend from.
**A lect the parser has no cited words for keeps the literary ones**, Najdi
included: no source has been read for it, and a form no source gives is not
written.

**The numeral is all this changes.** Arabic makes the counted noun agree with the
number, and the dialects covered agree in the same direction: two to ten take a
plural noun, eleven upwards take a singular, and three to ten drop their final
vowel before a noun that follows. None of that happens here, because the text around
the number is the author's and this rewrites a numeral in place. Write the noun the
way the number you passed in requires.

The flag is off everywhere by default, so a number keeps its literary words
unless you ask for a lect. `with_number_forms` gives your own words for values,
with or without a lect under them, and `describe()` names the parser and digests
your words, so a run records which words it used.

A price and a phone number cannot be told apart by length, so nothing here
guesses from length alone below eleven digits: a phone number is known by its
prefix or by the word before it. `موديل 4729` stays a quantity because `موديل`
is not an identifier word. `ARAB_PHONE_REGIONS` and `IDENTIFIER_WORDS` are plain
tuples; pass your own for another vocabulary. `phone_shapes` and `phone_prefixes`
take your own patterns for numbers the bundled plans do not cover; no preset sets
them.

`phone_regions` names the regions whose numbering plans are read, and
`ARAB_PHONE_REGIONS` lists the 22 members of the Arab League. The plans are bundled
in `arbtok/data/phone_plans.json`: for each region its country code, its trunk
prefix and, for each number type, the pattern and lengths of a national number. The
table is built by `scripts/build_phone_plans.py` from `resources/PhoneNumberMetadata.xml`
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

The rules from `speak_percent` to `identifier_words`, and `dialect_numbers` and
`number_forms` with them, write Arabic words, so they raise `ValueError` for a
`lang` that is not Arabic.

`KSA_VOICE_AGENT` leaves `spoken_forms` and `canonical_unicode` off, because it
speaks the numbers itself. `TtsNorm.describe()` gives the string to record, as
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
