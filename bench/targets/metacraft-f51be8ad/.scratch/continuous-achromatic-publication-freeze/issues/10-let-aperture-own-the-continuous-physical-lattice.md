# 10 - Let aperture own the continuous physical Lattice

Status: ready-for-agent

Assignee: unassigned

Label: `ready-for-agent`

Blocked by: none

Parent: [Publication freeze](../spec.md)

## Work

Deepen the existing in-process aperture Module so one Interface resolves the
physical Lattice for monochromatic and continuous designs after an exact period
is admitted. It owns footprint, physical span, coordinates, occupied mask,
central-line span count, occupied-area count, reference target phase, and
`ApertureIntent` validation.

Change continuous assignment to consume the resolved Lattice and its exact
reference. Delete its private `F/NA` grid construction. Record footprint and
Lattice provenance in `AchromaticAperture` and preserve immutable arrays across
all wavelengths.

Turn the current 51-versus-63 mismatch into an explicit rejection test, then
make the positive continuous fixture state a coherent 63-site diameter for the
admitted 320 nm period.

## Acceptance

- Matching circular radius/diameter and square intents close through the shared
  Lattice Interface; mismatches return the typed declared/compiled counts.
- Honest aperture omission derives and records one circular lattice.
- The current positive target has 63 central diameter sites, 65 by 65 storage,
  and 3069 occupied sites.
- Monochromatic and continuous placement consume the same Lattice behavior;
  continuous code contains no private centered-grid implementation.
- Every wavelength's field cites the same Lattice/aperture and reuses byte-equal
  coordinate, occupancy, geometry, and orientation maps.
- Existing propagation/PB Result bytes and architecture tests remain unchanged
  unless an intentional canonical migration is recorded.

## Non-goals

No new layout lifecycle, no wavelength-dependent placement, and no silent
normalization of contradictory user facts.
