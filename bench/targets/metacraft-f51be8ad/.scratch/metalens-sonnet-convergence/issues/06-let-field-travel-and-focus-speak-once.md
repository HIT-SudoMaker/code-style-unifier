# 06 — Let field travel and focus speak once

Type: implementation

Status: resolved (2026-07-28)

Blocked by: ticket 05A.

## Outcome

Field describes electromagnetic components. One bound realization propagates
them. Metalens evaluation speaks once, and conclusion only closes admitted
facts.

## What to build

- Keep the reusable `Field` value and its component manifest under `field/`.
- Move `FocalRegion`, `FocusSurvey`, `Focus`, `Leakage`, and their evidence
  under metalens focus science.
- Remove metalens focus values from `field.__all__`.
- Deepen the angular-spectrum implementation behind one small Interface that
  owns qualification, spectrum preparation, memory budgeting, component
  propagation, axial survey, and local refinement.
- Prevent callers and tests from importing private preparation, batching, or
  refinement functions.
- Preserve the bound Torch realization: CUDA when admitted, Torch CPU only
  when CUDA is absent, float64/complex128 tensors, two-times padding, and the
  recorded transform and evanescent conventions.
- Propagate each nonzero component from one prepared spectrum and preserve an
  explicit zero component without an unnecessary transform.
- Keep the focal observation interval at `0.8f` through `1.2f` and retain only
  the axial survey, best-focus plane, required power facts, binding, and
  provenance.
- Let bound propagation own one declared component group, its axial search,
  and the matching transverse plane.
- Make `evaluate_focus` the sole owner of x/y half-maximum widths, depth,
  transmission, concentration, completeness, and applicable retained-channel
  leakage.
- Return complete `Focus` evidence only when all closing facts are bracketed.
  Otherwise admit `FocusSurvey` as a diagnostic and emit one typed Finding.
- Remove every calculation from `conclude`, including geometric retained
  power and leakage.

## TDD seam

Use small, reviewed component Fields and recorded focal observations:

1. qualify and propagate one linear-basis Field;
2. propagate two circular-basis components with one prepared spectrum each;
3. evaluate one complete Focus;
4. evaluate one unbracketed FocusSurvey and Finding;
5. evaluate applicable Leakage from the same admitted focal observation;
6. prove conclusion can run with Torch and propagation disabled.

No canonical full brief or live solver run belongs in this ticket.

## Acceptance

- `field` exposes reusable Field language, not a universal focus workflow.
- Metalens owns FocalRegion, FocusSurvey, Focus, and Leakage.
- One deep angular-spectrum Module owns its complete numerical implementation.
- No production numerical FFT path uses NumPy or four-times padding.
- Binding and execution use the same admitted device and numerical facts.
- Bound propagation searches once and retains the matching plane;
  `evaluate_focus` never propagates and `conclude` never evaluates.
- Incomplete focus remains an exact diagnostic and never closes the Focus
  claim.
- Focused Field, focus, binding, evidence, and architecture tests pass.
- Pyright reports zero errors; touched files have zero CSU hard violations.
- `git diff -- rust` is empty.

## Verification

- Focused Ticket 06 tests: 51 passed.
- Full non-live suite: 340 passed, 15 deselected, 0 skipped.
- Pyright: 0 errors, 0 warnings.
- CSU: 16 touched production files, 0 hard violations.
- Standards review: passed.
- Specification review: passed.
- Rust tree: unchanged.

## Do not add

Do not add scalar/vector type trees, a device selector, CPU/CUDA
implementations, an algorithm registry, full three-dimensional field storage,
vector angular spectrum, or Debye–Wolf.
