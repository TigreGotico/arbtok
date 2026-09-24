# Span-level pronunciation gold

Each line of `<lect>.jsonl` is one sentence, one span in it, a category, and the readings a cited
source accepts for that span, in phones. `scripts/span_gold.py build` writes these files from the
items in that script, and `scripts/span_gold.py score` scores arbtok against them per lect, category
and part. The comparison rules are in the script's docstring. They were fixed before any score was
read.

Every accepted reading carries its source, the page or entry it is printed on, and the form as
printed. The Najdi dialect readings are native-informant forms from Alshammari 2026, including the
paper's statement that [k] and [ts] are in free variation. The Najdi numbers are from Ingham 1982's
Shammar text. No reading comes from a phonemiser or from a person's ear.

Abbreviations are written input, the text a voice agent is asked to read, and no corpus of that
input is held: the call, WhatsApp and broadcast transcripts spell out what was said and contain no
written abbreviation. So their readings are the expansions a dictionary gives, and this gold is the
measurement a resolver is written against, not a record of observed use. ر.س and د. are not included:
no source giving their expansion was found.

The `held_out` part is chosen by a hash of each item's id. No rule is tuned against it, and it is
reported apart.
