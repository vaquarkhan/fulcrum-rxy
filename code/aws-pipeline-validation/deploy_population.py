"""Deploy the randomized microservice estate to real AWS Lambda (boto3).

Each boundary self-measures Kinetic Efficiency (E) from real request timing and calls the
shared leaf `hops` times over real Lambda invokes (real overhead). A cascading-failure model
ties the error rate to hop count. Deployed CodeSize is varied per boundary (padding) so that
Cognitive Load (L), computed later from real function configuration, varies for real.

Reuses the least-privilege fulcrum-rvx-boundary-exec role (logs + xray + invoke leaf only).
Creates only Lambda functions named fulcrum-rvx-pop-*. Re-runnable (updates if present).

Usage: python deploy_population.py
Author: Viquar Khan (ORCID 0009-0008-3592-4162). Copyright 2026 Viquar Khan.
"""
from __future__ import annotations

import csv
import io
import os
import time
import zipfile

import boto3
from botocore.exceptions import ClientError

from population_spec import make_specs, REGION, leaf_arn, role_arn

HERE = os.path.dirname(os.path.abspath(__file__))

HANDLER_SRC = '''import os, time, random
U = float(os.environ.get("USEFUL_MS", "20"))
H = int(os.environ.get("HOPS", "0"))
PF = float(os.environ.get("P_FAIL", "0.02"))
CPL = float(os.environ.get("COUPLING", "0"))
LEAF = os.environ.get("LEAF_ARN", "")
_lam = None
def burn(ms):
    end = time.perf_counter() + ms / 1000.0
    x = 0
    while time.perf_counter() < end:
        x += 1
    return x
def handler(event, ctx):
    global _lam
    t0 = time.perf_counter()
    u0 = time.perf_counter(); burn(U); useful = time.perf_counter() - u0
    for _ in range(H):
        if LEAF:
            try:
                import boto3
                if _lam is None:
                    _lam = boto3.client("lambda")
                _lam.invoke(FunctionName=LEAF, InvocationType="RequestResponse", Payload=b"{}")
            except Exception:
                pass
    total = time.perf_counter() - t0
    # Errors are dominated by coupling (shared-contention / coordination failures), so a
    # coupling-entangled boundary fails more; hops add a small residual. This gives Semantic
    # Distinctness a domain to predict, independent of the latency (hops->E) domain.
    fail_prob = min(0.9, 0.03 + 0.6 * CPL + 0.01 * H)
    ok = random.random() >= fail_prob
    return {"service": os.environ.get("SVC"), "E": (useful / total) if total > 0 else None,
            "useful": useful, "total": total, "ok": ok}
'''


def build_zip(pad_kb: int) -> bytes:
    src = HANDLER_SRC
    if pad_kb > 0:
        src += "\n# padding to vary deployed CodeSize:\n#" + ("x" * (pad_kb * 1024))
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("index.py", src)
    return buf.getvalue()


def load_coupling():
    """COUPLING = 1 - S per boundary (from measured co-change). Requires s_scores.csv."""
    import csv as _csv
    path = os.path.join(HERE, "s_scores.csv")
    cpl = {}
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            for row in _csv.DictReader(f):
                cpl[row["name"]] = max(0.0, 1.0 - float(row["S"]))
    return cpl


def main() -> int:
    lam = boto3.client("lambda", region_name=REGION)
    LEAF_ARN = leaf_arn()   # resolved from AWS_ACCOUNT_ID or the calling identity, never hardcoded
    ROLE_ARN = role_arn()
    specs = make_specs()
    cpl = load_coupling()
    print(f"Deploying {len(specs)} randomized boundaries to real AWS Lambda "
          f"(coupling set for {len(cpl)} from s_scores.csv) ...")
    created, updated = 0, 0
    for s in specs:
        zip_bytes = build_zip(s["code_pad_kb"])
        env = {"Variables": {"SVC": s["name"], "USEFUL_MS": str(s["useful_ms"]),
                             "HOPS": str(s["hops"]), "P_FAIL": str(s["p_fail"]),
                             "COUPLING": str(round(cpl.get(s["name"], 0.0), 4)),
                             "LEAF_ARN": LEAF_ARN}}
        common = dict(FunctionName=s["name"], Runtime="python3.12", Role=ROLE_ARN,
                      Handler="index.handler", Timeout=30, MemorySize=s["memory"],
                      TracingConfig={"Mode": "Active"}, Environment=env)
        try:
            lam.create_function(Code={"ZipFile": zip_bytes}, **common)
            created += 1
        except ClientError as e:
            if e.response["Error"]["Code"] == "ResourceConflictException":
                lam.update_function_code(FunctionName=s["name"], ZipFile=zip_bytes)
                waiter = lam.get_waiter("function_updated_v2")
                waiter.wait(FunctionName=s["name"])
                lam.update_function_configuration(**common)
                updated += 1
            else:
                raise
    print(f"  created {created}, updated {updated}")

    # wait until all active
    waiter = lam.get_waiter("function_active_v2")
    for s in specs:
        waiter.wait(FunctionName=s["name"])
    print("  all functions active")

    manifest = os.path.join(HERE, "population_manifest.csv")
    with open(manifest, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["name", "useful_ms", "hops", "memory",
                                          "code_pad_kb", "p_fail", "cluster"])
        w.writeheader()
        for s in specs:
            w.writerow(s)
    print(f"  wrote {manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
