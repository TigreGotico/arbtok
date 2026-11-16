"""With the stem lexicon not cached and the Hub out of reach, the plugin raises
ModelUnavailableError naming the lexicon. It does not read the text without it."""
import os
import subprocess
import sys

import pytest

SCRIPT = """
from arbtok import ModelUnavailableError
from arbtok.plugin import ArbtokG2PPlugin
try:
    print("IPA", ArbtokG2PPlugin().transcribe("ذهب الولد إلى المدرسة"))
except ModelUnavailableError as exc:
    print("RAISED", isinstance(exc, ValueError), exc)
"""

HUB_VARIABLES = ("HF_HUB_OFFLINE", "HF_ENDPOINT", "HF_HUB_CACHE", "HUGGINGFACE_HUB_CACHE", "HF_DATASETS_OFFLINE")


@pytest.mark.timeout(600)
@pytest.mark.parametrize("network", [{"HF_HUB_OFFLINE": "1"}, {"HF_ENDPOINT": "http://127.0.0.1:9"}],
                         ids=["offline", "unreachable"])
def test_a_lexicon_that_cannot_be_fetched_raises(tmp_path, network):
    env = {k: v for k, v in os.environ.items() if k not in HUB_VARIABLES}
    env.update(HF_HOME=str(tmp_path / "hf"), XDG_CACHE_HOME=str(tmp_path / "cache"), **network)
    result = subprocess.run([sys.executable, "-c", SCRIPT], env=env, capture_output=True,
                            text=True, timeout=540)
    assert result.stdout.startswith("RAISED True "), result.stdout + result.stderr
    assert "TigreGotico/arabic-stem-lexicon" in result.stdout
    assert "'ar-stems.tsv'" in result.stdout
