"""Build the bundled numbering-plan table from Google's libphonenumber metadata.

    python scripts/build_phone_plans.py arbtok/data/phone_plans.json

It reads ``resources/PhoneNumberMetadata.xml`` at the release tag named in ``TAG`` and
writes, for each region of :data:`arbtok.textnorm.ARAB_PHONE_REGIONS`, its country
code, its national prefix and, for each number type the region defines, the pattern a
national significant number matches and the lengths it may have. The ``source`` object
records the URL, the tag and the sha256 of the metadata read, so the table can be
rebuilt and checked. A pattern that Python's ``re`` cannot compile stops the build.
"""
import hashlib
import json
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET

from arbtok.textnorm import ARAB_PHONE_REGIONS

TAG = "v9.0.39"
URL = f"https://raw.githubusercontent.com/google/libphonenumber/{TAG}/resources/PhoneNumberMetadata.xml"
TYPES = {"fixedLine": "fixed_line", "mobile": "mobile", "tollFree": "toll_free", "premiumRate": "premium_rate",
         "sharedCost": "shared_cost", "uan": "uan", "voip": "voip"}


def lengths(spec: str):
    """``[8-10],12`` as ``[8, 9, 10, 12]``."""
    out = set()
    for part in spec.split(","):
        span = re.fullmatch(r"\[(\d+)-(\d+)\]", part)
        out.update(range(int(span.group(1)), int(span.group(2)) + 1) if span else [int(part)])
    return sorted(out)


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
            types[name] = {"national_number_pattern": pattern, "possible_lengths": lengths(national)}
        regions[region] = {"country_code": int(territory.get("countryCode")),
                           "national_prefix": territory.get("nationalPrefix") or "", "types": types}
    table = {"source": {"url": URL, "tag": TAG, "sha256": hashlib.sha256(xml).hexdigest()}, "regions": regions}
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(table, f, ensure_ascii=False, indent=1, sort_keys=True)
        f.write("\n")


if __name__ == "__main__":
    build(sys.argv[1])
