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

#: Every Arabic variety arbtok speaks for.
_ARABIC = [
    "ar", "arb", "ar-x-peninsular", "ar-x-gulf", "ar-x-levantine",
    "ar-x-maghrebi", "ar-x-mashriqi", "ar-SA-x-najd", "ar-SA-x-hejaz",
    "ar-EG", "ar-IQ", "ar-SY", "ar-LB", "ar-JO", "ar-PS", "ar-MA", "ar-DZ",
    "ar-TN", "ar-LY", "ar-AE", "ar-BH", "ar-KW", "ar-QA", "ar-OM", "ar-YE",
    "ar-SD",
]


class ArbtokDiacritizer(NormalizePlugin):
    """Put back the vowels the writing leaves out — guarded by the lattice.

    Restoring tashkeel is a statistical problem, so it belongs to a model. But a
    model asked to write into a word can write anything, and downstream that is
    undetectable — the phonemizer will faithfully transcribe the hallucination.
    So the model proposes and the lattice disposes: only act where the writing is
    actually silent, never overwrite a human's marks, and refuse a result the
    variety's grapheme table does not license (:mod:`arbtok.diacritize`).
    """

    def __init__(self) -> None:
        self._by_lang: dict = {}

    def normalize(self, text: str, lang: str) -> str:
        from arbtok.diacritize import LatticeDiacritizer

        if lang not in self._by_lang:
            self._by_lang[lang] = LatticeDiacritizer(lang=lang)
        return self._by_lang[lang].diacritize(text)

    @property
    def language_codes(self) -> List[str]:
        return list(_ARABIC)


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
        return list(_ARABIC)


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

        out = apply_cross_word(rows)

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
        return list(_ARABIC)
