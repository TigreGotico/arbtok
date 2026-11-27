"""The loom contact fragment carries the cited loanword tables of the lect."""
import sys
from pathlib import Path

from orthography2ipa import resolve

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import loom_fragment  # noqa: E402


def test_the_egyptian_fragment_carries_the_egyptian_map():
    part = loom_fragment.fragment(resolve("ar-EG"))["contact"][0]
    # Hafez (1996), Watson (2002): Cairene ǧīm is a stop and the interdentals merge.
    assert (part["map"]["dʒ"], part["map"]["θ"], part["map"]["ð"]) == ("ɡ", "t", "d")
    assert part["map"]["ŋ"] == "nɡ"
    assert part["rewrite"] == [{"pattern": "ŋ(?=k)", "template": "n"}]
    assert part["words"]["model"] == "muːdiːl"
    assert part["donor"] == resolve("en-GB")


def test_the_donor_words_are_the_bundled_lexicon():
    part = loom_fragment.fragment(resolve("ar-EG"))["contact"][0]
    assert part["donor_words"]["a"] == "eɪ"
    assert len(part["donor_words"]) == 74318
