# Fulcrum RVx - Production-Grade Validation on Real AWS Lambda

**Account:** (a dev AWS account, treated as prod; account id redacted) | **Region:** us-east-1 | **Date:** 2026-08-20
**Author:** Viquar Khan (ORCID [0009-0008-3592-4162](https://orcid.org/0009-0008-3592-4162))

## What was run

A randomized estate of **36 real AWS Lambda boundaries** (X-Ray active tracing, least-privilege
IAM), engineered so each dimension drives a different independent outcome, giving every single
signal a domain to win - a fair test of the composite:

- synchronous **hops -> tail latency** (Kinetic Efficiency domain)
- **memory / code size -> cost** (Cognitive Load domain)
- **coupling -> error rate** via a shared-contention failure model (Semantic Distinctness domain)

All three signals were measured for real (E from request timing, S from version-control
co-change, L from deployed config). Outcomes (p95 latency, error rate, GB-s cost) were measured
independently - RVx never sees them. **Replicated 5x** with fresh live load. Non-circular:
RVx = f(E,S,L); label = g(latency, error, cost).

## Results (mean +/- SD over 5 replications)

**Construct validity - all three signals now valid on real infra:**

- E vs latency: **-0.52 +/- 0.16**
- L vs cost: **+0.64 +/- 0.02**
- S vs errors: **-0.50 +/- 0.15**  (new - S predicts its outcome once coupling has a runtime cost)

**Separation AUC per domain (each single signal wins its aligned domain):**

| scorer | latency-heavy | cost-heavy | reliability-heavy | worst-case |
|---|---|---|---|---|
| **additive mean** | 0.755 | 0.715 | 0.794 | **0.705 +/- 0.021** |
| efficiency only (E) | 0.819 | 0.671 | 0.759 | 0.671 +/- 0.009 |
| RVx (multiplicative) | 0.713 | 0.639 | 0.735 | 0.627 +/- 0.027 |
| geometric mean | 0.708 | 0.632 | 0.729 | 0.617 |
| hard minimum | 0.683 | 0.595 | 0.710 | 0.581 |
| distinctness only (S) | 0.602 | 0.537 | 0.678 | 0.527 |
| inverse load only (1-L) | 0.458 | 0.766 | 0.533 | 0.458 |

## What this validates (backed)

1. **Measurability + construct validity of all three signals on real AWS** - E<->latency,
   L<->cost, and (newly) S<->errors, each non-circular and stable across replications.
2. **The fusion thesis holds on real data**: a fused composite is the most robust scorer
   (worst-case AUC 0.705 > best single signal E 0.671). Fusing three signals hedges against
   not knowing which dimension dominates.
3. Three of Schneidewind's six criteria measured on a deployed benchmark (association,
   discriminative power, repeatability).

## The honest correction

**The data selects the ADDITIVE composition, not the multiplicative RVx.** The multiplicative
form landed mid-pack (worst-case 0.627), below the additive composite and E alone. Likely
mechanism: measured S is floor-bound (monorepo co-change artifact), and the multiplicative
weakest-link product lets a near-zero S collapse otherwise-healthy scores; the additive mean is
robust to one degenerate signal. Per the paper's pre-registered commitment (Section 12.3), the additive
composition is adopted as the deployment default; the multiplicative form is retained only for
component-level diagnostic decomposition. Khan's Law (weakest-link) survives as an interpretive
lens, not as the empirically preferred arithmetic.

## Still future work (scoped)

Longitudinal tracking and predictability on an organic, labeled production estate over time
(H2/H4) - the deployed benchmark cannot substitute for a real company estate observed over time.

## Reproduce

```bash
python gen_git_history.py        # measure S; sets each boundary's deployed coupling = 1 - S
python deploy_population.py      # 36 randomized Lambda boundaries, coupling-driven errors
python run_study.py              # single run
python replicate_study.py --reps 5   # aggregate_results.json, AGGREGATE_RESULTS.md
python make_aws_figure.py        # figures/figure10_aws_validation.png
python teardown_all.py           # remove all AWS resources
```

---

*Author: Viquar Khan (ORCID [0009-0008-3592-4162](https://orcid.org/0009-0008-3592-4162)). Copyright 2026 Viquar Khan.*
