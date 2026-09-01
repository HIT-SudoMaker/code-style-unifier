# 03 — Let period choose before height

Type: implementation

Status: resolved (2026-07-28)

Blocked by: ticket 02.

Decision: [ADR 0011](../../../docs/adr/0011-let-period-choice-precede-height.md).

## Outcome

Period and height form two explicit, paired choices. Each choice is grounded
before the next scientific domain can exist.

## What to build

- Move metalens material binding, period, height, and phase-envelope science
  under `science/metalens/`.
- Introduce `PeriodDomain` and `PeriodChoice` as the exact counterpart to
  `HeightDomain` and `HeightChoice`.
- Form `PeriodDomain` only from the exact brief, material binding, substrate
  sample, sampling ceiling, order ceiling, and fixed 10 nm period grid.
- Preserve the current G0-only hard limit:
  `min(sampling ceiling, order ceiling)`, followed by the greatest 10 nm
  multiple strictly below that exact ceiling.
- Let `PeriodChoice` cite exactly one basis: explicit brief constraint or
  received period advice. Accept it unchanged or refuse it; never floor,
  clamp, or repair it.
- Derive `HeightDomain` only from an admitted `PeriodChoice`. Do not make the
  height value carry a second independent period authority.
- Keep finite height priors, aspect constraints, shape dimensions, dimension
  step, and exact candidate counts in `HeightDomain`.
- Estimate the phase envelope only for a propagation-phase height question.
- Let `HeightChoice` cite exactly one basis and accept one allowed height
  unchanged.
- Prevent every cell sweep until both choices exist as admitted evidence.

## TDD seam

Build the chain from pure scientific values:

```text
material binding
→ period domain
→ period advice
→ period choice
→ height domain
→ phase envelope where applicable
→ height advice
→ height choice
```

Cover an exact-grid ceiling, a non-grid ceiling, explicit period, advised
period, invalid period, explicit height, advised height, and advice outside
its exact domain.

## Acceptance

- `PeriodDomain → PeriodChoice` and `HeightDomain → HeightChoice` use paired
  names and paired validation structure.
- An exact 850 nm physical ceiling yields a maximum period of 840 nm.
- The fixed period grid is independent of the brief's lateral
  `dimension_step_nm`; that step enters only the height domain's candidate
  arithmetic.
- Advice cannot change dimension step, shape, materials, strategy, or brief.
- A geometric-phase height question does not fabricate a phase envelope.
- Invalid or unavailable choices leave an honest compilation outcome and
  open no solver work.
- Existing scientific ceiling, aspect, height, envelope, and candidate
  arithmetic remains unchanged unless the specification explicitly corrects
  ownership.
- Focused material, period, height, envelope, and compiler tests pass.
- Pyright reports zero errors; touched files have zero CSU hard violations.
- `git diff -- rust` is empty.

## Do not add

Do not add a period planner, mutable selection state, recommendation fallback,
height sweep, solver preflight, or generalized choice framework.
