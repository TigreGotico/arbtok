"""The diacritizer proposes; the lattice disposes.

Restoring tashkeel is a statistical problem, so it belongs to a model. But a
model asked to write into a word can write anything — including a letter that
was never there and a reading the orthography does not license. Downstream that
is undetectable: the phonemizer will faithfully transcribe the hallucination.

arbtok is the one library that knows about both the diacritizer and the
orthography2ipa lattice, so it is where the guards live.
"""
import pytest

from arbtok.diacritize import LatticeDiacritizer, strip_marks
from arbtok.plugin import ArbtokG2PPlugin


@pytest.fixture(scope="module")
def diacritizer():
    return LatticeDiacritizer()


# ─── guard 1: only act where the writing is silent ──────────────────────

def test_already_diacritized_words_are_left_alone(diacritizer):
    """A human's tashkeel is evidence. A model must never overwrite it."""
    marked = "كِتَاب جَمِيل"
    assert diacritizer.diacritize(marked) == marked


def test_a_bare_skeleton_is_diacritized(diacritizer):
    out = diacritizer.diacritize("كتب")
    assert out != "كتب"
    assert strip_marks(out) == "كتب"


def test_partially_marked_text_only_gains_what_it_lacks(diacritizer):
    """The marked word survives verbatim; the bare one is filled in."""
    out = diacritizer.diacritize("كِتَاب جميل")
    assert out.split(" ")[0] == "كِتَاب"
    assert out.split(" ")[1] != "جميل"


# ─── guard 2: the skeleton is inviolable ────────────────────────────────

def test_a_rewritten_letter_is_repaired_not_discarded(diacritizer, monkeypatch):
    """A diacritizer MARKS a word; it does not rewrite it.

    When it rewrites one anyway the marks are usually still right, so they are
    kept and our letter is put back. Rejecting the whole proposal would throw
    away good marks along with the bad letter.
    """
    class Rewriting:
        def diacritize(self, text):
            return "كَلْب"  # right marks, wrong middle letter (ت -> ل)

    monkeypatch.setattr(diacritizer, "_diacritizer", Rewriting())
    # The marks survive; the skeleton is ours.
    assert diacritizer.diacritize_word("كتب") == "كَتْب"
    assert "كتب" in diacritizer.repaired


def test_an_unrepairable_proposal_is_refused(diacritizer, monkeypatch):
    """A proposal whose skeleton does not even align cannot be repaired."""
    class Lengthening:
        def diacritize(self, text):
            return "كَتَبَاتٌ"  # more letters than we handed over

    monkeypatch.setattr(diacritizer, "_diacritizer", Lengthening())
    assert diacritizer.diacritize_word("كتب") == "كتب"
    assert "كتب" in diacritizer.rejected


def test_the_alef_madda_class_is_repaired(diacritizer):
    """The real case: rawi rewrites آ to أ, destroying the long /aː/.

    آبد is /ʔaːbid/; the model returns أَبْد, which is /ʔabd/ — the length is
    simply gone. Repairing keeps the marks and puts the madda back.
    """
    out = diacritizer.diacritize_word("آبد")
    assert out.startswith("آ"), out


def test_a_restored_hamza_is_allowed(diacritizer, monkeypatch):
    """The rawi models legitimately restore a hamza carrier and the dagger-alef.

    That is a documented widening of the task — they fix real, inconsistently
    spelled input — so a change confined to those letters is not a
    hallucination.
    """
    class Restoring:
        def diacritize(self, text):
            return "أَمِير"  # bare alif ا restored to the hamza carrier أ

    monkeypatch.setattr(diacritizer, "_diacritizer", Restoring())
    assert diacritizer.diacritize_word("امير") == "أَمِير"


# ─── guard 3: the result must be licensed ───────────────────────────────

def test_an_unlicensed_proposal_is_refused(diacritizer, monkeypatch):
    """A mark sequence the orthography does not admit is not an answer."""
    class Unlicensed:
        def diacritize(self, text):
            return "كتبـ࣠"  # a mark the ar grapheme table does not map

    monkeypatch.setattr(diacritizer, "_diacritizer", Unlicensed())
    out = diacritizer.diacritize_word("كتب")
    assert out == "كتب"


# ─── end to end ─────────────────────────────────────────────────────────

def test_the_plugin_transcribes_undiacritized_text():
    """The whole point: bare Arabic in, IPA out, with the marks restored."""
    plugin = ArbtokG2PPlugin()
    assert plugin.transcribe("كتب الولد الدرس") == "katab alwalad addaras"


def test_diacritization_can_be_turned_off():
    """Without it, a bare skeleton has no vowels to read — and it shows."""
    assert ArbtokG2PPlugin(diacritize=False).transcribe("كتب") == "ktb"


def test_waqf_is_applied_by_default():
    """The models restore the full iʿrāb; speech does not pronounce it."""
    out = LatticeDiacritizer(waqf=True).diacritize("كتب الدرس")
    full = LatticeDiacritizer(waqf=False).diacritize("كتب الدرس")
    assert out != full
    assert full.endswith("َ") or full.endswith("ُ") or full.endswith("ِ")
