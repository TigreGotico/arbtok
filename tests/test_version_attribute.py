"""arbtok exposes its own version, sourced from arbtok/version.py.

Provenance in this fleet is recorded by pin and digest: a receipt that names an
installed package must be able to ask it what it is. Before this test existed,
`import arbtok; arbtok.__version__` raised AttributeError on a clean install of
the published wheel.
"""
import importlib.metadata
import re
from pathlib import Path

import arbtok


def _version_str_from_source():
    """Recompute VERSION_STR the same way arbtok/version.py does, independently."""
    import arbtok.version as version_module
    import inspect

    source = inspect.getsource(version_module)
    block = re.search(r"# START_VERSION_BLOCK(.*?)# END_VERSION_BLOCK", source, re.S).group(1)
    ns = {}
    exec(block, ns)  # noqa: S102 - trusted local source file, not user input

    version_str = f"{ns['VERSION_MAJOR']}.{ns['VERSION_MINOR']}.{ns['VERSION_BUILD']}"
    if ns["VERSION_ALPHA"]:
        version_str += f"a{ns['VERSION_ALPHA']}"
    return version_str


def test_arbtok_has_a_nonempty_version_string():
    assert isinstance(arbtok.__version__, str)
    assert arbtok.__version__


def test_version_matches_the_computed_block_in_version_py():
    assert arbtok.__version__ == _version_str_from_source()


def test_version_is_in_all():
    assert "__version__" in arbtok.__all__


def test_version_matches_the_installed_distribution_when_installed():
    try:
        dist = importlib.metadata.distribution("arbtok")
    except importlib.metadata.PackageNotFoundError:
        return  # not installed as a distribution in this environment; nothing to compare

    # A shared environment can register a different arbtok distribution while this
    # source tree is reached via PYTHONPATH rather than being the installed one;
    # only compare when the imported module actually lives under that distribution.
    dist_root = Path(dist.locate_file("")).resolve()
    module_path = Path(arbtok.__file__).resolve()
    if dist_root not in module_path.parents:
        return

    assert arbtok.__version__ == dist.version
