"""A phone number of any Arab League member is read digit by digit under VOICE_AGENT,
written the way a person in that country writes it, and a date, a price or a count is not.

The number of each country is libphonenumber's example mobile number for its region,
written out in the international and the national format libphonenumber prints for it."""
import dataclasses
import json
import subprocess
import sys
from pathlib import Path

import pytest

from arbtok import textnorm
from arbtok.textnorm import ARAB_PHONE_REGIONS, TtsNorm, normalize_for_tts
from tests.voice_agent import VOICE_AGENT

WORDS = dict(zip("0123456789٠١٢٣٤٥٦٧٨٩", ("صفر", "واحد", "اثنين", "ثلاثة", "أربعة", "خمسة",
                                          "ستة", "سبعة", "ثمانية", "تسعة") * 2))
NO_REGIONS = dataclasses.replace(VOICE_AGENT, phone_regions=())


def one_by_one(written):
    return " ".join(WORDS[c] for c in written if c in WORDS)


INTERNATIONAL = [
    ("SA", "+966 51 234 5678"),     # libphonenumber example number, MOBILE, SA
    ("AE", "+971 50 123 4567"),     # libphonenumber example number, MOBILE, AE
    ("KW", "+965 500 12345"),       # libphonenumber example number, MOBILE, KW
    ("QA", "+974 3312 3456"),       # libphonenumber example number, MOBILE, QA
    ("BH", "+973 3600 1234"),       # libphonenumber example number, MOBILE, BH
    ("OM", "+968 9212 3456"),       # libphonenumber example number, MOBILE, OM
    ("YE", "+967 712 345 678"),     # libphonenumber example number, MOBILE, YE
    ("IQ", "+964 791 234 5678"),    # libphonenumber example number, MOBILE, IQ
    ("JO", "+962 7 9012 3456"),     # libphonenumber example number, MOBILE, JO
    ("LB", "+961 71 123 456"),      # libphonenumber example number, MOBILE, LB
    ("SY", "+963 944 567 890"),     # libphonenumber example number, MOBILE, SY
    ("PS", "+970 599 123 456"),     # libphonenumber example number, MOBILE, PS
    ("EG", "+20 10 01234567"),      # libphonenumber example number, MOBILE, EG
    ("SD", "+249 91 123 1234"),     # libphonenumber example number, MOBILE, SD
    ("LY", "+218 91-2345678"),      # libphonenumber example number, MOBILE, LY
    ("TN", "+216 20 123 456"),      # libphonenumber example number, MOBILE, TN
    ("DZ", "+213 551 23 45 67"),    # libphonenumber example number, MOBILE, DZ
    ("MA", "+212 6 50 12 34 56"),   # libphonenumber example number, MOBILE, MA
    ("MR", "+222 22 12 34 56"),     # libphonenumber example number, MOBILE, MR
    ("SO", "+252 7 1123456"),       # libphonenumber example number, MOBILE, SO
    ("DJ", "+253 77 83 10 01"),     # libphonenumber example number, MOBILE, DJ
    ("KM", "+269 321 23 45"),       # libphonenumber example number, MOBILE, KM
]

# The same numbers dialled from abroad with 00 in place of the plus.
DIALLED = [
    ("SA", "00966 51 234 5678"),    # libphonenumber example number, MOBILE, SA
    ("AE", "00971 50 123 4567"),    # libphonenumber example number, MOBILE, AE
    ("KW", "00965 500 12345"),      # libphonenumber example number, MOBILE, KW
    ("QA", "00974 3312 3456"),      # libphonenumber example number, MOBILE, QA
    ("BH", "00973 3600 1234"),      # libphonenumber example number, MOBILE, BH
    ("OM", "00968 9212 3456"),      # libphonenumber example number, MOBILE, OM
    ("YE", "00967 712 345 678"),    # libphonenumber example number, MOBILE, YE
    ("IQ", "00964 791 234 5678"),   # libphonenumber example number, MOBILE, IQ
    ("JO", "00962 7 9012 3456"),    # libphonenumber example number, MOBILE, JO
    ("LB", "00961 71 123 456"),     # libphonenumber example number, MOBILE, LB
    ("SY", "00963 944 567 890"),    # libphonenumber example number, MOBILE, SY
    ("PS", "00970 599 123 456"),    # libphonenumber example number, MOBILE, PS
    ("EG", "0020 10 01234567"),     # libphonenumber example number, MOBILE, EG
    ("SD", "00249 91 123 1234"),    # libphonenumber example number, MOBILE, SD
    ("LY", "00218 91-2345678"),     # libphonenumber example number, MOBILE, LY
    ("TN", "00216 20 123 456"),     # libphonenumber example number, MOBILE, TN
    ("DZ", "00213 551 23 45 67"),   # libphonenumber example number, MOBILE, DZ
    ("MA", "00212 6 50 12 34 56"),  # libphonenumber example number, MOBILE, MA
    ("MR", "00222 22 12 34 56"),    # libphonenumber example number, MOBILE, MR
    ("SO", "00252 7 1123456"),      # libphonenumber example number, MOBILE, SO
    ("DJ", "00253 77 83 10 01"),    # libphonenumber example number, MOBILE, DJ
    ("KM", "00269 321 23 45"),      # libphonenumber example number, MOBILE, KM
]

# The national format, where it starts with the region's trunk prefix 0.
NATIONAL = [
    ("SA", "051 234 5678"),         # libphonenumber example number, MOBILE, SA
    ("AE", "050 123 4567"),         # libphonenumber example number, MOBILE, AE
    ("YE", "0712 345 678"),         # libphonenumber example number, MOBILE, YE
    ("IQ", "0791 234 5678"),        # libphonenumber example number, MOBILE, IQ
    ("JO", "07 9012 3456"),         # libphonenumber example number, MOBILE, JO
    ("SY", "0944 567 890"),         # libphonenumber example number, MOBILE, SY
    ("PS", "0599 123 456"),         # libphonenumber example number, MOBILE, PS
    ("EG", "010 01234567"),         # libphonenumber example number, MOBILE, EG
    ("SD", "091 123 1234"),         # libphonenumber example number, MOBILE, SD
    ("LY", "091-2345678"),          # libphonenumber example number, MOBILE, LY
    ("DZ", "0551 23 45 67"),        # libphonenumber example number, MOBILE, DZ
    ("MA", "06 50 12 34 56"),       # libphonenumber example number, MOBILE, MA
]

# The national format with no trunk prefix in it: Kuwait, Qatar, Bahrain, Oman, Tunisia,
# Mauritania, Djibouti and the Comoros have none, and Lebanon and Somalia write their
# mobiles without it. Bare, such a number is a quantity; after a word that names it a
# phone number, it is one.
NATIONAL_BARE = [
    ("KW", "500 12345"),            # libphonenumber example number, MOBILE, KW
    ("QA", "3312 3456"),            # libphonenumber example number, MOBILE, QA
    ("BH", "3600 1234"),            # libphonenumber example number, MOBILE, BH
    ("OM", "9212 3456"),            # libphonenumber example number, MOBILE, OM
    ("LB", "71 123 456"),           # libphonenumber example number, MOBILE, LB
    ("TN", "20 123 456"),           # libphonenumber example number, MOBILE, TN
    ("MR", "22 12 34 56"),          # libphonenumber example number, MOBILE, MR
    ("SO", "7 1123456"),            # libphonenumber example number, MOBILE, SO
    ("DJ", "77 83 10 01"),          # libphonenumber example number, MOBILE, DJ
    ("KM", "321 23 45"),            # libphonenumber example number, MOBILE, KM
]


def test_every_arab_league_member_is_covered():
    assert set(ARAB_PHONE_REGIONS) == {r for r, _ in INTERNATIONAL} == {r for r, _ in DIALLED}
    assert len(ARAB_PHONE_REGIONS) == 22
    assert set(ARAB_PHONE_REGIONS) == {r for r, _ in NATIONAL} | {r for r, _ in NATIONAL_BARE}


def _ids(cases):
    return [region for region, _ in cases]


@pytest.mark.parametrize("region, written", INTERNATIONAL + DIALLED + NATIONAL,
                         ids=_ids(INTERNATIONAL) + [r + "-00" for r in _ids(DIALLED)]
                         + [r + "-national" for r in _ids(NATIONAL)])
def test_a_phone_number_is_read_digit_by_digit(region, written):
    said = normalize_for_tts(f"اتصل على {written} اليوم", "ar", VOICE_AGENT)
    assert said == f"اتصل على {one_by_one(written)} اليوم"


@pytest.mark.parametrize("region, written", NATIONAL_BARE, ids=_ids(NATIONAL_BARE))
def test_a_number_without_a_trunk_prefix_is_read_after_a_word_that_names_it(region, written):
    assert normalize_for_tts(f"رقمي {written}", "ar", VOICE_AGENT) == f"رقمي {one_by_one(written)}"


def test_a_bare_kuwaiti_mobile_stays_a_number_and_after_raqmi_is_read_out():
    # libphonenumber example number, MOBILE, KW
    assert normalize_for_tts("50012345", "ar", VOICE_AGENT) \
        == normalize_for_tts("50012345", "ar", NO_REGIONS)
    assert "صفر" not in normalize_for_tts("50012345", "ar", VOICE_AGENT)
    assert normalize_for_tts("رقمي 50012345", "ar", VOICE_AGENT) == "رقمي " + one_by_one("50012345")


def test_arabic_indic_digits_are_read_as_ascii_ones_are():
    # libphonenumber example number, MOBILE, EG, in Arabic-Indic digits
    said = normalize_for_tts("اتصل على ٠١٠ ٠١٢٣٤٥٦٧ اليوم", "ar", VOICE_AGENT)
    assert said == f"اتصل على {one_by_one('01001234567')} اليوم"


def test_a_number_in_the_other_digit_script_is_not_taken_into_a_phone_number():
    # libphonenumber example number, MOBILE, EG, its last digit written in Arabic-Indic: the
    # ASCII digits are one short of a number and the digit after them is another number.
    written = "اتصل على +20 10 0123456 ٧ اليوم"
    assert normalize_for_tts(written, "ar", VOICE_AGENT) == normalize_for_tts(written, "ar", NO_REGIONS)


def test_a_number_after_the_phone_number_is_not_taken_into_it():
    # libphonenumber example number, MOBILE, EG
    said = normalize_for_tts("اتصل على 010 01234567 3 مرات", "ar", VOICE_AGENT)
    assert said == f"اتصل على {one_by_one('01001234567')} ثلاثة مرات"


@pytest.mark.parametrize("written", [
    "بتاريخ 05-06-2024",
    "بتاريخ 05/06/2024",
    "بتاريخ 5 6 2024",
    "بتاريخ 2024-06-05",
    "الموعد الساعة 10:30",
    "في عام 2024",
    "السعر 1 500 000 ريال",
    "السعر 12,000 ريال",
    "عندي 15 سيارة",
    "السعر 50012345 ريال",
])
def test_a_date_a_time_a_price_or_a_count_is_not_a_phone_number(written):
    said = normalize_for_tts(written, "ar", VOICE_AGENT)
    assert said == normalize_for_tts(written, "ar", NO_REGIONS)
    assert one_by_one(written) not in said


def test_phone_regions_speak_arabic():
    with pytest.raises(ValueError):
        normalize_for_tts("+20 10 01234567", "en", TtsNorm(phone_regions=ARAB_PHONE_REGIONS))


def test_the_bundled_plans_are_the_arab_league_members():
    plans = json.loads((Path(textnorm.__file__).parent / "data" / "phone_plans.json").read_text(encoding="utf-8"))
    assert set(plans["regions"]) == set(ARAB_PHONE_REGIONS)


@pytest.mark.parametrize("written", [
    "8001000341",       # Saudi toll-free, 800
    "920012345",        # Saudi unified number, 920
    "0112345678",       # Riyadh landline, 011 with the trunk 0
    "0138123456",       # Eastern Province landline, 013 with the trunk 0
])
def test_a_saudi_service_number_or_landline_is_read_digit_by_digit(written):
    assert normalize_for_tts(f"اتصل على {written}", "ar", VOICE_AGENT) == f"اتصل على {one_by_one(written)}"


def test_reading_a_phone_number_loads_no_phone_number_library():
    code = ("import sys, arbtok\n"
            "from arbtok.textnorm import normalize_for_tts\n"
            "from tests.voice_agent import VOICE_AGENT\n"
            "print(normalize_for_tts('اتصل على +20 10 01234567', 'ar', VOICE_AGENT))\n"
            "print(sorted(m for m in sys.modules if m.split('.')[0] in ('phonenumbers', 'phonenumberslite')))")
    said, loaded = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                                  check=True, cwd=Path(__file__).parent.parent).stdout.strip().split("\n")
    assert said == f"اتصل على {one_by_one('201001234567')}"
    assert loaded == "[]"


def test_a_description_names_the_phone_plans_it_read():
    """A regenerated table changes which runs are phone numbers, so the description of a
    config that reads them names the table by release and by its bytes."""
    import hashlib

    raw = (Path(textnorm.__file__).parent / "data" / "phone_plans.json").read_bytes()
    described = KSA_VOICE_AGENT.describe()
    assert json.loads(raw)["source"]["tag"] in described
    assert hashlib.sha256(raw).hexdigest()[:12] in described
    assert "phone plans" not in TtsNorm().describe()
