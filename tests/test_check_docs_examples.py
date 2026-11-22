"""The docs example checker fails every page that states an output it cannot prove."""

import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "check_docs_examples.py"
FENCE = "```"

CLEAN = """print(1 + 1)
# 2
x = 3
x * 2  # 6
for i in range(2):
    print(i)
# 0
# 1
"""

FAULTS = {
    "wrong print output": "print(1 + 1)\n# 3\n",
    "block does not parse": "x = (\n",
    "claimless statement raises": "1 / 0\n",
    "wrong trailing output in a py fence": "x = 2\nx  # 3\n",
    "wrong exception text": "int('a')  # ValueError: nope\n",
    "comment under an assignment": "x = 1 + 1\n# 3\n",
    "trailing comment on an assignment": "x = 2  # 3\n",
    "comment under an if block": "if True:\n    print(2)\n# 2\n",
    "output stated on a default object repr": "object()  # 'WRONG'\n",
}


def run(tmp_path: Path, code: str, lang: str = "python") -> int:
    page = tmp_path / "page.md"
    page.write_text(f"# Page\n\n{FENCE}{lang}\n{code}{FENCE}\n", encoding="utf-8")
    result = subprocess.run([sys.executable, str(SCRIPT), str(page)], capture_output=True, text=True)
    return result.returncode


def test_clean_page_passes(tmp_path):
    assert run(tmp_path, CLEAN) == 0


@pytest.mark.parametrize("name", FAULTS)
def test_fault_fails(tmp_path, name):
    lang = "py" if "py fence" in name else "python"
    assert run(tmp_path, FAULTS[name], lang) == 1
