"""Commit the pipeline package to AWS CodeCommit via the API (no git, no credentials prompt).

Uses your existing AWS CLI credentials through boto3. Creates a single commit on the target
branch containing the files this pipeline needs at the repo root. Re-runnable: it reads the
current branch tip (if any) and commits on top.

Usage: python push_to_codecommit.py [--repo fulcrum-rvx-validation] [--branch main] [--region us-east-1]
"""
from __future__ import annotations

import argparse
import os

import boto3
from botocore.exceptions import ClientError

HERE = os.path.dirname(os.path.abspath(__file__))

# Files that live at the repo root (validate stage imports rvx + reads boundaries.json).
FILES = ["app-stack.yaml", "pipeline-stack.yaml", "validate_gate.py", "rvx.py",
         "boundaries.json", "simulate_pipeline.py", "README.md"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default="fulcrum-rvx-validation")
    ap.add_argument("--branch", default="main")
    ap.add_argument("--region", default="us-east-1")
    args = ap.parse_args()

    cc = boto3.client("codecommit", region_name=args.region)

    put_files = []
    for name in FILES:
        path = os.path.join(HERE, name)
        if not os.path.exists(path):
            print(f"  skip (missing): {name}")
            continue
        with open(path, "rb") as fh:
            put_files.append({"filePath": name, "fileContent": fh.read()})
    print(f"committing {len(put_files)} files to {args.repo}@{args.branch} ...")

    # Find the current branch tip, if the branch already exists.
    parent = None
    try:
        b = cc.get_branch(repositoryName=args.repo, branchName=args.branch)
        parent = b["branch"]["commitId"]
    except ClientError as e:
        if e.response["Error"]["Code"] not in ("BranchDoesNotExistException",):
            raise

    kwargs = dict(repositoryName=args.repo, branchName=args.branch,
                  authorName="Viquar Khan", email="vaquar.khan@gmail.com",
                  commitMessage="Add Fulcrum RVx validation pipeline (app + gate + pipeline)",
                  putFiles=put_files)
    if parent:
        kwargs["parentCommitId"] = parent

    try:
        resp = cc.create_commit(**kwargs)
        print(f"  commit {resp['commitId']} created on {args.branch}")
        return 0
    except ClientError as e:
        code = e.response["Error"]["Code"]
        if code == "NoChangeException":
            print("  no changes since last commit; nothing to push")
            return 0
        raise


if __name__ == "__main__":
    raise SystemExit(main())
