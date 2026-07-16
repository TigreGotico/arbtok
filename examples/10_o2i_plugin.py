"""arbtok as orthography2ipa step plugins.

Plain orthography2ipa cannot vocalize undiacritized Arabic — its input contract
is diacritized text. Installing arbtok registers named `normalize`/`rescore`/
`sandhi` plugins that let orthography2ipa restore the vowels. The plugin is opted
into by name at the call site, never applied implicitly.

Run::

    python examples/10_o2i_plugin.py
"""
from orthography2ipa import G2P


def main() -> None:
    bare = "كتب"

    plain = G2P("ar").transcribe(bare)
    with_arbtok = G2P("ar", plugins={"normalize": "arbtok"}).transcribe(bare)

    print("plain o2i        :", plain)          # no vowels to read
    print("o2i + arbtok     :", with_arbtok)    # arbtok restores them


if __name__ == "__main__":
    main()
