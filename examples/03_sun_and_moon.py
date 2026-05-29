"""Show definite-article assimilation: sun letters double, moon letters keep the L.

Run::

    python examples/03_sun_and_moon.py
"""
from arbtok.tokenizer import Sentence


def main() -> None:
    pairs = [
        ("الشَّمْس", "sun letter (ش): L assimilates, consonant doubles"),
        ("النُّور", "sun letter (ن): L assimilates, consonant doubles"),
        ("الْقَمَر", "moon letter (ق): L is pronounced"),
        ("الْبَيْت", "moon letter (ب): L is pronounced"),
    ]
    for text, note in pairs:
        print(f"{text:<10}  ->  {Sentence(text).ipa:<12}  {note}")


if __name__ == "__main__":
    main()
