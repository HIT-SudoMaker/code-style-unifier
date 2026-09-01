# 0022 - Let sampling bound the period and order bound the proof

Status: accepted

Implementation status: implemented (2026-08-09)

Supersedes only the period-legality clauses of
[ADR 0009 - Keep G0-only metalens proofs in the zeroth-order domain](0009-keep-g0-only-metalens-proofs-in-the-zeroth-order-domain.md).
It preserves ADR 0009's evidence claim that G0 coefficients cannot establish a
complete multi-order output field.

## Context

The metalens period domain retained two different questions: whether a lattice
samples the requested phase profile, and whether one response representation
can prove the resulting output field. ADR 0009 answered both by shrinking a
G0 route's period candidates to the smaller sampling and order ceiling. That
made a downstream observer determine upstream design legality and excluded
sampling-legal published designs before their evidence needs could be stated.

## Decision

The sampling ceiling `wavelength / (2 * numerical aperture)` is the sole hard
upper bound on metalens cell-period legality. `PeriodDomain.period_limit_nm` is
always the greatest 10 nm multiple strictly below that exact ceiling. Equality
with the sampling ceiling is illegal. Explicit brief periods, fresh
consultation answers, and Authority-backed replay use this same rule.

The order ceiling `wavelength / (substrate index + numerical aperture)` remains
exact material-grounded proof context. It does not remove a sampling-legal
candidate. A selected period below it is `zeroth order`; a selected period at
or above it is `multi order`, retaining the visible `higher orders possible`
caution through the height domain and later studies.

Proof applicability remains strict. The coefficient-only field-formation seam
accepts only `zeroth order`; it cannot form the complete aperture field, and
therefore cannot close a Result, from a multi-order choice. The separately
qualified sampled reference-surface formation is the only current route that
may carry `multi order` into a complete field. A future order-resolved method
must prove its own applicability rather than changing period legality.

## Consequences

Period legality has one owner and response applicability has one owner.
Coefficient-only routes may now pause after a legal multi-order period and
height have been selected instead of rewriting the period domain to fit G0.
The domain schema retains response capability for proof context and stable
identity; no capability registry, policy object, schema migration, or second
consultation lifecycle is introduced.

This decision changes period-domain identities derived from the corrected
limit. Existing zeroth-order choices and behavior otherwise remain unchanged.
The resolved decision record and implementation ticket are
[Four-brief grounding decision 07](../../.scratch/four-brief-grounding/decisions/07-let-sampling-bound-the-period-and-order-bound-the-proof.md)
and
[Four-brief baseline ticket 01](../../.scratch/four-brief-baseline/issues/01-let-sampling-bound-the-period-and-order-bound-the-proof.md).
