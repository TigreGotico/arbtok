"""arbtok against plain orthography2ipa, on gold neither of them produced.

Salesteq/arabic-dialects-gold20 cannot answer this. Its IPA column was made by
correcting orthography2ipa's own output against the literature, so the reference
descends from one of the systems under test. Having LLM judges re-transcribe that
output does not break the loop: the thing being judged is still the engine's answer,
and a judge that agrees with it is agreeing with the system, not with a speaker.

IqraEval's Qur'anic gold is written by a third party in Halabi notation, from recitation
rather than from any grapheme-to-phoneme engine, so a comparison scored on it is a
measurement rather than a mirror.

Two inputs and two engines, so the diacritizer's contribution separates from the
grapheme mapping's:

  * diacritized input  -- both engines see the vowels; this compares phone mapping alone
  * bare input         -- the marks are stripped; arbtok points the text, plain o2i cannot
"""
import argparse, json, sys, unicodedata

from benchmark_iqraeval import load_gold, normalize, phoneme_ref_to_ipa, score

MARKS = set("ًٌٍَُِّْٰ")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", default="dev")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--json", default=None)
    a = ap.parse_args()

    from arbtok.plugin import ArbtokG2PPlugin
    from orthography2ipa.g2p import G2P

    rows = load_gold(a.split, limit=a.limit)
    assert len(rows) > 100, f"control failed: only {len(rows)} gold rows loaded"
    print(f"IqraEval/{a.split}: {len(rows)} rows (third-party gold, Halabi notation)",
          file=sys.stderr)

    plain = G2P("ar")
    arms = {
        "o2i_diac":    (plain.transcribe, False),
        "arbtok_diac": (ArbtokG2PPlugin(lang="ar", diacritize=False, register="full").transcribe, False),
        "o2i_bare":    (plain.transcribe, True),
        "arbtok_bare": (ArbtokG2PPlugin(lang="ar", diacritize=True, register="full").transcribe, True),
    }
    out = {}
    for name, (fn, undiac) in arms.items():
        metrics, _ = score(rows, fn, undiac=undiac)
        out[name] = metrics
        print(f"  {name:14s} PER {metrics['per']:.4f}  n={metrics['n']}", file=sys.stderr)

    print()
    print(f"IqraEval/{a.split}, n={out['o2i_diac']['n']} — PER, lower is better")
    print(f"  {'input':22s} {'plain o2i':>10s} {'arbtok':>10s} {'delta':>10s}")
    for label, k in (("diacritized (as written)", "diac"), ("bare (marks stripped)", "bare")):
        o, b = out[f"o2i_{k}"]["per"], out[f"arbtok_{k}"]["per"]
        print(f"  {label:22s} {o:10.4f} {b:10.4f} {o - b:+10.4f}")

    if a.json:
        json.dump(out, open(a.json, "w"), indent=1)
        print(f"wrote {a.json}", file=sys.stderr)


if __name__ == "__main__":
    main()
