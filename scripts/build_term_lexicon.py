"""Build a bundled term lexicon from a harvest of published Arabic spellings.

    python scripts/build_term_lexicon.py HARVEST.jsonl arbtok/data/term_lexicons/cars-sa.tsv

The harvest is one JSON object per line: a Latin-script name (``brand``, and
``model`` when the row names one), the Arabic spelling a public web page gave it
(``arabic_form``), what kind of page that was (``form_kind``), the page
(``source_url``) and the day it was read (``date_read``).

Only spellings a public page published are bundled. A harvest may also hold forms
of other kinds, mined from recordings for instance; those describe somebody's
data, not the public record, and are refused by kind rather than by trust.
"""
import json
import sys

PUBLISHED = ("brand-site", "distributor-site", "marketplace")
HEADER = "# latin\tarabic_form\tform_kind\tsource_url\tdate_read\n"


def build(harvest_path: str, out_path: str) -> int:
    rows, seen = [], {}
    for line in open(harvest_path, encoding="utf-8"):
        r = json.loads(line)
        if r["form_kind"] not in PUBLISHED:
            continue
        if not r["source_url"].startswith("https://") or not r["date_read"]:
            sys.exit(f"refused: a published form without its page and date: {r}")
        latin, arabic = (r["model"] or r["brand"]).strip(), r["arabic_form"].strip()
        if seen.setdefault(arabic, latin) != latin:
            sys.exit(f"refused: {arabic!r} is published for both {seen[arabic]!r} and {latin!r}")
        rows.append((latin, arabic, r["form_kind"], r["source_url"], r["date_read"]))
    rows = sorted(set(rows), key=lambda row: (row[0].lower(), PUBLISHED.index(row[2]), row[1]))
    with open(out_path, "w", encoding="utf-8") as out:
        out.write(HEADER)
        out.writelines("\t".join(row) + "\n" for row in rows)
    return len(rows)


if __name__ == "__main__":
    print(build(sys.argv[1], sys.argv[2]), "rows")
