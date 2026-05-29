"""Restore diacritics with the bundled ONNX model, then phonemize.

Run::

    python examples/05_diacritize.py
"""
from arbtok.tashkeel import TashkeelDiacritizer
from arbtok.tokenizer import Sentence


def main() -> None:
    diac = TashkeelDiacritizer()  # loads the in-tree model.onnx once

    for raw in ["قال الملك", "ذهب الطالب", "السلام عليكم"]:
        vocalized = diac.diacritize(raw)
        print(f"{raw:<14}  ->  {vocalized}")
        print(f"{'':14}      ipa: {Sentence(vocalized).ipa}")


if __name__ == "__main__":
    main()
