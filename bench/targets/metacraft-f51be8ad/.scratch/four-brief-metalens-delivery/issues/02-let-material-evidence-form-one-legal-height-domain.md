# 02 — Let material evidence form one legal height domain

**Type:** implementation

**Status:** wontfix

**Superseded by:** `../../metalens-sonnet-convergence/spec.md`

**Blocked by:** ticket 01, because both tickets touch application composition.

## Outcome

Material evidence precedes period advice. One validated period and one
separate height advice form the finite height domain without silently changing
the brief or advice.

## What to build

- Deepen the existing adviser interface with `recommend_period` and
  `recommend_height`; retain distinct immutable records for both.
- Sample the exact substrate index before computing the order ceiling or
  requesting period advice.
- Compute exact Decimal sampling and order ceilings, then the greatest 10 nm
  multiple strictly below their minimum as the period limit.
- Accept a 10 nm-aligned explicit or advised period unchanged, or return a
  typed finding; never floor, clamp, or repair it.
- Let Design retain intent and sampling ceiling only. Let HeightDomain retain
  the selected period, period basis, exact order ceiling, period limit, order
  regime, finite height prior, fabrication bounds, and candidate counts.
- Request height advice only after the domain exists; for propagation phase,
  include its exact phase envelope.
- Make `dimension_step_nm` the sole canonical brief field and remove
  `lateral_step_nm` without an alias.
- Enforce the necessary generated-geometry minima: at least sixteen distinct
  propagation dimensions or two distinct geometric axes.
- Preserve both advice records and bases through Result provenance and replay.

## TDD seam

Begin at pure compilation with one exact worked ceiling, including the
grid-aligned edge where 850 nm yields a period limit of 840 nm. Continue
vertically through missing, invalid, and accepted advice.

## Acceptance

- The chain is material evidence → period advice → validated period/basis →
  height domain → propagation envelope when applicable → height advice →
  height choice.
- No solver sweep opens before both choices are valid.
- Invalid or unavailable advice returns an honest waiting Study.
- The four standard briefs produce their specified finite height priors and
  candidate arithmetic.
- No `PeriodChoice`, period planner, second provider Adapter, or generic
  choice framework is introduced.
- Focused tests, architecture tests, Pyright, and CSU pass.
- Rust has no diff.

## Verification

Implemented on 2026-07-28 without a commit.

- Material, advice, conduct, height, envelope, phase-set, and Result checks
  passed in deterministic groups, including 104 primary science checks and
  the complete 12-test propagation Result module.
- Independent advice, height, envelope, and architecture review: 59 passed;
  one explicit live check deselected.
- Pyright: zero errors.
- CSU on touched production files: zero hard violations.
- `lateral_step_nm`, `HeightAdviser`, and production compatibility aliases:
  absent.
- Rust diff: empty.

The broad suite remains slow because legacy Result tests recompute Field
propagation. Ticket 03 now changes that test organization without changing
the scientific contracts established here.
