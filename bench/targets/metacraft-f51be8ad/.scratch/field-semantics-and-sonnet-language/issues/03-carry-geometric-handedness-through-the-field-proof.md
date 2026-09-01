# 03 — Carry geometric handedness through the field proof

**Type:** implementation (spec geometric vertical)

**Status:** wontfix

**Superseded by:** `../../metalens-sonnet-convergence/spec.md`

**Depends on:** ticket 02

## What to build

Migrate the geometric-phase proof to the same
`aperture -> field -> focal region -> focus` contract. Form a circular-basis
field whose physical components are right- and left-handed amplitudes. Use the
admitted incident-polarization convention to interpret one component as
converted and the other as retained; do not encode those route roles as basis
names.

Propagate both components over the same axial samples. Evaluate useful focus
and leakage from admitted focal-region evidence. Delete
`propagate_channel_fields`, duplicate aperture-field reconstruction, and
conclusion-time propagation.

Rename public Jones entries with explicit direction:
`output_x_from_input_x`, `output_y_from_input_x`,
`output_x_from_input_y`, and `output_y_from_input_y`.

## TDD seam

Through `conduct`, run the standard right-handed geometric brief and a
left-handed mirror fixture. Fetch the admitted field and require that physical
handedness components exchange route roles while the component basis and
stored arrays remain honest. Require converted focus and retained leakage to
come from the same admitted focal-region survey and survive replay.

## Acceptance

- PB orientation remains analytic; no orientation-specific solver task exists.
- Both handedness components are explicit and independently propagated.
- Converted and retained are interpretation roles, never Field basis values.
- Jones schema, decoder, phase convention, library, aperture, field, focus,
  and result migrate atomically.
- No old abbreviated Jones entry or channel-field operation remains.
- Geometric standard-brief and replay tests pass.
- Rust diff is empty and touched files pass CSU.
