"""Dialect-aware tashkeel — the flagship.

The SAME bare (undiacritized) sentence is phonemized under several varieties.
arbtok restores the missing vowels dialect-aware: the diacritizer's choice is
constrained to the readings each variety's orthography licenses, so the vowels
AND the consonant reflexes come out variety-appropriate.

Run::

    python examples/07_dialect_aware.py
"""
from arbtok.plugin import ArbtokG2PPlugin


def main() -> None:
    bare = "يشرب القهوة في البيت"  # "he drinks the coffee at home" — no ḥarakāt

    for lang, note in [
        ("ar", "MSA: qāf /q/, diphthong /aj/ in bayt"),
        ("ar-SA-x-najd", "Najdi: qāf → /ɡ/, gahawa epenthesis"),
        ("ar-TN", "Tunisian: /q/ kept, bayt monophthongized to /iː/"),
    ]:
        ipa = ArbtokG2PPlugin(lang=lang).transcribe(bare)
        print(f"{lang:<14}  {ipa}")
        print(f"{'':14}  {note}")


if __name__ == "__main__":
    main()
