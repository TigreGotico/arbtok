"""The rawi flagship ensemble, bundled inside arbtok — the ONLY diacritization
model arbtok consults at runtime.

The artifact (``arbtok/models/rawi_ensemble.logits.int8.onnx``) is a stitched
``rawi-v2 + rawi-v3`` gated ensemble (rawi-v2 decides WHERE a mark goes, rawi-v3's
value head decides WHICH) re-exported with a second output, ``gated_logits``: the
value-head logits with class 0 lifted just above the row max wherever the gate is
bare, so ``logits.argmax(-1)`` is byte-identical to the graph's own ``gated_cls``
decision while the rest of each row keeps the value head's real per-class scores.
That gives every caller the ensemble's decision **as a distribution** — which is
what lets the writing constrain the decision (mask, below) and lets the lattice
score licensed readings (:mod:`arbtok.fusion`). Provenance: the member weights are
the TigreGotico rawi family, published in the ``text2tashkeel`` wheel on PyPI
(Apache-2.0); ``tools/build_ensemble_logits_onnx.py`` reproduces the re-export and
asserts the argmax-agreement gate. Reading it takes onnxruntime + numpy only.

The scorer (:mod:`arbtok.fusion`), the guarded generator
(:mod:`arbtok.diacritize`) and the convenience wrapper (:mod:`arbtok.tashkeel`)
all read this one model — they are decision rules over one distribution.

Decision-time constraints (:mod:`arbtok.orthography`): because the distribution
is available, :meth:`EnsembleDiacritizer.diacritize` masks the classes the
writing contradicts *before* the argmax — the model cannot rewrite a letter the
writing spells (the madda-destruction class of errors) and cannot overwrite a
mark a human wrote, because the classes that would do either are never choosable
at all.
"""

from __future__ import annotations

import json
import unicodedata
from functools import lru_cache
from pathlib import Path

import numpy as np
import onnxruntime as ort

_MODELS_DIR = Path(__file__).parent / "models"
#: The stitched flagship re-export that also emits the pre-argmax distribution.
DEFAULT_ENSEMBLE_ONNX = _MODELS_DIR / "rawi_ensemble.logits.int8.onnx"
#: rawi-v2/v3 share this vocab (NFD char ids + diacritic-class strings).
DEFAULT_VOCAB = _MODELS_DIR / "rawi_v2.vocab.json"


class EnsembleDiacritizer:
    """Read the bundled stitched ensemble ONNX directly.

    rawi normalizes to NFD (أ → ا + hamza) and drops Unicode symbol (``So``)
    characters; marks (category ``Mn``) are stripped so the model always predicts
    from a bare skeleton, and are re-applied only to letters (``L*``). The graph's
    ``gated_logits`` output is the distribution to score; ``gated_cls`` is its
    argmax, the ensemble's own unconstrained decision.
    """

    def __init__(self, model_path=DEFAULT_ENSEMBLE_ONNX, vocab_path=DEFAULT_VOCAB,
                 providers=None) -> None:
        v = json.loads(Path(vocab_path).read_text(encoding="utf-8"))
        self.c2i = dict(v["char_to_idx"])
        self.i2d = {i: s for s, i in dict(v["diac_to_idx"]).items()}
        self.unk = self.c2i.get("<UNK>", 1)
        self.sess = ort.InferenceSession(
            str(model_path), providers=providers or ["CPUExecutionProvider"])

    @property
    def classes(self):
        """The diacritic-class strings, indexed by class id."""
        return [self.i2d[i] for i in range(len(self.i2d))]

    @staticmethod
    def _normalize(text: str) -> str:
        return "".join(
            c for c in unicodedata.normalize("NFD", text)
            if unicodedata.category(c) != "So"
        )

    def _bare(self, text: str) -> str:
        return "".join(
            c for c in self._normalize(text) if unicodedata.category(c) != "Mn"
        )

    def logits(self, text: str):
        """Return ``(bare, logits[T, C], classes)`` — the raw distribution, before
        any decision. ``bare`` is the NFD base sequence the model saw; ``logits``
        is ``None`` when there is nothing to mark.

        Raw and unconstrained by design: masking is a *decision-time* concern,
        and a scorer (fusion) applies its own constraints — the variety's
        licensing — instead of the generic orthographic ones."""
        bare = self._bare(text)
        if not bare:
            return bare, None, self.classes
        ids = np.array([[self.c2i.get(c, self.unk) for c in bare]], np.int64)
        out = self.sess.run(["gated_logits"], {"input": ids})[0][0]
        return bare, out, self.classes

    def decode(self, bare: str, class_ids) -> str:
        """Recompose *bare* with one class id per character (NFC)."""
        out = "".join(
            ch + (self.i2d[int(p)] if unicodedata.category(ch).startswith("L") else "")
            for ch, p in zip(bare, class_ids)
        )
        return unicodedata.normalize("NFC", out)

    def _constrained_argmax(self, text: str, bare: str, logits) -> np.ndarray:
        """Argmax under the orthographic mask — see :mod:`arbtok.orthography`.

        The classes that contradict the source are removed BEFORE the argmax: a
        letter the writing spells (hamza, madda) cannot be rewritten, and a mark
        a human already wrote is pinned to exactly what is written. Where the
        writing is silent the model stays free — restoring a hamza to a
        defectively-spelled alif is its documented job, not a bug.
        """
        from arbtok.orthography import (
            ORTHOGRAPHIC_MARKS, allowed_classes, pinned_class, source_marks,
        )
        src_bare, src_marks = source_marks(text, self._normalize)
        if src_bare != bare or len(src_marks) != len(bare):
            # The decompositions disagree, so a mask built from one cannot be
            # trusted against the other. Decide unconstrained rather than guess.
            return logits.argmax(-1)
        classes = self.classes
        out = np.empty(len(bare), dtype=np.int64)
        for i, ch in enumerate(bare):
            if not unicodedata.category(ch).startswith("L"):
                out[i] = 0
                continue
            marks = src_marks[i]
            if marks - ORTHOGRAPHIC_MARKS:
                # The writing already says it. Pin to exactly what is written.
                pin = pinned_class(classes, marks)
                if pin >= 0:
                    out[i] = pin
                    continue
            allowed = allowed_classes(classes, marks)
            row = logits[i]
            out[i] = max(allowed, key=lambda j: row[j]) if allowed else 0
        return out

    def diacritize(self, text: str) -> str:
        """Return *text* with the ensemble's constrained-argmax reading applied.

        The generator's decision rule: mask the classes the writing contradicts,
        then take the best of what remains (:meth:`_constrained_argmax`)."""
        bare, logits, _ = self.logits(text)
        if not bare:
            return text
        return self.decode(bare, self._constrained_argmax(text, bare, logits))


@lru_cache(maxsize=None)
def get_ensemble() -> EnsembleDiacritizer:
    """A shared, lazily-built ensemble reader (the ONNX session is built once)."""
    return EnsembleDiacritizer()
