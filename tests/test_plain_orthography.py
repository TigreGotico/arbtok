"""``plain_orthography`` writes the output the way speech-recognition transcripts are
written: no harakat, alef without hamza, ڤ as ف."""
import dataclasses

import pytest

from arbtok.textnorm import TtsNorm, normalize_for_tts
from tests.voice_agent import VOICE_AGENT

def plain():
    return dataclasses.replace(VOICE_AGENT, plain_orthography=True, spell_out_codes=True)


SAID = [
    ("السعر 1450 ريال", "السعر الف واربع مئة وخمسين ريال"),
    ("عندنا 4 ألوان", "عندنا اربعة الوان"),
    ("سيارتك BMW جاهزة", "سيارتك بي ام دبليو جاهزة"),
    ("إن شاء الله", "ان شاء الله"),
    ("رينج روڤر", "رينج روفر"),
    ("مَرْحَبًا", "مرحبا"),
    ("الـسيارة", "السيارة"),
    # ة, ى, ؤ and ئ are what the transcripts keep
    ("مدينة على مسؤول رئيس", "مدينة على مسؤول رئيس"),
]


@pytest.mark.parametrize("written, said", SAID, ids=[w for w, _ in SAID])
def test_the_output_is_in_the_transcripts_orthography(written, said):
    assert normalize_for_tts(written, "ar", plain()) == said


def test_off_the_output_keeps_its_hamza_and_marks():
    out = normalize_for_tts("سيارتك BMW بسعر 1450 ريال", "ar", dataclasses.replace(VOICE_AGENT, spell_out_codes=True))
    assert "ألف" in out and "ِ" in out


def test_it_is_named_by_describe():
    assert "plain_orthography" in TtsNorm(plain_orthography=True).describe()


@pytest.mark.parametrize("decomposed", ["\u0627\u0654\u0644\u0641", "\u0627\u0655\u0646", "\u0627\u0653\u062e\u0631"],
                         ids=["hamza above", "hamza below", "madda"])
def test_a_decomposed_alef_loses_its_hamza_without_canonical_unicode(decomposed):
    """The voice agent runs with canonical_unicode off, so a hamza written as a combining
    mark after ا reaches this rule unfolded."""
    out = normalize_for_tts(decomposed, "ar", plain())
    assert not plain().canonical_unicode
    assert out == "ا" + decomposed[2:], [hex(ord(c)) for c in out]


@pytest.mark.parametrize("decomposed, plain_form", [
    ("\u0645\u0633\u0648\u0654\u0648\u0644 \u0633\u0627\u064a\u0654\u0642", "مسؤول سائق"),
    ("\u0628\u0631\u064a\u0654", "برئ"),
], ids=["waw and ya", "ya"])
def test_a_decomposed_hamza_on_waw_or_ya_is_kept(decomposed, plain_form):
    """ؤ and ئ are what the transcripts keep, written decomposed as much as composed."""
    assert normalize_for_tts(decomposed, "ar", plain()) == plain_form


@pytest.mark.parametrize("written, plain_form", [
    ("ذَٰلِكَ ٱلْكِتَٰبُ", "ذلك الكتاب"),
    ("وَأَقِيمُوا۟ ٱلصَّلَوٰةَ وَءَاتُوا۟ ٱلزَّكَوٰةَ", "واقيموا الصلاة وءاتوا الزكاة"),
    ("هَٰذَا", "هذا"),
    ("بِسْمِ ٱللَّهِ ٱلرَّحْمَٰنِ", "بسم الله الرحمن"),
    ("عَلَىٰ", "على"),
    ("لَا رَيْبَ ۛ فِيهِ ۛ", "لا ريب  فيه "),
    ("\u06de ٱلْحَمْدُ \u06dd", " الحمد "),
])
def test_quranic_spelling_is_written_plainly(written, plain_form):
    assert normalize_for_tts(written, "ar", plain()) == plain_form
