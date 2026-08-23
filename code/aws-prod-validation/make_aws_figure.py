"""Render Figure 10: real-AWS validation results (worst-case AUC per scorer and per domain).

Reads aggregate_results.json and writes ../../figures/figure10_aws_validation.png.
Author: Viquar Khan (ORCID 0009-0008-3592-4162). Copyright 2026 Viquar Khan.
"""
from __future__ import annotations

import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
FIG = os.path.normpath(os.path.join(HERE, "..", "..", "figures", "figure10_aws_validation.png"))

SHORT = {"RVx (multiplicative)": "RVx (mult.)", "additive mean": "additive",
         "hard minimum": "hard-min", "geometric mean": "geo-mean",
         "efficiency only (E)": "E only", "distinctness only (S)": "S only",
         "inverse load only (1-L)": "1-L only"}


def main() -> int:
    with open(os.path.join(HERE, "aggregate_results.json"), encoding="utf-8") as f:
        agg = json.load(f)
    scorers = list(SHORT.keys())
    domains = ["latency-heavy", "cost-heavy", "reliability-heavy"]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5.2))

    # Panel A: AUC per domain (grouped bars)
    x = range(len(scorers))
    w = 0.26
    colors = ["#3b7dd8", "#e0912a", "#4aa564"]
    for di, d in enumerate(domains):
        vals = [agg["per_domain"][f"{d}|{s}"][0] for s in scorers]
        errs = [agg["per_domain"][f"{d}|{s}"][1] for s in scorers]
        ax1.bar([xi + (di - 1) * w for xi in x], vals, w, yerr=errs, capsize=2,
                label=d, color=colors[di])
    ax1.axhline(0.5, color="gray", ls="--", lw=1)
    ax1.set_xticks(list(x))
    ax1.set_xticklabels([SHORT[s] for s in scorers], rotation=35, ha="right", fontsize=9)
    ax1.set_ylabel("ROC AUC")
    ax1.set_ylim(0.4, 0.9)
    ax1.set_title("(a) Separation AUC per domain (real AWS, 5 reps)")
    ax1.legend(fontsize=8, loc="upper right")

    # Panel B: worst-case AUC (robustness)
    wc = [(s, agg["worst_case"][s][0], agg["worst_case"][s][1]) for s in scorers]
    wc.sort(key=lambda t: t[1], reverse=True)
    names = [SHORT[s] for s, _, _ in wc]
    vals = [v for _, v, _ in wc]
    errs = [e for _, _, e in wc]
    bar_colors = ["#4aa564" if n == "additive" else ("#3b7dd8" if n == "RVx (mult.)" else "#9aa7b4")
                  for n in names]
    ax2.barh(range(len(names)), vals, xerr=errs, capsize=3, color=bar_colors)
    ax2.set_yticks(range(len(names)))
    ax2.set_yticklabels(names, fontsize=9)
    ax2.invert_yaxis()
    ax2.axvline(0.5, color="gray", ls="--", lw=1)
    ax2.set_xlabel("worst-case ROC AUC across domains")
    ax2.set_xlim(0.4, 0.8)
    ax2.set_title("(b) Cross-domain robustness (higher = better)")

    fig.tight_layout()
    fig.savefig(FIG, dpi=150, bbox_inches="tight")
    print(f"wrote {FIG}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
