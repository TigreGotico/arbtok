"""No digit reaches the phoneme map, and Arabizi digits are still gutturals.

Arabic normalization verbalizes every number, including the ones the word-by-word
pass misses — a number glued to punctuation, Arabic-Indic/Persian digits, and a
stray percent sign. The one thing it must *not* touch is an Arabizi token, where a
digit glued to Latin letters spells a guttural (``3`` = ع, ``7`` = ح); those stay
for the Arabizi transcription path. The two guarantees are tested together so
neither can be traded away for the other.
"""
import re

import pytest

from arbtok.util import normalize
from arbtok.plugin import ArbtokG2PPlugin

# Any ASCII, Arabic-Indic, or Persian digit.
_ANY_DIGIT = re.compile(r"[0-9٠-٩۰-۹]")


class TestNoDigitLeak:
    """A digit character must never survive into the normalized dialog."""

    def test_number_glued_to_arabic_comma_is_verbalized(self):
        # "10،" — the number carries the Arabic comma, so the word pass skips it.
        out = normalize("مخرج 10، صاحبه", "ar")
        assert not _ANY_DIGIT.search(out)
        assert "عشر" in out

    def test_arabic_indic_digits_are_verbalized(self):
        out = normalize("الموديل ٢٠٢٤", "ar")
        assert not _ANY_DIGIT.search(out)
        # 2024 spelled out, no Arabic-Indic digit left behind
        assert "ألف" in out or "ألفان" in out or "ألفين" in out

    def test_persian_digits_are_verbalized(self):
        out = normalize("سنة ۱۹۹۹", "ar")
        assert not _ANY_DIGIT.search(out)

    def test_standalone_number_regression(self):
        # The ordinary case still works after the residual pass.
        out = normalize("عندي 3 سيارات", "ar")
        assert not _ANY_DIGIT.search(out)
        assert "ثلاث" in out  # ثلاث / ثلاثة

    @pytest.mark.parametrize("text", [
        "مخرج 10، صاحبه",
        "الموديل ٢٠٢٤",
        "خصم 30%",
        "عندي 3 سيارات",
        "السنة ١٩٤٥ كانت",
        "رقم 7 و 8",
        "الغرفة 100%",
        "درجة الحرارة 25 مئوية",
    ])
    def test_no_bare_digit_token_across_batch(self, text):
        # The strong invariant: not one output token is a bare digit run, and no
        # digit character survives anywhere in the string.
        out = normalize(text, "ar")
        assert not _ANY_DIGIT.search(out), f"digit leaked: {out!r}"
        assert not any(re.fullmatch(r"[0-9٠-٩۰-۹]+", tok) for tok in out.split())


class TestPercentIsSpoken:
    """A percent sign is pronounced, never left as a bare symbol."""

    def test_ascii_percent_is_verbalized(self):
        out = normalize("خصم 30%", "ar")
        assert not _ANY_DIGIT.search(out)
        assert "ثلاثون" in out
        assert "%" not in out
        assert "بالمئة" in out

    def test_arabic_percent_sign_is_verbalized(self):
        out = normalize("خصم ٣٠٪", "ar")
        assert not _ANY_DIGIT.search(out)
        assert "٪" not in out
        assert "بالمئة" in out


class TestArabiziDigitsPreserved:
    """The counter-guarantee: an Arabizi digit is a guttural, not a number."""

    def test_three_stays_ayn(self):
        # 3 = ع → the ʕayn must appear in the IPA, and never as the number "three".
        p = ArbtokG2PPlugin(lang="ar-EG")
        out = p.transcribe("3ala")
        assert "ʕ" in out
        assert not _ANY_DIGIT.search(out)

    def test_seven_stays_haa(self):
        # 7 = ح → the ħāʾ, not the number "seven".
        p = ArbtokG2PPlugin(lang="ar-EG")
        out = p.transcribe("7abibi")
        assert out.startswith("ħ")
        assert not _ANY_DIGIT.search(out)
