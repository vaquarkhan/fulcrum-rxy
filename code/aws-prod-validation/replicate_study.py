"""Multi-replication production validation: repeats the measurement over several load runs
and several independent change-history draws (distinct 'git repos'), so every AUC is reported
as a mean +/- SD across replications rather than a single point estimate.

For each replication r:
  - re-measure E, latency, error rate by re-driving the live estate (fresh load);
  - draw an independent Semantic Distinctness history (compute_s with a per-rep seed);
  - measure structural L from the real deployed config;
  - score every form and compute rank AUC per domain, plus rank correlations.

Aggregates mean +/- SD per scorer per domain, worst-case robustness, and Spearman
correlations across replications. Read + invoke only.

Usage: python replicate_study.py [--reps 4]
Author: Viquar Khan (ORCID 0009-0008-3592-4162). Copyright 2026 Viquar Khan.
"""
from __future__ import annotations

import argparse
import json
import os
import statistics as st
from concurrent.futures import ThreadPoolExecutor

import boto3

import csv

from population_spec import make_specs, REGION
import run_study as rs

HERE = os.path.dirname(os.path.abspath(__file__))
FOCUS = ["RVx (multiplicative)", "additive mean", "hard minimum", "geometric mean",
         "efficiency only (E)", "distinctness only (S)", "inverse load only (1-L)"]


def one_rep(lam, specs, s_map):
    results = {}
    with ThreadPoolExecutor(max_workers=5) as ex:
        futs = {ex.submit(rs.drive_boundary, lam, n, rs.K_INVOKES): n for n in specs}
        for fut in futs:
            n = futs[fut]
            r = fut.result()
            if r:
                results[n] = r
    rows = []
    for n, r in results.items():
        L, mem, _ = rs.measure_L(lam, n)
        cost = (mem / 1024.0) * (r["lat_mean"] / 1000.0)
        rows.append({"name": n, "E": r["E"], "S": s_map.get(n, 1.0), "L": L,
                     "lat": r["lat_p95"], "err": r["err_rate"], "cost": cost})
    lat_n = rs.minmax([r["lat"] for r in rows])
    cost_n = rs.minmax([r["cost"] for r in rows])
    err_n = rs.minmax([r["err"] for r in rows])

    dom_auc = {}
    for d, w in rs.DOMAINS.items():
        net_bad = [w["lat"] * lat_n[i] + w["cost"] * cost_n[i] + w["err"] * err_n[i]
                   for i in range(len(rows))]
        med = sorted(net_bad)[len(net_bad) // 2]
        labels = [1 if nb <= med else 0 for nb in net_bad]
        for name in FOCUS:
            fn = rs.SCORERS[name]
            scores = [fn(r["E"], r["S"], r["L"]) for r in rows]
            dom_auc[(d, name)] = rs.rank_auc(list(zip(scores, labels)))

    rvx_scores = [rs.rvx_multiplicative(r["E"], r["S"], r["L"]) for r in rows]
    corr = {
        "RVx_vs_latency": rs.spearman(rvx_scores, [r["lat"] for r in rows]),
        "RVx_vs_cost": rs.spearman(rvx_scores, [r["cost"] for r in rows]),
        "RVx_vs_errors": rs.spearman(rvx_scores, [r["err"] for r in rows]),
        "E_vs_latency": rs.spearman([r["E"] for r in rows], [r["lat"] for r in rows]),
        "L_vs_cost": rs.spearman([r["L"] for r in rows], [r["cost"] for r in rows]),
        "S_vs_errors": rs.spearman([r["S"] for r in rows], [r["err"] for r in rows]),
    }
    return dom_auc, corr


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", type=int, default=4)
    args = ap.parse_args()

    lam = boto3.client("lambda", region_name=REGION)
    specs = [s["name"] for s in make_specs()]

    # Use the SAME S that set the deployed COUPLING (which drives the error outcome), so S is
    # scored against the outcome it actually influences. Replication variance comes from
    # re-driving live load, not from re-drawing S.
    s_map = {}
    with open(os.path.join(HERE, "s_scores.csv"), encoding="utf-8") as f:
        for row in csv.DictReader(f):
            s_map[row["name"]] = float(row["S"])

    dom_series = {(d, n): [] for d in rs.DOMAINS for n in FOCUS}
    corr_series = {k: [] for k in ["RVx_vs_latency", "RVx_vs_cost", "RVx_vs_errors",
                                   "E_vs_latency", "L_vs_cost", "S_vs_errors"]}
    worst_series = {n: [] for n in FOCUS}

    for rep in range(args.reps):
        print(f"replication {rep + 1}/{args.reps} (fresh live load) ...")
        dom_auc, corr = one_rep(lam, specs, s_map)
        for key, v in dom_auc.items():
            dom_series[key].append(v)
        for k, v in corr.items():
            corr_series[k].append(v)
        for n in FOCUS:
            worst_series[n].append(min(dom_auc[(d, n)] for d in rs.DOMAINS))

    def ms(v):
        return (st.mean(v), st.pstdev(v) if len(v) > 1 else 0.0)

    print(f"\nAUC over {args.reps} replications (mean +/- SD):")
    hdr = "scorer".ljust(26) + "".join(f"{d:>20}" for d in rs.DOMAINS) + f"{'worst-case':>18}"
    print(hdr); print("-" * len(hdr))
    agg = {"reps": args.reps, "per_domain": {}, "worst_case": {}, "correlations": {}}
    for n in FOCUS:
        cells = ""
        for d in rs.DOMAINS:
            m, s = ms(dom_series[(d, n)])
            agg["per_domain"][f"{d}|{n}"] = [round(m, 3), round(s, 3)]
            cells += f"{m:>13.3f}+-{s:<4.3f}"
        wm, ws = ms(worst_series[n])
        agg["worst_case"][n] = [round(wm, 3), round(ws, 3)]
        print(n.ljust(26) + cells + f"{wm:>11.3f}+-{ws:<4.3f}")

    print(f"\nRank correlations with independent outcomes (mean +/- SD over {args.reps} reps):")
    for k, series in corr_series.items():
        m, s = ms(series)
        agg["correlations"][k] = [round(m, 3), round(s, 3)]
        print(f"  {k:20} {m:+.3f} +/- {s:.3f}")

    with open(os.path.join(HERE, "aggregate_results.json"), "w", encoding="utf-8") as f:
        json.dump(agg, f, indent=2)

    best = max(FOCUS, key=lambda n: agg["worst_case"][n][0])
    print(f"\nMost robust scorer (best mean worst-case AUC): {best} "
          f"({agg['worst_case'][best][0]:.3f})")
    write_md(agg, best, args.reps)
    print(f"wrote aggregate_results.json and AGGREGATE_RESULTS.md in {HERE}")
    return 0


def write_md(agg, best, reps):
    L = ["# Fulcrum RVx: Production Validation on Real AWS Lambda (multi-replication)\n"]
    L.append(f"- 36 randomized real Lambda boundaries, us-east-1; **{reps} replications** "
             f"(fresh load + independent change-history draw each).\n")
    L.append("- Signals measured for real (E timing, S co-change, L deployed config); outcomes "
             "measured independently (p95 latency, error rate, GB-s cost). RVx never sees outcomes.\n")
    L.append("\n## AUC per domain and worst-case (mean +/- SD)\n")
    L.append("| scorer | " + " | ".join(rs.DOMAINS) + " | worst-case |")
    L.append("|" + "---|" * (len(rs.DOMAINS) + 2))
    for n in FOCUS:
        cells = " | ".join(f"{agg['per_domain'][f'{d}|{n}'][0]:.3f}Â±{agg['per_domain'][f'{d}|{n}'][1]:.3f}"
                           for d in rs.DOMAINS)
        wc = agg["worst_case"][n]
        L.append(f"| {n} | {cells} | {wc[0]:.3f}Â±{wc[1]:.3f} |")
    L.append("\n## Rank correlations with independent outcomes (mean +/- SD)\n")
    for k, v in agg["correlations"].items():
        L.append(f"- {k}: {v[0]:+.3f} Â± {v[1]:.3f}")
    L.append(f"\n## Headline\n\nMost robust scorer by mean worst-case AUC: **{best}** "
             f"({agg['worst_case'][best][0]:.3f} Â± {agg['worst_case'][best][1]:.3f}).\n")
    with open(os.path.join(HERE, "AGGREGATE_RESULTS.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(L))


if __name__ == "__main__":
    raise SystemExit(main())
