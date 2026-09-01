# 05 — Let native names be exact

Type: bug fix

Status: resolved (2026-07-29)

Blocked by: ticket 04.

## Outcome

The Lumerical session translates every current natural property through an
explicit, object-specific, bidirectional product dialect. Unknown properties
fail before the engine.

## Problem

The current `_native_property` table falls back to replacing underscores with
spaces. Recent live failures proved that unit-bearing public names do not
mechanically equal native names. `start_wavelength_nm` and
`stop_wavelength_nm` remain exposed to the same class of failure.

## Scope

1. Replace the fallback with an exhaustive mapping for each native object kind
   constructed by current periodic templates.
2. Keep unit conversion beside the property mapping.
3. Provide the inverse mapping used by inspection.
4. Cover simulation time, source offset, start/stop wavelength, positions,
   spans, boundaries, shape dimensions, material, source settings, grating
   settings, and every other currently emitted property.
5. Reject unknown object kinds, unknown properties, and unsupported inverse
   reads before calling the engine.

## Acceptance

- No `key.replace("_", " ")` product fallback remains.
- Template-emitted property names are exhaustively covered.
- `simulation_time_fs -> simulation time`,
  `source_offset_nm -> source offset`,
  `start_wavelength_nm -> start wavelength`, and
  `stop_wavelength_nm -> stop wavelength` use exact units and round trip.
- Shape-specific dimensions map correctly for circles, squares, rectangles,
  and ellipses.
- Fake-engine tests observe exact native calls and inverse reads.
- Public MetaCraft names contain no native spelling.
- No product-version branch, compatibility alias, or live solver run is added.
- Rust is unchanged.

## Do not add

Do not add fuzzy matching, reflection over native objects, a generic codec
registry, or a second dialect outside the Lumerical session.
