"""Fulcrum AWS validation harness (STRICTLY READ-ONLY).

Instantiates the Section 12 protocol on a real AWS account:
  E  (Kinetic Efficiency)   <- X-Ray traces (per-boundary useful vs overhead time)
  S  (Semantic Distinctness)<- git co-change history (optional, needs --repo)
  L  (Cognitive Load)       <- static complexity / capacity (optional, needs --repo + --capacity)
  outcomes                  <- CloudWatch (Lambda Duration, Errors) and optional Cost Explorer
It joins these per boundary, computes RVx, and if a labels CSV is supplied, reports AUC.

SAFETY: this tool only ever calls read/describe/get/list APIs. It never creates, modifies, or
deletes any AWS resource. It launches no infrastructure. Use ReadOnly or least-privilege creds.

Usage:
  python aws_validation_harness.py --region us-east-1 --hours 6
  python aws_validation_harness.py --region us-east-1 --hours 6 --repo C:\\path\\to\\repo --labels labels.csv

Dependencies: standard library + AWS CLI on PATH (already used elsewhere in this bundle).
Author: Viquar Khan (ORCID 0009-0008-3592-4162). Copyright 2026 Viquar Khan.
"""
from __future__ import annotations

import argparse, json, subprocess, datetime, collections, os, sys, csv

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "experiments"))
from fulcrum_core import rvx_multiplicative, rank_auc, _clamp  # noqa: E402

# ---- read-only allowlist: every AWS call must start with one of these ----
READONLY_PREFIXES = ("xray get-", "xray batch-get-", "cloudwatch get-", "cloudwatch list-",
                     "lambda list-", "ce get-", "sts get-")


def aws(args, region):
    joined = " ".join(args[:2])
    if not any(joined.startswith(p) for p in READONLY_PREFIXES):
        raise RuntimeError(f"BLOCKED: '{joined}' is not on the read-only allowlist")
    out = subprocess.run(["aws"] + args + ["--region", region, "--output", "json"],
                         capture_output=True, text=True)
    if out.returncode != 0:
        raise RuntimeError(out.stderr.strip()[:300])
    return json.loads(out.stdout) if out.stdout.strip() else {}


# ---------- E from X-Ray ----------
def is_remote_sub(ss):
    return ss.get("namespace") in ("aws", "remote") or "http" in ss


def kinetic_efficiency(region, hours):
    now = datetime.datetime.now(datetime.timezone.utc)
    start = (now - datetime.timedelta(hours=hours)).strftime("%Y-%m-%dT%H:%M:%S")
    end = now.strftime("%Y-%m-%dT%H:%M:%S")
    summ = aws(["xray", "get-trace-summaries", "--start-time", start, "--end-time", end], region)
    ids = [t["Id"] for t in summ.get("TraceSummaries", [])]
    agg = collections.defaultdict(lambda: {"n": 0, "sumE": 0.0})
    for i in range(0, len(ids), 5):
        traces = aws(["xray", "batch-get-traces", "--trace-ids"] + ids[i:i + 5], region)
        for tr in traces.get("Traces", []):
            for seg in tr.get("Segments", []):
                doc = json.loads(seg["Document"])
                if doc.get("origin") != "AWS::Lambda::Function":
                    continue
                t_total = doc.get("end_time", 0) - doc.get("start_time", 0)
                if t_total <= 0:
                    continue
                ov = 0.0
                for ss in doc.get("subsegments", []):
                    d = ss.get("end_time", 0) - ss.get("start_time", 0)
                    if d > 0 and is_remote_sub(ss):
                        ov += d
                E = _clamp((t_total - min(ov, t_total)) / t_total)
                a = agg[doc.get("name", "?")]
                a["n"] += 1; a["sumE"] += E
    return {k: {"E": v["sumE"] / v["n"], "traces": v["n"]} for k, v in agg.items()}


# ---------- outcomes from CloudWatch ----------
def outcomes(region, names, hours):
    now = datetime.datetime.now(datetime.timezone.utc)
    start = (now - datetime.timedelta(hours=hours)).strftime("%Y-%m-%dT%H:%M:%SZ")
    end = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    res = {}
    for name in names:
        q = [{"Id": "dur", "MetricStat": {"Metric": {"Namespace": "AWS/Lambda", "MetricName": "Duration",
              "Dimensions": [{"Name": "FunctionName", "Value": name}]}, "Period": 3600, "Stat": "p99"}},
             {"Id": "err", "MetricStat": {"Metric": {"Namespace": "AWS/Lambda", "MetricName": "Errors",
              "Dimensions": [{"Name": "FunctionName", "Value": name}]}, "Period": 3600, "Stat": "Sum"}}]
        try:
            d = aws(["cloudwatch", "get-metric-data", "--metric-data-queries", json.dumps(q),
                     "--start-time", start, "--end-time", end], region)
            vals = {m["Id"]: m.get("Values", []) for m in d.get("MetricDataResults", [])}
            p99 = max(vals.get("dur", [0]) or [0])
            errs = sum(vals.get("err", []) or [0])
            res[name] = {"p99_ms": round(p99, 1), "errors": errs}
        except Exception as e:
            res[name] = {"p99_ms": None, "errors": None, "note": str(e)[:80]}
    return res


# ---------- S and L from a local repo (optional) ----------
def git_cochange(repo, months=12):
    """Return co-change fraction per top-level module (proxy for a service)."""
    since = (datetime.date.today() - datetime.timedelta(days=30 * months)).isoformat()
    try:
        log = subprocess.run(["git", "-C", repo, "-P", "log", "--since", since,
                              "--name-only", "--pretty=format:==%H"], capture_output=True, text=True)
        if log.returncode != 0:
            return {}
    except Exception:
        return {}
    commits, cur = [], set()
    for line in log.stdout.splitlines():
        if line.startswith("=="):
            if cur:
                commits.append(cur); cur = set()
        elif line.strip():
            top = line.split("/")[0]
            cur.add(top)
    if cur:
        commits.append(cur)
    touch = collections.Counter()
    co = collections.Counter()
    for c in commits:
        for m in c:
            touch[m] += 1
            if len(c) > 1:
                co[m] += 1
    return {m: {"S": 1.0 - (co[m] / touch[m]) if touch[m] else 1.0, "changesets": touch[m]}
            for m in touch}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--region", default="us-east-1")
    ap.add_argument("--hours", type=int, default=6)
    ap.add_argument("--repo", default=None, help="local git repo path for S (optional)")
    ap.add_argument("--labels", default=None, help="CSV name,label (1 healthy/0 monolith) (optional)")
    args = ap.parse_args()

    print("=" * 78)
    print("Fulcrum AWS validation harness  (READ-ONLY: get/describe/list calls only)")
    ident = aws(["sts", "get-caller-identity"], args.region)
    print(f"account {ident.get('Account')}  arn {ident.get('Arn')}  region {args.region}")
    print("=" * 78)

    print("\n[1] Kinetic Efficiency (E) from X-Ray ...")
    E = kinetic_efficiency(args.region, args.hours)
    names = list(E.keys())
    print(f"    boundaries with traces: {len(names)}")

    print("[2] Outcomes from CloudWatch (Lambda p99 duration, errors) ...")
    O = outcomes(args.region, names, args.hours) if names else {}

    S = {}
    if args.repo:
        print("[3] Semantic Distinctness (S) from git co-change ...")
        S = git_cochange(args.repo)
        print(f"    modules analyzed: {len(S)}")
    else:
        print("[3] S skipped (no --repo). Marked unmeasured (Section 7.5 / N1).")

    labels = {}
    if args.labels and os.path.exists(args.labels):
        with open(args.labels) as f:
            for row in csv.DictReader(f):
                labels[row["name"]] = int(row["label"])

    print("\n[4] Per-boundary results")
    print(f"{'boundary':50}{'E':>7}{'S':>7}{'p99(ms)':>10}{'errors':>8}{'RVx*':>8}")
    scored = []
    for n in names:
        e = E[n]["E"]
        s = S.get(n, {}).get("S")
        # RVx* uses E and S when available; L requires static analysis (not in this run).
        rvx_star = rvx_multiplicative(e, s if s is not None else 0.5, 0.5)
        o = O.get(n, {})
        print(f"{n[:48]:50}{e:>7.3f}{(s if s is not None else float('nan')):>7.3f}"
              f"{(o.get('p99_ms') if o.get('p99_ms') is not None else float('nan')):>10}"
              f"{(o.get('errors') if o.get('errors') is not None else float('nan')):>8}{rvx_star:>8.3f}")
        scored.append((n, rvx_star))

    if labels and len(set(labels.values())) == 2:
        pairs = [(v, labels[n]) for n, v in scored if n in labels]
        if pairs:
            print(f"\n[5] Separation vs labels: AUC = {rank_auc(pairs):.3f}  (n={len(pairs)})")
    else:
        print("\n[5] No usable labels: reported measurements only (add --labels name,label to test H1).")

    print("\nHONEST SCOPE: this reports real measurements from a real account. It becomes the H1/H2")
    print("study only on a varied, labeled, higher-traffic estate. L requires static analysis wired in.")
    print("* RVx* here uses measured E, git S where available, and a placeholder L=0.5; it is a partial")
    print("  score until L is supplied. No AWS resource was created, modified, or deleted.")


if __name__ == "__main__":
    main()
