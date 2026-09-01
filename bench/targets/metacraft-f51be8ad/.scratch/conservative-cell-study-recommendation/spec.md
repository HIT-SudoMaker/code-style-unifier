# Conservative cell-study seam

Label: `wayfinder:spec`

Status: resolved (2026-08-10)

## Context

The current metalens cadence chooses a period, asks a second scalar height
question, and lets downstream request builders reconstruct a complete
fabrication grid. PB selection always returns the least-bad Jones cell and
propagation phase matching assumes zero global offset. These are three
independent evidence leaks, not reasons to add another provider or planner
framework.

## Contract

Keep period legality first. After an admitted `PeriodChoice`, one pure deep
`cell_study` Module forms a typed decision card and accepts one exact answer.
The card contains immutable options with exact height, geometry identities,
response channels, work count, forecast, cautions, criteria, and provenance.
The harness selects an offered option identity or returns `evidence_required`.
It cannot alter user facts, constraints, criteria, or extent.

`CellStudyPlan.work` is the only source for periodic execution. Propagation
uses one work item per geometry. PB uses one unrotated geometry with exactly
`x` and `y` Jones work; orientation is derived analytically after one cell is
qualified. No downstream module may rebuild a grid or Cartesian product.

Propagation assesses 8, 12, and 16 independently, searches a deterministic
global phase offset, applies cyclic half-step tolerance, distinct-cell and
useful-power checks, and reports typed refusal/findings. PB requires a
versioned/user-owned qualification profile, filters before ranking, and
returns `NoQualifiedPbCell` when none qualifies.

Authority remains truth; a run manifest is a deterministic projection with
references. Old roots are migrated or rejected explicitly. No live solver,
aperture, field, or large benchmark run belongs to this cutover.

## Dependency frontier

`01 → 02 → 03 → 04 → [05, 06] → 07 → 08`

Completion means the new seam is covered by unit, architecture, and four-case
acceptance tests; existing unrelated worktree changes are preserved.
