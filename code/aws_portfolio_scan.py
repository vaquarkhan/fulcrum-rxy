"""Fulcrum portfolio scan on a REAL AWS account (STRICTLY READ-ONLY).

For every active Lambda boundary it measures, from real data:
  L (Cognitive Load, structural) <- Lambda config: code size, memory, timeout, layers, env vars
  E (Kinetic Efficiency)         <- X-Ray traces where tracing is enabled
  outcomes                       <- CloudWatch: p99 duration, error rate, invocations
It computes RVx where E is available, and reports the real correlation between the RVx signals
and measured p99 latency (an honest, small H2-style probe on real outcomes).

SAFETY: only get/describe/list calls. Creates/modifies/deletes nothing. Launches nothing.
Usage: python aws_portfolio_scan.py [--profile NAME] [--region us-east-1] [--days 14]
Author: Viquar Khan. Copyright 2026 Viquar Khan.
"""
from __future__ import annotations
import argparse, json, subprocess, datetime, os, sys, math
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "experiments"))
from fulcrum_core import rvx_multiplicative, spearman, _clamp  # noqa: E402

RO = ("lambda list-", "lambda get-", "cloudwatch get-", "xray get-", "xray batch-get-", "sts get-")


def mk_aws(profile, region):
    def aws(args):
        j = " ".join(args[:2])
        if not any(j.startswith(p) for p in RO):
            raise RuntimeError(f"BLOCKED non-readonly: {j}")
        cmd = ["aws"] + args + ["--region", region, "--output", "json"]
        if profile:
            cmd += ["--profile", profile]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError(r.stderr[:250])
        return json.loads(r.stdout) if r.stdout.strip() else {}
    return aws


def bounded(x, k):
    return x / (x + k) if x + k > 0 else 0.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile", default=None)
    ap.add_argument("--region", default="us-east-1")
    ap.add_argument("--days", type=int, default=14)
    a = ap.parse_args()
    aws = mk_aws(a.profile, a.region)

    ident = aws(["sts", "get-caller-identity"])
    print("=" * 84)
    print(f"Fulcrum portfolio scan (READ-ONLY)  account {ident.get('Account')}  {ident.get('Arn')}")
    print("=" * 84)

    # list functions
    names, token = [], None
    while True:
        args = ["lambda", "list-functions", "--max-items", "400"]
        if token:
            args += ["--starting-token", token]
        d = aws(args)
        names += [f["FunctionName"] for f in d.get("Functions", [])]
        token = d.get("NextToken")
        if not token:
            break

    now = datetime.datetime.now(datetime.timezone.utc)
    start = (now - datetime.timedelta(days=a.days)).strftime("%Y-%m-%dT%H:%M:%SZ")
    end = now.strftime("%Y-%m-%dT%H:%M:%SZ")

    def metric_batch(metric, stat, period):
        res = {}
        for i in range(0, len(names), 100):
            chunk = names[i:i + 100]
            q = [{"Id": f"m{j}", "MetricStat": {"Metric": {"Namespace": "AWS/Lambda",
                  "MetricName": metric, "Dimensions": [{"Name": "FunctionName", "Value": n}]},
                  "Period": period, "Stat": stat}} for j, n in enumerate(chunk)]
            d = aws(["cloudwatch", "get-metric-data", "--metric-data-queries", json.dumps(q),
                     "--start-time", start, "--end-time", end])
            idmap = {f"m{j}": chunk[j] for j in range(len(chunk))}
            for m in d.get("MetricDataResults", []):
                res[idmap[m["Id"]]] = m.get("Values", []) or []
        return res

    inv = {k: sum(v) for k, v in metric_batch("Invocations", "Sum", a.days * 86400).items()}
    active = [n for n in names if inv.get(n, 0) > 0]
    print(f"functions: {len(names)}   active (>0 invocations in {a.days}d): {len(active)}\n")
    if not active:
        print("no active functions; nothing to measure"); return

    p99 = {k: (max(v) if v else 0) for k, v in metric_batch("Duration", "p99", 86400).items()}
    errs = {k: sum(v) for k, v in metric_batch("Errors", "Sum", a.days * 86400).items()}

    # E from X-Ray service graph (last 6h)
    E = {}
    try:
        s6 = (now - datetime.timedelta(hours=6)).strftime("%Y-%m-%dT%H:%M:%S")
        e6 = now.strftime("%Y-%m-%dT%H:%M:%S")
        g = aws(["xray", "get-service-graph", "--start-time", s6, "--end-time", e6])
        for s in g.get("Services", []):
            if s.get("Type") == "AWS::Lambda::Function":
                ss = s.get("SummaryStatistics", {})
                c = ss.get("TotalCount", 0) or 0
                if c:
                    tot = ss.get("TotalResponseTime", 0) / c
                    down = sum((e.get("SummaryStatistics", {}).get("TotalResponseTime", 0) /
                                (e.get("SummaryStatistics", {}).get("TotalCount", 1) or 1))
                               for e in s.get("Edges", []) or [])
                    E[s["Name"]] = _clamp((tot - min(down, tot)) / tot) if tot > 0 else 0.0
    except Exception as ex:
        print("X-Ray unavailable:", str(ex)[:80])

    # L from config for active functions
    rows = []
    for n in active:
        try:
            cfg = aws(["lambda", "get-function-configuration", "--function-name", n])
        except Exception:
            continue
        code = cfg.get("CodeSize", 0)
        mem = cfg.get("MemorySize", 128)
        to = cfg.get("Timeout", 3)
        layers = len(cfg.get("Layers", []) or [])
        envc = len((cfg.get("Environment", {}) or {}).get("Variables", {}) or {})
        # normalized structural complexity proxies (bounded), equal weight; capacity held constant (N16 -> structural)
        L = _clamp((bounded(code, 5e6) + bounded(mem, 1024) + bounded(to, 60)
                    + bounded(layers, 3) + bounded(envc, 15)) / 5.0)
        e = E.get(n)
        rvx = rvx_multiplicative(e, 0.5, L) if e is not None else None
        rows.append({"name": n, "inv": inv.get(n, 0), "p99": p99.get(n, 0),
                     "err_rate": (errs.get(n, 0) / inv.get(n, 1)), "E": e, "L": round(L, 3),
                     "rvx": rvx})

    rows.sort(key=lambda r: -r["inv"])
    print(f"{'boundary':52}{'inv':>8}{'p99(ms)':>9}{'err%':>7}{'E':>7}{'L':>7}{'RVx*':>7}")
    for r in rows:
        e = f"{r['E']:.2f}" if r["E"] is not None else "  -"
        rvx = f"{r['rvx']:.3f}" if r["rvx"] is not None else "   -"
        print(f"{r['name'][:50]:52}{r['inv']:>8}{r['p99']:>9.0f}{100*r['err_rate']:>7.1f}{e:>7}{r['L']:>7}{rvx:>7}")

    # honest H2-style probe on real outcomes
    Ls = [r["L"] for r in rows]
    ps = [r["p99"] for r in rows]
    if len(rows) >= 5 and len(set(ps)) > 1:
        print(f"\nReal correlation on {len(rows)} active boundaries (independent CloudWatch outcomes):")
        print(f"  Spearman(L, p99 latency)      = {spearman(Ls, ps):+.3f}  (positive = more complex -> slower)")
        withE = [r for r in rows if r["E"] is not None]
        if len(withE) >= 5:
            print(f"  Spearman(E, p99 latency)      = {spearman([r['E'] for r in withE],[r['p99'] for r in withE]):+.3f}")
        else:
            print(f"  (E available for only {len(withE)} boundaries; too few for a stable E-p99 correlation)")
    else:
        print("\nToo few active boundaries or no p99 variation for a correlation.")

    print("\nHONEST SCOPE: real measurements from a real account, read-only. L is structural (capacity")
    print("held constant, N16). No ground-truth labels and no git S here, so this is a real portfolio")
    print("PROFILE and a small outcome probe, not the labeled H1/H2 validation. * RVx* uses S=0.5 placeholder.")


if __name__ == "__main__":
    main()
