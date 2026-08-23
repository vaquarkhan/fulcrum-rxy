"""Fulcrum RVx production validation study on a real AWS Lambda estate.

Measures all three signals for real and scores them against INDEPENDENTLY measured outcomes
that RVx never sees:

  E (Kinetic Efficiency)   <- real request timing (useful vs total), averaged over invokes
  S (Semantic Distinctness)<- real git co-change (s_scores.csv from gen_git_history.py)
  L (Cognitive Load)       <- real deployed Lambda config (CodeSize, memory, timeout, ...),
                              capacity held constant (structural, N16)
  outcomes                 <- measured p95 latency, error rate, and GB-second cost proxy

It then tests, across three domain weightings (latency-heavy, balanced, reliability/cost),
whether each scoring form separates measured-healthy from measured-unhealthy boundaries
(rank AUC with bootstrap CIs), and reports RVx's worst-case robustness vs single signals and
the additive form. Non-circular: RVx is a function of (E,S,L); the label is a function of
independently measured (latency, error, cost).

Read + invoke only. Writes feature_table.csv, study_results.json, RESULTS.md.
Usage: python run_study.py
Author: Viquar Khan (ORCID 0009-0008-3592-4162). Copyright 2026 Viquar Khan.
"""
from __future__ import annotations

import csv
import json
import os
import random
import sys
import time
from concurrent.futures import ThreadPoolExecutor

import boto3

from population_spec import make_specs, REGION

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "experiments"))
from fulcrum_core import (SCORERS, rank_auc, spearman, _clamp,  # noqa: E402
                          rvx_multiplicative)

HERE = os.path.dirname(os.path.abspath(__file__))
K_INVOKES = 20
WARMUP = 3      # discard cold-start invokes so latency reflects steady-state architecture
DOMAINS = {
    "latency-heavy":     dict(lat=0.70, cost=0.15, err=0.15),   # E should win
    "cost-heavy":        dict(lat=0.15, cost=0.70, err=0.15),   # L should win
    "reliability-heavy": dict(lat=0.15, cost=0.15, err=0.70),   # S should win (coupling-driven)
}


def bounded(x, k):
    return x / (x + k) if x + k > 0 else 0.0


def drive_boundary(lam, name, k):
    """Invoke a boundary; measure E (server), steady-state client latency (ms), error rate.

    The first WARMUP invokes are discarded so cold-start time does not swamp the
    architectural (hop-overhead) latency signal.
    """
    for _ in range(WARMUP):
        try:
            lam.invoke(FunctionName=name, InvocationType="RequestResponse", Payload=b"{}")
        except Exception:
            pass
    es, lats, oks = [], [], []
    for _ in range(k):
        t0 = time.perf_counter()
        try:
            r = lam.invoke(FunctionName=name, InvocationType="RequestResponse", Payload=b"{}")
            dt = (time.perf_counter() - t0) * 1000.0
            payload = json.loads(r["Payload"].read() or b"{}")
            e = payload.get("E")
            ok = bool(payload.get("ok", True)) and r.get("FunctionError") is None
            if e is not None:
                es.append(float(e))
            lats.append(dt)
            oks.append(1 if ok else 0)
        except Exception:
            oks.append(0)
    if not es:
        return None
    lats.sort()
    p95 = lats[min(len(lats) - 1, int(0.95 * len(lats)))]
    return {"E": sum(es) / len(es), "lat_p95": p95, "lat_mean": sum(lats) / len(lats),
            "err_rate": 1.0 - (sum(oks) / len(oks))}


def measure_L(lam, name):
    """Structural Cognitive Load from real deployed config (capacity constant, N16)."""
    cfg = lam.get_function_configuration(FunctionName=name)
    code = cfg.get("CodeSize", 0)
    mem = cfg.get("MemorySize", 128)
    to = cfg.get("Timeout", 3)
    layers = len(cfg.get("Layers", []) or [])
    envc = len((cfg.get("Environment", {}) or {}).get("Variables", {}) or {})
    L = _clamp((bounded(code, 5e6) + bounded(mem, 1024) + bounded(to, 60)
                + bounded(layers, 3) + bounded(envc, 15)) / 5.0)
    return L, mem, code


def minmax(vals):
    lo, hi = min(vals), max(vals)
    rng = hi - lo
    return [(v - lo) / rng if rng > 0 else 0.0 for v in vals]


def bootstrap_auc_ci(scores, labels, B=2000, seed=1):
    rng = random.Random(seed)
    n = len(scores)
    idx = list(range(n))
    aucs = []
    for _ in range(B):
        sample = [rng.choice(idx) for _ in range(n)]
        sl = [(scores[i], labels[i]) for i in sample]
        a = rank_auc(sl)
        if a == a:  # not NaN
            aucs.append(a)
    aucs.sort()
    lo = aucs[int(0.025 * len(aucs))]
    hi = aucs[int(0.975 * len(aucs))]
    return lo, hi


def main() -> int:
    lam = boto3.client("lambda", region_name=REGION)
    specs = {s["name"]: s for s in make_specs()}

    # S from git step
    s_scores = {}
    with open(os.path.join(HERE, "s_scores.csv"), encoding="utf-8") as f:
        for row in csv.DictReader(f):
            s_scores[row["name"]] = float(row["S"])

    print(f"Driving load on {len(specs)} boundaries ({WARMUP} warmup + {K_INVOKES} measured invokes each) ...")
    results = {}
    with ThreadPoolExecutor(max_workers=5) as ex:
        futs = {ex.submit(drive_boundary, lam, n, K_INVOKES): n for n in specs}
        for fut in futs:
            n = futs[fut]
            r = fut.result()
            if r:
                results[n] = r
    print(f"  measured {len(results)} boundaries")

    # assemble feature table
    rows = []
    for n, r in results.items():
        L, mem, code = measure_L(lam, n)
        cost = (mem / 1024.0) * (r["lat_mean"] / 1000.0)   # GB-seconds proxy per request
        rows.append({"name": n, "E": round(r["E"], 4), "S": round(s_scores.get(n, 1.0), 4),
                     "L": round(L, 4), "lat_p95_ms": round(r["lat_p95"], 1),
                     "err_rate": round(r["err_rate"], 4), "cost_gbs": round(cost, 6),
                     "hops": specs[n]["hops"], "memory": mem})

    with open(os.path.join(HERE, "feature_table.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    # normalized bad-outcomes
    lat_n = minmax([r["lat_p95_ms"] for r in rows])
    cost_n = minmax([r["cost_gbs"] for r in rows])
    err_n = minmax([r["err_rate"] for r in rows])

    focus = ["RVx (multiplicative)", "additive mean", "hard minimum", "geometric mean",
             "efficiency only (E)", "distinctness only (S)", "inverse load only (1-L)"]

    per_domain = {d: {} for d in DOMAINS}
    per_domain_ci = {d: {} for d in DOMAINS}
    for d, w in DOMAINS.items():
        net_bad = [w["lat"] * lat_n[i] + w["cost"] * cost_n[i] + w["err"] * err_n[i]
                   for i in range(len(rows))]
        order = sorted(net_bad)
        med = order[len(order) // 2]
        labels = [1 if nb <= med else 0 for nb in net_bad]   # healthy = low bad
        for name in focus:
            fn = SCORERS[name]
            scores = [fn(r["E"], r["S"], r["L"]) for r in rows]
            per_domain[d][name] = rank_auc(list(zip(scores, labels)))
            per_domain_ci[d][name] = bootstrap_auc_ci(scores, labels)

    worst = {name: min(per_domain[d][name] for d in DOMAINS) for name in focus}

    # Spearman of each signal / RVx against each raw independent outcome
    def col(key):
        return [r[key] for r in rows]
    rvx_scores = [rvx_multiplicative(r["E"], r["S"], r["L"]) for r in rows]
    corr = {
        "RVx_vs_latency": spearman(rvx_scores, col("lat_p95_ms")),
        "RVx_vs_cost": spearman(rvx_scores, col("cost_gbs")),
        "RVx_vs_errors": spearman(rvx_scores, col("err_rate")),
        "E_vs_latency": spearman(col("E"), col("lat_p95_ms")),
        "L_vs_cost": spearman(col("L"), col("cost_gbs")),
        "S_vs_errors": spearman(col("S"), col("err_rate")),
    }

    summary = {"n_boundaries": len(rows), "k_invokes": K_INVOKES,
               "auc_per_domain": per_domain, "auc_ci_per_domain": per_domain_ci,
               "worst_case_auc": worst, "correlations": corr}
    with open(os.path.join(HERE, "study_results.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    # console report
    print("\nAUC per domain (higher = better separation of measured-healthy vs unhealthy):")
    hdr = "scorer".ljust(26) + "".join(f"{d:>19}" for d in DOMAINS) + f"{'worst-case':>13}"
    print(hdr); print("-" * len(hdr))
    for name in focus:
        row = name.ljust(26) + "".join(f"{per_domain[d][name]:>19.3f}" for d in DOMAINS)
        row += f"{worst[name]:>13.3f}"
        print(row)
    print("\nRank correlations with independent measured outcomes (Spearman):")
    for k, v in corr.items():
        print(f"  {k:20} {v:+.3f}")

    write_results_md(summary, rows)
    print(f"\nwrote feature_table.csv, study_results.json, RESULTS.md in {HERE}")
    return 0


def write_results_md(summary, rows):
    focus = ["RVx (multiplicative)", "additive mean", "hard minimum", "geometric mean",
             "efficiency only (E)", "distinctness only (S)", "inverse load only (1-L)"]
    L = []
    L.append("# Fulcrum RVx: Production Validation on a Real AWS Lambda Estate\n")
    L.append(f"- Boundaries: **{summary['n_boundaries']}** randomized real Lambda functions "
             f"(us-east-1), {summary['k_invokes']} invokes each.\n")
    L.append("- Signals measured for real: E (request timing), S (git co-change), "
             "L (deployed config, structural).\n")
    L.append("- Outcomes measured independently: p95 latency, error rate, GB-second cost. "
             "RVx never observes these.\n")
    L.append("\n## AUC per domain and worst-case robustness\n")
    L.append("| scorer | " + " | ".join(DOMAINS) + " | worst-case |")
    L.append("|" + "---|" * (len(DOMAINS) + 2))
    for name in focus:
        cells = " | ".join(f"{summary['auc_per_domain'][d][name]:.3f}" for d in DOMAINS)
        L.append(f"| {name} | {cells} | {summary['worst_case_auc'][name]:.3f} |")
    L.append("\n## Rank correlations with independent outcomes (Spearman)\n")
    for k, v in summary["correlations"].items():
        L.append(f"- {k}: {v:+.3f}")
    best = max(focus, key=lambda n: summary["worst_case_auc"][n])
    L.append(f"\n## Headline\n\nMost robust scorer by worst-case AUC across domains: **{best}** "
             f"(worst-case {summary['worst_case_auc'][best]:.3f}).\n")
    with open(os.path.join(HERE, "RESULTS.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(L))


if __name__ == "__main__":
    raise SystemExit(main())
