# 0008 — Honor explicit cell constraints before advice

Status: accepted

Amends:
[ADR 0007 — Report order risk without capping the cell period](0007-report-order-risk-without-capping-the-cell-period.md).

Period-selection clauses superseded by
[ADR 0009 — Keep G0-only metalens proofs in the zeroth-order domain](0009-keep-g0-only-metalens-proofs-in-the-zeroth-order-domain.md).

Period and height ownership clauses superseded by
[ADR 0011 — Let period choice precede height](0011-let-period-choice-precede-height.md).

## Context

ADR 0007 correctly made the sampling ceiling an upper bound and the order
ceiling a warning, but the current implementation still makes the largest
sampling-safe period the only physical period. Published metalenses commonly
use a smaller disclosed period, and a paper-reproduction brief may also state
an exact atom height. Replacing either fact with an LLM recommendation would
erase the experiment being reproduced.

## Decision

A metalens brief may state an exact cell period, atom height, and
route-compatible fixed atom geometry as constraints. The compiler preserves
those facts without consultation.

- An explicit period must be positive and no greater than the sampling
  ceiling itself. When absent, ADR 0007's floored sampling-ceiling default
  remains; the floored default is not the ceiling.
- The height domain owns the resulting physical period, derives its order
  regime from the admitted material sample, and keeps `higher orders possible`
  non-blocking.
- An explicit height becomes the sole constrained height after fabrication
  validation, even when it lies outside the control strategy's default height
  prior.
  Its height choice cites the brief constraint and domain through an explicit
  height basis; it does not manufacture synthetic advice.
- An explicit propagation height remains subject to the method's certified
  phase-envelope exclusions. Forecasts and advice cannot rewrite or veto it.
- A fixed atom geometry is validated against the exact period, height, aspect
  limit, and gap. It forms a singleton candidate plan. A generic sweep step
  constrains generated candidates, not a cited geometry that satisfies those
  physical bounds.
- Without an explicit height, the existing control-strategy height domain,
  phase envelope where applicable, height advice, and deterministic choice
  remain unchanged.
- Shape remains an explicit brief fact. Advice may recommend a shape for a
  general design, but it cannot rewrite a paper-bound brief.

Explicit constraints do not bypass material qualification, fabrication
checks, solver evidence, phase-set formation, field propagation, or focus
evaluation. Rust authority and protocol bytes remain unchanged.

## Consequences

No new lifecycle position named `period choice` is introduced. Published
periods and heights can pass through the existing
`brief -> design -> height domain -> height choice` mental order, while
unspecified designs retain the existing advice path. A result remains an
`adapted reproduction` unless every comparison fact and evaluation convention
is actually preserved.
