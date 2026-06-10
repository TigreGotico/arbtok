# arbtok — backlog

## Open issues
None open.

## Gaps
- [ ] No `README.md` (only an in-module docstring in `arbtok/__init__.py`).
- [ ] No packaging metadata (`pyproject.toml`/`setup.py`); cannot be pip-installed or published. Only `requirements.txt`.
- [ ] No `.github/workflows/` — missing standard gh-automations CI (build-tests, coverage, license-check, release_workflow, publish_stable).
- [ ] Vendored `pyarabic` and `tashkeel` are undeclared third-party code with their own licensing (`arbtok/tashkeel/LICENSE`, `SOURCE`); needs license-check reconciliation if published.
- [ ] `tests/__ini__.py` is misspelled (`__init__.py`).
- [ ] Tashkeel diacritizer model is flagged as needing replacement with a better model.

## Code TODOs
- [ ] `arbtok/dialects.py:2` — extend with per-dialect phoneme realizations.
- [ ] `arbtok/dialects.py:72` — LLM-generated, needs native-speaker validation.
- [ ] `arbtok/dialects.py:107` — clarify irregular entries.
- [ ] `arbtok/tokenizer.py:421` — improve `CharToken.ipa` to avoid mistakes upstream.
- [ ] `arbtok/tokenizer.py:485` — handle whitespace removal better.
- [ ] `arbtok/tashkeel/__init__.py:1` — evaluate diacritizers; need a better model.
- [ ] `arbtok/test.py:4` — gold cases are LLM-generated, awaiting human review.
- [ ] `arbtok/test.py` — numerous `# TODO - failing` gold cases (wasl, hamza, sun-letter shadda, cross-word sandhi, alif maqsura, loanword clusters, multiword assimilation).
