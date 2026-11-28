"""The loom sandhi fragment gives the IR arbtok's cross-word forms."""
import json
from pathlib import Path

import pytest
from orthography2ipa.ir.compiler import build_ir
from orthography2ipa.ir.interpreter import Interpreter

FRAGMENT = json.loads((Path(__file__).resolve().parent.parent / "arbtok" / "data" / "loom" / "sandhi.json")
                      .read_text(encoding="utf-8"))


@pytest.mark.parametrize("text", ["جَدِيد وْ قَدِيم", "جَدِيد وْ"])
def test_the_bare_conjunction_carries_no_stress(text):
    # arbtok writes the bare conjunction unstressed; the loom file must match it.
    plain = Interpreter(build_ir("abv-BH")).transcribe(text).split()
    words = Interpreter(build_ir("abv-BH", fragments=[FRAGMENT])).transcribe(text).split()
    assert plain[1] == "ˈw"
    assert words[1] == "w"
    assert words[0] == plain[0]
