# 05 — Let aperture arrange one metalens field

Type: implementation

Status: resolved (2026-07-28)

Blocked by: tickets 02 and 03.

## Outcome

One metalens Aperture Module owns the circular placement problem. Control
strategies provide scientific assignments without duplicating the lattice.

## What to build

- Move `Cell`, `Aperture`, aperture evidence, and metalens phase placement
  under `science/metalens/`.
- Keep the shared circular phase mathematics local and explicit; retain
  cyclic distance at the `0 == 2π` seam.
- Make Aperture own the lattice coordinates, occupied circular mask, target
  phase, stable state identities, and vectorized identity placement.
- Let propagation phase supply one admitted finite `PhaseSet`.
- Let geometric phase supply one admitted anisotropic Cell and continuous
  `Orientations`.
- Merge duplicate propagation/geometric grid and hyperbolic target-phase
  construction behind the Aperture Interface.
- Preserve the distinct response, selection, and fabrication meanings in
  paired `propagation_phase` and `geometric_phase` Modules.
- Keep quantized 8/12/16 matching finite and hash/vector lookup based.
- Keep geometric orientation analytic; do not solve each orientation or
  manufacture phase levels.
- Remove route-string parameters from aperture values and documents.

## TDD seam

Through the Aperture Interface:

1. assign one 8-state propagation aperture across the `0/2π` seam;
2. repeat for 12 and 16 states using the same admitted library;
3. assign one continuous geometric aperture from one admitted cell;
4. prove both strategies produce the same coordinates, occupied mask, and
   target phase for the same metalens design;
5. prove stable identity lookup performs no per-site cell-library search.

## Acceptance

- `Aperture` is exported by metalens science, not shared `science` or `field`.
- Aperture has one owner for grid, target phase, mask, and placement.
- Propagation and geometric Modules contain only their real scientific
  differences.
- Propagation matching remains deterministic and cyclic.
- Geometric phase remains one selected cell plus continuous orientations.
- The representation does not require phase levels for every future
  pointwise assignment, but no large-na assignment is implemented.
- Focused aperture, phase-set, orientation, and architecture tests pass.
- Pyright reports zero errors; touched files have zero CSU hard violations.
- `git diff -- rust` is empty.

## Do not add

Do not add an Aperture registry, generic strategy base class, optimizer,
large-na matcher, orientation sweep, or compatibility aperture decoder.
