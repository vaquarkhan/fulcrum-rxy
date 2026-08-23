# AWS CI/CD pipeline validation (CodeCommit / CodePipeline)

This package demonstrates the Fulcrum governance loop (Section 8) as a **deployment pipeline gate**:

> Build and deploy service boundaries, drive real traffic, measure **RVx** per boundary from the
> running system, and **fail the pipeline** if separation fails or a distributed monolith is not flagged.

Two forms share the same scorer and gate logic:

## 1. Local simulation (no AWS, no cost)

`simulate_pipeline.py` runs five stages using real HTTP testbed services in `../testbed/`:

```
SOURCE  ->  BUILD  ->  DEPLOY  ->  LOAD TEST  ->  VALIDATE (RVx gate)
```

```bash
python simulate_pipeline.py
```

## 2. Real AWS CodePipeline

| File | Purpose |
|------|---------|
| `app-stack.yaml` | Lambda boundaries with X-Ray Active (E measurable) |
| `pipeline-stack.yaml` | CodeCommit -> Build -> Deploy -> Validate pipeline |
| `validate_gate.py` | Validate stage: invoke boundaries, compute RVx, fail on bad separation |
| `boundaries.json` | Per-boundary S, L, and engineered labels |
| `push_to_codecommit.py` | Seed CodeCommit via boto3 |

```bash
python validate_gate.py
python push_to_codecommit.py
```

### Safety

- `validate_gate.py` is read + invoke only (Lambda invoke, CloudWatch metrics, STS identity).
- Deploying the CloudFormation stacks **creates** AWS resources and incurs cost. Use a dev account only.
- Run `teardown_all.py` from `../aws-prod-validation/` after population studies; pipeline stacks are torn down separately.
