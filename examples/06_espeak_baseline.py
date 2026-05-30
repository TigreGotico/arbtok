"""Compare the rule-based IPA against the espeak-ng baseline (guarded).

Run::

    python examples/06_espeak_baseline.py
"""
import shutil

from arbtok.tokenizer import Sentence


def main() -> None:
    text = "قَالَ ٱلْمَلِكُ"
    print("arbtok :", Sentence(text).ipa)

    if not shutil.which("espeak-ng"):
        print("espeak :", "skipped (espeak-ng binary not found on PATH)")
        return

    from arbtok.espeak_wrapper import EspeakPhonemizer

    esp = EspeakPhonemizer()
    sentences = esp.phonemize(text, "ar")  # list[list[str]] grouped by sentence
    joined = " | ".join("".join(s) for s in sentences)
    print("espeak :", joined)


if __name__ == "__main__":
    main()
