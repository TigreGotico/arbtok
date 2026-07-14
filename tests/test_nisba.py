"""The nisba's shadda, which the writing does not print."""

import pytest

from arbtok.diacritize import LatticeDiacritizer
from arbtok.nisba import restore_nisba
from arbtok.plugin import ArbtokG2PPlugin


@pytest.fixture(scope="module")
def ipa():
    d = LatticeDiacritizer(lang="ar")
    engine = ArbtokG2PPlugin(lang="ar", diacritize=False)
    return lambda w: engine.transcribe_word(d.diacritize_word(w)).replace("ˈ", "")


class TestRestoreNisba:
    def test_bare_final_ya_takes_the_suffix(self):
        """⟨ـي⟩ → ⟨ـِيّ⟩: the suffix is /-ijj/ (Wright I §249)."""
        assert restore_nisba("مصري") == "مصرِيّ"

    def test_a_printed_shadda_is_left_alone(self):
        """The writing has already spoken; it is not ours to respell."""
        assert restore_nisba("عَرَبِيّ") == "عَرَبِيّ"

    def test_a_sukun_before_the_ya_is_overwritten(self):
        """A sukun there is not a reading — it is the model missing the suffix."""
        assert restore_nisba("مِصْرْي").endswith("رِيّ")

    def test_defective_participle_is_not_a_nisba(self):
        """بَاقِي is فاعِل of a III-weak root: the yāʾ is the radical, so /iː/."""
        for word in ("باقي", "ثاني", "جاري"):
            assert restore_nisba(word) == word

    def test_function_words_are_not_nisbas(self):
        assert restore_nisba("الذي") == "الذي"

    def test_a_word_without_a_final_ya_is_untouched(self):
        assert restore_nisba("كتاب") == "كتاب"


class TestTranscription:
    def test_nisba_reads_as_ijj(self, ipa):
        assert ipa("مصري") == "misˤrijj"
        assert ipa("آشوري") == "ʔaːʃuːrijj"

    def test_defective_participle_keeps_its_long_vowel(self, ipa):
        assert ipa("باقي") == "baːqiː"
        assert ipa("ثاني") == "θaːniː"

    @pytest.mark.xfail(strict=True, reason=(
        "a borrowed final /iː/ is a lexical fact about a word never built from an "
        "Arabic root; no rule reaches it, and a caller-supplied lexicon is the fix"))
    def test_loanword_keeps_its_long_vowel(self, ipa):
        assert ipa("تاكسي") == "taːksiː"
