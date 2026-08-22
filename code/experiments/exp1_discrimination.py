"""Experiment 1: does the multiplicative RVx separate good from bad boundaries
better than the additive and single-signal baselines?

This is the Section 12.3 ablation run as a controlled, non-circular experiment. We do
NOT assume the RVx formula defines the truth. Instead we generate boundaries with a
latent quality under THREE different ground-truth models, add measurement noise to the
observed E/S/L signals, and ask which SCORING FORM best recovers the true label (ROC AUC).

Honest reading:
- If reality is "weakest-link" (a boundary must be good on all three at once), the
  multiplicative and minimum forms should win and additive should lose. That is the
  paper's central design bet.
- If reality is "additive" (dimensions trade off linearly), the additive form should win.
So this experiment does not prove RVx is universally best; it proves the design bet is
correct IF and ONLY IF boundary quality is weakest-link, and it makes that the crisp,
testable question a real corpus must answer. That is proof of the mechanism, not of
production validity.

Dependency-free. Deterministic (seeded). Run: python exp1_discrimination.py
"""
from __future__ import annotations

import random

from fulcrum_core import SCORERS, rank_auc, _clamp


def gen_boundary(rng):
    """Latent dimensions in [0,1]: e=efficiency, s=distinctness, g=goodness-of-load (=1-L_true)."""
    e = rng.random()
    s = rng.random()
    g = rng.random()          # goodness on load; true L = 1 - g
    return e, s, g


def true_quality(e, s, g, model):
    if model == "weakest_link":
        return min(e, s, g)                      # must be good on all three
    if model == "additive":
        return (e + s + g) / 3.0                 # linear trade-off
    if model == "product":
        return e * s * g                         # AND-gate with graded compensation
    raise ValueError(model)


def observe(x, noise, rng):
    return _clamp(x + rng.gauss(0.0, noise))


def run(model, n=400, noise=0.10, seeds=40):
    """Return {scorer_name: mean AUC} recovering the true (median-split) label."""
    totals = {name: 0.0 for name in SCORERS}
    for seed in range(seeds):
        rng = random.Random(1000 + seed)
        rows = []
        for _ in range(n):
            e, s, g = gen_boundary(rng)
            q = true_quality(e, s, g, model)
            # observed signals with measurement noise; L observed = 1 - observed g
            E = observe(e, noise, rng)
            S = observe(s, noise, rng)
            L = observe(1.0 - g, noise, rng)
            rows.append((q, E, S, L))
        # balanced labels via median split of TRUE quality
        med = sorted(r[0] for r in rows)[len(rows) // 2]
        labeled = [(1 if q >= med else 0, E, S, L) for (q, E, S, L) in rows]
        for name, fn in SCORERS.items():
            sl = [(fn(E, S, L), y) for (y, E, S, L) in labeled]
            totals[name] += rank_auc(sl)
    return {name: totals[name] / seeds for name in SCORERS}


def main():
    models = ["weakest_link", "product", "additive"]
    results = {m: run(m) for m in models}
    names = list(SCORERS.keys())
    w = max(len(n) for n in names)
    print("Experiment 1: AUC of each scoring form at recovering the true boundary label")
    print("(400 boundaries, 40 seeds, measurement noise sigma=0.10; higher AUC = better)\n")
    header = "scoring form".ljust(w) + "".join(f"{m:>16}" for m in models)
    print(header)
    print("-" * len(header))
    for name in names:
        row = name.ljust(w) + "".join(f"{results[m][name]:>16.3f}" for m in models)
        print(row)
    print("\nHow to read this:")
    for m in models:
        best = max(names, key=lambda n: results[m][n])
        print(f"  under '{m}' truth, best scorer = {best} (AUC {results[m][best]:.3f})")
    print("\nInterpretation: RVx (multiplicative) and hard minimum dominate when boundary")
    print("quality is weakest-link or product; additive wins only if quality is truly linear.")
    print("The multiplicative form's advantage is therefore real and conditional, and the")
    print("open empirical question a real corpus must answer is: which truth model does")
    print("production boundary quality actually follow?")


if __name__ == "__main__":
    main()
