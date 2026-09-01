# ADR 0024: Let one cell study own bounded response work

Status: accepted

Date: 2026-08-10

## Context

Metalens planning previously separated period and height advice, then allowed
periodic request builders to reconstruct a complete fabrication grid. PB cell
selection could rank a response without an explicit qualification profile, and
propagation phase matching assumed a zero global offset. These behaviours
blurred planning, execution, and evidence ownership.

## Decision

After an admitted `PeriodChoice`, a pure deep `cell_study` Module owns one
immutable bounded `CellStudyPlan`. Its decision card contains exact height,
geometry, response channels, work count, cautions, and provenance. A harness
may choose an offered option identity or return `evidence_required`; it cannot
edit user facts, constraints, criteria, or extent.

`periodic_request` projects plan-owned work verbatim. Propagation performs
independent 8/12/16 assessments with deterministic global phase-offset search,
cyclic half-step tolerance, distinct cells, and useful-power gates. PB
requires a versioned/user-owned qualification profile, filters before ranking,
and refuses all-poor response sets. PB orientation is analytical after one
qualified cell and never creates solver work.

Authority owns truth. A run manifest is only a deterministic projection with
exact references and cannot restore state. Old period/height roots are
explicitly migrated or rejected; they are never silently reinterpreted.

## Consequences

The planning Interface becomes deeper while downstream Modules become smaller:
no grid reconstruction, no fabricated PB threshold, and no phase-set claim
from an unshifted or non-distinct response library. Numeric qualification
defaults are intentionally absent; a missing profile is an evidence boundary,
not an invitation for a harness to invent policy. Large solver scans, aperture
field propagation, and paper-value benchmark equality remain outside this
decision.
