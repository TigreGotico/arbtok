"""arbtok, as steps orthography2ipa can run.

arbtok is an engine built ON orthography2ipa — it is not a plugin to it. But the
*pieces* it owns are exactly the steps orthography2ipa made pluggable, and there
is no reason to keep them locked inside one package:

===============  ========================================================
stage            what arbtok contributes
===============  ========================================================
``normalize``    restore the tashkeel the writing omits, under the lattice's
                 guard — the model proposes, the lattice disposes
``rescore``      the Arabic morpho-phonology no grapheme table can express:
                 sun-letter assimilation, hamzat al-waṣl, the hamza carrier,
                 the accusative alif
``sandhi``       what happens BETWEEN words: idghām/iqlāb, the pause that
                 removes a case ending, waṣl
===============  ========================================================

Registered, these make plain orthography2ipa able to transcribe **undiacritized**
Arabic — which it cannot do alone, and by design: its input contract is
diacritized text and it ships no weights::

    from orthography2ipa import G2P
    G2P("ar").transcribe("كتب")                                     # 'ˈktb' — no vowels to read
    G2P("ar", plugins={"normalize": "arbtok"}).transcribe("كتب")    # 'ˈkataba'

Note the second line. The plugin is **named**, not merely installed. Installing
arbtok must not silently change what orthography2ipa says about Arabic — the
caller asks for it, in code, where anyone reading the call site can see that a
model is putting the vowels in.
"""

from __future__ import annotations

from typing import List, Sequence

from orthography2ipa.plugins import NormalizePlugin, SandhiPlugin
from orthography2ipa.rescorer_plugin import RescorerPlugin

__all__ = [
    "ArbtokDiacritizer",
    "ArbtokRescorers",
    "ArbtokSandhi",
]


def _arabic_codes() -> List[str]:
    """Every Arabic variety arbtok speaks for, read from the orthography2ipa
    registry — not pinned in a list here.

    :func:`arbtok.dialects.supported_lects` already enumerates the ``ar*`` specs
    installed upstream; a second hand-kept copy drifts the moment o2i registers a
    new lect (a Saudi variety, a qeltu group, a Sahelian code). Deriving the
    ``language_codes`` the plugins advertise from that same source means a spec
    added upstream is spoken for the instant it is installed, with no list to
    update in step.
    """
    from arbtok.dialects import supported_lects

    return [lect.code for lect in supported_lects()]


class ArbtokDiacritizer(NormalizePlugin):
    """Put back the vowels the writing leaves out — guarded by the lattice.

    Restoring tashkeel is a statistical problem, so it belongs to a model. But a
    model asked to write into a word can write anything, and downstream that is
    undetectable — the phonemizer will faithfully transcribe the hallucination.
    So the model proposes and the lattice disposes: only act where the writing is
    actually silent, never overwrite a human's marks, and refuse a result the
    variety's grapheme table does not license (:mod:`arbtok.diacritize`).
    """

    #: Which generator answers a word nobody has written down. ``lattice`` tokenizes
    #: one constrained-argmax guess and refuses it if the orthography does not license
    #: it; ``fusion`` enumerates the licensed readings and lets rawi score them.
    #:
    #: The default is ``lattice`` and the reason is a measurement rather than a
    #: preference. On the shipped code-switched gold, 881 rows across 44 lects, scored
    #: per character position against the editor-authored vocalization: rawi alone
    #: 0.1757, lattice 0.0989, fusion 0.1012. Fusion is 52 positions in 22,800 behind
    #: the simpler path — about one standard error before within-sentence correlation
    #: widens it — so that gold cannot separate them, and the cheaper path wins a tie.
    #:
    #: Set ``ARBTOK_DIACRITIZER=fusion`` to select the other one. It exists so the
    #: comparison can be re-run on a gold that might separate them; it is not dead
    #: code and it is not the default.
    PATHS = ("lattice", "fusion")

    def __init__(self) -> None:
        self._by_lang: dict = {}

    @staticmethod
    def _path() -> str:
        import os
        want = os.environ.get("ARBTOK_DIACRITIZER", "lattice").strip().lower()
        if want not in ArbtokDiacritizer.PATHS:
            raise ValueError(
                f"ARBTOK_DIACRITIZER={want!r} is not one of {ArbtokDiacritizer.PATHS}. "
                "Refusing rather than falling back: a typo that silently kept the "
                "default would read exactly like the setting working."
            )
        return want

    def normalize(self, text: str, lang: str) -> str:
        key = (lang, self._path())
        if key not in self._by_lang:
            if key[1] == "fusion":
                from arbtok.fusion import FusionDiacritizer as _D
            else:
                from arbtok.diacritize import LatticeDiacritizer as _D
            self._by_lang[key] = _D(lang=lang)
        return self._by_lang[key].diacritize(text)

    @property
    def language_codes(self) -> List[str]:
        return _arabic_codes()


class ArbtokRescorers(RescorerPlugin):
    """The Arabic morpho-phonology the shared grapheme table cannot express.

    Sun-letter assimilation (the lām of ⟨ال⟩ into a following coronal), hamzat
    al-waṣl, a hamza carrier before a sukūn, the otiose alif after tanwīn
    al-fatḥ. These are rules about *words*, not about *letters*, which is why they
    are rescorers and not grapheme entries.
    """

    def rescorers(self, lang: str) -> Sequence:
        from arbtok.lattice import DEFAULT_RESCORERS

        return list(DEFAULT_RESCORERS)

    @property
    def language_codes(self) -> List[str]:
        return _arabic_codes()


class ArbtokSandhi(SandhiPlugin):
    """What happens between words.

    A final /n/ takes the shape of what follows it — مِنْ رَبِّهِمْ is *mir
    rabbihim*, مِنْ بَيْتِكَ is *mim bajtika*. A pause removes a case ending, and
    takes a tāʾ marbūṭa with it, because the tāʾ was only voiced by the ending that
    just left.

    The spelling is not redundant here: whether a word ends in a case ending is a
    fact about the page, and guessing it from the last characters of the IPA
    confuses an ending with a stem — the ``-in`` of قَاضٍ is an ending and the
    ``-in`` of مُؤْمِن is the word.
    """

    def apply(
        self,
        words: Sequence[str],
        surfaces: Sequence[str],
        pausal: Sequence[bool],
        lang: str,
    ) -> List[str]:
        from arbtok.sandhi import apply_cross_word

        # orthography2ipa places stress per word BEFORE sandhi runs, so the IPA
        # arriving here carries a mark that arbtok's own pipeline has not applied
        # yet: `ˈmin` is still *min*, and a rule matching on the shape of a word
        # would miss it. Strip the marks for the match, put them back after — the
        # rewrite is at the word's END, so a leading mark survives untouched.
        # The mark sits INSIDE the word (maˈdiːnatun), so it has to go back where
        # it was — not on the front. Sandhi only ever rewrites a word's END (a
        # final /n/ assimilates; a pause removes a case ending), so the mark's
        # index is stable, and it is dropped only if the word shrank past it.
        stripped, marks = [], []
        for w in words:
            idx = next((i for i, ch in enumerate(w) if ch in "ˈˌ"), None)
            marks.append((idx, w[idx]) if idx is not None else None)
            stripped.append(w.replace("ˈ", "").replace("ˌ", ""))

        # arbtok models the pause as a punctuation token; orthography2ipa hands it
        # to us as a flag, because it has already dropped the punctuation.
        rows = []
        for ipa, surface, at_pause in zip(stripped, surfaces, pausal):
            rows.append((ipa, surface, False))
            if at_pause:
                rows.append(("", "", True))   # the pause itself

        out = apply_cross_word(rows, lang=lang)

        rewritten = [
            out[i] for i, (_, _, is_pause) in enumerate(rows) if not is_pause
        ]

        restored = []
        for word, mark in zip(rewritten, marks):
            if mark is None or mark[0] > len(word):
                restored.append(word)
            else:
                idx, ch = mark
                restored.append(word[:idx] + ch + word[idx:])
        return restored

    @property
    def language_codes(self) -> List[str]:
        return _arabic_codes()
