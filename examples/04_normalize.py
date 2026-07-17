"""Normalize numbers and percent signs, then phonemize the spoken form.

Run::

    python examples/04_normalize.py
"""
from arbtok.tokenizer import Sentence
from arbtok.util import normalize


def main() -> None:
    raw = "عندي 25 كتاب و 50%"
    spoken = normalize(raw, "ar")
    print("raw     :", raw)
    print("spoken  :", spoken)
    print("ipa     :", Sentence(spoken).ipa)


if __name__ == "__main__":
    main()
