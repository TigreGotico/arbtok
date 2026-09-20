"""A ya is [j] or a length mark, and the branches have to say which.

The character cascade read a ya through four branches, two of which returned
``"j"``: a diphthong test sitting immediately above an unguarded ``return "j"``.
The reading was right -- the glide of /aj/ IS [j] -- but a guard that cannot
change the answer reads to the next maintainer as if it could.
"""
import ast
import inspect

import pytest

from arbtok import tokenizer
from arbtok.tokenizer import WordToken

ALIF, FATHA, KASRA, SUKUN = "ا", "َ", "ِ", "ْ"
YA, BA, TA, NUN = "ي", "ب", "ت", "ن"


def test_the_last_guard_of_a_ya_decides_something():
    """The guard directly above the fallthrough must return something else.

    Anywhere else in the chain a guard may repeat the fallthrough's answer and
    still earn its place -- the shadda guard returns ``"j"`` and exists to stop
    the mater-lectionis branch under it from firing. The last guard has nothing
    left to pre-empt, so returning the fallthrough's own answer makes it dead.
    """
    body = ast.parse(inspect.getsource(tokenizer._ya_ipa)).body[0].body
    fallthrough = body[-1]
    assert isinstance(fallthrough, ast.Return)
    guards = [node for node in body if isinstance(node, ast.If)]
    returned = [node.value for node in guards[-1].body if isinstance(node, ast.Return)]
    assert returned, "the last guard of _ya_ipa no longer returns"
    assert ast.dump(returned[0]) != ast.dump(fallthrough.value)


@pytest.mark.parametrize("word, fragments", [
    # the glide of /aj/: a ya after fatha, closing the diphthong of bajt
    (BA + FATHA + YA + SUKUN + TA, ["b", "a", "j", "", "t"]),
    # the same ya carrying its own vowel: the consonant, bajat
    (BA + FATHA + YA + FATHA + TA, ["b", "a", "j", "a", "t"]),
    # the mater lectionis: the one reading that is not [j]
    (BA + KASRA + YA + NUN, ["b", "i", "ː", "n"]),
], ids=["diphthong glide", "consonant", "mater lectionis"])
def test_a_ya_reads_as_its_phone(word, fragments):
    assert [tok.ipa for tok in WordToken(surface=word, word_idx=0).tokens] == fragments
