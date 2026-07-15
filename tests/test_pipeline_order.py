"""Diacritization is an MSA stage; dialect allophony is a later stage.

The stem lexicon and the tashkeel model are both trained on Modern Standard
Arabic, and dialect text is *written* in MSA orthography. So the pipeline
restores the missing short vowels on the MSA-shaped orthography **first**, and
only then does the word lattice apply the target variety's allophony (the qāf
reflex, affrication, …) to the resulting segments.

The order is observable: a bare word phonemized for Najdi comes out with both
its restored vowels *and* the Najdi qāf → /ɡ/ reflex. Neither stage alone
produces that string, so a run that gets it has run them in this order.
"""
import pytest

from arbtok.diacritize import LatticeDiacritizer
from arbtok.plugin import ArbtokG2PPlugin


@pytest.fixture(scope="module")
def diacritizer_available():
    # The order pin needs the tashkeel model to actually restore the vowels;
    # if the model is absent the stage is a pass-through and there is nothing
    # to order. Match the rest of the suite, which assumes it is present.
    try:
        LatticeDiacritizer(lexicon=None).diacritize("قلم")
        return True
    except Exception:  # pragma: no cover - only when weights are missing
        return False


def _phon(word, lang, diacritize):
    return ArbtokG2PPlugin(lang=lang, diacritize=diacritize).transcribe(word)


def test_diacritization_runs_before_dialect_allophony(diacritizer_available):
    """Bare ``قلم`` → Najdi carries restored vowels *and* the qāf reflex.

    - ``ar``, diacritized: ``ˈqalam`` — MSA vowels restored, qāf kept.
    - ``ar-SA-x-najd``, diacritized: ``ˈɡalam`` — the *same* restored vowels,
      with the Najdi qāf → /ɡ/ reflex now applied on top.
    - ``ar-SA-x-najd``, **not** diacritized: ``ɡlm`` — the reflex fired on a
      bare consonant skeleton, no vowels.

    ``ˈɡalam`` can only exist if the MSA diacritizer ran (it supplied the
    ``a…a`` the bare form lacks) and the Najdi allophony ran *after* it (it
    supplied the /ɡ/). Reverse the stages and the diacritizer, an MSA model,
    would be asked to vowel a string the lattice has already turned to IPA.
    """
    if not diacritizer_available:
        pytest.skip("tashkeel model unavailable; diacritization is pass-through")

    assert _phon("قلم", "ar", diacritize=True) == "ˈqalam"
    assert _phon("قلم", "ar-SA-x-najd", diacritize=True) == "ˈɡalam"
    # No diacritization: the reflex still fires, but on the bare skeleton.
    assert _phon("قلم", "ar-SA-x-najd", diacritize=False) == "ɡlm"


def test_the_lexicon_and_diacritizer_read_msa_orthography(diacritizer_available):
    """The MSA stages are lect-agnostic: they see orthography, not phonology.

    ``ar-EG`` sends qāf → /ʔ/, yet the bare word still diacritizes and reads,
    proving the MSA diacritizer is not confused by the target being Egyptian —
    it works the orthography, and the Egyptian reflex lands afterwards.
    """
    if not diacritizer_available:
        pytest.skip("tashkeel model unavailable; diacritization is pass-through")

    assert _phon("قلم", "ar-EG", diacritize=True) == "ˈʔalam"
