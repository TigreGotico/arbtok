"""arbtok ships no voice-agent preset: a caller composes one from TtsNorm's options, as
the README shows, and the README's example says what it prints."""
import re
from pathlib import Path

import pytest

import arbtok.textnorm as textnorm
from tests.voice_agent import VOICE_AGENT

README = Path(__file__).parent.parent / "README.md"


def test_the_old_preset_name_is_gone():
    with pytest.raises(AttributeError):
        textnorm.KSA_VOICE_AGENT
    with pytest.raises(ImportError):
        from arbtok.textnorm import KSA_VOICE_AGENT  # noqa: F401


def test_the_readme_example_prints_what_it_documents():
    section = README.read_text(encoding="utf-8").split("### Numbers a voice agent reads out", 1)[1]
    code = re.search(r"```python\n(.*?)```", section, re.S).group(1)
    namespace = {}
    exec(code, namespace)
    assert namespace["VOICE_AGENT"] == VOICE_AGENT
    calls = re.findall(r"^(normalize_for_tts\(.*\))\n# (.*)$", code, re.M)
    assert calls
    for call, documented in calls:
        assert repr(eval(call, namespace)) == documented
