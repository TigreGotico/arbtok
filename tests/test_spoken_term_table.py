"""The spoken-sa table: terms Saudi agents say, spelled as two recognizers agree to write them."""
import pytest

from arbtok import textnorm
from arbtok.textnorm import CER_CANONICAL, normalize_asr

SAME = [
    ("لو حاب تجرب سيارة MINI", "لو حاب تجرب سيارة ميني"),
    ("عن أسعار وMINI", "عن اسعار وميني"),
    ("بخيار M Sport Package", "بخيار ام سبورت بكج"),
    ("عليها Package الصيانة", "عليها بكج الصيانة"),
    ("متوفر عندنا 3 SERIES", "متوفر عندنا الفئة الثالثة"),
    ("متوفر عندنا BMW 3 SERIES", "متوفر عندنا بي ام دبليو الفية الثالثة"),
]
DIFFERENT = [
    ("لو حاب تجرب سيارة MINI", "لو حاب تجرب سيارة جيني"),
    ("متوفر عندنا 3 SERIES", "متوفر عندنا الفئة الخامسة"),
    ("بخيار M Sport Package", "بخيار ام سبورت"),
]


@pytest.mark.parametrize("written, heard", SAME, ids=[w for w, _ in SAME])
def test_a_spoken_term_and_its_latin_name_score_zero(written, heard):
    assert normalize_asr(written, CER_CANONICAL) == normalize_asr(heard, CER_CANONICAL)


@pytest.mark.parametrize("written, heard", DIFFERENT, ids=[f"{w} / {h}" for w, h in DIFFERENT])
def test_a_different_term_still_counts(written, heard):
    assert normalize_asr(written, CER_CANONICAL) != normalize_asr(heard, CER_CANONICAL)


def test_every_row_names_its_evidence():
    rows = textnorm._term_rows("spoken-sa")
    assert rows and all(r["basis"] == "two recognizers agree" and int(r["agreed_rows"]) >= 50 for r in rows)


def test_the_table_reads_both_ways():
    assert textnorm.bundled_asr_lexicon("spoken-sa")["ميني"] == "MINI"
    assert textnorm.bundled_tts_lexicon("spoken-sa")["MINI"] == "ميني"
