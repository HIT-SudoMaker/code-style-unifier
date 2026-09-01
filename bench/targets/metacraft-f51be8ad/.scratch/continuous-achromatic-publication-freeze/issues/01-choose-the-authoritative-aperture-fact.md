# Choose the authoritative aperture fact

Status: resolved (2026-08-15)

Assignee: unassigned

Label: `wayfinder:grilling`

Blocked by: none

Parent: [Freeze the evidence-compiled continuous-achromatic metalens](../map.md)

## Question

When focal length, numerical aperture, physical diameter, site count, and a
later-selected period do not all agree, which values remain exact user facts,
which values are derived, and which typed mismatch must stop compilation rather
than letting the continuous Method silently rebuild its own grid?

## Decision

Focal length, NA, and a supplied `ApertureIntent` are exact user facts. The
period is a later admitted design fact. None silently overrides another.

After period selection, the existing aperture Module resolves the one physical
Lattice. Circular half-span is derived from focal length and NA; period fixes
the coordinates; a declared radius/diameter site count is validated against the
derived central-line count. A mismatch stops compilation as
`aperture_intent_mismatch:<declared>:<compiled>`. If aperture was honestly
omitted, footprint and span count are derived and recorded.

The continuous Method must consume that Lattice and may not rebuild a private
grid. The current 51-site continuous fixture is inconsistent with the admitted
320 nm period and must become an explicit mismatch test or be deliberately
corrected to the compiled 63-site diameter.

## Consequence

Deepen the current in-process aperture Module. Do not add a continuous-only
layout Module. The deletion test is positive: deleting this seam would scatter
footprint, count, coordinate, and mismatch logic back into every placement
caller.
