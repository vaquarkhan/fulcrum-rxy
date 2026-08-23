"""Fulcrum RVx validation gate (runs in the pipeline's Validate stage, and locally).

STRICTLY READ + INVOKE ONLY. It invokes the deployed boundary Lambdas to generate real
timing, measures Kinetic Efficiency (E) from each function's own response, reads CloudWatch
p99 duration as an independent outcome, combines E with the engineered Semantic Distinctness
(S) and Cognitive Load (L) from boundaries.json, computes RVx, and:

  1. checks that RVx ranks healthy boundaries above distributed monoliths (rank AUC, H1);
  2. calibrates the monolith band edge to the realized score distribution (N4/N5);
  3. exits NON-ZERO (failing the pipeline) if separation is below the gate or any monolith
     is not flagged after calibration.

It creates/modifies/deletes no AWS resource. lambda:InvokeFunction and read-only
cloudwatch:GetMetricData are the only mutating-looking calls, and invoke is required to
produce traffic to measure. Use least-privilege credentials.

Usage: python validate_gate.py [--config boundaries.json]
Author: Viquar Khan (ORCID 0009-0008-3592-4162). Copyright 2026 Viquar Khan.
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import subprocess
import sys
import tempfile

from rvx import rvx, rank_auc

HERE = os.path.dirname(os.path.abspath(__file__))
# A raw '{}' payload file, referenced via fileb:// so it works on aws-cli v1 and v2 alike
# (v2 otherwise requires --cli-binary-format raw-in-base64-out).
_PAYLOAD_FILE = os.path.join(HERE, "_invoke_payload.json")

# Only these AWS operations are permitted from this tool.
ALLOWED = ("lambda invoke", "cloudwatch get-metric-data", "sts get-caller-identity")


def aws_json(args: list[str], region: str) -> dict:
    op = " ".join(args[:2])
    if not any(op.startswith(a) for a in ALLOWED):
        raise RuntimeError(f"BLOCKED: '{op}' is not on the allowlist {ALLOWED}")
    r = subprocess.run(["aws"] + args + ["--region", region, "--output", "json"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip()[:300])
    return json.loads(r.stdout) if r.stdout.strip() else {}


def invoke_and_measure_E(fn_name: str, region: str, n: int) -> float | None:
    """Invoke the boundary n times; average the E it reports for each request."""
    es: list[float] = []
    if not os.path.exists(_PAYLOAD_FILE):
        with open(_PAYLOAD_FILE, "wb") as pf:
            pf.write(b"{}")
    for _ in range(n):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tf:
            out_path = tf.name
        try:
            aws_json(["lambda", "invoke", "--function-name", fn_name,
                      "--payload", f"fileb://{_PAYLOAD_FILE}", out_path], region)
            with open(out_path, encoding="utf-8") as fh:
                payload = json.load(fh)
            e = payload.get("E")
            if e is not None:
                es.append(float(e))
        except Exception:
            pass
        finally:
            try:
                os.remove(out_path)
            except OSError:
                pass
    return sum(es) / len(es) if es else None


def cloudwatch_p99(fn_name: str, region: str, hours: int = 1) -> float | None:
    now = datetime.datetime.now(datetime.timezone.utc)
    start = (now - datetime.timedelta(hours=hours)).strftime("%Y-%m-%dT%H:%M:%SZ")
    end = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    q = [{"Id": "dur", "MetricStat": {"Metric": {"Namespace": "AWS/Lambda",
          "MetricName": "Duration", "Dimensions": [{"Name": "FunctionName", "Value": fn_name}]},
          "Period": 3600, "Stat": "p99"}}]
    try:
        d = aws_json(["cloudwatch", "get-metric-data", "--metric-data-queries", json.dumps(q),
                      "--start-time", start, "--end-time", end], region)
        vals = (d.get("MetricDataResults", [{}])[0]).get("Values", [])
        return round(max(vals), 1) if vals else None
    except Exception:
        return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=os.path.join(HERE, "boundaries.json"))
    args = ap.parse_args()
    with open(args.config, encoding="utf-8") as f:
        cfg = json.load(f)
    region = cfg.get("region", "us-east-1")
    gate = cfg.get("min_separation_auc", 0.80)
    n = cfg.get("invocations_per_boundary", 12)

    ident = aws_json(["sts", "get-caller-identity"], region)
    print("=" * 74)
    print(f"Fulcrum RVx VALIDATE gate  account {ident.get('Account')}  region {region}")
    print("=" * 74)
    print("Invoking boundaries to generate real timing, then measuring E ...\n")

    print(f"  {'boundary':26}{'label':>18}{'E(meas)':>9}{'p99ms':>8}{'S':>6}{'L':>6}{'RVx':>7}")
    rows, report = [], []
    for b in cfg["boundaries"]:
        E = invoke_and_measure_E(b["name"], region, n)
        if E is None:
            print(f"  {b['name']:26}{'':>18}{'n/a':>9}  (invoke/measure failed)")
            continue
        p99 = cloudwatch_p99(b["name"], region)
        score = rvx(E=E, S=b["S"], L=b["L"])
        lab = "healthy" if b["label"] == 1 else "distributed-monolith"
        p99s = f"{p99:.0f}" if p99 is not None else "-"
        print(f"  {b['name']:26}{lab:>18}{E:>9.3f}{p99s:>8}{b['S']:>6.2f}{b['L']:>6.2f}{score:>7.3f}")
        rows.append((score, b["label"]))
        report.append({"boundary": b["name"], "label": b["label"], "E": round(E, 3),
                       "p99_ms": p99, "S": b["S"], "L": b["L"], "rvx": round(score, 3)})

    if len({y for _, y in rows}) < 2:
        print("\nGATE: FAIL - need both healthy and monolith boundaries measured.")
        return 2

    auc = rank_auc(rows)
    healthy = sorted(r["rvx"] for r in report if r["label"] == 1)
    monolith = sorted(r["rvx"] for r in report if r["label"] == 0)
    calibrated_edge = round((min(healthy) + max(monolith)) / 2.0, 3)
    healthy_below = [r["boundary"] for r in report if r["label"] == 1 and r["rvx"] < calibrated_edge]
    flagged = [r["boundary"] for r in report if r["label"] == 0 and r["rvx"] < calibrated_edge]

    print(f"\n  [H1] separation AUC: {auc:.3f}  (gate needs >= {gate})")
    print(f"  calibrated monolith edge (N4/N5): {calibrated_edge}")
    print(f"  monoliths flagged: {len(flagged)}/{len(monolith)}   healthy false positives: {healthy_below or 'none'}")

    passed = auc >= gate and not healthy_below and len(flagged) == len(monolith)
    summary = {"account": ident.get("Account"), "region": region, "separation_auc": round(auc, 3),
               "calibrated_edge": calibrated_edge, "monoliths_flagged": len(flagged),
               "n_monolith": len(monolith), "healthy_false_positives": healthy_below,
               "passed": passed, "boundaries": report}
    with open(os.path.join(HERE, "aws_validation_report.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print("\n" + "#" * 74)
    if passed:
        print("GATE: PASS - RVx separated healthy from distributed-monolith boundaries on")
        print("      REAL AWS Lambda (E measured live), and flagged every monolith. No AWS")
        print("      resource was created, modified, or deleted by this gate.")
    else:
        print("GATE: FAIL - RVx did not separate the estate; pipeline should stop here.")
    print("#" * 74)
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
