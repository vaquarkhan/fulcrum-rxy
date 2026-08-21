"""Generate PNG figures for the Fulcrum paper (clean, no text overflow, no overlap).

Renders the four diagrams as publication-quality PNGs plus three data figures, into
./figures/*.png. Boxes are generously sized, labels are short, fonts fit inside boxes,
and arrows are routed to avoid crossing text.

Dependencies: matplotlib only. Run: python generate_figures.py
Author: Viquar Khan (ORCID 0009-0008-3592-4162). Copyright 2026 Viquar Khan.
"""
from __future__ import annotations

import os
import sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

OUT = os.path.join(os.path.dirname(__file__), "figures")
os.makedirs(OUT, exist_ok=True)

BLUE_FC, BLUE_EC = "#e8eef8", "#33518a"
GREEN_FC, GREEN_EC = "#e6f2e6", "#2f6b2f"
RED_FC, RED_EC = "#f8e9e9", "#96393a"
GREY = "#444444"
DPI = 200


def box(ax, cx, cy, w, h, text, fc=BLUE_FC, ec=BLUE_EC, fs=9):
    """Box centered at (cx, cy). clip_on=False so nothing is cut at the axes edge."""
    ax.add_patch(FancyBboxPatch((cx - w / 2, cy - h / 2), w, h,
                                boxstyle="round,pad=0.008,rounding_size=0.02",
                                linewidth=1.4, edgecolor=ec, facecolor=fc, zorder=2, clip_on=False))
    ax.text(cx, cy, text, ha="center", va="center", fontsize=fs, zorder=3,
            linespacing=1.25, clip_on=False)


def arrow(ax, p_from, p_to, color=GREY, rad=0.0, ls="-", label=None, lx=0.0, ly=0.03):
    ax.add_patch(FancyArrowPatch(p_from, p_to, arrowstyle="-|>", mutation_scale=13,
                                 linewidth=1.2, color=color, linestyle=ls,
                                 connectionstyle=f"arc3,rad={rad}", shrinkA=3, shrinkB=3,
                                 zorder=1, clip_on=False))
    if label:
        mx, my = (p_from[0] + p_to[0]) / 2 + lx, (p_from[1] + p_to[1]) / 2 + ly
        ax.text(mx, my, label, ha="center", va="center", fontsize=7.5, color=color,
                bbox=dict(boxstyle="round,pad=0.1", fc="white", ec="none"), zorder=4, clip_on=False)


def new_ax(w, h):
    fig, ax = plt.subplots(figsize=(w, h))
    # Margin beyond [0,1] so edge content is never clipped; tight bbox crops to content.
    ax.set_xlim(-0.04, 1.04)
    ax.set_ylim(-0.04, 1.04)
    ax.axis("off")
    return fig, ax


def save(fig, name):
    p = os.path.join(OUT, name)
    fig.savefig(p, dpi=DPI, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("wrote", p)


def figure1():
    fig, ax = new_ax(12, 4.6)
    ax.text(0.23, 0.92, "Monolith", ha="center", fontsize=13, fontweight="bold")
    y = 0.60
    box(ax, 0.10, y, 0.13, 0.15, "Module A")
    box(ax, 0.28, y, 0.13, 0.15, "Module B")
    box(ax, 0.46, y, 0.13, 0.15, "Module C")
    arrow(ax, (0.165, y), (0.215, y))
    arrow(ax, (0.345, y), (0.395, y))
    ax.text(0.28, 0.40, "in-process calls: cheap, reliable", ha="center", fontsize=8.5, style="italic")

    ax.text(0.78, 0.92, "Distributed Monolith", ha="center", fontsize=13, fontweight="bold")
    box(ax, 0.63, y, 0.13, 0.15, "Service A", fc=RED_FC, ec=RED_EC)
    box(ax, 0.80, y, 0.13, 0.15, "Service B", fc=RED_FC, ec=RED_EC)
    box(ax, 0.97, y, 0.13, 0.15, "Service C", fc=RED_FC, ec=RED_EC)
    arrow(ax, (0.695, y + 0.02), (0.735, y + 0.02), color=RED_EC, label="sync RPC", ly=0.055)
    arrow(ax, (0.865, y + 0.02), (0.905, y + 0.02), color=RED_EC, label="sync RPC", ly=0.055)
    arrow(ax, (0.735, y - 0.03), (0.695, y - 0.03), color="#bf8a8a", ls="--", rad=-0.4)
    arrow(ax, (0.905, y - 0.03), (0.865, y - 0.03), color="#bf8a8a", ls="--", rad=-0.4)
    ax.text(0.80, 0.36, "remote calls add latency and failure modes;\nreverse edges show the coupling was never removed",
            ha="center", fontsize=8.5, style="italic", color=RED_EC)
    ax.text(0.5, 0.10, "Figure 1. The same call chain split along the wrong boundary becomes a distributed monolith.",
            ha="center", fontsize=9.5)
    save(fig, "figure1_granularity_paradox.png")


def figure2():
    fig, ax = new_ax(12, 5.2)
    # inputs
    box(ax, 0.11, 0.78, 0.18, 0.12, "Distributed\ntraces")
    box(ax, 0.11, 0.55, 0.18, 0.12, "Version\nhistory")
    box(ax, 0.11, 0.32, 0.18, 0.12, "Static analysis\n+ team capacity")
    # components
    box(ax, 0.37, 0.78, 0.17, 0.12, "Kinetic\nEfficiency  E", fc=GREEN_FC, ec=GREEN_EC)
    box(ax, 0.37, 0.55, 0.17, 0.12, "Semantic\nDistinctness  S", fc=GREEN_FC, ec=GREEN_EC)
    box(ax, 0.37, 0.32, 0.17, 0.12, "Cognitive\nLoad  L", fc=GREEN_FC, ec=GREEN_EC)
    arrow(ax, (0.20, 0.78), (0.285, 0.78))
    arrow(ax, (0.20, 0.55), (0.285, 0.55))
    arrow(ax, (0.20, 0.32), (0.285, 0.32))
    # composite
    box(ax, 0.63, 0.55, 0.17, 0.16, "RVx composite\n(multiplicative)")
    arrow(ax, (0.455, 0.78), (0.545, 0.60), rad=0.15)
    arrow(ax, (0.455, 0.55), (0.545, 0.55))
    arrow(ax, (0.455, 0.32), (0.545, 0.50), rad=-0.15)
    # normalize
    box(ax, 0.88, 0.55, 0.16, 0.12, "Normalize\nto (0, 1)")
    arrow(ax, (0.715, 0.55), (0.80, 0.55))
    # decision
    box(ax, 0.88, 0.30, 0.16, 0.12, "Governance\ndecision")
    arrow(ax, (0.88, 0.49), (0.88, 0.36))
    ax.text(0.5, 0.11, "RVx_raw = (E^beta x S) / (L^alpha + epsilon),  then  RVx = RVx_raw / (1 + RVx_raw)",
            ha="center", fontsize=9, family="monospace")
    ax.text(0.5, 0.04, "Figure 2. The RVx computation pipeline, from raw signals to a bounded, governable score.",
            ha="center", fontsize=9.5)
    save(fig, "figure2_rvx_pipeline.png")


def figure3():
    fig, ax = new_ax(12, 5.6)
    ax.text(0.13, 0.95, "Sources", ha="center", fontsize=12, fontweight="bold")
    box(ax, 0.13, 0.80, 0.22, 0.10, "Tracing backend")
    box(ax, 0.13, 0.66, 0.22, 0.10, "Version control")
    box(ax, 0.13, 0.52, 0.22, 0.10, "Source code")
    box(ax, 0.13, 0.38, 0.22, 0.10, "Team capacity")
    ax.text(0.50, 0.95, "Pipeline", ha="center", fontsize=12, fontweight="bold")
    box(ax, 0.50, 0.80, 0.24, 0.10, "Kinetic Efficiency", fc=GREEN_FC, ec=GREEN_EC)
    box(ax, 0.50, 0.66, 0.24, 0.10, "Semantic Distinctness", fc=GREEN_FC, ec=GREEN_EC, fs=8)
    box(ax, 0.50, 0.52, 0.24, 0.10, "Cognitive Load", fc=GREEN_FC, ec=GREEN_EC)
    box(ax, 0.50, 0.36, 0.20, 0.10, "RVx calculator")
    arrow(ax, (0.24, 0.80), (0.38, 0.80))
    arrow(ax, (0.24, 0.66), (0.38, 0.66))
    arrow(ax, (0.24, 0.52), (0.38, 0.52))
    arrow(ax, (0.24, 0.38), (0.40, 0.37), rad=-0.05)
    arrow(ax, (0.50, 0.75), (0.50, 0.41))          # KE -> RVx
    arrow(ax, (0.56, 0.61), (0.53, 0.41), rad=0.1)  # SD -> RVx
    arrow(ax, (0.50, 0.47), (0.50, 0.41))          # CL -> RVx
    ax.text(0.86, 0.95, "Outputs", ha="center", fontsize=12, fontweight="bold")
    box(ax, 0.86, 0.72, 0.24, 0.10, "Boundary report")
    box(ax, 0.86, 0.56, 0.24, 0.10, "CI gate / advisory")
    box(ax, 0.86, 0.40, 0.24, 0.10, "Optional controller")
    arrow(ax, (0.60, 0.36), (0.74, 0.70), rad=0.2)
    arrow(ax, (0.86, 0.67), (0.86, 0.61))
    arrow(ax, (0.80, 0.70), (0.78, 0.45), color="#999999", ls="--", rad=0.2)
    ax.text(0.5, 0.13, "Figure 3. Reference measurement architecture: every input is data teams already produce.",
            ha="center", fontsize=9.5)
    save(fig, "figure3_measurement_architecture.png")


def figure4():
    fig, ax = new_ax(8.5, 5.6)
    bw, bh = 0.30, 0.14
    box(ax, 0.30, 0.80, bw, bh, "SENSE\ncompute RVx", fs=9)
    box(ax, 0.74, 0.52, bw, bh, "DECIDE\nband + weakest", fs=9)
    box(ax, 0.30, 0.16, bw, bh, "ACTUATE\nrecommend / apply", fs=9)
    box(ax, 0.14, 0.52, 0.26, bh, "VERIFY\nre-measure", fs=9)
    arrow(ax, (0.45, 0.78), (0.68, 0.60), rad=0.25)
    arrow(ax, (0.72, 0.45), (0.44, 0.22), rad=0.25)
    arrow(ax, (0.28, 0.23), (0.18, 0.46), rad=0.25)
    arrow(ax, (0.20, 0.59), (0.24, 0.74), rad=0.25)
    ax.text(0.44, 0.50, "Fulcrum loop", ha="center", va="center", fontsize=12,
            fontweight="bold", color=BLUE_EC)
    ax.text(0.5, 0.03, "Figure 4. The Fulcrum sense, decide, actuate, verify governance loop.",
            ha="center", fontsize=9.5)
    save(fig, "figure4_fulcrum_loop.png")


def figure5_sensitivity():
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "experiments"))
    from fulcrum_core import rvx_multiplicative as rvx
    xs = [i / 20 for i in range(1, 20)]
    fig, ax = plt.subplots(figsize=(7.5, 4.8))
    ax.plot(xs, [rvx(e, 0.6, 0.4) for e in xs], marker="o", ms=3, label="vary E (S=0.6, L=0.4)")
    ax.plot(xs, [rvx(0.6, s, 0.4) for s in xs], marker="s", ms=3, label="vary S (E=0.6, L=0.4)")
    ax.plot(xs, [rvx(0.6, 0.6, l) for l in xs], marker="^", ms=3, label="vary L (E=0.6, S=0.6)")
    ax.axhline(0.7, color=GREEN_EC, ls="--", lw=1, label="optimal edge 0.7")
    ax.axhline(0.4, color=RED_EC, ls="--", lw=1, label="monolith edge 0.4")
    ax.set_xlabel("component value")
    ax.set_ylabel("normalized RVx")
    ax.set_title("Figure 5. RVx sensitivity to each component (Table 3 data)")
    ax.legend(fontsize=8, loc="upper left")
    ax.grid(alpha=0.3)
    fig.savefig(os.path.join(OUT, "figure5_sensitivity.png"), dpi=DPI, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("wrote figure5")


def figure6_exp1():
    scorers = ["RVx\n(mult)", "additive", "hard\nmin", "geo\nmean", "num-\nload", "E\nonly", "S\nonly", "1-L\nonly"]
    weakest = [0.865, 0.843, 0.940, 0.920, 0.915, 0.694, 0.684, 0.704]
    product = [0.918, 0.930, 0.915, 0.952, 0.948, 0.741, 0.728, 0.743]
    additive = [0.911, 0.969, 0.829, 0.905, 0.903, 0.756, 0.754, 0.757]
    x = list(range(len(scorers)))
    w = 0.27
    fig, ax = plt.subplots(figsize=(9.5, 5))
    ax.bar([i - w for i in x], weakest, w, label="weakest-link truth", color=BLUE_EC)
    ax.bar(x, product, w, label="product truth", color=GREEN_EC)
    ax.bar([i + w for i in x], additive, w, label="additive truth", color=RED_EC)
    ax.axhline(0.5, color="#888", ls="--", lw=1, label="chance (0.5)")
    ax.set_xticks(x)
    ax.set_xticklabels(scorers, fontsize=8)
    ax.set_ylabel("ROC AUC (recovering true label)")
    ax.set_ylim(0.5, 1.0)
    ax.set_title("Figure 6. Experiment 1: fusion beats single signals; best composition depends on truth model")
    ax.legend(fontsize=8, ncol=2)
    ax.grid(axis="y", alpha=0.3)
    fig.savefig(os.path.join(OUT, "figure6_exp1_auc.png"), dpi=DPI, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("wrote figure6")


def figure7_exp2():
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "experiments"))
    from exp2_agentic import modeled_accuracy
    ns = list(range(1, 201))
    fig, ax = plt.subplots(figsize=(8, 4.8))
    ax.plot(ns, [modeled_accuracy(n, 0.9) for n in ns], color=RED_EC, lw=2, label="tool distinctness 0.9")
    ax.plot(ns, [modeled_accuracy(n, 0.6) for n in ns], color=BLUE_EC, lw=2, ls="--", label="tool distinctness 0.6")
    ax.axvline(20, color="#888", ls=":", lw=1)
    ax.axvline(107, color="#888", ls=":", lw=1)
    ax.text(24, 0.9, "~20 tools", fontsize=8)
    ax.text(111, 0.55, "~107 tools", fontsize=8)
    ax.set_xlabel("number of tools shown to the agent (n)")
    ax.set_ylabel("modeled tool-selection accuracy")
    ax.set_title("Figure 7. Experiment 2: the tool-selection collapse and Agent Context Load")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)
    fig.savefig(os.path.join(OUT, "figure7_exp2_collapse.png"), dpi=DPI, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("wrote figure7")


def figure8_exp3():
    # 40-seed means and standard deviations (from exp3_simulation.run_multiseed)
    regimes = ["latency-\nsensitive", "balanced", "reliability-\nheavy"]
    rvx = [0.749, 0.823, 0.892];      rvx_sd = [0.013, 0.011, 0.008]
    additive = [0.696, 0.780, 0.887]; add_sd = [0.013, 0.011, 0.008]
    eonly = [0.869, 0.853, 0.660];    e_sd = [0.010, 0.010, 0.014]
    x = list(range(len(regimes)))
    w = 0.25
    fig, ax = plt.subplots(figsize=(8.5, 5))
    ax.bar([i - w for i in x], rvx, w, yerr=rvx_sd, capsize=3, label="RVx (multiplicative)", color=BLUE_EC)
    ax.bar(x, additive, w, yerr=add_sd, capsize=3, label="additive mean", color=GREEN_EC)
    ax.bar([i + w for i in x], eonly, w, yerr=e_sd, capsize=3, label="efficiency only (E)", color=RED_EC)
    ax.axhline(0.5, color="#888", ls="--", lw=1, label="chance (0.5)")
    ax.set_xticks(x)
    ax.set_xticklabels(regimes, fontsize=9)
    ax.set_ylabel("AUC vs independent net-value label")
    ax.set_ylim(0.5, 1.0)
    ax.set_title("Figure 8. Experiment 3 (40 seeds, error bars 1 SD): RVx most robust across domains")
    ax.legend(fontsize=8, loc="lower center", ncol=2)
    ax.grid(axis="y", alpha=0.3)
    fig.savefig(os.path.join(OUT, "figure8_exp3_robustness.png"), dpi=DPI, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("wrote figure8")


def figure9_dmc():
    """Distributed-Monolith Cost: measurable wasted-time core plus an illustrative dollar overlay.

    Grounded core: W = N * t_total * (1 - E), the wasted request-seconds per period, an identity
    over the measured E. Only the right-hand dollar axis is illustrative (constant c, labeled).
    """
    N_t = 3_000_000      # example: 3M tx/month at t_total = 1 s (so units are request-seconds)
    c = 0.005            # ILLUSTRATIVE cost per wasted request-second (a fraction of a cent)
    es = [i / 100 for i in range(1, 100)]
    W = [N_t * (1 - e) / 1e6 for e in es]      # wasted request-seconds per month, in millions

    fig, ax = plt.subplots(figsize=(8.5, 5))
    # shaded bands tie the cost curve to the RVx decision bands
    ax.axvspan(0.0, 0.4, color=RED_FC, alpha=0.6, zorder=0)
    ax.axvspan(0.7, 1.0, color=GREEN_FC, alpha=0.6, zorder=0)
    ax.text(0.20, max(W) * 0.92, "distributed-monolith\nefficiency band", ha="center",
            fontsize=8.5, color=RED_EC)
    ax.text(0.85, max(W) * 0.92, "healthy\nband", ha="center", fontsize=8.5, color=GREEN_EC)

    ax.plot(es, W, color=BLUE_EC, lw=2.2, label="wasted time W = N t_total (1 - E)  (measurable)")
    ax.set_xlabel("Kinetic Efficiency E")
    ax.set_ylabel("wasted request-seconds per month (millions)")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, max(W) * 1.05)
    ax.grid(alpha=0.3)

    # illustrative dollar overlay on a secondary axis, explicitly labeled
    ax2 = ax.twinx()
    ax2.plot(es, [w * 1e6 * c for w in W], color=RED_EC, lw=1.6, ls="--",
             label="illustrative monthly $ = W x c")
    ax2.set_ylabel("illustrative monthly cost ($), c = 0.005 $/req-s", color=RED_EC)
    ax2.tick_params(axis="y", labelcolor=RED_EC)
    ax2.set_ylim(0, max(W) * 1.05 * 1e6 * c)

    lines1, labels1 = ax.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax.legend(lines1 + lines2, labels1 + labels2, fontsize=8, loc="upper right")
    ax.set_title("Figure 9. Distributed-Monolith Cost: measurable wasted time, illustrative dollar overlay")
    fig.savefig(os.path.join(OUT, "figure9_dmc.png"), dpi=DPI, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("wrote figure9")


if __name__ == "__main__":
    figure1(); figure2(); figure3(); figure4()
    figure5_sensitivity(); figure6_exp1(); figure7_exp2(); figure8_exp3()
    figure9_dmc()
    print("done: 9 figures in", OUT)
