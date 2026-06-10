# arbtok — agent guide

Experimental Arabic grapheme-to-IPA phonemizer and text normalizer for TTS front-ends, targeting Modern Standard Arabic (MSA). Authored by a non-Arabic-speaker; many phonological rules and the reference IPA test set are LLM-generated and unverified.

## Setup
No `pyproject.toml`/`setup.py` — install dependencies directly:

```
pip install -r requirements.txt
```

Runtime deps: `numpy`, `onnxruntime`, `quebra-frases`, `langcodes`, `ovos-number-parser>=0.4.0`, `ovos-date-parser>=0.6.4a1`.
The optional espeak comparison path needs the `espeak-ng` binary on PATH.
Tests additionally need `jiwer` and `phonnx` (`pip install -r tests/requirements.txt`).

## Test
```
pip install -r requirements.txt -r tests/requirements.txt
pytest tests/
```

`tests/test_ipa.py` parametrizes over `arbtok.test.ALL_TEST_CASES` (the gold set); many cases are marked failing in comments. `scripts/metrics.py` computes CER/WER against the gold set and can compare to espeak-ng output.

## Lint/Typecheck
None configured.

## Layout
- `arbtok/tokenizer.py` — core. `CharToken` / `WordToken` / `Sentence` classes; context-aware grapheme→IPA via linked-list neighbor pointers (definite-article assimilation, sun/moon letters, hamzat al-wasl, tanwin, idgham/iqlab). `Sentence(text).ipa` is the main entry.
- `arbtok/dialects.py` — `ArabicDialect` enum, `ARABIC_TO_IPA_CONSONANTS`, `VOWEL_MAP`, `DIACRITIC_TO_IPA`, `TANWIN_TO_IPA`, `WORD_EXCEPTIONS`. Only MSA populated.
- `arbtok/constants.py` — named Arabic grapheme constants for readability.
- `arbtok/tashkeel/` — `TashkeelDiacritizer`, a vendored port of libtashkeel running `model.onnx` to add missing diacritics. Includes `model.onnx` + id maps + its own LICENSE.
- `arbtok/espeak_wrapper.py` — `EspeakPhonemizer` shelling out to espeak-ng (baseline comparison only).
- `arbtok/num2words.py` — Arabic number-to-words with case/gender variants.
- `arbtok/util.py` — `normalize()`, date/time/unit/number normalization (uses ovos-number-parser / ovos-date-parser).
- `arbtok/pyarabic/` — vendored copy of the pyarabic library.
- `arbtok/test.py` — `ALL_TEST_CASES` gold IPA reference set (LLM-generated).
- `scripts/metrics.py` — benchmark harness (jiwer CER/WER).
- `tests/` — pytest suite; `lexicon.tsv`, `ar_test.txt` comparison data.

Not a plugin: no entry points, no console scripts, pure importable library.

## Conventions (org hard rules)
- Branches: `dev` (work) / `master` (stable). NEVER `main`.
- Never edit any `version.py`; gh-automations bumps semver from conventional-commit prefixes (`feat:`, `fix:`, `feat!:`).
- New repos private by default.
- Commit identity: JarbasAi <jarbasai@mailfence.com>.
- Reference `OpenVoiceOS/gh-automations` reusable workflows at `@dev`.
- No Neon / `neon-*` references.
- No meta-commentary in code/docs/commits (no history, no dates).
- CI is provided by `OpenVoiceOS/gh-automations`.

## Gotchas
- Accuracy is explicitly low and unverified; the gold set itself is LLM-generated. Do not treat passing tests as linguistic correctness.
- Many `ALL_TEST_CASES` entries are commented `# TODO - failing`; the suite is a target, not a pass baseline.
- `pyarabic` and `tashkeel` are vendored, not declared deps; edits stay in-tree.
- `tests/__ini__.py` is misspelled (should be `__init__.py`) — package import for the tests dir may be fragile.
- No packaging metadata at all: cannot `pip install .`; consumers import from a checkout.
