# 06 — Let rectangle and ellipse share one geometric proof

**Type:** implementation

**Status:** wontfix

**Superseded by:** `../../metalens-sonnet-convergence/spec.md`

**Blocked by:** ticket 05, to serialize shared Cell, template, and sweep edits.

## Outcome

Khorasaninejad-inspired rectangular and Yang-inspired elliptical briefs use
one geometric proof: a paired-basis sweep selects one anisotropic Cell and
continuous analytic rotation forms the aperture.

## What to build

- Publish `khorasaninejad_rectangle_brief` and `yang_ellipse_brief` with the
  exact canonical facts and 20 nm / 100 nm dimension steps.
- Make the existing `Cell` with `Circle | Square | Rectangle | Ellipse` the
  sole fabrication identity; remove the parallel `RectangularFin` model.
- Preserve typed geometry from transient Adapter candidates through native
  construction and admitted evidence.
- Sweep x and y bases independently for every legal anisotropic candidate.
- Select deterministically by converted power minus retained power, then
  converted power, axis product, long/major axis, and short/minor axis.
- Use `converted` and `retained` consistently; derive leakage only as a Result
  measure.
- Compile `orientations`, create continuous analytic rotations, and return one
  Result per brief without orientation solves.
- Remove geometric 8/12/16 phase sets, phase levels, and rotation
  index/count bookkeeping.

## TDD seam

Begin with the public geometric route using paired fake basis evidence. Add
one rectangle and one ellipse construction case, then selection, continuous
rotation, missing-basis recovery, and replay.

## Acceptance

- Rectangle and ellipse have equal route status and share one Cell language.
- Every chosen cell cites admitted x/y evidence.
- Exactly one Result is formed per geometric brief.
- PB aperture construction performs no orientation solve and no fabricated
  phase quantization.
- No coarse-to-fine optimizer, response threshold, parallel geometry model,
  or shape alias is introduced.
- Focused tests, architecture tests, Pyright, and CSU pass.
- Rust has no diff.
