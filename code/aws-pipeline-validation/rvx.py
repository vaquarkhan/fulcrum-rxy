"""Minimal, self-contained RVx scorer + rank AUC (so the pushed repo needs no other files).

Mirrors experiments/fulcrum_core.py (Appendix C of the paper). Stdlib only.
Author: Viquar Khan (ORCID 0009-0008-3592-4162). Copyright 2026 Viquar Khan.
"""
from __future__ import annotations

BETA, ALPHA, GAMMA, EPSILON = 1.2, 0.8, 1.0, 0.1


def clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def rvx(E: float, S: float, L: float) -> float:
    """(E**beta * S**gamma) / (L**alpha + epsilon), then x/(1+x)."""
    raw = (E ** BETA) * (S ** GAMMA) / ((L ** ALPHA) + EPSILON)
    return raw / (1.0 + raw)


def rank_auc(scores_labels: list[tuple[float, int]]) -> float:
    """Rank-based ROC AUC (Mann-Whitney U) with average ranks for ties."""
    n_pos = sum(1 for _, y in scores_labels if y == 1)
    n_neg = sum(1 for _, y in scores_labels if y == 0)
    if not n_pos or not n_neg:
        return float("nan")
    combined = sorted(scores_labels, key=lambda t: t[0])
    n = len(combined)
    rank = [0.0] * n
    i = 0
    while i < n:
        j = i
        while j + 1 < n and combined[j + 1][0] == combined[i][0]:
            j += 1
        avg = (i + j) / 2.0 + 1.0
        for k in range(i, j + 1):
            rank[k] = avg
        i = j + 1
    rank_sum_pos = sum(rank[k] for k in range(n) if combined[k][1] == 1)
    u = rank_sum_pos - n_pos * (n_pos + 1) / 2.0
    return u / (n_pos * n_neg)
