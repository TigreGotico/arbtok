# arbtok

<!-- agent-hint
covers: what arbtok does, how to install it, a first transcription in a dialect and where each topic is documented
source: pyproject.toml, arbtok/__init__.py, arbtok/plugin.py, arbtok/diacritize.py
generated: no
verify: .venv/bin/python scripts/check_docs_examples.py README.md
see: docs/index.md, docs/quickstart.md, AGENTS.md
-->

arbtok turns Arabic text into IPA for Modern Standard Arabic, Classical Arabic and 30 or more regional varieties. It restores the missing short vowels with a dialect-aware diacritizer that ships in the wheel, and it builds on [orthography2ipa](https://github.com/TigreGotico/orthography2ipa). The documentation starts at [docs/index.md](docs/index.md).

Try it in your browser: [TigreGotico/arbtok on Hugging Face](https://huggingface.co/spaces/TigreGotico/arbtok).

arbtok covers Arabic lects only. No leader language (pt-PT, pt-BR, es-CO, fr-FR, it-IT, de-DE, nl-NL, da-DK, kab, hi-IN, bn-IN, mwr) is in scope. [orthography2ipa](https://github.com/TigreGotico/orthography2ipa) covers those languages.

## Install

```bash
pip install --pre arbtok
```

## Quickstart

```python
from arbtok.plugin import ArbtokG2PPlugin

bare = "ذهب الولد الى المدرسة"
print(ArbtokG2PPlugin(lang="ar").transcribe(bare))
# ˈðahab ˈalwalad ˈʔilaː lˈmudrasa
print(ArbtokG2PPlugin(lang="ar-TN").transcribe(bare))
# ˈðahab ˈalwalad ˈʔilɛː lˈmudrasa
```

## Documentation

| Page | Content |
|------|---------|
| [Quickstart](docs/quickstart.md) | Install, install notes, a first call in a dialect |
| [Overview](docs/overview.md) | What arbtok adds over orthography2ipa, the capabilities, the word lattice |
| [Diacritization](docs/tashkeel.md) | The bundled model and the stem lexicon |
| [Rawi-lattice fusion](docs/rawi-fusion.md) | Dialect-aware tashkeel |
| [Varieties](docs/dialects.md) | Language tags, per-lect phonology, loanword nativization |
| [Waqf](docs/waqf.md) | The register switch |
| [Arabizi input](docs/arabizi.md) | Latin-script Arabic with digit consonants |
| [Text normalization](docs/normalization.md) | Recognizer output and spoken forms, numbers for a voice agent |
| [Code-switched gold](docs/gold-code-switched.md) | The loanword gold set |
| [API reference](docs/api.md) | Every public name, the orthography2ipa pipeline steps |
| [Advanced](docs/advanced.md) | Token tree, espeak baseline, recipes |
| [Per-lect benchmarks](docs/benchmarks.md) | Scores, and the test suite's gold |

## License

Apache-2.0.
