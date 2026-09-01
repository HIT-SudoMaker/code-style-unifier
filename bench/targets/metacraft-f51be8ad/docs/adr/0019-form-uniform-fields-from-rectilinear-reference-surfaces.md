# 0019 — Form uniform fields from rectilinear reference surfaces

Status: accepted

## Research basis

This decision applies the installed-product and primary-documentation findings
in [Lumerical rectilinear reference-surface sampling](../research/2026-08-05-lumerical-rectilinear-reference-surface-sampling.md).

It does not supersede [ADR 0017](0017-let-one-periodic-layout-place-every-reference-plane.md).
ADR 0017 remains the sole owner of the substrate interface, periodic vertical
layout, parent-group setup contract, world-coordinate interpretation, and
declared reflection and transmission planes.

## Context

ADR 0015 established `periodic_reference_surface_response` as an independent
capability. The first implementation decoded the embedded Native surface
directly into `PlaneSurface`, required one uniform transverse spacing, removed
the terminal periodic samples, and then constructed `Field`.

That path succeeded for a 43 by 43 uniform qualification fixture. A later
candidate returned a finite, closed 36 by 33 rectilinear grid whose axes were
strictly increasing but non-uniform. The solver had completed successfully;
the observation failed only because MetaCraft treated an FFT applicability
condition as a Native dataset invariant.

The same implementation then copied an already embedded surface through
`ReferenceSurfaceWork`, `PeriodicReferenceSurfaceRequest`,
`ObservedPeriodicReferenceSurface`, and a second `PeriodicResponse.observe`
call. That call scheduled no new solve and added no physical observation. It
was a shallow request path around an existing admitted same-solve fact.

## Decision

### Retain the raw observation

A periodic reference-surface observation retains the product's actual
horizontal and vertical coordinate vectors and finite complex components.
The vectors must be one-dimensional, finite, strictly increasing, and
consistent with component shape and the independently declared physical
context. They need not be uniform, square, equally spaced, or equal in sample
count.

The solver Adapter validates Native structure and context. It does not apply a
uniform-spacing gate, invent coordinates from shape, interpolate, select a
propagation method, or silently fall back.

`periodic_reference_surface_response` remains an independent product
capability. It proves that the exact transmission surface can be embedded in
the transmission or polarization observation produced by the same Native
solve. It does not prove uniform formation or propagation.

### Delete the shallow request path

`PeriodicReferenceSurfaceRequest`, `ReferenceSurfaceWork`,
`ObservedPeriodicReferenceSurface`, `AdmittedPeriodicReferenceSurface`, their
private codecs, and the second no-solve observation round trip are removed.
Science consumes the embedded raw surfaces from the already observed
transmission or polarization batch.

This deletion does not merge the three qualification capabilities. It removes
only an Interface that repeated an existing observation without owning work or
policy.

### Form one compatible batch

One field-owned numerical Module forms a complete compatible batch of raw
rectilinear surfaces into the existing uniform `Field` language. Its small
Interface accepts one sealed batch and one exact qualified formation; it
returns the corresponding ordered uniform fields or raises one direct fault.
It does not return a partial batch.

This all-or-nothing contract applies to preflight and the resulting `Field`
values. Science completes the whole formation before invoking any Authority
admission callback. The following ordered admissions use Authority's
content-addressed, append-only, idempotent object contract; they are not a
transactional batch. If one admission faults, the caller receives no apparent
surface batch, while any exact facts already admitted remain safe to reuse on
retry.

The Module owns target-grid derivation, periodic seam treatment, complex-field
interpolation, common-grid validation, order preservation, immutable output,
and numerical provenance. The resulting `Field` cites the exact admitted raw
observation from which it was formed.

The formation is a Python numerical realization with its own qualification.
Lumerical's reference-surface capability cannot grant that qualification.
Callers do not choose an algorithm, density, tolerance, FFT, or future NUFFT
through an enum, registry, or fallback flag. Compilation and binding select an
exact qualified realization.

The existing `PlaneSurface`, `Field`, field-evidence meaning, propagation
Interface, and six-name `metacraft.field` package export remain unchanged.
Specialized rectilinear and formation values stay with their exact owner
Modules and are not re-exported from the field package root.

### Retain only existing solve completion

The Lumerical Adapter persists the existing `ProjectExecution` immediately
after solve completion and before observation. If observation then faults, the
current call's unchanged exception proves that failure; no
`ObservationFailureRecord`, failure sidecar, or exception classification is
added. An execution-only artifact creates no `WorkRecord`, Authority receipt,
scientific evidence, claim closure, recovery state, or second lifecycle.

## Frozen numerical implementation gate

The accepted formation realization is
`periodic_rectilinear_bilinear_v1`. One complete compatible batch uses one 24
by 24 half-open uniform target grid and separable periodic bilinear
interpolation. The realization accepts at most 256 surfaces per batch. It
performs no extrapolation and no amplitude or power normalization.

Qualification requires all of these limits:

- raw round-trip relative L2 error at most `0.0081`;
- normalized maximum error at most `0.0093`;
- relative power-proxy change from the 20 by 20 convergence grid to the 24 by
  24 target grid at most `0.0006`.

The linked Research Record reports passing from-x results of `0.00798322`,
`0.00926499`, and `0.000571006`, and passing from-y results of `0.00789876`,
`0.00811822`, and `0.000236897`, in the order of the three diagnostics above.
Those values came from read-only opening of retained `after.fsp` files in the
existing failed gate root. The qualification spent zero Native solves and did
not reuse, resume, or mutate that root.

The earlier 64 by 64 candidate was rejected because high-NA delivery crossed
the already qualified 1 GiB vector-field guard. At 400 nm period the accepted
24 by 24 target step is 16.67 nm, comparable to the retained Native grid's
largest 15 nm step. All five delivery tests across the four cases passed with
this resource-closed target.

This froze the implementation contract, and Ticket 08.6's 2026-08-05
resolution records its completed deterministic implementation. A different
density, interpolation rule, threshold, or batch limit requires a new decision
and qualification rather than a caller option or fallback.

## Consequences

- Native observation remains source-faithful even when current propagation
  cannot consume it directly.
- Uniformity becomes a property established by formation, not a fiction
  asserted by the Adapter.
- One batch owns one target grid, so x/y bases and different candidates cannot
  drift through caller-local interpolation choices.
- Existing FFT propagation remains narrow and unchanged.
- Future anisotropic-spacing or NUFFT methods can consume the retained raw
  observation through a separately qualified realization; no such framework
  is introduced now.
- The new coordinate objects increase retained evidence size and add one
  explicit observation-to-field movement. That cost buys replayable science
  and prevents a product sampling detail from being erased.
