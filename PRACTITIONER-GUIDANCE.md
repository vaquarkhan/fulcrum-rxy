# DDD + Fulcrum: How to Cut Microservices Without Building a Distributed Monolith

A one-page, practitioner checklist derived from the Fulcrum / RVx research and its real-AWS
validation. DDD tells you *where* the seams might be; Fulcrum tells you whether a cut actually
*pays off*. Use them together.

---

## The rule in one sentence

**Do not split on domain nouns or database tables alone. Split where a boundary keeps most of a
request's work local, where the two sides do not change together, and where a team can own it —
and measure all three before and after you cut.**

## The three questions to ask of every boundary

| Dimension | Question | Warning sign (distributed monolith) | What the AWS data showed |
|---|---|---|---|
| **Kinetic Efficiency (E)** | Does the cut turn in-process calls into chatty synchronous network calls? | One request fans out into many synchronous hops; little local work per hop | Strongest runtime signal (E vs latency ρ ≈ −0.52). Synchronous fan-out is the #1 killer. |
| **Semantic Distinctness (S)** | Do the two sides change together in version history? | Almost every feature touches both repos (temporal coupling / shared contract) | Coupling drives cascading errors (S vs errors ρ ≈ −0.50). |
| **Cognitive Load (L)** | Can the owning team actually maintain it? | Oversized "Blob" service no single team owns | Complexity/size drives cost (L vs cost ρ ≈ +0.64). |

## If a boundary fails, the fix is dimension-specific

- **Low E (chatty):** make the interaction asynchronous / event-driven, batch the calls, or
  **merge** the services. This is the highest-leverage fix.
- **Low S (entangled):** you cut in the wrong place. Re-cut along the seam the change history
  reveals, or keep the two together — they are one bounded context.
- **High L (overloaded):** reassign ownership or simplify the surface; do not let a service grow
  past what its team can hold.

## Anti-patterns to stop doing

- One service per database table.
- "Small enough to rewrite in two weeks" as a sizing rule.
- Splitting by technical layer (API / logic / data as separate services) — guarantees fan-out.
- Deciding boundaries once on a whiteboard and never re-measuring.

## The workflow (sense → decide → act → verify)

1. **Propose** boundaries with DDD (bounded contexts, aggregates).
2. **Measure** E, S, L for each candidate — separately. Trust the three components before any
   single composite score, and act on the **weakest** one.
3. **Gate it in CI/CD.** A pipeline that measures a boundary and fails the build if it scores as a
   distributed monolith works on real infrastructure (demonstrated on AWS). Catch bad cuts before
   they ship.
4. **Re-measure over time** — healthy boundaries rot into monoliths as coupling creeps in.

## If a team fixes only one thing

Cut the **synchronous cross-boundary calls**. Efficiency was the strongest single predictor of
real latency; prefer asynchronous or merged interactions over chatty synchronous fan-out.

## Honest caveat

This guidance is principled and partially evidence-backed: on real AWS each signal predicted its
target outcome and fusing the three was more robust than any single one. Full predictive validation
on organically-grown production systems over time is still future work, so treat thresholds as
directional and **calibrate them to your own estate** rather than as universal constants.
