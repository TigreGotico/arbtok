"""Build the bundled numbering-plan table from Google's libphonenumber metadata.

    python scripts/build_phone_plans.py arbtok/data/phone_plans.json

It reads ``resources/PhoneNumberMetadata.xml`` at the release tag named in ``TAG`` and
writes, for each region of :data:`arbtok.textnorm.ARAB_PHONE_REGIONS`, its country
code, its national prefix and, for each number type the region defines, the pattern a
national significant number matches and the lengths it may have. For each type it also
writes the digits a number of the type starts with, each with the lengths such a number
has: the first digit, and for the toll-free, shared-cost and unified types the first
three digits. They are read from the pattern by walking Python's parse of it, which is
internal to the interpreter, so it is done here and not at runtime. The ``source`` object
records the URL, the tag and the sha256 of the metadata read, so the table can be
rebuilt and checked. A pattern that Python's ``re`` cannot compile stops the build.
"""
import hashlib
import json
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET

try:
    from re import _constants as sre, _parser as sre_parse
except ImportError:  # Python 3.10
    import sre_constants as sre, sre_parse

from arbtok.textnorm import ARAB_PHONE_REGIONS

TAG = "v9.0.39"
URL = f"https://raw.githubusercontent.com/google/libphonenumber/{TAG}/resources/PhoneNumberMetadata.xml"
TYPES = {"fixedLine": "fixed_line", "mobile": "mobile", "tollFree": "toll_free", "premiumRate": "premium_rate",
         "sharedCost": "shared_cost", "uan": "uan", "voip": "voip"}
# Types whose first three digits say what they are: 800 and 920 in Saudi Arabia.
MARKED = ("toll_free", "shared_cost", "uan")
# The most digits a phone number has, the international limit of ITU-T E.164.
LONGEST_NUMBER = 15
DIGITS = "0123456789"


def lengths(spec: str):
    """``[8-10],12`` as ``[8, 9, 10, 12]``."""
    out = set()
    for part in spec.split(","):
        span = re.fullmatch(r"\[(\d+)-(\d+)\]", part)
        out.update(range(int(span.group(1)), int(span.group(2)) + 1) if span else [int(part)])
    return sorted(out)


def grow(items, states, n: int):
    """``states`` each extended by what the parsed pattern ``items`` can match next. A
    state is the first ``n`` digits matched and the count of all digits matched; no count
    passes :data:`LONGEST_NUMBER`, the E.164 limit."""
    for op, av in items:
        if op is sre.LITERAL:
            chars = {chr(av)}
        elif op is sre.IN:
            chars, negated = set(), False
            for kind, value in av:
                if kind is sre.LITERAL:
                    chars.add(chr(value))
                elif kind is sre.RANGE:
                    chars |= {chr(c) for c in range(value[0], value[1] + 1)}
                elif kind is sre.CATEGORY and value is sre.CATEGORY_DIGIT:
                    chars |= set(DIGITS)
                elif kind is sre.NEGATE:
                    negated = True
                else:
                    raise ValueError(f"a numbering pattern holds {kind}")
            chars = set(DIGITS) - chars if negated else chars & set(DIGITS)
        elif op is sre.SUBPATTERN:
            states = grow(av[-1], states, n)
            continue
        elif op is sre.BRANCH:
            states = set().union(*(grow(branch, states, n) for branch in av[1]))
            continue
        elif op in (sre.MAX_REPEAT, sre.MIN_REPEAT):
            low, high, sub = av
            out = set()
            for times in range(min(high, LONGEST_NUMBER) + 1):
                if times >= low:
                    out |= states
                states = grow(sub, states, n)
            states = out
            continue
        elif op is sre.AT:
            continue
        else:
            raise ValueError(f"a numbering pattern holds {op}")
        states = {(head + c if len(head) < n else head, count + 1)
                  for head, count in states if count < LONGEST_NUMBER for c in chars}
    return states


def starts(pattern: str, n: int, allowed) -> dict:
    """Every string of ``n`` digits a number that ``pattern`` matches can start with, and
    for each the lengths in ``allowed`` such a number has."""
    found: dict = {}
    for head, count in grow(sre_parse.parse(pattern), {("", 0)}, n):
        if len(head) == n:
            found.setdefault(head, set()).add(count)
    return {head: sorted(counts & set(allowed)) for head, counts in sorted(found.items())}


def build(out_path: str) -> None:
    xml = urllib.request.urlopen(URL, timeout=120).read()
    territories = {t.get("id"): t for t in ET.fromstring(xml).iter("territory")}
    regions = {}
    for region in ARAB_PHONE_REGIONS:
        territory = territories[region]
        types = {}
        for tag, name in TYPES.items():
            desc = territory.find(tag)
            if desc is None or desc.find("nationalNumberPattern") is None:
                continue
            national = desc.find("possibleLengths").get("national")
            if national == "-1":
                continue
            pattern = re.sub(r"\s", "", desc.find("nationalNumberPattern").text)
            try:
                re.compile(pattern)
            except re.error as error:
                sys.exit(f"{region} {name}: {pattern!r} does not compile: {error}")
            possible = lengths(national)
            types[name] = {"national_number_pattern": pattern, "possible_lengths": possible,
                           "leading_digits": starts(pattern, 1, possible)}
            if name in MARKED:
                types[name]["leading_three_digits"] = starts(pattern, 3, possible)
        regions[region] = {"country_code": int(territory.get("countryCode")),
                           "national_prefix": territory.get("nationalPrefix") or "", "types": types}
    table = {"source": {"url": URL, "tag": TAG, "sha256": hashlib.sha256(xml).hexdigest()}, "regions": regions}
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(table, f, ensure_ascii=False, indent=1, sort_keys=True)
        f.write("\n")


if __name__ == "__main__":
    build(sys.argv[1])
