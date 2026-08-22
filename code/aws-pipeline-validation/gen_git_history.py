"""Measure Semantic Distinctness (S) from a change-history model that encodes coupling
clusters. Each commit touches a subset of one cluster (with occasional cross-cluster
leakage); S = 1 - co-change fraction per boundary, the same temporal-coupling definition as
git_scl_scan.py. Boundaries in active, tightly-coupled clusters co-change often -> low S;
isolated boundaries -> high S. S is derived from the change sets, not assigned by hand.

(Computed in-process for speed; the co-change arithmetic is identical to parsing `git log`.)

Usage: python gen_git_history.py
Author: Viquar Khan (ORCID 0009-0008-3592-4162). Copyright 2026 Viquar Khan.
"""
from __future__ import annotations

import collections
import csv
import os
import random

from population_spec import make_specs, N_CLUSTERS, SEED

HERE = os.path.dirname(os.path.abspath(__file__))
N_COMMITS = 400


def compute_s(seed: int = SEED + 1) -> dict:
    """Return {name: S} from an independent change-history draw (a distinct 'repo')."""
    specs = make_specs()
    rng = random.Random(seed)
    clusters = collections.defaultdict(list)
    for s in specs:
        clusters[s["cluster"]].append(s["name"])
    weights = [rng.uniform(0.3, 3.0) for _ in range(N_CLUSTERS)]
    commits = []
    for _ in range(N_COMMITS):
        c = rng.choices(range(N_CLUSTERS), weights=weights)[0]
        members = clusters.get(c, [])
        if not members:
            continue
        j = rng.randint(1, max(1, len(members)))
        touched = set(rng.sample(members, j))
        if rng.random() < 0.10:
            touched.add(rng.choice(specs)["name"])
        commits.append(touched)
    touch = collections.Counter()
    co = collections.Counter()
    for cset in commits:
        multi = len(cset) > 1
        for m in cset:
            touch[m] += 1
            if multi:
                co[m] += 1
    return {s["name"]: (1.0 - (co[s["name"]] / touch[s["name"]]) if touch[s["name"]] else 1.0)
            for s in specs}


def main() -> int:
    specs = make_specs()
    rng = random.Random(SEED + 1)

    clusters = collections.defaultdict(list)
    for s in specs:
        clusters[s["cluster"]].append(s["name"])

    # some clusters change far more often than others
    weights = [rng.uniform(0.3, 3.0) for _ in range(N_CLUSTERS)]

    commits = []
    for _ in range(N_COMMITS):
        c = rng.choices(range(N_CLUSTERS), weights=weights)[0]
        members = clusters.get(c, [])
        if not members:
            continue
        j = rng.randint(1, max(1, len(members)))
        touched = set(rng.sample(members, j))
        if rng.random() < 0.10:                      # cross-cluster leakage
            touched.add(rng.choice(specs)["name"])
        commits.append(touched)

    touch = collections.Counter()
    co = collections.Counter()
    for cset in commits:
        multi = len(cset) > 1
        for m in cset:
            touch[m] += 1
            if multi:
                co[m] += 1

    out = os.path.join(HERE, "s_scores.csv")
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["name", "S", "changesets"])
        for s in specs:
            n = s["name"]
            S = 1.0 - (co[n] / touch[n]) if touch[n] else 1.0
            w.writerow([n, round(S, 4), touch[n]])
    print(f"measured S from {len(commits)} change sets across {N_CLUSTERS} coupling clusters; wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
