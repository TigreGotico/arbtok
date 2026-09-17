"""A token that is only partly Latin is split into its script runs.

`is_latin` is true of any token CONTAINING a Latin letter, so a mixed token went whole
to `transliterate`, which cannot look it up. الـcharger read `ʃaːdʒa`: the guest word off
the donor's rules rather than its lexicon, and the Arabic article dropped from the output
altogether. Written with a space, ال charger was always correct — so two spellings of the
same phrase disagreed, and the glued one silently lost a word.

The invariant is that they agree. It is stronger than pinning either reading, because it
stays true when the guest word's own reading changes.
"""
import pytest

pytest.importorskip("orthography2ipa", reason="the pipeline needs orthography2ipa")


def _plugin(lang="ar"):
    from arbtok.plugin import ArbtokG2PPlugin
    return ArbtokG2PPlugin(lang=lang, diacritize=True, nativize=True, pausal=True)


@pytest.mark.parametrize("glued, spaced", [
    ("الـcharger", "ال charger"),
    ("الـprinter", "ال printer"),
    ("الـcar", "ال car"),
    ("الـmeeting", "ال meeting"),
    ("الcharger", "ال charger"),          # no tatweel, same shape
])
def test_a_glued_article_reads_as_a_spaced_one(glued, spaced):
    p = _plugin()
    assert p.transcribe(glued) == p.transcribe(spaced)


def test_the_article_is_not_dropped():
    """The word that used to vanish."""
    got = _plugin().transcribe("الـcharger")
    assert got.split()[0].endswith("al"), got
    assert len(got.split()) == 2, got


def test_the_guest_keeps_its_lexicon_reading():
    """It read `ʃaːdʒa` off the rules; the donor lexicon says ʃaːrdʒar."""
    p = _plugin()
    assert "ʃaːrdʒar" in p.transcribe("الـcharger")


@pytest.mark.parametrize("text, unchanged", [
    ("عندي meeting مع manager", "ˈʕindiː miːtink ˈmaʕ manidʒar"),
    ("الموديل", "almuːˈdiːl"),
    ("charger", "ʃaːrdʒar"),
    ("الكتاب", "alkiˈtaːb"),
])
def test_unmixed_tokens_are_untouched(text, unchanged):
    """A pure-Arabic or pure-Latin token never reaches the split."""
    assert _plugin().transcribe(text) == unchanged
