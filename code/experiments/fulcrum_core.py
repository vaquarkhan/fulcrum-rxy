"""Fulcrum core: the RVx scorer and the competing scoring forms under test.

Dependency-free (Python 3.10+, standard library only). This is the same core defined in
Appendix C of the paper, plus the alternative composition forms so the experiments can
compare them head to head (the Section 12.3 ablation, run in code).

Author: Viquar Khan (ORCID 0009-0008-3592-4162). Copyright 2026 Viquar Khan.
"""
from __future__ import annotations

BETA, ALPHA, GAMMA, EPSILON = 1.2, 0.8, 1.0, 0.1


def _clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


# ---- The RVx composition and its rivals (all take E, S, L in [0,1]) ----
# Convention: higher = healthier. L is "bad" (load), so health uses (1 - L).

def rvx_multiplicative(E: float, S: float, L: float) -> float:
    """The paper's form: (E**beta * S**gamma) / (L**alpha + epsilon), then x/(1+x)."""
    raw = (E ** BETA) * (S ** GAMMA) / ((L ** ALPHA) + EPSILON)
    return raw / (1.0 + raw)


def score_additive(E: float, S: float, L: float) -> float:
    """Additive baseline: the naive average that the paper argues is wrong."""
    return (E + S + (1.0 - L)) / 3.0


def score_min(E: float, S: float, L: float) -> float:
    """Hard weakest-link: the minimum of the three healthy dimensions."""
    return min(E, S, 1.0 - L)


def score_geomean(E: float, S: float, L: float) -> float:
    """Geometric mean of the three healthy dimensions."""
    return (E * S * (1.0 - L)) ** (1.0 / 3.0)


def score_numerator_load(E: float, S: float, L: float) -> float:
    """Numerator-load variant: E**beta * S**gamma * (1-L)**alpha (Section 12.3)."""
    return (E ** BETA) * (S ** GAMMA) * ((1.0 - L) ** ALPHA)


def score_only_E(E: float, S: float, L: float) -> float:
    return E


def score_only_S(E: float, S: float, L: float) -> float:
    return S


def score_only_invL(E: float, S: float, L: float) -> float:
    return 1.0 - L


SCORERS = {
    "RVx (multiplicative)": rvx_multiplicative,
    "additive mean": score_additive,
    "hard minimum": score_min,
    "geometric mean": score_geomean,
    "numerator-load": score_numerator_load,
    "efficiency only (E)": score_only_E,
    "distinctness only (S)": score_only_S,
    "inverse load only (1-L)": score_only_invL,
}


# ---- Metrics (stdlib only) ----

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


def spearman(xs: list[float], ys: list[float]) -> float:
    """Spearman rank correlation (stdlib)."""
    def ranks(v):
        order = sorted(range(len(v)), key=lambda i: v[i])
        r = [0.0] * len(v)
        i = 0
        while i < len(v):
            j = i
            while j + 1 < len(v) and v[order[j + 1]] == v[order[i]]:
                j += 1
            avg = (i + j) / 2.0 + 1.0
            for k in range(i, j + 1):
                r[order[k]] = avg
            i = j + 1
        return r
    rx, ry = ranks(xs), ranks(ys)
    n = len(xs)
    mx = sum(rx) / n
    my = sum(ry) / n
    cov = sum((rx[i] - mx) * (ry[i] - my) for i in range(n))
    vx = sum((rx[i] - mx) ** 2 for i in range(n)) ** 0.5
    vy = sum((ry[i] - my) ** 2 for i in range(n)) ** 0.5
    return cov / (vx * vy) if vx and vy else float("nan")
