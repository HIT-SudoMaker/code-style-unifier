# Define the orthogonal lattice promise

Status: resolved (2026-08-13)

Assignee: Codex

Label: `wayfinder:grilling`

Blocked by: none

Parent: [Find the continuous-achromatic metalens compilation road](../map.md)

## Question

Does the first continuous-achromatic method require a square lattice with
equal orthogonal periods, or a rectangular Bravais lattice whose two periods
may differ? Which lattice facts are user constraints, which may be resolved by
Design, and which must be fixed in a bounded cell-study plan?

## Resolution

The first continuous-achromatic method uses one square lattice: its two
in-plane translation vectors are orthogonal and share one equal period. A
rectangular lattice with unequal periods and a hexagonal lattice are outside
this Method.

The square lattice is not a required Brief field. It is already fixed by the
only current periodic template and therefore belongs to Method applicability,
the exact realization binding, and the admitted CellStudyPlan. An explicit
user period remains a legitimate constraint; otherwise period domain and
consultation select one value before the plan freezes it. Adding a lattice
kind to the Brief would expose an unsupported choice and duplicate template
truth.

The square cell contains an anisotropic rectangular meta atom whose physical
orientation supplies the PB base phase. The entire passive device retains one
period, one height, and one geometry-plus-orientation assignment across the
continuous band. Wavelength changes material response and the observed Jones
operator, not the fabricated layout.
