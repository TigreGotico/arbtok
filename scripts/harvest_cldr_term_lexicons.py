#!/usr/bin/env python3
"""Harvest Arabic/English CLDR term pairs (units, currencies, territories, languages)
into TSV files plus a manifest. Stdlib only. Pinned to one CLDR release tag."""
import hashlib
import json
import subprocess
import sys
import time
import unicodedata
import urllib.request
from pathlib import Path

TAG = "48.2.1"
BASE = f"https://raw.githubusercontent.com/unicode-org/cldr-json/{TAG}"
# Where the tables and the manifest go, and where the fetched CLDR files are kept:
#   python scripts/harvest_cldr_term_lexicons.py OUT_DIR [RAW_DIR]
OUT_DIR = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("term-lexicons")
RAW_DIR = (Path(sys.argv[2]) if len(sys.argv) > 2 else OUT_DIR / "raw-cldr") / TAG
MARKET = "world"
LICENCE = "Unicode-3.0"
LICENCE_URL = f"{BASE}/LICENSE"
REQUEST_GAP = 2.0

FILES = {
    "units": {
        "path": "cldr-json/cldr-units-full/main/{loc}/units.json",
        "form_kind": "cldr-unit",
        "out": "units-cldr.tsv",
    },
    "currencies": {
        "path": "cldr-json/cldr-numbers-full/main/{loc}/currencies.json",
        "form_kind": "cldr-currency",
        "out": "currencies-cldr.tsv",
    },
    "territories": {
        "path": "cldr-json/cldr-localenames-full/main/{loc}/territories.json",
        "form_kind": "cldr-territory",
        "out": "territories-cldr.tsv",
    },
    "languages": {
        "path": "cldr-json/cldr-localenames-full/main/{loc}/languages.json",
        "form_kind": "cldr-language",
        "out": "languages-cldr.tsv",
    },
}

COLS = [
    "latin", "arabic_form", "form_kind", "source_url", "date_read",
    "fetch_sha256", "domain", "market", "licence", "cldr_key",
]

_last_request = [None]


def paced_fetch(url: str) -> bytes:
    if _last_request[0] is not None:
        elapsed = time.monotonic() - _last_request[0]
        if elapsed < REQUEST_GAP:
            time.sleep(REQUEST_GAP - elapsed)
    req = urllib.request.Request(url, headers={"User-Agent": "tigregotico-cldr-harvest/1.0"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = resp.read()
    _last_request[0] = time.monotonic()
    return data


def rig_date() -> str:
    return subprocess.check_output(["date", "-u", "+%Y-%m-%d"]).decode().strip()


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def assert_clean(value: str, label: str) -> None:
    if "\t" in value or "\n" in value or "\r" in value:
        raise AssertionError(f"{label} contains a tab or newline: {value!r}")


def has_arabic_char(text: str) -> bool:
    for ch in text:
        try:
            name = unicodedata.name(ch)
        except ValueError:
            continue
        if "ARABIC" in name:
            return True
    return False


def extract_units(doc, loc):
    out = {}
    units = doc["main"][loc]["units"]
    for form in ("long", "short", "narrow"):
        for key, val in units.get(form, {}).items():
            if isinstance(val, dict) and isinstance(val.get("displayName"), str):
                out[f"units/{form}/{key}/displayName"] = val["displayName"]
    return out


def extract_currencies(doc, loc):
    out = {}
    currencies = doc["main"][loc]["numbers"]["currencies"]
    for code, val in currencies.items():
        if isinstance(val, dict) and isinstance(val.get("displayName"), str):
            out[f"numbers/currencies/{code}/displayName"] = val["displayName"]
    return out


def extract_flat(doc, loc, key_name):
    out = {}
    node = doc["main"][loc]["localeDisplayNames"][key_name]
    for code, val in node.items():
        if isinstance(val, str):
            out[f"localeDisplayNames/{key_name}/{code}"] = val
    return out


EXTRACTORS = {
    "units": lambda doc, loc: extract_units(doc, loc),
    "currencies": lambda doc, loc: extract_currencies(doc, loc),
    "territories": lambda doc, loc: extract_flat(doc, loc, "territories"),
    "languages": lambda doc, loc: extract_flat(doc, loc, "languages"),
}


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    targets = [spec["out"] for spec in FILES.values()] + ["manifest.json"]
    existing = [t for t in targets if (OUT_DIR / t).exists()]
    if existing:
        raise SystemExit(f"REFUSING to overwrite existing target files: {existing}")

    manifest = {
        "cldr_version": TAG,
        "licence": LICENCE,
        "licence_url": LICENCE_URL,
        "files": {},
    }

    bad_arabic_rows = []

    for name, spec in FILES.items():
        url_ar = BASE + "/" + spec["path"].format(loc="ar")
        url_en = BASE + "/" + spec["path"].format(loc="en")

        raw_ar = paced_fetch(url_ar)
        date_ar = rig_date()
        raw_en = paced_fetch(url_en)

        sha_ar = sha256_hex(raw_ar)
        sha_en = sha256_hex(raw_en)

        (RAW_DIR / f"{name}-ar.json").write_bytes(raw_ar)
        (RAW_DIR / f"{name}-en.json").write_bytes(raw_en)

        doc_ar = json.loads(raw_ar)
        doc_en = json.loads(raw_en)

        ar_map = EXTRACTORS[name](doc_ar, "ar")
        en_map = EXTRACTORS[name](doc_en, "en")

        rows = []
        seen = set()
        skipped_no_english = 0
        skipped_untranslated = 0

        for cldr_key, arabic_raw in ar_map.items():
            arabic_form = arabic_raw.strip()
            if cldr_key not in en_map:
                skipped_no_english += 1
                continue
            latin = en_map[cldr_key].strip()
            if not latin or not arabic_form:
                skipped_no_english += 1
                continue
            if arabic_form == latin:
                skipped_untranslated += 1
                continue

            assert_clean(latin, "latin")
            assert_clean(arabic_form, "arabic_form")

            dedupe_key = (latin, arabic_form, spec["form_kind"], cldr_key)
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)

            if not has_arabic_char(arabic_form):
                bad_arabic_rows.append({
                    "file": name, "cldr_key": cldr_key,
                    "latin": latin, "arabic_form": arabic_form,
                })

            rows.append({
                "latin": latin,
                "arabic_form": arabic_form,
                "form_kind": spec["form_kind"],
                "source_url": url_ar,
                "date_read": date_ar,
                "fetch_sha256": sha_ar,
                "domain": name,
                "market": MARKET,
                "licence": LICENCE,
                "cldr_key": cldr_key,
            })

        out_path = OUT_DIR / spec["out"]
        with open(out_path, "w", encoding="utf-8", newline="") as fh:
            fh.write("\t".join(COLS) + "\n")
            for r in rows:
                fh.write("\t".join(r[c] for c in COLS) + "\n")

        tsv_bytes = out_path.read_bytes()
        manifest["files"][name] = {
            "output": spec["out"],
            "source_url_ar": url_ar,
            "source_url_en": url_en,
            "fetch_sha256_ar": sha_ar,
            "fetch_sha256_en": sha_en,
            "date_read": date_ar,
            "row_count": len(rows),
            "skipped_no_english": skipped_no_english,
            "skipped_untranslated": skipped_untranslated,
            "sha256": sha256_hex(tsv_bytes),
        }

    manifest_path = OUT_DIR / "manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=2)

    print("MANIFEST:")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))

    if bad_arabic_rows:
        print(f"WARNING: {len(bad_arabic_rows)} rows have an arabic_form with no Arabic-script character:")
        for row in bad_arabic_rows:
            print(" ", json.dumps(row, ensure_ascii=False))
    else:
        print("All arabic_form values contain at least one Arabic-script character.")

    print("DONE")


if __name__ == "__main__":
    main()
