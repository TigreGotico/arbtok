"""Diacritization (tashkeel) via text2tashkeel.

arbtok delegates diacritization to ``text2tashkeel`` — a model picker
over bundled ONNX diacritization models (no PyTorch, offline by
default). ``TashkeelDiacritizer`` is a thin convenience wrapper.

``pausal=True`` drops the word-final case and mood endings (iʿrāb),
leaving the pausal form that is actually spoken — the models restore the
full endings, which is right for a pedagogical text and stilted for
speech. The transform is text2tashkeel's own (:func:`text2tashkeel.pausal`),
so the two libraries cannot drift: it also lengthens tanwīn al-fatḥ rather
than dropping it, keeps a shadda's gemination, and leaves a lexical final
vowel (a pronoun's) alone.
"""
from typing import Optional

from text2tashkeel import Diacritizer, pausal as _pausal

__all__ = ["TashkeelDiacritizer", "TashkeelError"]

class TashkeelError(Exception):
    """Error raised when diacritization fails."""


class TashkeelDiacritizer:
    """Add diacritics to Arabic text.

    Wraps :class:`text2tashkeel.Diacritizer`; pass ``model`` to pick a
    specific configuration (default: text2tashkeel's flagship
    ensemble).
    """

    def __init__(self, model: Optional[str] = None) -> None:
        self._diacritizer = (Diacritizer(model) if model
                             else Diacritizer())

    def __call__(self, text: str, pausal: bool = False) -> str:
        return self.diacritize(text, pausal=pausal)

    def diacritize(self, text: str, pausal: bool = False) -> str:
        """Return *text* with diacritics restored.

        ``pausal=True`` drops the case and mood endings, leaving the form
        that is spoken (:func:`text2tashkeel.pausal`).
        """
        try:
            diacritized = self._diacritizer.diacritize(text)
        except Exception as exc:
            raise TashkeelError(str(exc)) from exc
        if pausal:
            diacritized = _pausal(diacritized)
        return diacritized
