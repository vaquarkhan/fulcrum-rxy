# Fulcrum experiments: proving the concepts with code

Dependency-free (Python 3.10+, standard library only). Run each file directly.
These are controlled, seeded, reproducible experiments that demonstrate the *mechanism*
of the Fulcrum concepts. They are honest about what they do and do not establish: they
prove behavior on defined models, not production validity. A live corpus / agent
benchmark remains the next step (paper Section 12).

## Files

- `fulcrum_core.py` — the RVx scorer plus every competing composition form (additive,
  hard-minimum, geometric-mean, numerator-load, single-signal) and stdlib metrics
  (rank AUC, Spearman).
- `exp1_discrimination.py` — the Section 12.3 ablation as a non-circular experiment.
- `exp2_agentic.py` — RVx-A for MCP tool boundaries, calibrated to the published
  tool-selection collapse.

## What Experiment 1 proves (and does not)

Generates boundaries with a latent quality under three ground-truth models (weakest-link,
product, additive), adds measurement noise, and asks which scoring form best recovers the
true label by ROC AUC. Result (400 boundaries, 40 seeds):

- **Proven, robust:** any fusion of the three signals (AUC 0.83 to 0.97) crushes any
  single signal (0.68 to 0.76). Fusing runtime, evolution, and load beats one signal.
- **Proven, conditional:** the *best* composition depends on the true structure. Hard
  minimum wins under weakest-link truth, geometric mean under product truth, additive
  under additive truth. The multiplicative RVx is consistently strong but not always the
  single best; the geometric mean is a strong, simpler contender.
- **Not proven:** which truth model real production boundaries follow. That is the crisp,
  falsifiable question a real corpus must answer.

## What Experiment 2 proves (and does not)

Uses a model of tool-selection accuracy calibrated to published anchors (near 0.9 at ~20
tools, collapsing toward ~0.13 near ~107 tools). Result:

- **Reproduces** the documented collapse as tool count and Agent Context Load rise.
- **Directional:** RVx-A tracks net value (accuracy weighted by efficiency) at Spearman
  ~0.66, better than it tracks accuracy alone (~0.56). Neither is near 1.0, because one
  bounded scalar cannot fully capture a multi-factor outcome. The code deliberately does
  not overclaim this.
- **Adaptive Tool Surfacing:** holding Agent Context Load low by surfacing a relevant
  subset recovers accuracy several-fold (in this run, 0.10 to 0.68), the same direction
  and magnitude class as the published filtered-subset gains.
- **Not proven:** anything about a live LLM. This is a calibrated model, not an evaluation.

## Honest status

These experiments move the paper's claims from "asserted" to "demonstrated on controlled
models." They are the mechanism proof. They are not the production validation, which needs
a real labeled corpus (microservice core) and a live agent benchmark (RVx-A).
