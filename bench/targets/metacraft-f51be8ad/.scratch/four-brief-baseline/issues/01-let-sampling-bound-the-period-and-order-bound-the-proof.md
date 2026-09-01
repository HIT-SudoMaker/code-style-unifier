# 01 — Let sampling bound the period and order bound the proof

**Parent spec:** [Four-brief grounded baseline](../spec.md)

**Decision source:** [Let sampling bound the period and order bound the proof](../../four-brief-grounding/decisions/07-let-sampling-bound-the-period-and-order-bound-the-proof.md)

**Status:** resolved (2026-08-09)

**Blocked by:** none

## What to change

Record one focused ADR after ADR 0021 that supersedes only ADR 0009's
period-legality clauses. Preserve ADR 0009's central evidence claim: a G0-only
periodic response cannot represent the complete output field once nonzero
orders may propagate. Update `CONTEXT.md` and `SCIENCE.md` so `sampling
ceiling`, `order ceiling`, `period limit`, `order regime`, and `cell period`
tell the same story.

Change the existing metalens period seam rather than adding a policy object.
`PeriodDomain.period_limit_nm` must be the greatest 10 nm multiple strictly
below `sampling_ceiling_nm` for every current response capability. Retain the
exact order ceiling and response capability in the domain as proof context.
Period requests must offer every 10 nm candidate through that sampling limit;
the order ceiling is a fact/caution, not a constraint ground. Explicit brief
periods and consultation answers obey the same legality function.

The selected `PeriodChoice` continues to classify `zeroth order` below the
order ceiling and `multi order` at or above it. Height domain, height advice,
and Study cautions retain that classification. At the downstream evidence
boundary, prove with deterministic fixtures that coefficient-only evidence
cannot close a complete aperture-field or Result for a multi-order choice,
while the existing qualified reference-surface route remains the only current
route that may carry such a choice forward.

## Acceptance

- Sampling-ceiling equality is illegal; the greatest lower 10 nm step is the
  period limit.
- A sampling-legal candidate above the order ceiling is offered, accepted,
  classified `multi order`, and retains a visible caution.
- A candidate at or above the sampling ceiling is rejected with sampling-owned
  meaning; no order-owned rejection masquerades as period illegality.
- Zeroth-order behavior remains byte-stable except where the corrected domain
  limit or its derived identity must change.
- Fresh consultation and Authority-backed replay validate the same candidate
  set and order classification.
- A multi-order G0 fixture cannot yield a complete-field claim; no test treats
  `WaitingStudies` as failure.

## Verification

Run focused period, consultation, replay, explicit-cell, height-domain, and
complete-field applicability tests, then the architecture and local Markdown
link gates. Do not run Lumerical or alter benchmark cases in this ticket.

## Stop condition

Stop when period legality has one owner and proof applicability has one owner.
Do not rename public domain values, add a capability registry, migrate stored
documents, or generalize the rule beyond metalens period evidence.

## Closure

ADR 0022, the canonical glossary, and `SCIENCE.md` now agree with the one
implemented rule. Focused period, consultation, replay, explicit-cell,
height, coefficient-field, reference-surface, standard-study, and conduct
verification passed without Lumerical execution. Architecture, Markdown-link,
and diff checks also passed.
