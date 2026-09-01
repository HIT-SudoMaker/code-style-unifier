# Paraxial ray-transfer vocabulary cutover

**Status:** Accepted — implemented present truth

## Decision

The independent first-order qualification Module is named
`chromatix_next.optics.paraxial_ray_transfer`. Its public Interface uses the
complete physical phrase “ray transfer” rather than the historical `ABCD`
abbreviation:

- `compose_ray_transfer_matrices`
- `free_space_ray_transfer_matrix`
- `spherical_refraction_ray_transfer_matrix`
- `thin_lens_ray_transfer_matrix`

The historical module and names are retired atomically:
`chromatix_next.optics.abcd`, `compose_abcd`, `free_space_abcd`,
`spherical_refraction_abcd`, and `thin_lens_abcd` are not importable and have
no alias, forwarding module, deprecated overload, `__getattr__`, or dual public
surface. Stable failures use the `paraxial_ray_transfer_*` identity family.

This Module is an independent analytic reference for the small-height,
small-angle limit of exact Ray tracing. It consumes no Ray Bundle, Medium, or
Spectrum, shares no numerical kernel with exact Ray actions, and cannot become
an execution backend or an `exact|paraxial` selector. The `(y, theta)` vector,
matrix order, free-space, thin-lens, spherical-refraction, and composition
equations remain unchanged by the vocabulary cutover.

## Scope reconciliation

The maintainer's 2026-08-14 final-closure approval accepts this breaking
pre-release vocabulary cutover. It narrowly supersedes the CSU Interface-truth
cleanup specification's frozen-public-name and frozen-error-identity clauses
for the enumerated ray-transfer names and identity family only. It does not
authorize any other public, state, scientific, numerical, device, Assembly, or
Workstation change.

## Evidence boundary

The active public-surface contract admits only the complete names. Package
evidence proves the retired module is absent, while exact-Ray comparison tests
use this Module only as an independent paraxial reference. No compatibility
test or migration shim is permitted.
