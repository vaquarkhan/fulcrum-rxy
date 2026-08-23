# Fulcrum RVx: Production Validation on Real AWS Lambda (multi-replication)

- 36 randomized real Lambda boundaries, us-east-1; **5 replications** (fresh load + independent change-history draw each).

- Signals measured for real (E timing, S co-change, L deployed config); outcomes measured independently (p95 latency, error rate, GB-s cost). RVx never sees outcomes.


## AUC per domain and worst-case (mean +/- SD)

| scorer | latency-heavy | cost-heavy | reliability-heavy | worst-case |
|---|---|---|---|---|
| RVx (multiplicative) | 0.713+/-0.048 | 0.639+/-0.004 | 0.735+/-0.102 | 0.627+/-0.027 |
| additive mean | 0.755+/-0.045 | 0.715+/-0.002 | 0.794+/-0.087 | 0.705+/-0.021 |
| hard minimum | 0.683+/-0.044 | 0.595+/-0.003 | 0.710+/-0.101 | 0.581+/-0.027 |
| geometric mean | 0.708+/-0.045 | 0.632+/-0.003 | 0.729+/-0.108 | 0.617+/-0.031 |
| efficiency only (E) | 0.819+/-0.068 | 0.671+/-0.009 | 0.759+/-0.052 | 0.671+/-0.009 |
| distinctness only (S) | 0.602+/-0.041 | 0.537+/-0.000 | 0.678+/-0.107 | 0.527+/-0.019 |
| inverse load only (1-L) | 0.458+/-0.056 | 0.766+/-0.000 | 0.533+/-0.063 | 0.458+/-0.056 |

## Rank correlations with independent outcomes (mean +/- SD)

- RVx_vs_latency: -0.317 +/- 0.131
- RVx_vs_cost: -0.327 +/- 0.029
- RVx_vs_errors: -0.500 +/- 0.171
- E_vs_latency: -0.522 +/- 0.158
- L_vs_cost: +0.639 +/- 0.015
- S_vs_errors: -0.503 +/- 0.146

## Headline

Most robust scorer by mean worst-case AUC: **additive mean** (0.705 +/- 0.021).

---

*Author: Viquar Khan (ORCID [0009-0008-3592-4162](https://orcid.org/0009-0008-3592-4162)). Copyright 2026 Viquar Khan.*
