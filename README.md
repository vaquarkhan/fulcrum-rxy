# Fulcrum &middot; The RVx Index

Full paper - https://zenodo.org/records/23284522


**A quantitative, governed fitness function for microservice boundary granularity.**

This repository holds the **code, the interactive calculator, and the reproducible validation harness**.
The research paper is published separately on **arXiv** (link below); this repo is code and tooling.

Fulcrum fuses three signals normally analyzed in isolation into one bounded, diagnostic, per-boundary
score, the **RVx Index**, that tells you whether a service boundary adds value or is a distributed
monolith:

- **Kinetic Efficiency (E)** - runtime overhead from distributed traces (useful time / total time).
- **Semantic Distinctness (S)** - evolutionary independence from version-control co-change.
- **Cognitive Load (L)** - maintenance complexity normalized against team capacity (Conway's Law made measurable).

```
RVx_raw = (E^beta * S) / (L^alpha + epsilon)      RVx = RVx_raw / (1 + RVx_raw)
```

A low score does not just flag a problem; its weakest component names the remedy (merge, re-cut, make
asynchronous, or reassign ownership). Fulcrum wraps RVx in a sense-decide-actuate-verify loop that can
run as a pull-request advisory or a CI/CD fitness gate.

## Paper

The full paper (definitions, formal properties, evaluation protocol, and results) is on arXiv:

> **arXiv:** _link to be added once posted_
> **Viquar Khan.** *Fulcrum: Quantitative, Governed Granularity for Microservice Boundaries with the RVx Index.* 2026. ORCID [0009-0008-3592-4162](https://orcid.org/0009-0008-3592-4162).

**Provenance.** This is the rigorous research treatment of ideas developed openly since 2017 in the
free field guide [Microservices Recipes - The Architect's Field Guide](https://github.com/vaquarkhan/microservices-recipes-a-free-gitbook),
where Fulcrum appears as the Adaptive Granularity Governance chapter.

## Try it

**Live site (GitHub Pages):** enable Pages with source = `/docs`. Visitors land on `docs/index.html`
(an illustrated overview of the Khan family of patterns) and click through to the calculator at
`docs/calculator.html`.

Or open **[`docs/calculator.html`](docs/calculator.html)** directly in a browser. Score a boundary,
score an AI agent's tool surface (RVx-A), pick a saga topology (SCS), or paste `name,E,S,L` rows to
rank your real services.

## What's here

| Path | Contents |
|------|----------|
| `fulcrum-calculator.html` / `docs/index.html` | Interactive RVx / RVx-A / SCS calculator |
| `code/experiments/` | Controlled experiments (exp1-3) + reference scorer `fulcrum_core.py` |
| `code/testbed/` | Local real-HTTP testbed that measures E on a running system |
| `code/aws-prod-validation/` | Real-AWS validation harness + `VALIDATION-REPORT.md` + data |
| `code/aws-pipeline-validation/` | CloudFormation + RVx CI/CD gate (CodeCommit/CodePipeline) |
| `figures/` | Figures, including the real-AWS validation (Figure 10) |
| `PRACTITIONER-GUIDANCE.md` | One-page "how to cut microservices" checklist |

## Reproduce

Dependency-free Python (matplotlib only for figures; boto3 for the AWS scripts). From `code/experiments/`:

```bash
python exp1_discrimination.py     # ablation: fusion beats single signals
python exp2_agentic.py            # RVx-A reproduces the tool-selection collapse
python exp3_simulation.py         # non-circular robustness simulation
```

Real-AWS validation (creates and deletes AWS Lambda resources; use a dev account, least-privilege creds):

```bash
cd code/aws-prod-validation
python gen_git_history.py
python deploy_population.py
python replicate_study.py --reps 5
python teardown_all.py            # removes every resource
```

Full numbers: `code/aws-prod-validation/VALIDATION-REPORT.md`.

## Contributing

The highest-impact contribution is data: run the harness on a real, labeled estate and submit an
anonymized feature table (see `CONTRIBUTING.md`). Never commit credentials, account IDs, or customer data.

## License

Code under Apache-2.0 (`LICENSE`). Documentation and figures under CC BY 4.0 (`LICENSE-docs`).
Cite via `CITATION.cff`.

---

*Author: Viquar Khan (ORCID [0009-0008-3592-4162](https://orcid.org/0009-0008-3592-4162)). Copyright 2026 Viquar Khan.*
