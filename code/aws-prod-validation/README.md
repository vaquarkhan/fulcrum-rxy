# Fulcrum RVx: CI/CD Validation Gate (local simulation + AWS CodePipeline)

This package demonstrates, end to end, the idea in the paper's Section 8 (the Fulcrum
governance loop) and Section 12 (the evaluation protocol) as a **deployment pipeline gate**:

> A pipeline builds and deploys a set of service boundaries, drives real traffic, measures
> **RVx** per boundary from the running system, and **fails the pipeline** if a boundary
> scores in the distributed-monolith band. RVx becomes a fitness function in CI/CD.

It comes in two forms that share the same scorer and the same gate logic:

## 1. Local simulation (runnable now, no AWS, no cost)

`simulate_pipeline.py` runs the whole pipeline on your machine using the real HTTP testbed
services in `../testbed/service.py`:

```
SOURCE  ->  BUILD  ->  DEPLOY  ->  LOAD TEST  ->  VALIDATE (RVx gate)
```

- **Deploy** launches several real service processes (healthy and distributed-monolith
  topologies) that talk over real HTTP.
- **Load test** drives traffic.
- **Validate** measures Kinetic Efficiency (E) from each running service, combines it with
  the engineered Semantic Distinctness (S) and Cognitive Load (L) for each boundary, computes
  RVx, and checks two things:
  1. **Separation (H1):** does RVx rank healthy boundaries above distributed-monolith ones?
     Reported as rank AUC.
  2. **Gate:** does every boundary clear the monolith band? If any healthy-intended boundary
     lands in the monolith band, or separation AUC is below threshold, the stage exits non-zero,
     exactly as a failing CodePipeline stage would.

Run it:

```
python simulate_pipeline.py
```

It prints each stage, a per-boundary RVx table, the separation AUC, and a final
`PIPELINE: PASS` / `PIPELINE: FAIL`. Deterministic enough to demonstrate the mechanism;
E is really measured from a running distributed system, so the low-E signature of a
distributed monolith is genuine, not asserted.

## 2. Real AWS CodePipeline (drop-in, deploy when ready)

The same gate, wired into AWS. Files:

| File | Purpose |
|------|---------|
| `template.yaml` | SAM template: Lambda boundaries with X-Ray tracing **Active** (so E is measurable), plus API Gateway to drive traffic. |
| `buildspec.yml` | CodeBuild build stage (package + unit checks). |
| `pipeline.yaml` | CloudFormation for the CodePipeline: Source -> Build -> Deploy -> **Validate**. |
| `validate_gate.py` | The Validate stage. Read-only: reads X-Ray + CloudWatch, computes RVx, exits non-zero to **fail the pipeline** if a boundary is a distributed monolith. |

### Safety (read this before deploying)

- `validate_gate.py` and the harnesses call **only** read/describe/get/list AWS APIs. They
  create, modify, and delete **nothing**. Use ReadOnly or least-privilege credentials for the
  validate stage.
- Deploying `template.yaml` and `pipeline.yaml` **does** create AWS resources (Lambda, API
  Gateway, CodePipeline, S3 artifact bucket, IAM roles) and will incur cost. Review and deploy
  deliberately, in a non-production account.
- Nothing here should be pointed at a production account without explicit intent.

### How to go from local to AWS

1. Prove the gate locally: `python simulate_pipeline.py`.
2. Create a CodeCommit repo (or connect GitHub) and push this package.
3. `sam build && sam deploy --guided` to try `template.yaml` once by hand.
4. Deploy `pipeline.yaml` to stand up the pipeline; every commit then re-runs the RVx gate.
```
