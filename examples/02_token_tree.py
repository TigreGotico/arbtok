"""Inspect the word/char token tree behind a transcription.

Run::

    python examples/02_token_tree.py
"""
from arbtok.tokenizer import Sentence


def main() -> None:
    sentence = Sentence("الْمَدْرَسَةِ")  # "the school"
    word = sentence.tokens[0]

    print("sentence ipa :", sentence.ipa)
    print("word         :", word.surface)
    print("has article  :", word.has_definite_article)
    print("is sun word  :", word.is_sun)
    print("per-character IPA fragments:")
    for ch in word.tokens:
        kind = "sun" if ch.is_sun else "moon"
        print(f"  {ch.surface!r:>6}  ->  {ch.ipa!r:<6}  ({kind})")


if __name__ == "__main__":
    main()
