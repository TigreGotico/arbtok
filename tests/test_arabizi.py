"""Arabizi — Arabic in Latin letters — routed back to the Arabic pipeline.

Covers the three things the input path (roadmap C3) has to get right:

* the digit map and the reverse-transliteration to an Arabic skeleton
  (:func:`arbtok.arabizi.to_arabic_skeleton`);
* the conservative detection gate (:func:`arbtok.arabizi.is_arabizi`) — a
  digit-guttural or an explicit hint routes to Arabizi, and a genuine English
  embed (``meeting``, ``manager``, ``email``) is *not* dragged onto that path;
* the plugin wiring — an Arabizi run reads as Arabic, an English run still
  nativises, and the two are told apart by the gate.
"""
import pytest

from arbtok.arabizi import (
    ARABIZI_DIGITS,
    is_arabizi,
    to_arabic_skeleton,
)
from arbtok.plugin import ArbtokG2PPlugin


class TestDigitMap:
    """Yaghan (2008) p. 44 — the digit-for-guttural core."""

    @pytest.mark.parametrize("digit,letter", [
        ("2", "ء"), ("3", "ع"), ("5", "خ"),
        ("6", "ط"), ("7", "ح"), ("8", "غ"), ("9", "ق"),
    ])
    def test_digit_gutturals(self, digit, letter):
        assert ARABIZI_DIGITS[digit] == letter

    def test_seven_is_haa(self):
        # 7abibi → ح-skeleton, never an English word
        assert to_arabic_skeleton("7abibi").startswith("ح")

    def test_three_is_ayn(self):
        assert to_arabic_skeleton("3ala").startswith("ع")

    def test_five_is_khaa(self):
        assert "خ" in to_arabic_skeleton("5alid")

    def test_nine_is_qaf(self):
        assert "ق" in to_arabic_skeleton("9alb")

    def test_prime_promotes_ayn_to_ghayn(self):
        assert to_arabic_skeleton("3'ali").startswith("غ")

    def test_prime_promotes_taa_to_zaa(self):
        assert "ظ" in to_arabic_skeleton("6'arf")


class TestDigraphs:
    def test_kh(self):
        assert to_arabic_skeleton("khubz").startswith("خ")

    def test_gh(self):
        assert to_arabic_skeleton("ghali").startswith("غ")

    def test_sh(self):
        assert to_arabic_skeleton("shams").startswith("ش")

    def test_th(self):
        assert to_arabic_skeleton("thani").startswith("ث")

    def test_dh(self):
        assert to_arabic_skeleton("dhahab").startswith("ذ")

    def test_doubled_vowel_is_a_mater(self):
        # sooq → س-و-ق (the oo is one long wāw, not two)
        assert to_arabic_skeleton("sooq") == "سوق"


class TestEmphatics:
    """Capitalised S D T Z mark the emphatic series."""

    def test_capital_t_is_emphatic(self):
        assert "ط" in to_arabic_skeleton("Tawil")

    def test_capital_s_is_emphatic(self):
        assert to_arabic_skeleton("Sabah").startswith("ص")

    def test_lower_s_is_plain_siin(self):
        assert to_arabic_skeleton("salam").startswith("س")


class TestSkeleton:
    """Reverse-transliteration produces an unpointed-ish Arabic skeleton."""

    def test_word_initial_vowel_gets_alif(self):
        assert to_arabic_skeleton("ana").startswith("ا")

    def test_vowels_are_written_not_dropped(self):
        # Arabizi spells vowels: habibi keeps its shape, not هبب
        assert to_arabic_skeleton("habibi") == "هابيب"

    def test_punctuation_stripped(self):
        assert "?" not in to_arabic_skeleton("shlonak?")
        assert "؟" not in to_arabic_skeleton("shlonak?")

    def test_produces_arabic_script(self):
        skel = to_arabic_skeleton("sh7alek")
        assert all("؀" <= c <= "ۿ" for c in skel)


class TestDetectionGate:
    """Conservative v1 gate: digit-guttural OR explicit hint, nothing else."""

    @pytest.mark.parametrize("word", ["3ala", "7abibi", "sh7alek", "wein7", "a2ollak"])
    def test_digit_guttural_is_arabizi(self, word):
        assert is_arabizi(word)

    @pytest.mark.parametrize("word", ["meeting", "manager", "email", "google",
                                      "computer", "internet"])
    def test_english_embed_is_not_arabizi(self, word):
        # THE false-positive guard: an English loan must NOT be read as Arabizi,
        # or its nativisation silently breaks.
        assert not is_arabizi(word)

    def test_all_alpha_arabizi_not_sniffed_without_hint(self):
        # habibi/inta are Arabizi but carry no digit; v1 refuses the guess.
        assert not is_arabizi("habibi")
        assert not is_arabizi("inta")

    def test_explicit_hint_true_forces_arabizi(self):
        assert is_arabizi("habibi", hint=True)

    def test_explicit_hint_false_forbids_arabizi(self):
        assert not is_arabizi("3ala", hint=False)


class TestPluginWiring:
    """The path in the real plugin."""

    def test_arabizi_reads_as_arabic_not_english(self):
        p = ArbtokG2PPlugin(lang="ar-EG")
        out = p.transcribe("7abibi")
        # read as حبيبي: the ḥāʾ the ``7`` spells, not the English letter-salad
        assert out.startswith("ħ")
        # the raw Arabizi digit never survives into the IPA
        assert "7" not in out
        # not the naive "read the Latin letters" failure ('ˈ7abibi')
        assert "abibi" not in out

    def test_english_embed_still_nativises(self):
        # digit-free English embed stays on the loanword path (Cairene ǧīm [ɡ])
        p = ArbtokG2PPlugin(lang="ar-EG")
        out = p.transcribe("عِنْدِي meeting مَعَ manager")
        assert "miːtinɡ" in out
        # donor English reading is non-rhotic (o2i #846): manager's final /r/
        # is absent from the donor IPA, so the Cairene reflex is manaɡa.
        assert "manaɡa" in out

    def test_hint_true_routes_all_alpha_to_arabizi(self):
        p = ArbtokG2PPlugin(lang="ar-EG")
        forced = p.transcribe("habibi", arabizi=True)
        loan = p.transcribe("habibi", arabizi=False)
        assert forced != loan

    def test_arabizi_disabled_falls_back_to_loan_path(self):
        p = ArbtokG2PPlugin(lang="ar-EG", arabizi=False)
        # with the path off, 3ala is NOT reverse-transliterated
        assert "ʕ" not in p.transcribe("3ala")

    @pytest.mark.parametrize("lect", [
        "ar-EG", "ar-SA-x-najd", "ar-x-levantine", "ar-KW", "ar-MA", "ar",
    ])
    def test_six_lects_produce_arabic_ipa(self, lect):
        # integration: a digit-guttural Arabizi run yields a non-empty IPA string
        # that carries the ʕayn it spells, across the lect families.
        p = ArbtokG2PPlugin(lang=lect)
        out = p.transcribe("3andi maw3ed")
        assert out
        assert "ʕ" in out
