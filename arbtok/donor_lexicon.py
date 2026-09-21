"""The bundled donor lexicons: English, and the French closed classes.

A code-switched Arabic sentence carries English words, and those words are
phonemized by the DONOR language's G2P before :mod:`arbtok.translit` maps the
result into the matrix language's inventory. English is a deep orthography:
its rule system cannot reach the right reading from spelling alone, and the
readings it misses are exactly the ones a Gulf call-centre sentence is made of
— ``engine``, ``service``, ``machine``, ``medicine``.

Measured on the en-GB rule spec against espeak-ng (which shares no data with
this lexicon's source): whole-word agreement goes 22.6% to 47.6% with the
overlay registered. On the loanword path 11 of 18 sampled words move to the
reading this repository's own gold notes document — ``inkajn`` to ``indʒin``,
``maʃajn`` to ``maʃiːn``, ``safajs`` to ``safis``.

orthography2ipa bundles no lexicon by design ("a lexicon is a word list, not a
description of a language"). That is the right call for a general G2P library
and the wrong one for this package, which exists to read one language's
code-switching and therefore has a specific donor whose lexicon it can name.
So the list ships here and is registered on arbtok's behalf rather than
the caller's. It lives in its own ``data/donor_lexicons`` directory rather than
beside ``data/lexicons``: those are Arabic per-lect closed-class lists under an
invariant this file cannot meet (each entry's IPA spells its own key, which is
not a property of an English word).

**A caller's own registration always wins.** This registers the bundled file
only when nothing is registered for the code yet, so an application that has
its own English lexicon keeps it. Registration is global to the
orthography2ipa process registry, which is why it must not overwrite.

Provenance: misaki (Apache-2.0) ``gb_gold.json``, a British English gold
lexicon — the same RP convention the ``en-GB`` spec targets. Its single-letter
phoneme shorthands are expanded to IPA at build time; see
``scripts/build_donor_lexicon.py``. Part-of-speech variants (``ˈrecord`` against
``reˈcord``) are dropped rather than guessed: the overlay is a word-to-IPA map
with no part-of-speech channel.

A French file ships beside it for Maghrebi code-switching, registered the same
way when ``fr-FR`` is the donor. It holds the closed-class words only, each read
from the French MFA dictionary (CC BY 4.0); see ``data/donor_lexicons/README.md``
and ``scripts/build_french_donor_lexicon.py``.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

#: The donor whose lexicon is bundled. Kept in step with
#: :data:`arbtok.translit.DONOR_LANG`.
BUNDLED_DONOR = "en-GB"


def bundled_path(code: str = BUNDLED_DONOR) -> Optional[Path]:
    """The shipped ``{code}.tsv``, or None when this package ships none."""
    path = Path(__file__).parent / "data" / "donor_lexicons" / f"{code}.tsv"
    return path if path.is_file() else None


def ensure_registered(code: str = BUNDLED_DONOR) -> bool:
    """Register the bundled lexicon for *code* unless one is already registered.

    Returns True when this call registered it. Idempotent, does no network I/O
    and reads nothing: orthography2ipa loads a lexicon lazily on first use, so
    the file is not opened until a word actually needs looking up.
    """
    try:
        # From the submodule, not the package root: `register_lexicon` is
        # re-exported at top level but `lexicon_path` is not, and importing the
        # pair from the root fails — silently, if the guard below is broad.
        from orthography2ipa.lexicon import lexicon_path, register_lexicon
    except ImportError:      # an orthography2ipa predating the overlay
        return False
    if lexicon_path(code) is not None:
        return False
    path = bundled_path(code)
    if path is None:
        return False
    register_lexicon(code, str(path))
    return True
