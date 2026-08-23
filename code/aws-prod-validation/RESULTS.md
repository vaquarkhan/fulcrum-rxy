# Fulcrum RVx: Production Validation on a Real AWS Lambda Estate

- Boundaries: **36** randomized real Lambda functions (us-east-1), 20 invokes each.

- Signals measured for real: E (request timing), S (git co-change), L (deployed config, structural).

- Outcomes measured independently: p95 latency, error rate, GB-second cost. RVx never observes these.


## AUC per domain and worst-case robustness

| scorer | latency-heavy | balanced | reliability-cost | worst-case |
|---|---|---|---|---|
| RVx (multiplicative) | 0.604 | 0.693 | 0.669 | 0.604 |
| additive mean | 0.585 | 0.731 | 0.740 | 0.585 |
| hard minimum | 0.605 | 0.663 | 0.622 | 0.605 |
| geometric mean | 0.598 | 0.687 | 0.663 | 0.598 |
| efficiency only (E) | 0.672 | 0.827 | 0.755 | 0.672 |
| distinctness only (S) | 0.534 | 0.567 | 0.560 | 0.534 |
| inverse load only (1-L) | 0.472 | 0.475 | 0.650 | 0.472 |

## Rank correlations with independent outcomes (Spearman)

- RVx_vs_latency: -0.266
- RVx_vs_cost: -0.319
- RVx_vs_errors: -0.398
- E_vs_latency: -0.327
- L_vs_cost: +0.642
- S_vs_errors: -0.282

## Headline

Most robust scorer by worst-case AUC across domains: **efficiency only (E)** (worst-case 0.672).

---

*Author: Viquar Khan (ORCID [0009-0008-3592-4162](https://orcid.org/0009-0008-3592-4162)). Copyright 2026 Viquar Khan.*
