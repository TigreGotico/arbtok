"""Diacritization (tashkeel) via the bundled rawi ensemble.

arbtok is self-contained: diacritization runs on the stitched rawi ensemble ONNX
shipped inside the wheel (:mod:`arbtok._ensemble` — onnxruntime + numpy, no
network, no external diacritization package). ``TashkeelDiacritizer`` is a thin
convenience wrapper over it.

``pausal=True`` drops the word-final case and mood endings (iʿrāb), leaving the
pausal form that is actually spoken — the model restores the full endings, which
is right for a pedagogical text and stilted for speech. The transform is
deterministic and rule-cited (:func:`arbtok.waqf.pausal`): it lengthens tanwīn
al-fatḥ rather than dropping it, keeps a shadda's gemination, and leaves a
lexical final vowel (a pronoun's) alone.
"""

from arbtok.waqf import pausal as _pausal

__all__ = ["TashkeelDiacritizer", "TashkeelError"]

class TashkeelError(Exception):
    """Error raised when diacritization fails."""


class TashkeelDiacritizer:
    """Add diacritics to Arabic text, using the bundled rawi ensemble.

    The decision is a constrained argmax over the ensemble distribution: the
    model cannot rewrite a letter the writing spells and cannot overwrite a mark
    a human wrote (see :mod:`arbtok._ensemble`).
    """

    def __init__(self) -> None:
        from arbtok._ensemble import get_ensemble
        self._diacritizer = get_ensemble()

    def __call__(self, text: str, pausal: bool = False) -> str:
        return self.diacritize(text, pausal=pausal)

    def diacritize(self, text: str, pausal: bool = False) -> str:
        """Return *text* with diacritics restored.

        ``pausal=True`` drops the case and mood endings, leaving the form
        that is spoken (:func:`arbtok.waqf.pausal`).
        """
        try:
            diacritized = self._diacritizer.diacritize(text)
        except Exception as exc:
            raise TashkeelError(str(exc)) from exc
        if pausal:
            diacritized = _pausal(diacritized)
        return diacritized
