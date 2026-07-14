"""A Latin-script word in an Arabic sentence."""

import pytest

from arbtok.plugin import ArbtokG2PPlugin
from arbtok.translit import is_latin, nativize, transliterate

NAJD = "ar-SA-x-najd"


class TestIsLatin:
    def test_latin(self):
        assert is_latin("meeting")

    def test_arabic(self):
        assert not is_latin("كتاب")


class TestNativization:
    """Alhoody (2019), Qassimi (= Najdi) — the variety we transcribe."""

    def test_p_becomes_b(self):
        """English /p/ has no Arabic counterpart (§5.1)."""
        assert transliterate("pizza", NAJD) == "bizza"

    def test_v_becomes_f(self):
        assert transliterate("video", NAJD).startswith("f")

    def test_ng_is_ng_when_not_before_k(self):
        """§5.1.10: /ŋ/ → [nɡ] elsewhere — meeting ends [-inɡ]."""
        assert transliterate("meeting", NAJD) == "miːtinɡ"

    def test_ng_is_n_before_k(self):
        assert nativize("ŋk", NAJD) == "nk"

    def test_donor_stress_is_not_carried_over(self):
        """Stress is re-derived by the matrix rule, not imported."""
        assert "ˈ" not in nativize("ˈmiːtɪŋ", NAJD)

    def test_a_symbol_outside_the_inventory_is_refused(self):
        """MSA declares /q/ and /dʒ/ and no /ɡ/ — /ɡ/ is a Gulf reflex of qāf. So
        the Najdi reading of `meeting` is not an MSA reading of anything."""
        assert transliterate("meeting", "ar") is None
        assert transliterate("meeting", NAJD) is not None


class TestInSentence:
    def test_a_loanword_is_read_not_spelled(self):
        """Left to the engine, `meeting` comes back as `meeˈting` — not IPA."""
        out = ArbtokG2PPlugin(lang=NAJD, diacritize=True).transcribe(
            "عندي meeting الساعة")
        assert out == "ˈʕindiː miːtinɡ aˈssaːʕa"

    def test_the_latin_letters_do_not_survive_into_the_ipa(self):
        """`meeting` used to come back as `meeˈting`: the letters themselves, which
        are not phonemes and have no embedding in a TTS frontend."""
        out = ArbtokG2PPlugin(lang=NAJD, diacritize=True).transcribe("Google مفيد")
        assert "G" not in out and "oo" not in out

    def test_the_arabic_around_it_is_unaffected(self):
        p = ArbtokG2PPlugin(lang=NAJD, diacritize=True)
        assert p.transcribe("أحب pizza") == "ˈʔaħab bizza"
