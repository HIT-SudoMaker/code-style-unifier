# 05 — Give the elliptical pillar the same geometric route

**Type:** implementation

**Status:** wontfix

**Superseded by:** [Four-brief delivery ticket 06](../../four-brief-metalens-delivery/issues/06-let-rectangle-and-ellipse-share-one-geometric-proof.md).

**Blocked by:** ticket 04.

## Outcome

An elliptical pillar follows the same geometric-phase contract as a
rectangular nanofin: two admitted basis responses select one cell, and
rotation supplies phase across the aperture.

The Yang 2018 elliptical-pillar example is the tracer bullet.

## What to build

- Extend the geometric route's full-cell union with one typed elliptical
  pillar while reusing the science-owned ellipse cross-section and admitted
  Cell. Its paired dimensions are `major_axis_nm` and `minor_axis_nm`.
- Preserve the same admitted Cell identity through science-table rows,
  evidence, selection, aperture assignment, fabrication output, and Result
  provenance. Product candidates remain private Adapter projections.
- Make the Yang fixed geometry a singleton candidate plan with two basis
  observations.
- Implement only the ellipse-specific Lumerical construction needed behind
  the existing cell-construction seam, including exact dimension read-back.
- Reuse the Jones-pair admission, per-basis recovery, leakage/converted-power
  reporting, and analytic rotation behavior from ticket 04.
- Keep public geometric-phase interfaces shared between rectangle and ellipse.

## TDD seam

First drive an ellipse through the lowest existing geometry-preserving public
seam. Then run the Yang brief through fake `conduct` and authority replay.

## Acceptance

- The Yang example completes a fake conduct with one selected elliptical
  pillar and analytic rotation states.
- Its 340 nm explicit height is accepted independently of the infrared default
  height prior after physical validation.
- `major_axis_nm` and `minor_axis_nm` retain their meaning and order at every
  boundary.
- Lumerical construction and read-back agree on ellipse dimensions.
- Basis recovery and stale-evidence rejection behave identically for rectangle
  and ellipse.
- No rectangle condition appears in the ellipse path except shared physical
  bounds.
- Focused tests, architecture tests, Pyright, and CSU on touched files pass.

## Do not add

- An ellipse-specific workflow.
- A second public Cell or an untyped geometry dictionary.
- A dynamic shape registry or plugin protocol.
- Rotation sweeps.
- Live Lumerical execution.
