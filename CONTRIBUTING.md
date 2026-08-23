# Contributing to Fulcrum / RVx

Thanks for your interest. This project is at the **benchmark-validated, pre-organic-production** stage,
so the single most valuable contribution is real data. There are three good ways to help.

## 1. Contribute validation data (highest impact)

RVx has been validated on controlled simulations and a replicated real-AWS deployed benchmark, but not
yet on an organically grown, labeled production estate. If you can run the harness on real services:

1. Compute a per-boundary feature table with columns `name,E,S,L` and, if available, independent
   outcomes (p95 latency, error rate, cost, and DORA metrics: deployment frequency, lead time,
   change-failure rate, time-to-restore).
2. Anonymize service names.
3. Open an issue using the **"Validation data submission"** template, or a PR adding the anonymized
   table under `data/community/`.

This is what would move RVx from *demonstrated* to *production-validated*.

## 2. Reproduce and report

Run the experiments (`code/experiments/exp1-3`) and the real-AWS harness (`code/aws-prod-validation/`,
dev account, least-privilege credentials, always run `teardown_all.py` after). Open an issue if a
result does not reproduce.

## 3. Improve the framework

Good targets, in rough priority:
- Better Semantic Distinctness measurement on monorepos (the floor-bound-S artifact, see paper 12.10).
- Repository-scale automation of the measurement pipeline.
- Additional composition-form ablations on real data.

## Ground rules

- **Never commit credentials, account IDs, or customer data.** Anonymize before submitting.
- **Do not commit PDF copies of the paper.** Publish on arXiv; this repo holds code and docs only.
- Keep the core experiments dependency-free (Python stdlib) where possible.
- Match the paper's honest-labeling discipline: state what is proved, demonstrated, or hypothesized.
- Code contributions are licensed under Apache-2.0; documentation under CC BY 4.0 (see LICENSE files).

## Questions

Open an issue or reach the author at vaquar.khan@gmail.com.

---

*Author: Viquar Khan (ORCID [0009-0008-3592-4162](https://orcid.org/0009-0008-3592-4162)). Copyright 2026 Viquar Khan.*
