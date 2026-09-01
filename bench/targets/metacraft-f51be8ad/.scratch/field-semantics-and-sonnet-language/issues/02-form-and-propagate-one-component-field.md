# 02 — Form and propagate one component field

**Type:** implementation (spec field foundation)

**Status:** wontfix

**Superseded by:** `../../metalens-sonnet-convergence/spec.md`

**Depends on:** ticket 01

## What to build

Introduce the component-based `Field`, plane surface, coordinate frame,
propagation medium, closed component basis, focal-region request, field
survey, focus, power measures, and convergence values behind one small Field
Interface.

Migrate the propagation-phase proof to:

`aperture -> field -> focal region -> focus`

`form_aperture_field` forms a transverse-linear component field.
`propagate_field` consumes the admitted field and produces a focal-region
survey through the task's qualified low-na realization.
`evaluate_focus` consumes only that survey.

Store each component in C order as deterministic raw little-endian `<c16`
bytes with media type `application/vnd.metacraft.ndarray`; expose arrays as
read-only complex128 values and admit a small exact-reference manifest. Add
strict decoders. Remove
`RESULT_CONVENTION`, `field_document` array-to-JSON expansion,
`propagate_scalar_field`, `FieldPlane`, `FocalEvaluation`, and the unused
`field/metrics.py` completion path.

## TDD seam

Start with one standard propagation-phase brief through `conduct`. Fetch and
decode its admitted field, focal-region, focus, and result evidence. Require
the expected linear basis, both electric components, exact binary references,
the `0.8f` to `1.2f` survey, bracketed measures, deterministic replay, and no
recomputation during conclusion.

Add Field-Interface examples for a uniform plane wave and one worked Gaussian
fixture. Expected values come from the existing analytic and refinement
fixtures.

## Acceptance

- Field construction rejects non-finite, mutable, wrong-shaped, incompatible,
  or missing components.
- The current realization accepts only its qualified plane/transverse basis.
- Component objects are fetched by reference; only exact raw `<c16` C-order
  bytes with the declared ndarray media type are decoded. No NPY or pickle
  decoder exists.
- `evaluate_focus` cannot import or call propagation code.
- `conclude` consumes admitted decoders only.
- Production numerical identifiers use full natural names, including
  `wave_number_x`, `wave_number_y`, and `wave_number_z`.
- Propagation standard-brief and replay tests pass.
- Rust diff is empty and touched files pass CSU.

## Do not add

Do not implement vector angular spectrum, Debye--Wolf, spectral batching,
Torch, an algorithm selector, or a numerical plugin seam.
