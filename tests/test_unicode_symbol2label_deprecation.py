"""arbtok.unicode_symbol2label is deprecated for one stable cycle.

Importing it warns once, names the removal release, the next major version, and
points at the caller's line. A fresh interpreter runs each import, because a
module warns only on its first import.
"""
import json
import subprocess
import sys
import warnings

from arbtok.version import VERSION_MAJOR

REMOVAL = f"{VERSION_MAJOR + 1}.0.0"

CALLER = """
import json
import warnings

with warnings.catch_warnings(record=True) as caught:
    warnings.simplefilter("always")
    from arbtok.unicode_symbol2label import UNICODE_SYMBOL_TO_LABEL
print(json.dumps([[w.category.__name__, str(w.message), w.filename]
                  for w in caught if issubclass(w.category, DeprecationWarning)]))
"""


def test_import_warns_with_removal_version_at_caller(tmp_path):
    caller = tmp_path / "caller.py"
    caller.write_text(CALLER, encoding="utf-8")
    result = subprocess.run([sys.executable, str(caller)], capture_output=True,
                            text=True, check=True)
    caught = json.loads(result.stdout.splitlines()[-1])
    assert len(caught) == 1, caught
    category, message, filename = caught[0]
    assert category == "DeprecationWarning"
    assert message.startswith("arbtok.unicode_symbol2label is deprecated")
    assert f"removed in arbtok {REMOVAL}." in message
    assert "Nothing replaces it" in message
    assert filename == str(caller)


def test_the_table_still_imports():
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        from arbtok.unicode_symbol2label import UNICODE_SYMBOL_TO_LABEL
    assert UNICODE_SYMBOL_TO_LABEL["؟"] == "علامة استفهام عربية"


def test_the_plugin_path_does_not_import_it():
    code = ("import sys, arbtok, arbtok.plugin, arbtok.o2i_plugins; "
            "print('arbtok.unicode_symbol2label' in sys.modules)")
    result = subprocess.run([sys.executable, "-c", code], capture_output=True,
                            text=True, check=True)
    assert result.stdout.strip() == "False"
