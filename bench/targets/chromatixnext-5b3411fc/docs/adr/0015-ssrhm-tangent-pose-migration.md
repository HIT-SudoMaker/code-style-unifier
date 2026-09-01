# SSRHM tangent Pose migration

**Status:** Accepted — implemented present truth

## Decision

Authored Surface and Collimated Ray pose use one physical Cartesian vocabulary
and one reading order: `origin|vertex -> tangent_x -> tangent_y -> shape or
power`. `normal` or launch direction is derived only as
`tangent_x × tangent_y`. Public constructors, attributes, persistent state
keys, and Pose-specific stable error identities migrate atomically from the
historical `axis_*`/`launch_plane_*` language. No old keyword, attribute, state
key, alias, deprecated overload, `__getattr__`, automatic exchange, legacy
loader, or dual schema is accepted.

Legacy checkpoints fail with atomic `state_installation_keys_mismatch` before
native tensor copy. State Installation owns checkpoint schema admission (key,
tensor kind, dtype, and shape); after projection, CollimatedRaySource owns
semantic Pose validation at construction, every public consumption, and its
single state-installation planner. Invalid semantic Pose never reaches a
downstream RayBundle identity, and the planner is not duplicated by the root
installer.

The existing private authored-basis seam remains the sole mechanical owner of
finite fixed-double unit/orthogonality/non-degeneracy facts and the derived
normal. No public Pose/Frame abstraction or universal vector framework is
introduced. The former `not_right_handed` triple-product check is removed:
with two ordered unit orthogonal tangents it is merely the squared norm of
their cross product and adds no independent handedness claim.

The sole authorized physical output change is Collimated launch placement:
`coordinate_x * launch_tangent_x + coordinate_y * launch_tangent_y` replaces
the historical crossed Grid-storage mapping. Surface geometry, Jones
embedding, direction, Plane-local polarization laws, equations, operation
order, tolerances, dtype, state lifecycle, Assembly, Workstation, and all
non-Pose error identities remain relation-preserving.

## Evidence boundary

The migration requires public signature and absence checks, atomic legacy-key
rejection, Source-owned mutation and install rejection, a non-square,
anisotropic, non-centred coordinate oracle, Surface/Jones/Assembly/
Workstation/Meta/CPU/CUDA no-drift evidence, and a manifest classifying every
changed byte as Pose language, Source-owner validation, or the single
coordinate correction.

## Supersession

This ADR partially supersedes the historical Pose names and unchanged-public-
state statements in ADR-0009, ADR-0010, and ADR-0013 once implementation is
complete. Their historical bodies remain intact and must carry visible forward
links; this decision does not supersede their numerical laws, fixed-double
rules, or public-Pose exclusion.

The 2026-08-14 final closure also reconciles this decision with the earlier
CSU Interface-truth cleanup specification. That specification's frozen-public-
name, state-key, and Pose-error clauses are superseded only for the exact
`axis_*`/`launch_plane_*` to `tangent_*`/`launch_*` cutover enumerated here.
Every non-Pose public name, state key, failure identity, equation, tolerance,
dtype, gradient, device meaning, and production seam remains frozen.

## STOP

Stop the migration if a compatibility layer, public Pose/Frame, state schema
fallback, downstream RayBundle failure, extra numerical drift, or any change
outside the declared Pose classes is required.
