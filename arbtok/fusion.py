"""Joint diacritization + phonemization: the diacritizer as a *scorer* over the
lattice, not a generator ahead of it.

The shipped pipeline (:mod:`arbtok.diacritize`) runs in one direction: the rawi
model writes one tashkeel string, the lattice then *checks* it, and a word whose
single guess the orthography refuses is dropped back to its bare skeleton — an
underdetermined reading. The model proposes exactly once, and when that one
proposal is unlicensed its whole distribution is thrown away with it. The
lattice's constraints never reach back to inform the choice; they can only veto
it after the fact.

This module closes that loop. rawi is a char-level classifier with an accessible
per-character distribution (:meth:`arbtok._ensemble.EnsembleDiacritizer.logits`), so instead
of taking its argmax and hoping the result is licensed, arbtok can enumerate the
*licensed* diacritizations of a word and let rawi **score** them — picking the
highest-probability reading the variety's orthography actually admits. The model
runs **once per sentence**; every hypothesis is scored by indexing the output
tensor it already produced, so the search is cheap.

The design, concretely:

1. **Enumerate hypotheses, constrained.** For each underdetermined letter a small
   set of candidate diacritic classes is taken from the top of rawi's own
   distribution. The classes rawi exposes are pure combining marks — it cannot
   propose a class that rewrites the consonant — so every hypothesis has the
   word's skeleton. A beam keeps the search bounded.

2. **Score with rawi's distribution.** A hypothesis's score is the sum of the
   log-probabilities rawi assigns to its per-character classes. This is monotone:
   swapping any position for a higher-logit class raises the score.

3. **Let the lattice dispose.** A hypothesis is a candidate only if the variety's
   grapheme table *licenses* it (it tokenizes with no ``UNKNOWN`` segment) — the
   same guard the shipped pipeline applies, but here it filters a *set* rather
   than vetoing a single guess. Among the licensed candidates the one rawi scores
   highest wins, with a small lattice-cost tie-break so a phonotactically cleaner
   reading is preferred when two are near-equal in the model's eyes.

4. **Pausal / per-lect prior.** With ``waqf`` on (the TTS register) the chosen
   reading is reduced to its pausal form, dropping the iʿrāb-style final short
   vowels the dialect targets would drop at pause anyway.

The lexicon is still consulted first: a written-down word is a lexical fact, not
a thing to score. Fusion only changes what happens for words nobody has recorded,
and its whole margin over the shipped pipeline is the set of words whose argmax
the orthography refuses — where the generator falls back to a bare skeleton and
the scorer instead recovers the best licensed reading.

Ownership note: this is arbtok code by design (roadmap §T.3 route 4). The bundled
ensemble (:mod:`arbtok._ensemble`) stays a generic diacritizer that knows nothing
of lattices; this module is the one place that knows about both it and
orthography2ipa.
"""

from __future__ import annotations

import math
import unicodedata
from typing import List, Optional, Sequence, Tuple

import numpy as np

from orthography2ipa import get, underdetermined_positions
from orthography2ipa.phonetok import PhonetokTokenizer, TokenKind

from arbtok.dialects import DEFAULT_LANG
from arbtok.diacritize import (
    _author_complete, _proclitic_complete, repair_skeleton, strip_marks,
    _skeleton_is_preserved,
)
from arbtok.dialect_lexicon import DialectLexicon
from arbtok.lexicon import DEFAULT_LEXICON, StemLexicon
from arbtok.lattice import word_lattice
from arbtok.nisba import restore_nisba
from arbtok.tokenizer import normalize_unicode

__all__ = ["FusionDiacritizer", "Hypothesis", "logprobs"]

def logprobs(row: np.ndarray) -> np.ndarray:
    """Numerically-stable log-softmax of one logit row."""
    m = row.max()
    shifted = row - m
    return shifted - math.log(float(np.exp(shifted).sum()))


class Hypothesis:
    """One diacritization of a word: the class id per character, its rawi
    log-probability, the rendered string, and (once measured) its lattice cost."""

    __slots__ = ("class_ids", "logprob", "text", "lattice_cost")

    def __init__(self, class_ids: Tuple[int, ...], logprob: float, text: str = "",
                 lattice_cost: float = 0.0) -> None:
        self.class_ids = class_ids
        self.logprob = logprob
        self.text = text
        self.lattice_cost = lattice_cost

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return (f"Hypothesis({self.text!r}, logprob={self.logprob:.3f}, "
                f"lattice_cost={self.lattice_cost:.3f})")


class FusionDiacritizer:
    """Diacritize by scoring the *licensed* readings, not by generating one.

    The interface matches :class:`arbtok.diacritize.LatticeDiacritizer` — a
    ``diacritize(text)`` that guards every word — so the plugin can swap one for
    the other behind a flag. It differs only in the mechanism for a word nobody
    has written down: rather than tokenizing a single model guess, it scores the
    orthography's licensed hypotheses with the model's distribution and keeps the
    best.

    ``beam`` bounds the search width; ``topk`` the classes considered per
    position; ``lattice_weight`` scales the phonotactic tie-break (0 disables it,
    leaving a pure maximum-likelihood pick among licensed readings).
    """

    def __init__(
        self,
        lang: str = DEFAULT_LANG,
        waqf: bool = True,
        lexicon: Optional[str] = DEFAULT_LEXICON,
        dialect_lexicon: bool = True,
        beam: int = 8,
        topk: int = 4,
        lattice_weight: float = 0.5,
    ) -> None:
        self.lang = lang
        self.waqf = waqf
        self.beam = beam
        self.topk = topk
        self.lattice_weight = lattice_weight
        self._diacritizer = None
        self._spec = get(lang)
        self._tokenizer = PhonetokTokenizer(self._spec)
        self.lexicon = StemLexicon(lexicon) if lexicon else None
        self._dialect_lexicon_on = dialect_lexicon
        #: The lect's closed-class lexicon, a hard prior consulted before the
        #: stem lexicon and before scoring (see :mod:`arbtok.dialect_lexicon`).
        self.dialect_lexicon = DialectLexicon(lang) if dialect_lexicon else None
        #: Words the fusion recovered — a licensed reading the plain argmax would
        #: have left unlicensed (the whole reason this path exists), in order.
        self.recovered: List[str] = []
        #: Words answered from the stem lexicon, which the model never scored.
        self.looked_up: List[str] = []
        #: Words answered from the lect's closed-class lexicon (the hard prior).
        self.dialect_looked_up: List[str] = []
        #: Words no licensed hypothesis covered, left as written (underdetermined).
        self.rejected: List[str] = []
        #: The n-best licensed hypotheses of the last fused word, best first.
        self.last_nbest: List[Hypothesis] = []

    @property
    def diacritizer(self):
        if self._diacritizer is None:
            # The bundled ensemble reader (logits / decode / diacritize) —
            # arbtok's own stitched ONNX, exposing the flagship distribution to
            # score. waqf is applied by this module (after scoring), not by the
            # model.
            from arbtok._ensemble import get_ensemble
            self._diacritizer = get_ensemble()
        return self._diacritizer

    # ── licensing (shared with the guarded pipeline) ────────────────────────

    def _is_licensed(self, word: str) -> bool:
        try:
            tokens = self._tokenizer.tokenize(normalize_unicode(word))
        except Exception:
            return False
        return all(t.kind is not TokenKind.UNKNOWN for t in tokens)

    def _lattice_cost(self, word: str) -> float:
        """Total lowest-cost-candidate cost of *word* on the variety lattice —
        the phonotactic tie-break. Lower is a cleaner path."""
        try:
            return float(sum(slot.top.cost for slot in word_lattice(word, self.lang)))
        except Exception:
            return 0.0

    def _dialect_lookup(self, word: str) -> Optional[str]:
        """The lect's closed-class vocalization for *word*, guarded like a stem
        entry (spells the word, licensed by the variety). Register-invariant, so
        it answers in both waqf modes. See :mod:`arbtok.dialect_lexicon`."""
        if self.dialect_lexicon is None:
            return None
        voc = self.dialect_lexicon.get(word)
        if voc is None:
            return None
        if strip_marks(voc) != strip_marks(word) or not self._is_licensed(voc):
            return None
        return voc

    def _lookup(self, word: str) -> Optional[str]:
        if self.lexicon is None or not self.waqf:
            return None
        stem = self.lexicon.get(word)
        if stem is None:
            return None
        stem = restore_nisba(stem)
        if strip_marks(stem) != strip_marks(word) or not self._is_licensed(stem):
            return None
        return stem

    # ── the beam ────────────────────────────────────────────────────────────

    def _pins(self, word: str, bare_word: str):
        """Per position of *bare_word*: the hard constraint the writing imposes.

        A human's mark is an **answer, not a suggestion**: a position that
        already carries a vocalic mark is pinned to exactly the class that
        spells it, so no hypothesis can override an explicit sukūn or kasra. A
        position whose source spells an orthographic mark (hamza, madda) is
        restricted to the classes carrying exactly that spelling, so no
        hypothesis can rewrite the letter. Only the genuinely silent positions
        are left to the model — fusion engages on unmarked positions alone.

        Returns a list (``None`` = free, ``int`` = pinned class id,
        ``set`` = allowed class ids), or ``None`` when the decompositions
        disagree and no mask can be trusted (see arbtok.orthography).
        """
        from arbtok.orthography import (
            ORTHOGRAPHIC_MARKS, allowed_classes, pinned_class, source_marks,
        )
        src_bare, src_marks = source_marks(word, self.diacritizer._normalize)
        if src_bare != bare_word or len(src_marks) != len(bare_word):
            return None
        classes = self.diacritizer.classes
        pins: List[object] = []
        for ch, marks in zip(bare_word, src_marks):
            if not unicodedata.category(ch).startswith("L"):
                pins.append(0)
                continue
            if marks - ORTHOGRAPHIC_MARKS:      # a human's vocalic mark: pinned
                pin = pinned_class(classes, marks)
                pins.append(pin if pin >= 0 else None)
                continue
            if marks:                            # spelled hamza/madda: restricted
                pins.append(set(allowed_classes(classes, marks)))
                continue
            pins.append(None)                    # silent: the model's to decide
        return pins

    def _beam_search(self, bare_word: str, word_logits: np.ndarray,
                     pins=None) -> List[Hypothesis]:
        """The ``beam`` best class-id assignments for *bare_word*, by summed
        log-probability. A non-letter position is pinned to the empty class;
        *pins* (from :meth:`_pins`) hard-constrains what the writing fixed."""
        beams: List[Tuple[float, Tuple[int, ...]]] = [(0.0, ())]
        for i, ch in enumerate(bare_word):
            row = word_logits[i]
            pin = pins[i] if pins is not None else None
            if isinstance(pin, (int, np.integer)):
                # the writing's answer (or a non-letter): one choice, cost-free
                choices = [(int(pin), 0.0)]
            elif not unicodedata.category(ch).startswith("L"):
                choices = [(0, 0.0)]
            else:
                lp = logprobs(row)
                order = np.argsort(lp)[::-1]
                if isinstance(pin, set):        # restricted to the spelling
                    order = [c for c in order if int(c) in pin][: self.topk]
                else:
                    order = order[: self.topk]
                choices = [(int(c), float(lp[c])) for c in order]
                if not choices:
                    choices = [(0, 0.0)]
            expanded: List[Tuple[float, Tuple[int, ...]]] = []
            for score, ids in beams:
                for cid, clp in choices:
                    expanded.append((score + clp, ids + (cid,)))
            expanded.sort(key=lambda t: t[0], reverse=True)
            beams = expanded[: self.beam]
        return [Hypothesis(ids, score) for score, ids in beams]

    def _generate(self, orig_word: str, normalized: str,
                  recovery: bool = False) -> str:
        """The generator's decision rule for one word — constrained argmax,
        pausal, skeleton repair, nisba, licensing — byte-identical to
        :meth:`arbtok.diacritize.LatticeDiacritizer.diacritize_word` past its
        gates. Used for a partially vocalized word (the writing's answers are
        completed, never rescored) and as the nothing-licensed fallback."""
        proposed = self.diacritizer.diacritize(normalized)
        if self.waqf:
            from arbtok.waqf import pausal
            proposed = pausal(proposed)
        if not _skeleton_is_preserved(normalized, proposed):
            repaired = repair_skeleton(normalized, proposed)
            proposed = repaired if repaired is not None else None
        if proposed is not None:
            proposed = restore_nisba(proposed)
            if self._is_licensed(proposed):
                if recovery:
                    self.recovered.append(orig_word)
                return proposed
        self.rejected.append(orig_word)
        return orig_word

    def _fuse_word(self, orig_word: str, bare_word: str,
                   word_logits: np.ndarray) -> str:
        normalized = normalize_unicode(orig_word)
        self.last_nbest = []

        # (1) The writing already says it — including the author-complete case:
        # a word whose only silent positions are the definite article's alif/lām
        # is complete as written (the lattice fixes their reading without a
        # model), so scoring it would only let the model overrule the author.
        positions = underdetermined_positions(normalized, self._spec)
        if _author_complete(normalized, positions):
            return orig_word

        # (2a) A closed-class dialect word: written in MSA orthography, said the
        # lect's way. A hard prior consulted before the stem lexicon and before
        # scoring — the model would score it for the wrong variety.
        dialect = self._dialect_lookup(normalized)
        if dialect is not None:
            self.dialect_looked_up.append(orig_word)
            return dialect

        # (2b) A written-down word is a lexical fact, not a thing to score.
        entry = self._lookup(normalized)
        if entry is not None:
            self.looked_up.append(orig_word)
            return entry

        # (2c) Author-near-complete: only a bare leading proclitic is silent.
        # The spec path reads it as the vowelless clitic the dialect gold
        # records (وكَان → /wkaːn/); neither the generator nor the scorer may
        # add a register fatḥa the author did not write. After the lexicons,
        # mirroring the guarded pipeline.
        if _proclitic_complete(normalized, positions):
            return orig_word

        if word_logits is None or not bare_word:
            self.rejected.append(orig_word)
            return orig_word

        # (2b) A word a human has vocalized — even partially — is the
        # generator's to complete, not the scorer's. The written marks are an
        # author's answers; completing the few silent positions is exactly the
        # constrained argmax the shipped generator applies, and using the same
        # decision rule keeps vocalized input byte-identical whether fusion is
        # on or off. Fusion's scoring engages only where the writing is wholly
        # silent (bare words), which is also the only place its PER margin
        # comes from.
        if strip_marks(normalized) != normalized:
            return self._generate(orig_word, normalized)

        # (3) Enumerate, render, keep the licensed ones — scored by rawi.
        # (Defense in depth: pins re-assert the writing inside the search, so
        # even a marked word reaching here could not have its marks overridden.)
        pins = self._pins(normalized, bare_word)
        licensed: List[Hypothesis] = []
        for hyp in self._beam_search(bare_word, word_logits, pins):
            rendered = restore_nisba(self.diacritizer.decode(
                bare_word, list(hyp.class_ids)))
            if self.waqf:
                from arbtok.waqf import pausal
                rendered = pausal(rendered)
            if not self._is_licensed(rendered):
                continue
            hyp.text = rendered
            hyp.lattice_cost = self._lattice_cost(rendered)
            licensed.append(hyp)

        if not licensed:
            # Nothing the orthography admits: fall back to the generator's own
            # reading, exactly as the shipped pipeline decides it.
            return self._generate(orig_word, normalized, recovery=True)

        # Rank: rawi log-probability first, phonotactic cost as the tie-break.
        licensed.sort(
            key=lambda h: h.logprob - self.lattice_weight * h.lattice_cost,
            reverse=True,
        )
        self.last_nbest = licensed
        best = licensed[0].text

        # Book-keeping: did fusion recover a word the plain argmax would have
        # left unlicensed? (The margin this whole path exists to capture.)
        argmax = restore_nisba(self.diacritizer.diacritize(normalized))
        if self.waqf:
            from arbtok.waqf import pausal
            argmax = pausal(argmax)
        if not self._is_licensed(argmax):
            self.recovered.append(orig_word)
        return best

    # ── sentence entry point (one model run) ────────────────────────────────

    def _bare_words(self, bare: str) -> List[Tuple[str, int]]:
        """Split the model's bare sequence into (word, start_index) on spaces,
        so each word indexes a contiguous block of logit rows."""
        words, start = [], None
        for i, ch in enumerate(bare):
            if ch == " ":
                if start is not None:
                    words.append((bare[start:i], start))
                    start = None
            elif start is None:
                start = i
        if start is not None:
            words.append((bare[start:], start))
        return words

    def diacritize(self, text: str) -> str:
        """Diacritize each word of *text*, scoring the licensed readings.

        The model runs once, on the whole sentence; every word is then fused by
        indexing that one output. When the sentence's word count and the model's
        bare word count disagree (a normalization edge), the whole sentence falls
        back to the shipped guarded pipeline rather than risk a misaligned slice.
        """
        bare, logits, _classes = self.diacritizer.logits(text)
        orig_words = [w for w in text.split(" ")]
        bare_words = self._bare_words(bare) if bare else []

        # Align by the non-empty words only; a mismatch means the safe thing is
        # the per-word guarded pipeline.
        orig_nonempty = [w for w in orig_words if w.strip()]
        if logits is None or len(bare_words) != len(orig_nonempty):
            from arbtok.diacritize import LatticeDiacritizer
            guard = LatticeDiacritizer(lang=self.lang, waqf=self.waqf,
                                       lexicon=None if self.lexicon is None
                                       else DEFAULT_LEXICON,
                                       dialect_lexicon=self._dialect_lexicon_on)
            return guard.diacritize(text)

        out, bi = [], 0
        for w in orig_words:
            if not w.strip():
                out.append(w)
                continue
            bare_word, start = bare_words[bi]
            bi += 1
            wl = logits[start:start + len(bare_word)]
            out.append(self._fuse_word(w, bare_word, wl))
        return " ".join(out)

    __call__ = diacritize
