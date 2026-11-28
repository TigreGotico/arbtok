"""Draw docs/img/lect-benchmark.svg: PER of each lect for the two arbtok arms and espeak-ng.

Run from the repo root: python docs/img/plot_lect_benchmark.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).parent))
from plot_style import save  # noqa: E402

lects = json.loads((ROOT / "benchmarks" / "lect_results.json").read_text(encoding="utf-8"))["lects"]
codes = sorted(lects, key=lambda c: lects[c]["arbtok_diac"]["per"])
ARMS = (("arbtok_diac", "arbtok, diacritized"), ("arbtok_undiac", "arbtok, bare"),
        ("espeak", "espeak-ng (MSA voice)"))


data = {"lects": codes,
        "arms": {key: [lects[c][key]["per"] if lects[c][key] else None for c in codes]
                 for key, _ in ARMS}}


def draw(fig, theme, data):
    ax = fig.subplots()
    y = range(len(data["lects"]))
    for colour, (key, label) in zip(theme["series"], ARMS):
        points = [(per, i) for i, per in zip(y, data["arms"][key]) if per is not None]
        ax.scatter([p for p, _ in points], [i for _, i in points],
                   s=22, color=colour, label=label, zorder=3)
    ax.set_yticks(list(y), data["lects"], fontsize=7)
    ax.invert_yaxis()
    ax.set_xlim(0, None)
    ax.set_xlabel("PER against the o2i Arabic TTS gold (lower is better)")
    ax.set_title("PER by lect", fontsize=9)
    ax.grid(axis="y", visible=False)
    ax.legend(loc="lower right", fontsize=8)


save(str(ROOT / "docs" / "img" / "lect-benchmark"), draw, data, width=7, height=7.5)
