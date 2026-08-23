"""Tear down ALL AWS resources created for the Fulcrum RVx validation.

Deletes: the 36 population Lambda functions, empties + removes the pipeline stack (which
owns the S3 artifact bucket), removes the app stack (leaf + boundary Lambdas + roles), and
deletes the CodeCommit repo. Idempotent: missing resources are skipped.

Usage: python teardown_all.py
Author: Viquar Khan (ORCID 0009-0008-3592-4162). Copyright 2026 Viquar Khan.
"""
from __future__ import annotations

import boto3
from botocore.exceptions import ClientError

from population_spec import make_specs, REGION, PROJECT, account_id

APP_STACK = f"{PROJECT}-app"
PIPELINE_STACK = f"{PROJECT}-pipeline"
REPO = f"{PROJECT}-validation"
# Bucket name is account-scoped; the account id is resolved at runtime, never hardcoded.
BUCKET = f"{PROJECT}-artifacts-{account_id()}"


def delete_pop_functions():
    lam = boto3.client("lambda", region_name=REGION)
    n = 0
    for s in make_specs():
        try:
            lam.delete_function(FunctionName=s["name"])
            n += 1
        except ClientError as e:
            if e.response["Error"]["Code"] != "ResourceNotFoundException":
                raise
    print(f"deleted {n} population functions")


def empty_bucket():
    s3 = boto3.resource("s3", region_name=REGION)
    try:
        b = s3.Bucket(BUCKET)
        b.object_versions.delete()
        print(f"emptied bucket {BUCKET}")
    except ClientError as e:
        if e.response["Error"]["Code"] not in ("NoSuchBucket", "404"):
            print(f"bucket empty skipped: {e.response['Error']['Code']}")


def delete_stack(name):
    cf = boto3.client("cloudformation", region_name=REGION)
    try:
        cf.delete_stack(StackName=name)
        print(f"deleting stack {name} ...")
        cf.get_waiter("stack_delete_complete").wait(StackName=name)
        print(f"  {name} deleted")
    except ClientError as e:
        print(f"  {name}: {e.response['Error']['Code']}")


def delete_repo():
    cc = boto3.client("codecommit", region_name=REGION)
    try:
        cc.delete_repository(repositoryName=REPO)
        print(f"deleted CodeCommit repo {REPO}")
    except ClientError as e:
        print(f"  repo: {e.response['Error']['Code']}")


def main() -> int:
    delete_pop_functions()
    empty_bucket()
    delete_stack(PIPELINE_STACK)
    delete_stack(APP_STACK)
    delete_repo()
    print("\nTeardown complete. Verify in the console; a few log groups may remain (free).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
