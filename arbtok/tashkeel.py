"""Diacritization (tashkeel) via text2tashkeel.

arbtok delegates diacritization to ``text2tashkeel`` — a model picker
over bundled ONNX diacritization models (no PyTorch, offline by
default). ``TashkeelDiacritizer`` is a thin convenience wrapper.

``pausal=True`` rewrites the word-final case vowels
(fatha/damma/kasra and the damm/kasr tanwīn) to sukūn — the pausal
form used when citing isolated words, which is also how dictionary
lexicons transcribe them.
"""
import re
from typing import Optional

from text2tashkeel import Diacritizer

__all__ = ["TashkeelDiacritizer", "TashkeelError"]

# word-final short case vowels and damm/kasr tanwin → sukun (pausal);
# the fath tanwin (ً) keeps its pausal long-a reading and is left alone
_PAUSAL_RE = re.compile(r"[ٌٍَُِ](?=\s|$)")
_SUKUN = "ْ"


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

        ``pausal=True`` turns word-final case vowels into sukūn.
        """
        try:
            diacritized = self._diacritizer.diacritize(text)
        except Exception as exc:
            raise TashkeelError(str(exc)) from exc
        if pausal:
            diacritized = _PAUSAL_RE.sub(_SUKUN, diacritized)
        return diacritized
