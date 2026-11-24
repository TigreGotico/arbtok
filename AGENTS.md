# arbtok: agent guide

`arbtok` is a Python package that turns Arabic text into IPA for Modern Standard Arabic, Classical Arabic and 30 or more regional varieties. It builds on the orthography2ipa lattice, and it adds a bundled diacritizer, dialect-aware fusion scoring, cross-word sandhi, loanword nativization and text normalization.

The documentation starts at [docs/index.md](docs/index.md).

## Repository map

| Path | Holds |
|---|---|
| `arbtok/plugin.py` | `ArbtokG2PPlugin`, the engine |
| `arbtok/diacritize.py`, `tashkeel.py`, `_ensemble.py`, `models/` | The diacritizer and the model that ships in the wheel |
| `arbtok/fusion.py`, `lattice.py` | The fusion scorer and the licensed readings |
| `arbtok/lexicon.py`, `dialect_lexicon.py`, `donor_lexicon.py` | The stem lexicon, the closed-class lexicon and the donor lexicons |
| `arbtok/dialects.py`, `translit.py`, `arabizi.py` | Lect resolution, loanword nativization and Arabizi input |
| `arbtok/textnorm.py`, `tokenizer.py`, `sandhi.py`, `waqf.py`, `stress.py` | Normalization, the token tree, cross-word rules, the pausal register and stress |
| `arbtok/o2i_plugins.py` | The orthography2ipa pipeline steps |
| `data/gold_code_switched/` | The code-switched gold set, one TSV per lect |
| `docs/`, `examples/`, `tests/`, `tools/` | Documentation, usage scripts, tests and the model build script |
| `scripts/` | Benchmarks, lexicon builders, `gold_code_switched.py` and `check_docs_examples.py` |

## Setup and tests

```bash
unset VIRTUAL_ENV
uv venv --python 3.11 .venv
uv pip install --python .venv/bin/python --prerelease=allow -e ".[test]"
.venv/bin/python -m pytest tests
```

Use uv, never pip. The suite drives the `espeak-ng` binary as a baseline, so install it first. The default stem lexicon comes from the Hugging Face Hub on the first call that diacritizes, and the Hub cache keeps it.

## Hard rules

1. The lattice owns the phonology. arbtok adds the diacritizer, the scorer, the sandhi and the nativization on top of the orthography2ipa spec of each lect ([dialects.md](docs/dialects.md#where-a-varietys-phonology-comes-from)).
2. A lexicon that cannot be read raises `LexiconUnavailable`. An uncached stem lexicon with no Hub access raises `ModelUnavailableError`. The plugin never reads the text without it ([tashkeel.md](docs/tashkeel.md#the-stem-lexicon)).
3. One lect never leaks state into another. `tests/test_lect_state_isolation.py` checks it ([dialects.md](docs/dialects.md)).
4. Every dependency floor in `pyproject.toml` carries its reason in a comment, and `tests/test_dependency_floors.py` checks the floors.
5. A pinned row of the code-switched gold keeps the `ipa` that the pipeline wrote. Never edit it by hand. `scripts/gold_code_switched.py validate` re-runs the pipeline ([gold-code-switched.md](docs/gold-code-switched.md#pipeline_status-pinned-vs-authentic-but-unpinned-rows)).
6. The benchmark figures are measurements of agreement with cited-rule reference output, not native-validated truth ([benchmarks.md](docs/benchmarks.md)).
7. A page example carries its output in a comment after two spaces on the same line or on the comment lines directly under it. `scripts/check_docs_examples.py` compares the two and fails a comment on a statement that shows no output.
8. The release workflow writes `arbtok/version.py` and `CHANGELOG.md`. Do not edit either.

## Before you push

1. Run the full test suite.
2. If you changed `README.md` or `docs/`, run the example check:

```bash
.venv/bin/python scripts/check_docs_examples.py README.md docs/*.md
```

3. If you changed the code-switched gold or the nativization tables, run `.venv/bin/python scripts/gold_code_switched.py validate`.
4. A page you add goes in the table of `docs/index.md`, gets an `agent-hint` comment after its H1, and ends with a footer that links the previous page, the index and the next page.

`dev` is the work branch and `master` is the stable branch.
