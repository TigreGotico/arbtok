"""The floors this package declares, and the reason each one is where it is.

A floor is a claim about what the installed dependency can do. It is worth a test
because the claim is invisible at import time: a resolver that satisfies an old floor
gives a package that imports cleanly, reports a healthy version, and quietly does less.
"""
import re
from pathlib import Path

import pytest

REQUIREMENTS = Path(__file__).resolve().parents[1] / "requirements.txt"


def _floors():
    floors = {}
    for line in REQUIREMENTS.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        match = re.fullmatch(r"([A-Za-z0-9._-]+)>=([0-9a-zA-Z.]+)", line)
        if match:
            floors[match.group(1).lower()] = match.group(2)
    return floors


def _as_tuple(version: str):
    """(major, minor, build, alpha); a release with no alpha sorts after every alpha of it."""
    head, _, alpha = version.partition("a")
    parts = [int(p) for p in head.split(".")]
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts) + (int(alpha) if alpha else float("inf"),)


def test_the_number_parser_floor_speaks_a_lects_cardinals():
    """``dialect_numbers`` asks the parser for a lect's own number words under the lect's
    ISO 639-3 code, and 0.21.0a1 is the release that has them. An older parser answers
    ``lang="acw"`` with the literary words and raises nothing, so the flag reads as on
    and changes no word."""
    assert _as_tuple(_floors()["ovos-number-parser"]) >= _as_tuple("0.21.0a1")


def test_the_number_parser_floor_reads_colloquial_teens():
    """Below 0.20.4a1 the parser read ten spellings of a contracted teen, all of the
    -اشر shape. A Saudi transcript writes them a dozen other ways, and
    ``spoken_numbers_to_digits`` left those as words."""
    assert _as_tuple(_floors()["ovos-number-parser"]) >= _as_tuple("0.20.4a1")


def test_the_number_parser_floor_gives_agreeing_ordinals():
    """A number after a rank noun is spoken with ``pronounce_ordinal`` in the noun's
    gender and the case of the cardinals. Below 0.22.0a1 the Arabic ordinals are
    masculine and nominative only, so الفئة 5 would read الفئة الخامس."""
    assert _as_tuple(_floors()["ovos-number-parser"]) >= _as_tuple("0.22.1a1")


def test_the_number_parser_floor_reads_water_as_water():
    """fix_asr_errors writes a recogniser's ماية and ميه as مية only inside a number.
    Below 0.22.7a1 the parser reads ميه as "hundred" anywhere, so "كباية ميه" would
    still reach the digits as 100."""
    assert _as_tuple(_floors()["ovos-number-parser"]) >= _as_tuple("0.22.7a1")


def test_the_number_parser_floor_leaves_a_homograph_as_written():
    """``spoken_numbers_to_digits`` hands the parser whole sentences. Below 0.22.10a1 it
    reads a word that is also an ordinary word as a number wherever it stands: "شربت مية
    باردة" (I drank cold water) becomes "شربت 100 باردة" and "الست جات" (the lady came)
    becomes "6 جات"."""
    assert _as_tuple(_floors()["ovos-number-parser"]) >= _as_tuple("0.22.10a1")


def test_every_floor_is_a_floor_and_not_a_pin_or_a_ceiling():
    """Floor pins only: a ceiling here becomes an unsatisfiable install downstream."""
    for line in REQUIREMENTS.read_text(encoding="utf-8").splitlines():
        line = line.split("#")[0].strip()
        if not line:
            continue
        assert "==" not in line and "<" not in line, line


@pytest.mark.parametrize("package", ["ovos-number-parser", "orthography2ipa", "ovos-utils", "ovos-config"])
def test_the_floors_that_carry_a_reason_are_still_declared(package):
    """Each of these was floored for a named reason, so a bump must not drop one."""
    assert package in _floors(), f"{package} lost its floor"


def test_the_version_comparison_orders_alphas_before_their_release():
    assert _as_tuple("0.20.4a1") < _as_tuple("0.20.4")
    assert _as_tuple("0.18.5a1") < _as_tuple("0.20.4a1")
    assert _as_tuple("0.20.10a1") > _as_tuple("0.20.9a1")
