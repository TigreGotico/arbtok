"""Loanword nativization — code-switched Latin words read per-lect.

A Latin-script word inside Arabic text is read as a loanword and adapted into the
matrix lect's phonology, out of that lect's own cited inventory. The same English
word therefore surfaces differently per variety.

Run::

    python examples/08_loanwords.py
"""
from arbtok.plugin import ArbtokG2PPlugin


def main() -> None:
    for word in ["manager", "think"]:
        eg = ArbtokG2PPlugin(lang="ar-EG").transcribe_word(word)
        najd = ArbtokG2PPlugin(lang="ar-SA-x-najd").transcribe_word(word)
        print(f"{word:<10}  ar-EG: {eg:<10}  ar-SA-x-najd: {najd}")

    # nativize=False leaves a Latin run untranscribed (linguistic output).
    p = ArbtokG2PPlugin(lang="ar-SA-x-najd", nativize=False)
    print("\nnativize=False:", p.transcribe("عندي meeting"))


if __name__ == "__main__":
    main()
