"""The rawi flagship ensemble as a *scorer* — a self-contained onnxruntime reader
for the stitched ``rawi-v2 + rawi-v3`` graph, bundled inside arbtok.

Why this lives in arbtok and not behind ``text2tashkeel.Diacritizer``: fusion
needs the ensemble's decision **as a distribution**, and the flagship text2tashkeel
ships is a *stitched* ONNX that folds its gate into the graph and returns an argmax
only — no distribution to score (that is the limiting factor docs/rawi-fusion.md
names). This module reads a re-export of that same graph which additionally emits
``gated_logits``: the rawi-v3 value-head logits with class 0 lifted just above the
row max wherever the rawi-v2 gate is bare, so ``logits.argmax(-1)`` is byte-
identical to the model's own ``gated_cls`` decision while the rest of the
distribution stays the value head's real per-class scores. arbtok bundles that
one artifact and reads it directly (no text2tashkeel model dependency for the
scoring path); see tools/build_ensemble_logits_onnx.py for how it was produced.

Interface parity: the object exposes exactly the three methods fusion consumes
from a text2tashkeel diacritizer — :meth:`logits`, :meth:`decode`,
:meth:`diacritize` — so :class:`arbtok.fusion.FusionDiacritizer` is agnostic to
which one it holds.
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
    argmax, the ensemble's own decision.
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
        """Return ``(bare, logits[T, C], classes)`` — the same contract as
        ``text2tashkeel.Diacritizer.logits``. ``bare`` is the NFD base sequence the
        model saw; ``logits`` is ``None`` when there is nothing to mark."""
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

    def diacritize(self, text: str) -> str:
        """The ensemble's own argmax reading — its ``gated_cls`` decoded. Used only
        on fusion's fallback path (nothing licensed) and its book-keeping."""
        bare = self._bare(text)
        if not bare:
            return text
        ids = np.array([[self.c2i.get(c, self.unk) for c in bare]], np.int64)
        cls = self.sess.run(["gated_cls"], {"input": ids})[0][0]
        return self.decode(bare, cls)


@lru_cache(maxsize=None)
def get_ensemble() -> EnsembleDiacritizer:
    """A shared, lazily-built ensemble reader (the ONNX session is built once)."""
    return EnsembleDiacritizer()
