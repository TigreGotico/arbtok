"""A number written directly after a rank noun is spoken as the ordinal that agrees with
the noun in gender, by the cardinal pass, from 1 to 99. The nouns, their genders and the
source of each row are in arbtok/data/rank_ordinals.tsv.
Ryding, "A Reference Grammar of Modern Standard Arabic", ch. 15 section 2: ordinals
"follow the noun that they modify and agree with it in gender"; section 2.4: the tens
"agree in case and definiteness with the modified noun"."""
import pytest

from arbtok.textnorm import TtsNorm, normalize_for_tts
from tests.voice_agent import VOICE_AGENT

PLAIN = TtsNorm(cardinal_numbers=True)


@pytest.mark.parametrize("text, oblique, nominative", [
    ("الفئة 5", "الفئة الخامسة", "الفئة الخامسة"),
    ("الطابق 3", "الطابق الثالث", "الطابق الثالث"),
    ("والطابق 3", "والطابق الثالث", "والطابق الثالث"),
    ("للطابق 3", "للطابق الثالث", "للطابق الثالث"),
    ("بالمرتبة 1", "بالمرتبة الأولى", "بالمرتبة الأولى"),
    ("فالفصل 2", "فالفصل الثاني", "فالفصل الثاني"),
    ("المادة 12", "المادة الثانية عشرة", "المادة الثانية عشرة"),
    ("القرن 21", "القرن الحادي والعشرين", "القرن الحادي والعشرون"),
    ("الفئة ٧", "الفئة السابعة", "الفئة السابعة"),
    ("الفئة 27", "الفئة السابعة والعشرين", "الفئة السابعة والعشرون"),
    ("الطابق 85", "الطابق الخامس والثمانين", "الطابق الخامس والثمانون"),
    ("الطابق 86", "الطابق السادس والثمانين", "الطابق السادس والثمانون"),
    ("الفئة 28", "الفئة الثامنة والعشرين", "الفئة الثامنة والعشرون"),
    ("الطابق 99", "الطابق التاسع والتسعين", "الطابق التاسع والتسعون"),
    ("سيارة من الفئة 5 وفي الطابق 3.", "سيارة من الفئة الخامسة وفي الطابق الثالث.",
     "سيارة من الفئة الخامسة وفي الطابق الثالث."),
])
def test_a_number_after_a_rank_noun_is_an_agreeing_ordinal(text, oblique, nominative):
    assert normalize_for_tts(text, "ar", VOICE_AGENT) == oblique
    assert normalize_for_tts(text, "ar", PLAIN) == nominative


@pytest.mark.parametrize("text, oblique, nominative", [
    # a room number is not a rank
    ("غرفة 205", "غرفة مئتين وخمسة", "غرفة مئتان وخمسة"),
    ("الغرفة 205", "الغرفة مئتين وخمسة", "الغرفة مئتان وخمسة"),
    ("رقم 3", "رقم ثلاثة", "رقم ثلاثة"),
    # only a whole number
    ("الفئة 5.5", "الفئة خمسة فاصلة خمسة", "الفئة خمسة فاصلة خمسة"),
    # a count, with no rank noun before it
    ("3 طوابق", "ثلاثة طوابق", "ثلاثة طوابق"),
    # from 100 the parser has no feminine or oblique ordinal
    ("الطابق 100", "الطابق مئة", "الطابق مئة"),
    ("الطابق 250", "الطابق مئتين وخمسين", "الطابق مئتان وخمسون"),
    ("الطابق 0", "الطابق صفر", "الطابق صفر"),
    # a noun without its article
    ("طابق 3", "طابق ثلاثة", "طابق ثلاثة"),
    # already in words
    ("الفئة الخامسة", "الفئة الخامسة", "الفئة الخامسة"),
])
def test_other_numbers_stay_cardinals(text, oblique, nominative):
    assert normalize_for_tts(text, "ar", VOICE_AGENT) == oblique
    assert normalize_for_tts(text, "ar", PLAIN) == nominative


def test_a_number_beside_a_latin_name_is_kept():
    assert normalize_for_tts("5 Series", "ar", VOICE_AGENT) == "5 Series"


@pytest.mark.parametrize("text", ["الفئة 5", "الطابق 3", "المادة 12", "القرن 21", "الفئة ٧"])
def test_without_the_cardinal_pass_nothing_changes(text):
    off = TtsNorm(cardinal_numbers=False, spoken_forms=False, canonical_unicode=False)
    assert normalize_for_tts(text, "ar", off) == text


@pytest.mark.parametrize("text, spoken", [("الفئة 5", "الفئة خمسة"), ("الطابق 3", "الطابق ثلاثة"),
                                          ("القرن 21", "القرن واحد وعشرون")])
def test_the_default_spoken_forms_are_unchanged(text, spoken):
    assert normalize_for_tts(text, "ar", TtsNorm()) == spoken
