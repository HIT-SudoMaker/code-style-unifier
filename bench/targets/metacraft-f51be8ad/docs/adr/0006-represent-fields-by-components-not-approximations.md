# 0006 — Represent fields by components, not approximations

Status: accepted

## Context

The first low-na implementation exposed a scalar angular-spectrum operator and
then allowed the word `scalar` to become the identity of field tasks and
evidence. The stored value was only an anonymous complex array: it carried no
component basis, medium, coordinate frame, or polarization meaning.

That vocabulary cannot extend honestly. A large-na exit field requires
explicit electric components, a Debye--Wolf reference begins on a pupil or
reference sphere, and a geometric-phase aperture contains both handedness
components. Parallel `Scalar*` and `Vector*` object families would duplicate
the same field, survey, focus, and evidence responsibilities.

The source audit and compared designs are retained in
[Field semantics and Sonnet language audit](../research/2026-07-27-field-semantics-and-sonnet-language-audit.md).

## Decision

MetaCraft has one component-based `Field` language. One field records:

- one wavelength;
- one sampled surface and coordinate frame;
- one locally uniform medium;
- one explicit component basis;
- electric component arrays;
- optional magnetic component arrays;
- exact source references.

The basis and component arrays state the field's vector meaning. No
`is_vector` Boolean exists. The brief calls its condition
`incident_polarization`; a propagated field has no duplicated global
polarization label. Local polarization is derived from the complex
components.

The scientific proof uses:

`aperture -> field -> focal region -> focus -> result`

Its operations are:

`form -> propagate -> evaluate -> conclude`

Each operation establishes exactly one fact. `evaluate` never propagates, and
`conclude` never reconstructs prior facts. The compiled task and its binding
choose the exact realization; callers never pass an algorithm selector or
receive a hidden fallback.

Scalar, vector, angular-spectrum, and Debye--Wolf terms remain explicit where
they are true: method applicability, realization identity, qualification, and
numerical provenance. They do not prefix general field, survey, focus, or
result values.

Dense component arrays are immutable binary authority objects. Canonical JSON
documents remain small manifests containing shape, dtype, units, basis,
physical semantics, source references, and exact component-object references.
The existing Authority accepts opaque bytes and media types, so this changes
no Rust source or protocol.

This decision amends the golden-proof wording in ADR 0004. Its former
`scalar field` and `converted and retained fields` steps become a component
`field` fact followed by a separately admitted `focal region` fact. The two
control strategies retain distinct response and evaluation evidence.

## Consequences

The current propagation-phase field contains explicit transverse electric
components. The current geometric-phase field uses a circular basis; its
metalens evaluation assigns handedness components to converted and retained
roles from the exact incident-polarization convention.

The vector angular-spectrum realization consumes a compatible plane-field
basis. A Richards--Wolf realization consumes an authored aplanatic pupil or
reference-sphere basis and uses FFT for a full conjugate focal grid or CZT for
an explicitly requested Cartesian region. They may produce comparable focal
distributions, but they are separate physical methods with separate inputs
and qualifications. A plane field is never relabelled as an aplanatic pupil.
The former pointwise Direct Debye realization is retired from production and
tests; analytic on-axis fields and vector invariants independently qualify
both Fourier realizations without creating a third runtime path.

One field remains single-wavelength. A future achromatic proof composes
multiple exact fields and may permit wavelength-specific grids, media, and
qualifications.

The public scientific language uses full natural names and paired word order.
Mathematical shorthand may remain in equations and native product strings,
but not as opaque production identifiers. Architecture tests enforce the
retired language and the unchanged Rust boundary.
