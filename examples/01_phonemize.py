"""Phonemize diacritized Arabic to IPA with the core Sentence entry point.

Run::

    python examples/01_phonemize.py
"""
from arbtok.tokenizer import Sentence


def main() -> None:
    samples = [
        "قَالَ ٱلْمَلِكُ",            # "the king said"
        "ذَهَبَ الطَّالِبُ إِلَى الْمَدْرَسَةِ",  # "the student went to the school"
        "السَّلَامُ عَلَيْكُمْ",        # "peace be upon you"
        "بَابٌ",                      # "a door" (tanwin ending)
    ]
    for text in samples:
        print(f"{text}  ->  {Sentence(text).ipa}")


if __name__ == "__main__":
    main()
