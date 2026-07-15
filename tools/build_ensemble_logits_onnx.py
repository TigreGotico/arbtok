"""Re-export the stitched rawi ensemble so it also emits a scorable distribution.

arbtok bundles ``arbtok/models/rawi_ensemble.logits.int8.onnx`` — a re-export of
text2tashkeel's stitched ``rawi-v2 + rawi-v3`` flagship. The shipped stitched graph
folds the gate in and returns ``gated_cls`` (an argmax) only; this re-export adds a
second output, ``gated_logits``, the pre-argmax distribution fusion scores.

    gated_cls    = where(argmax(rawi_v2) == 0, 0, argmax(rawi_v3.value))
    gated_logits = rawi_v3.value logits, with class 0 lifted to (row max + margin)
                   at every position the gate zeroes

so ``argmax(gated_logits) == gated_cls`` everywhere (the correctness gate), while
the rest of the row keeps the value head's real per-class log-probabilities.

Provenance / build-time only: the member weights come from the text2tashkeel wheel
(``rawi_v2.int8.onnx``, ``rawi_v3.int8.onnx``, shared ``rawi_v2.vocab.json``). This
is **not** a runtime dependency — the stitched artifact is self-contained; arbtok
reads it with onnxruntime alone (arbtok/_ensemble.py). Run this only to regenerate
the bundled artifact:

    python tools/build_ensemble_logits_onnx.py -o arbtok/models/rawi_ensemble.logits.int8.onnx

Requires text2tashkeel installed (for its bundled member ONNX + vocab) and onnx.
"""
from __future__ import annotations

import argparse
import json
import unicodedata
from pathlib import Path

import numpy as np
import onnx
import onnxruntime as ort
from onnx import TensorProto, compose, helper, numpy_helper

#: How far class 0 is lifted above the row max where the gate is bare — enough to
#: win the argmax, small enough to leave the other classes' log-probabilities
#: essentially untouched for the scorer.
_GATE_MARGIN = 1.0


def _t2t_models_dir() -> Path:
    import text2tashkeel
    return Path(text2tashkeel.__file__).parent / "models"


def build(out_path: str, int8: bool = True) -> None:
    d = _t2t_models_dir()
    gate_f = "rawi_v2.int8.onnx" if int8 else "rawi_v2.onnx"
    val_f = "rawi_v3.int8.onnx" if int8 else "rawi_v3.onnx"
    g = compose.add_prefix(onnx.load(d / gate_f), prefix="g_")
    v = compose.add_prefix(onnx.load(d / val_f), prefix="v_")
    merged = compose.merge_models(g, v, io_map=[])     # parallel union (g_input, v_input)
    graph = merged.graph

    n_cls = len(json.loads((d / "rawi_v2.vocab.json").read_text())["diac_to_idx"])
    onehot0 = np.zeros(n_cls, np.float32); onehot0[0] = 1.0

    del graph.input[:]
    graph.input.append(
        helper.make_tensor_value_info("input", TensorProto.INT64, ["batch", "seq"]))
    graph.initializer.extend([
        numpy_helper.from_array(np.array(0, np.int64), "zero_i64"),
        numpy_helper.from_array(np.array([0], np.int64), "idx0_i64"),
        numpy_helper.from_array(np.array([2], np.int64), "axis2_i64"),
        numpy_helper.from_array(np.array(_GATE_MARGIN, np.float32), "gate_margin"),
        numpy_helper.from_array(onehot0, "onehot0"),
    ])
    graph.node.insert(0, helper.make_node("Identity", ["input"], ["v_input"]))
    graph.node.insert(0, helper.make_node("Identity", ["input"], ["g_input"]))
    graph.node.extend([
        helper.make_node("ArgMax", ["g_output"], ["g_cls"], axis=-1, keepdims=0),
        helper.make_node("ArgMax", ["v_value"], ["v_cls"], axis=-1, keepdims=0),
        helper.make_node("Equal", ["g_cls", "zero_i64"], ["is_bare"]),
        helper.make_node("Where", ["is_bare", "zero_i64", "v_cls"], ["gated_cls"]),
        # gated_logits = v_value with class 0 lifted above the row max where bare
        helper.make_node("ReduceMax", ["v_value"], ["v_max"], axes=[-1], keepdims=1),
        helper.make_node("Gather", ["v_value", "idx0_i64"], ["v_at0"], axis=-1),
        helper.make_node("Sub", ["v_max", "v_at0"], ["v_deficit"]),
        helper.make_node("Add", ["v_deficit", "gate_margin"], ["v_deficit_m"]),
        helper.make_node("Relu", ["v_deficit_m"], ["v_boost"]),
        helper.make_node("Cast", ["is_bare"], ["is_bare_f"], to=TensorProto.FLOAT),
        helper.make_node("Unsqueeze", ["is_bare_f", "axis2_i64"], ["is_bare_f3"]),
        helper.make_node("Mul", ["v_boost", "is_bare_f3"], ["boost_gated"]),
        helper.make_node("Mul", ["boost_gated", "onehot0"], ["boost_cls"]),
        helper.make_node("Add", ["v_value", "boost_cls"], ["gated_logits"]),
    ])
    del graph.output[:]
    graph.output.append(
        helper.make_tensor_value_info("gated_cls", TensorProto.INT64, ["batch", "seq"]))
    graph.output.append(
        helper.make_tensor_value_info(
            "gated_logits", TensorProto.FLOAT, ["batch", "seq", n_cls]))
    onnx.checker.check_model(merged)
    onnx.save(merged, out_path)
    print(f"wrote {out_path} ({Path(out_path).stat().st_size / 1e6:.1f} MB)")


def verify(out_path: str, int8: bool = True) -> None:
    """Two correctness gates, on a probe set:

    1. ``argmax(gated_logits) == gated_cls`` — the exposed distribution decides
       exactly what the graph decides;
    2. our ``gated_cls`` is byte-equal to text2tashkeel's *shipped* stitched
       ensemble's ``gated_cls`` — the re-export is the same model, plus an
       output, and nothing else.
    """
    d = _t2t_models_dir()
    val = json.loads((d / "rawi_v2.vocab.json").read_text())
    c2i = dict(val["char_to_idx"]); unk = c2i.get("<UNK>", 1)
    sess = ort.InferenceSession(out_path, providers=["CPUExecutionProvider"])
    ref_path = d / ("rawi_ensemble.int8.onnx" if int8 else "rawi_ensemble.onnx")
    ref = (ort.InferenceSession(str(ref_path), providers=["CPUExecutionProvider"])
           if ref_path.exists() else None)

    tests = [
        "بسم الله الرحمن الرحيم", "العلم نور والجهل ظلام", "هذا كتاب مفيد",
        "في التأني السلامة وفي العجلة الندامة", "محمد رسول الله",
        "الحمد لله رب العالمين", "وإن وهبها لرب الأرض لم يلزمه القبول",
    ]
    ok = True
    for t in tests:
        nfd = "".join(c for c in unicodedata.normalize("NFD", t)
                      if unicodedata.category(c) != "So")
        bare = "".join(c for c in nfd if unicodedata.category(c) != "Mn")
        if not bare:
            continue
        ids = np.array([[c2i.get(c, unk) for c in bare]], np.int64)
        cls, logits = sess.run(["gated_cls", "gated_logits"], {"input": ids})
        ok &= bool((logits[0].argmax(-1) == cls[0]).all())
        if ref is not None:
            ref_cls = ref.run(["gated_cls"], {"input": ids})[0]
            ok &= bool((cls == ref_cls).all())
    print("re-export correctness gates (argmax==gated_cls; ==shipped ensemble):", ok)
    assert ok


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("-o", "--out", default="arbtok/models/rawi_ensemble.logits.int8.onnx")
    ap.add_argument("--fp32", action="store_true", help="stitch the fp32 members")
    args = ap.parse_args()
    build(args.out, int8=not args.fp32)
    verify(args.out, int8=not args.fp32)


if __name__ == "__main__":
    main()
