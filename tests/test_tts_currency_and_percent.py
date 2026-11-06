"""Amounts the voice-agent configuration reads: a number beside a currency code is an amount
and is spoken, ر.س after a number is said ريال, and a percent sign written before its
number is read as one written after it.

English Wikipedia's "Saudi riyal" gives the riyal's symbol as "SAR, SR, ر.س"
(https://en.wikipedia.org/w/index.php?oldid=1252604873)."""
import pytest

from arbtok.textnorm import TtsNorm, normalize_for_tts
from tests.voice_agent import VOICE_AGENT


@pytest.mark.parametrize("text, said", [
    ("السعر 500 SAR", "السعر خمس مئة SAR"),
    ("السعر SAR 500", "السعر SAR خمس مئة"),
    ("السعر 50 SR", "السعر خمسين SR"),
    ("المبلغ 100 USD تقريبا", "المبلغ مئة USD تقريبا"),
])
def test_a_number_beside_a_currency_code_is_an_amount(text, said):
    assert normalize_for_tts(text, "ar", VOICE_AGENT) == said


@pytest.mark.parametrize("text", ["MG 5", "5 Series", "BMW 520 جاهزة", "عندنا GV 70"])
def test_a_number_beside_a_name_is_still_kept(text):
    assert normalize_for_tts(text, "ar", VOICE_AGENT) == text


@pytest.mark.parametrize("text, said", [
    ("المجموع 1,200 ر.س", "المجموع ألف ومئتين ريال"),
    ("المجموع 1200ر.س", "المجموع ألف ومئتين ريال"),
    ("المجموع ١٢٠٠ ر.س", "المجموع ألف ومئتين ريال"),
    ("المجموع 1,200 ر. س", "المجموع ألف ومئتين ريال"),
    ("المجموع 1,200 ر.س.", "المجموع ألف ومئتين ريال."),
    ("المجموع 1,200 ر.س، شامل الضريبة", "المجموع ألف ومئتين ريال، شامل الضريبة"),
])
def test_the_riyal_sign_after_a_number_is_said(text, said):
    assert normalize_for_tts(text, "ar", VOICE_AGENT) == said


@pytest.mark.parametrize("text", ["العملة ر.س", "ر.س هي العملة"])
def test_the_riyal_sign_with_no_number_before_it_is_left(text):
    assert normalize_for_tts(text, "ar", VOICE_AGENT) == text


def test_without_the_cardinals_the_riyal_sign_is_left():
    off = TtsNorm(spoken_forms=False, canonical_unicode=False)
    assert normalize_for_tts("المجموع 1,200 ر.س", "ar", off) == "المجموع 1,200 ر.س"


@pytest.mark.parametrize("text, said", [
    ("%10 خصم على الكاش", "عشرة في المئة خصم على الكاش"),
    ("خصم %4.5 فقط", "خصم أربعة فاصلة خمسة في المئة فقط"),
    ("٪١٥ خصم", "خمسة عشر في المئة خصم"),
    ("خصم 15% و%20 على القطع", "خصم خمسة عشر في المئة وعشرين في المئة على القطع"),
    ("خصم 15%", "خصم خمسة عشر في المئة"),
])
def test_a_percent_sign_before_its_number_is_read(text, said):
    assert normalize_for_tts(text, "ar", VOICE_AGENT) == said


@pytest.mark.parametrize("text", ["a%20b", "الرابط example.com/a%20b", "الرابط ?q=%20", "%20b", "%2F",
                                  "الرابط /x/%20/y"])
def test_percent_encoding_is_left(text):
    assert "في المئة" not in normalize_for_tts(text, "ar", VOICE_AGENT)
