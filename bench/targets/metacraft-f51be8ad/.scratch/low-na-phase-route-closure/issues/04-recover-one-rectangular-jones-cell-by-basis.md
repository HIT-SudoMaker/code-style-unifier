# 04 — Recover one rectangular Jones cell by basis

**Type:** implementation

**Status:** wontfix

**Superseded by:** [Four-brief delivery ticket 06](../../four-brief-metalens-delivery/issues/06-let-rectangle-and-ellipse-share-one-geometric-proof.md).

**Blocked by:** tickets 01 and 02.

## Outcome

The geometric-phase route selects one admitted rectangular nanofin from its
two linear-basis responses, then forms the aperture analytically by rotation.
Interrupted evidence resumes only the missing basis.

The Khorasaninejad 2016 rectangular-nanofin example is the tracer bullet.

## What to build

- Add optional typed `fixed_geometry` to `AtomIntent`, and validate that it
  agrees with the declared atom shape. Preserve that same atom intent through
  the brief and compiled design; do not add a parallel top-level design field.
- Carry the fixed rectangle through the science-owned geometry and admitted
  Cell vocabulary, using `long_side_nm` and `short_side_nm`. Do not add a
  parallel generic dimension bag.
- Admit a cited geometry when it satisfies physical period, height,
  minimum-feature, gap, and aspect constraints, even when it is not aligned to
  a generated sweep step. For this check use the unrounded
  `height / aspect_limit` bound; grid rounding belongs only to generated
  candidates.
- Make a fixed geometry a singleton candidate plan. Preserve the existing
  coarse generated grid only for a general brief without fixed geometry.
- Give `x` and `y` basis observations distinct artifact, receipt, and work
  identities, each bound to the task, candidate, height choice, material
  binding, convention, and basis.
- Resume only an absent basis; reject stale, duplicated, or cross-candidate
  basis evidence.
- Aggregate the two admitted basis records into the Jones response that closes
  `jones_library`; do not turn either basis into a proof obligation.
- Derive converted and retained response from the admitted Jones pair, select
  one cell, and generate orientation states analytically without additional
  solver calls.
- Preserve the chosen dimensions, height, basis provenance, and rotations in
  fabrication output and Result replay.

## TDD seam

Start at the geometric evidence boundary with one complete Jones pair, one
missing-`y` pair, and one mixed pair. Then close the Khorasaninejad brief
through fake `conduct`.

## Acceptance

- A valid cited off-grid rectangle is admitted; an identical geometry that
  violates a physical bound is refused.
- The 600 nm height, 325 nm period, 250 nm long side, and 95 nm short side
  example passes the raw 75 nm feature-and-gap bound despite the 20 nm
  generated-grid step.
- The fixed rectangle has one owner inside the atom intent; brief and design
  expose no duplicate geometry field.
- Complete `x/y` evidence selects one cell and produces analytic rotations.
- Recovery dispatches only the missing basis.
- Mixed candidate, period, height, binding, or basis evidence cannot close.
- The selected Jones response and aperture reuse one stable admitted Cell
  identity.
- The Khorasaninejad example completes a fake conduct and replays with exact
  geometry and basis provenance.
- Focused tests, architecture tests, Pyright, and CSU on touched files pass.

## Do not add

- A geometric-phase multi-cell phase library.
- Separate `x response` and `y response` proof claims.
- Rotation-by-rotation Lumerical solves.
- An arbitrary Jones-matrix framework beyond the two admitted bases.
- Live Lumerical execution.
