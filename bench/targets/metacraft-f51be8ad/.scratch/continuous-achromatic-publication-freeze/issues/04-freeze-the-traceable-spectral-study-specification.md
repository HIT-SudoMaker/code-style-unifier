# 04 - Freeze one traceable spectral study specification

Status: ready-for-agent

Assignee: unassigned

Label: `ready-for-agent`

Blocked by: [10 - Let aperture own the continuous physical Lattice](10-let-aperture-own-the-continuous-physical-lattice.md)

Parent: [Publication freeze](../spec.md)

## Work

Deepen the existing achromatic Module with one immutable, content-addressed
study specification that owns the literature seed, fabrication derivation,
wavelength split, geometry enumeration, work ceilings, qualification-profile
reference, and deterministic assignment policy.

Replace the unlabelled 400 nm, 600 nm, five-dimension, 10-rectangle, 5+4
wavelength, and threshold globals. For the first publication slice, record the
600 nm TiO2 height and order-safe 400 nm period ceiling with primary-source
provenance; enumerate every legal unequal rectangle on the Brief's fabrication
grid. The current seed must close to 136 geometries and at most 2448 x/y works.

`SpectralCellStudyPlan` must cite the exact specification and material binding.
The harness supplies no study-policy knobs. Keep the current reference-screen
then follow-up execution shape and both existing evidence Adapters.

## Acceptance

- Canonical round-trip and mutation tests cover every specification field.
- Plan identity changes when protocol, source, height, period policy,
  wavelength split, fabrication grid, geometry extent, profile, or work budget
  changes.
- The current seed derives 320 nm period, 600 nm height, 136 legal geometries,
  272 reference works, 2176 maximum follow-up works, and 2448 maximum works.
- Incomplete material evidence returns an evidence requirement before a plan.
- An empty fabrication domain or excessive declared work cannot reach an
  Adapter.
- Tests cross the specification/plan Interface and do not mirror private
  helper placement.

## Non-goals

No generic planner, height sweep, compound fin, alternate material template,
solver Adapter, or harness-visible policy object.
