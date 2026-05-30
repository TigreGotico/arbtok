"""Normalize numbers and percent signs, then phonemize the spoken form.

Run::

    python examples/04_normalize.py
"""
from arbtok.num2words import num2words
from arbtok.tokenizer import Sentence
from arbtok.util import normalize


def main() -> None:
    raw = "عندي 3 كتب"
    spoken = normalize(raw, "ar")
    print("raw     :", raw)
    print("spoken  :", spoken)
    print("ipa     :", Sentence(spoken).ipa)

    print()
    # Arabic number-to-words with diacritics and percent handling.
    print("num2words:", num2words("عندي 25 كتاب و 50%"))


if __name__ == "__main__":
    main()
