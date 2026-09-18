"""The plugin must import, not merely the package.

`import arbtok` succeeding says nothing about `arbtok.plugin`: a broken transitive
dependency breaks the second while the first and the distribution metadata stay healthy.
That is the shape the failure takes, and it is worth its own test because the consumer
that hits it is a multiprocessing pool initializer, which hangs rather than raising.
"""
import importlib.metadata as md


def test_the_distribution_reports_a_version():
    assert md.version("arbtok")


def test_the_plugin_module_imports():
    """Red on any environment where the ovos dependency chain is broken."""
    from arbtok.plugin import ArbtokG2PPlugin
    assert ArbtokG2PPlugin is not None


def test_the_modules_a_pool_initializer_imports_all_resolve():
    """These four are what the aligner's worker initializer imports."""
    failures = []
    for module, attr in (("arbtok.plugin", "ArbtokG2PPlugin"),
                         ("arbtok.lattice", "word_lattice"),
                         ("arbtok.tokenizer", "Sentence")):
        try:
            getattr(__import__(module, fromlist=[attr]), attr)
        except Exception as exc:
            failures.append(f"{module}.{attr}: {type(exc).__name__}: {exc}")
    assert not failures, "; ".join(failures)
