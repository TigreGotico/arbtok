"""arbtok as orthography2ipa pipeline steps.

Plain orthography2ipa cannot vocalize undiacritized Arabic — its input contract
is diacritized text. `arbtok.o2i_plugins.pipeline` builds an orthography2ipa
Pipeline that restores the vowels. The caller passes it at the call site, so
installing arbtok never changes an output on its own.

Run::

    python examples/10_o2i_plugin.py
"""
from orthography2ipa import G2P

from arbtok.o2i_plugins import pipeline


def main() -> None:
    bare = "كتب"

    plain = G2P("ar").transcribe(bare)
    with_arbtok = G2P("ar", pipeline=pipeline("ar")).transcribe(bare)

    print("plain o2i        :", plain)          # no vowels to read
    print("o2i + arbtok     :", with_arbtok)    # arbtok restores them


if __name__ == "__main__":
    main()
