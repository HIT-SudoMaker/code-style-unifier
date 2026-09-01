# 05 — Let discrepancies select the response sweep

Type: implementation

Status: resolved (2026-08-06)

Blocked by: 04 — Let field assumptions reveal their bias.

Execution state: dependency satisfied; Ticket 04 resolved the bounded
diagnostic-field differences on 2026-08-06.

## What to build

Inspect only the recorded intermediate response evidence selected by the
endpoint and assumption comparisons. Explain phase coverage, transmission,
polarization conversion, leakage, candidate density, or sampled-surface
behavior without opening unbounded or live solver work.

Selection is based on bounded method-family representatives. It produces
investigation hypotheses for exact cases, not claims about an exact paper-scale
Result that Ticket 03 did not admit.

## Option C boundary

Ticket 03 proved that no exact paper-scale Result exists yet. Therefore this
ticket applies the selection rules only to Ticket 04's bounded representative
diagnostics. A selected family is an investigation hypothesis, not evidence of
paper disagreement. Exact endpoint rules remain dormant until an exact Result
and exact comparison are separately admitted.

## Selection rules

- [x] The bounded selector does not infer a design-end or ideal-field endpoint
      difference while no exact Result exists; those exact-only rules remain
      dormant rather than being fabricated from representatives.
- [x] An assigned-target or assigned-orientation difference selects only the
      admitted aperture assignment and no cell-response family.
- [x] A realized-phase difference selects propagation phase coverage,
      candidate spacing, selection loss, and tie-break evidence.
- [x] A realized-amplitude difference selects useful power, transmitted power,
      conversion power, or retained-channel leakage.
- [x] A sampled-surface difference selects raw rectilinear coordinates,
      uniform reference-surface formation, field sampling, and vector
      propagation evidence.
- [x] A case whose endpoint and diagnostic comparisons agree selects no
      response sweep and records that stop decision.

## Method-specific constraints

- [x] Propagation inspection holds the blind selected period and height fixed
      while reviewing lateral geometry against phase and transmission.
- [x] Geometric inspection reviews the admitted long/short-axis response and
      Jones conversion at the selected cell.
- [x] Analytic rotations create no orientation-specific solver work.
- [x] High-NA inspection retains sampled surface evidence and does not replace
      it with coefficient-only claims.
- [x] No published geometry is injected as a candidate or constraint.

## Architecture and cost constraints

- [x] Use retained recorded evidence first; this ticket performs zero Adviser,
      Native, Lumerical, product-session, permit, or placement work.
- [x] Do not create a sweep runner, optimizer, result registry, mutable study,
      or second evidence lifecycle.
- [x] A missing recorded fact returns one exact investigation need for Ticket
      06; malformed retained evidence raises directly.

## Verification

- [x] Each inspected evidence set cites one upstream discrepancy and contains
      no unrelated parameter family.
- [x] Representatives with no discrepancy prove zero selected sweep work.
- [x] Focused tests, relevant non-live and architecture tests, Pyright,
      blocking CSU, frozen Rust diff, and `git diff --check` pass.

## Stop condition

Stop with one evidence-backed explanation, one bounded missing observation, or
one explicit no-sweep decision per case. Do not run the missing observation.

## Resolution

One external read-only Interface,
`select_response_investigation(diagnostic, *, fetch)`, now converts the first
bounded diagnostic difference into exactly one immutable
`ResponseInvestigation`. It reads only the selected references and verifies
their content identity. A missing retained object returns one bounded need;
malformed bytes raise directly; no divergence returns `no sweep` with zero
reads.

The selection vocabulary is deliberately finite:

- assigned target or assigned orientation -> field assignment;
- realized phase -> propagation phase response;
- realized coefficient -> propagation useful response;
- realized Jones -> geometric Jones response;
- sampled surface -> sampled-surface provenance;
- no divergence -> no sweep.

Ticket 04's complete representative matrix selected only field-assignment and
propagation-phase hypotheses. These findings are not exact Yun, Yang, Arbabi,
or Khorasaninejad discrepancies. They therefore earn no exact Live observation
for Ticket 06. Ticket 06 remains a separate human gate without a scientifically
justified exact run until an exact unresolved comparison is named.
