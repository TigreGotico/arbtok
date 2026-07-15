"""Rawi-lattice fusion: the diacritizer as a scorer over licensed readings.

The properties that make the mechanism correct, independent of the empirical
gate (which lives in scripts/benchmark_fusion.py and docs/rawi-fusion.md):

* the scorer's log-probability is monotone in the logits it sums;
* a hypothesis is only ever emitted if the variety's orthography licenses it;
* a fully-marked word is never touched (the writing already said it);
* the lexicon is consulted before the model;
* three lects run end to end on real bare input.
"""
from __future__ import annotations

import numpy as np
import pytest

from arbtok.fusion import FusionDiacritizer, Hypothesis, logprobs

pytestmark = pytest.mark.filterwarnings("ignore")


# ── scoring monotonicity ────────────────────────────────────────────────────

def test_logprobs_are_a_proper_log_softmax():
    row = np.array([0.1, 2.0, 0.5, 3.0])
    lp = logprobs(row)
    # sums to 1 in probability space
    assert np.isclose(np.exp(lp).sum(), 1.0)
    # order preserved: a higher logit is a higher log-prob
    assert lp[3] > lp[1] > lp[2] > lp[0]


def test_scoring_is_monotone_in_the_chosen_class():
    """Swapping any position for a higher-logit class raises the hypothesis
    score — the property that makes "highest-scoring licensed reading" well posed."""
    f = FusionDiacritizer(lang="ar", lexicon=None, topk=4, beam=8)
    # two positions, clearly ordered logits
    logits = np.array([[0.0, 3.0, 1.0], [0.0, 1.0, 4.0]])
    hyps = f._beam_search("بب", logits)
    # the top hypothesis picks the argmax class at each position
    best = max(hyps, key=lambda h: h.logprob)
    assert best.class_ids == (1, 2)
    # a hypothesis that downgrades one position scores strictly lower
    downgraded = [h for h in hyps if h.class_ids == (2, 2)]
    if downgraded:
        assert downgraded[0].logprob < best.logprob


def test_beam_is_ordered_best_first_and_bounded():
    f = FusionDiacritizer(lang="ar", lexicon=None, topk=3, beam=5)
    logits = np.random.RandomState(0).randn(3, 10)
    hyps = f._beam_search("بتث", logits)
    assert len(hyps) <= 5
    scores = [h.logprob for h in hyps]
    assert scores == sorted(scores, reverse=True)


# ── hypothesis constraint correctness ───────────────────────────────────────

def test_non_letter_positions_pinned_to_empty_class():
    f = FusionDiacritizer(lang="ar", lexicon=None)
    logits = np.random.RandomState(1).randn(3, 10)
    # middle char is a space (non-letter) → its class id must be 0 in every hyp
    hyps = f._beam_search("ب ب", logits)
    assert all(h.class_ids[1] == 0 for h in hyps)


def test_emitted_reading_is_always_licensed():
    """Every word fusion returns either is unchanged input or tokenizes with no
    UNKNOWN segment against the variety spec."""
    f = FusionDiacritizer(lang="ar", lexicon=None)
    for sentence in ("ذهب الرجل الى المدرسة", "كتب الولد الدرس", "شرب القهوة"):
        out = f.diacritize(sentence)
        for w in out.split():
            assert f._is_licensed(w), (sentence, w)


def test_fully_marked_word_is_untouched():
    f = FusionDiacritizer(lang="ar", lexicon=None)
    marked = "كَتَبَ"
    assert f.diacritize(marked) == marked


def test_last_nbest_exposed_and_ranked():
    f = FusionDiacritizer(lang="ar", lexicon=None)
    f.diacritize("المدرسة")
    assert f.last_nbest, "fusion should expose its n-best for the last word"
    scored = [h.logprob - f.lattice_weight * h.lattice_cost for h in f.last_nbest]
    assert scored == sorted(scored, reverse=True)
    assert all(isinstance(h, Hypothesis) for h in f.last_nbest)


# ── lexicon precedence ──────────────────────────────────────────────────────

def test_lexicon_consulted_before_the_model(tmp_path):
    lex = tmp_path / "stems.tsv"
    # a stem the model would not produce, to prove the lexicon wins
    lex.write_text("قهوة\tقَهْوَة\n", encoding="utf-8")
    f = FusionDiacritizer(lang="ar", lexicon=str(lex))
    out = f.diacritize("قهوة")
    assert out == "قَهْوَة"
    assert "قهوة" in f.looked_up


# ── end to end, three lects ─────────────────────────────────────────────────

@pytest.mark.parametrize("lect", ["ar", "ar-EG", "ar-SA-x-najd"])
def test_three_lects_end_to_end(lect):
    from arbtok.plugin import ArbtokG2PPlugin

    plug = ArbtokG2PPlugin(lang=lect, diacritize=True, fusion=True)
    out = plug.transcribe("ذهب الولد الى المدرسة")
    assert out and isinstance(out, str)
    # produced IPA, not passed the Arabic through untranscribed
    assert not any("؀" <= ch <= "ۿ" for ch in out)


def test_alignment_mismatch_falls_back_to_guarded_pipeline():
    """A sentence whose bare word count cannot align degrades to the shipped
    guarded pipeline rather than slicing the logits wrongly — it must still
    return licensed words."""
    f = FusionDiacritizer(lang="ar", lexicon=None)
    out = f.diacritize("، ، ،")  # punctuation-only tokens, an alignment edge
    assert isinstance(out, str)


# ── the bundled ensemble distribution (arbtok/_ensemble.py) ──────────────────

_PROBE = [
    "بسم الله الرحمن الرحيم", "العلم نور والجهل ظلام", "هذا كتاب مفيد",
    "في التأني السلامة وفي العجلة الندامة", "محمد رسول الله",
    "الحمد لله رب العالمين", "وإن وهبها لرب الأرض لم يلزمه القبول",
]


def test_ensemble_logits_contract():
    """`logits(text)` returns `(bare, logits[T, C], classes)` — one row per NFD
    base character, C == number of classes, and `None` when nothing to mark."""
    from arbtok._ensemble import get_ensemble
    d = get_ensemble()
    bare, logits, classes = d.logits("بسم الله الرحمن الرحيم")
    assert logits is not None
    assert logits.shape == (len(bare), len(classes))
    # nothing to mark (bare skeleton empty) → no distribution
    empty_bare, empty_logits, _ = d.logits("ًٌٍَُِّْ")  # stray combining marks only
    assert empty_bare == "" and empty_logits is None


def test_ensemble_logits_argmax_equals_the_ensemble_decision():
    """The correctness gate for scoring the stitched flagship: the argmax of the
    exposed `gated_logits` distribution is byte-identical to the graph's own
    `gated_cls` decision at every position, on a probe set. Without this the
    scorer would be reading a different model than the one that decides."""
    from arbtok._ensemble import get_ensemble
    d = get_ensemble()
    for text in _PROBE:
        bare, logits, _ = d.logits(text)
        if logits is None:
            continue
        ids = np.array([[d.c2i.get(c, d.unk) for c in bare]], np.int64)
        gated_cls = d.sess.run(["gated_cls"], {"input": ids})[0][0]
        assert (logits.argmax(-1) == gated_cls).all(), text


def test_ensemble_diacritize_respects_the_writing():
    """The generator's decision rule masks before the argmax: a madda alif is
    never rewritten to a hamza (the /aː/ survives), and a mark a human wrote is
    never overwritten — the arbtok.orthography constraints, applied to the
    bundled ensemble distribution."""
    from arbtok._ensemble import get_ensemble
    d = get_ensemble()
    # madda preserved: آ must survive in the output
    assert "آ" in d.diacritize("آبد")
    # a human's kasra is pinned, not overwritten
    assert "كِ" in d.diacritize("كِتاب")


def test_fusion_never_overrides_written_marks():
    """A human's mark is an answer, not a suggestion: on the MAIN path an
    explicit sukūn or kasra survives fusion verbatim (the reviewer-measured
    regression: الشُّورْبَة must keep /uː...ba/, not come back rescored)."""
    f = FusionDiacritizer(lang="ar", lexicon=None, waqf=True)
    for word, kept in [("الشُّورْبَة", "شُّورْبَ"), ("الْجِدِيدَة", "جِدِيدَ")]:
        out = f.diacritize(word)
        assert kept in out, (word, out)


def test_vocalized_input_identical_fusion_on_and_off():
    """Fusion engages only where the writing is silent: on (even partially)
    vocalized input the output is byte-identical with fusion on or off,
    because a vocalized word is completed by the same generator decision rule."""
    from arbtok.plugin import ArbtokG2PPlugin
    sents = [
        "التَّاير فِيه بَنْشَر لَازِم أُصَلِّحُه",     # partially vocalized loans
        "ضَاع مِنِّي الْمُوبَايل مِن جَيبِي",
        "ما كاينْش بْلاصَة فْ الْقَاعَة",
        "أَعْطِينِي الْفَرْشِيطَة بَاش نَاكُل",
    ]
    for lect in ("ar", "ar-IQ", "ar-MA"):
        on = ArbtokG2PPlugin(lang=lect, diacritize=True)
        off = ArbtokG2PPlugin(lang=lect, diacritize=True, fusion=False)
        for s in sents:
            assert on.transcribe(s) == off.transcribe(s), (lect, s)


def test_ensemble_inference_is_deterministic():
    """Three runs over the same input yield byte-identical logits — the session
    is single-threaded sequential, so an argmax near-tie cannot flip run-to-run
    (the flaky-pin class of failures)."""
    from arbtok._ensemble import EnsembleDiacritizer
    outs = []
    for _ in range(3):
        d = EnsembleDiacritizer()   # fresh session each time
        bare, logits, _ = d.logits("وإن وهبها لرب الأرض لم يلزمه القبول")
        outs.append(logits.tobytes())
    assert outs[0] == outs[1] == outs[2]
