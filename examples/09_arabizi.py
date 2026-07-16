"""Arabizi — Arabic written in Latin letters and digits — read as Arabic.

A Latin run carrying a digit-guttural (7=ح, 3=ع, 9=ق, …) is detected as Arabizi,
reverse-transliterated to an unpointed Arabic skeleton, and sent through the same
diacritize + phonology stack as native script. Digit-free English embeds stay on
the loanword path.

Run::

    python examples/09_arabizi.py
"""
from arbtok.plugin import ArbtokG2PPlugin


def main() -> None:
    p = ArbtokG2PPlugin(lang="ar-EG")  # arabizi=True by default

    print("arabizi (auto):", p.transcribe("7abibi 3ala"))
    print("english embed :", p.transcribe("عِنْدِي meeting"))
    print("forced arabizi:", p.transcribe("habibi", arabizi=True))
    print("forced loan   :", p.transcribe("3ala", arabizi=False))


if __name__ == "__main__":
    main()
