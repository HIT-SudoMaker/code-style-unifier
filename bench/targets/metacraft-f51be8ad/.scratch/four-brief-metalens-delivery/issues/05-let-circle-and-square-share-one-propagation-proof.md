# 05 — Let circle and square share one propagation proof

**Type:** implementation

**Status:** wontfix

**Superseded by:** `../../metalens-sonnet-convergence/spec.md`

**Blocked by:** ticket 04.

## Outcome

Johansen-inspired circular and Pi-inspired square briefs use one propagation
proof: one complete real cell library per brief yields independent 8-, 12-,
and 16-state Results.

## What to build

- Publish `johansen_circle_brief` and `pi_square_brief` with the exact facts
  in the canonical specification and no period, height, or lateral geometry.
- Construct typed circle and square candidates from the chosen domain and
  declared dimension step.
- Gather one complete Lumerical library for each brief.
- Use the existing finite cyclic assignment to select distinct cells for
  uniformly spaced 8-, 12-, and 16-state targets.
- Realize the aperture through vectorized stable-identity lookup and propagate
  its component-based Field with the admitted realization.
- Return three independent Results per brief with cells, state tables,
  aperture identities, focus measures, advice, bindings, and exact evidence.

## TDD seam

Begin with one compact propagation tracer through `conduct`, backed by fake
native evidence. Add separate route tests for cyclic phase closure and the
three independent quantizations.

## Acceptance

- Circle and square have equal route status and share one implementation.
- The 0/2π seam uses cyclic distance.
- Matching computes finite library loss once and performs no per-site library
  search.
- Six deterministic fake-backed propagation Results are independently
  serializable and replayable.
- No paper-provided answer, fixed workflow, optimizer, large-na method, or
  fifth public brief is added.
- Focused tests, architecture tests, Pyright, and CSU pass.
- Rust has no diff.

## Comments

### 2026-07-28 — preserve an honest unresolved brief

During fake-backed verification, both standard-aperture execution cost and a
compact tracer's unbracketed depth of focus prevented an honest Result. The
briefs and diagnostics remain unchanged. Per maintainer decision, verification
must not tune a brief merely to force a Result or fabricate focal evidence.
The shared route, typed evidence, cyclic matching, and Result interfaces are
still verified at their truthful seams; an affected brief may remain a
waiting Study for later scientific inspection.

### 2026-07-28 — implementation evidence

Published the exact Johansen-inspired circle and Pi-inspired square briefs and
moved historical examples behind test support. Both compile through the shared
typed propagation route; fake native evidence verifies circle and square
construction, cyclic phase closure, 8/12/16-state assignment, vectorized
stable-identity aperture realization, and the complete field seam. A compact
conduct proof truthfully waits when the requested focal evidence is not
bracketed.

The conduct proof also exposed and fixed a reference-closure defect: period
advice now cites only the material binding embedded in its document rather than
claiming an unembedded material sample.

Per the final maintainer ruling, this ticket does not tune either public brief
to manufacture six Results. Scientific completion remains visible as waiting
evidence for later live review. Focused tests, architecture tests, Pyright, and
the touched-file CSU hard gate pass; Rust remains unchanged.
