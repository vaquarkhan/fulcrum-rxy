"""Shared, seeded specification of a randomized microservice estate for the RVx production
validation study. The estate is NOT hand-labeled good/bad: every structural parameter is
drawn at random, so the health of each boundary emerges from measured outcomes, not design.

Author: Viquar Khan (ORCID 0009-0008-3592-4162). Copyright 2026 Viquar Khan.
"""
from __future__ import annotations

import os
import random

PROJECT = "fulcrum-rvx"
POP_PREFIX = f"{PROJECT}-pop-"
REGION = os.environ.get("AWS_REGION", "us-east-1")


def account_id() -> str:
    """Resolve the AWS account id at runtime; never hardcoded. Uses AWS_ACCOUNT_ID if set,
    otherwise the calling identity via STS. Returns a placeholder when neither is available."""
    acct = os.environ.get("AWS_ACCOUNT_ID")
    if acct:
        return acct
    try:
        import boto3
        return boto3.client("sts", region_name=REGION).get_caller_identity()["Account"]
    except Exception:
        return "ACCOUNT_ID"  # set AWS_ACCOUNT_ID or configure AWS credentials before deploying


def leaf_arn() -> str:
    return f"arn:aws:lambda:{REGION}:{account_id()}:function:{PROJECT}-leaf"


def role_arn() -> str:
    return f"arn:aws:iam::{account_id()}:role/{PROJECT}-boundary-exec"

N_BOUNDARIES = 36
N_CLUSTERS = 8          # coupling clusters (drive Semantic Distinctness via co-change)
SEED = 20260820
MEMORY_CHOICES = [128, 256, 512, 768, 1024]


def make_specs(n: int = N_BOUNDARIES, seed: int = SEED) -> list[dict]:
    """Return n randomized boundary specs. Deterministic for a given seed."""
    rng = random.Random(seed)
    specs = []
    for i in range(n):
        specs.append({
            "name": f"{POP_PREFIX}{i:02d}",
            "useful_ms": round(rng.uniform(2.0, 55.0), 1),   # local CPU work
            "hops": rng.randint(0, 10),                       # synchronous downstream calls
            "memory": rng.choice(MEMORY_CHOICES),             # affects cost + a bit of L
            "code_pad_kb": rng.randint(0, 40),                # varies real deployed CodeSize -> L
            "p_fail": round(rng.uniform(0.005, 0.03), 4),     # per-hop failure base (-> errors)
            "cluster": rng.randint(0, N_CLUSTERS - 1),        # coupling group (-> S via git)
        })
    return specs


if __name__ == "__main__":
    for s in make_specs():
        print(s)
