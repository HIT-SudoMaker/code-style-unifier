# SSRHM exact topology and Plane-local correction

**Pose-vocabulary partial supersession:** The historical `axis_*` Pose names
and unchanged-public-state claims in this decision are superseded by
[`0015-ssrhm-tangent-pose-migration.md`](0015-ssrhm-tangent-pose-migration.md).
Its exact-topology and Plane-local numerical corrections remain authoritative.

**Status:** Accepted — implemented present truth

**Partial supersession of:** only the exact-topology fallback and
Plane-local projection-degeneracy claims in
`0010-exact-polarized-ray-admissibility-and-closure.md`. ADR-0010 remains the
implemented authority for authored binary64 admissibility, exact-preservation
behaviour, and the polarized-Ray domain decision inherited from ADR-0009. Its
historical thirty-action inventory claim is superseded by the directional
cutover: current truth is twenty-four Optical Component actions plus three
state-only directional owners, three closed Terminal/diagonal enums, and two
Assembly-issued Encounter reference types. This ADR is the implemented
authority for the two corrected numerical surfaces and changes no public
capability.

## Context

Independent review reproduced two finite-binary64 counterexamples against
claims currently recorded as implemented truth.

First, the certified dot-product fallback can erase the only decisive term
when common scaling moves it below the binary64 subnormal range. Let
`c = binary64(sqrt(1/2))` and `tiny = 2^-600`, with

```text
ray_direction = (c, c, tiny)
plane_axis_y  = (c, c, 0)
plane_axis_x  = (-tiny*c, tiny*c, 1)
plane_normal  = cross(plane_axis_y, plane_axis_x)
```

For the exact rational values represented by those binary64 operands,
`ray_direction · plane_normal = 4503599627370497 / 2^1252 > 0`. The
pre-correction predicate returned zero. With the ray origin at zero and the
Plane origin equal to `ray_direction`, the exact forward parameter is one, but
the pre-correction Plane encounter reported no encounter and distance zero.
This is a topology defect,
not an admissibility tolerance question.

The same witness also exposes a distinct continuous-representation boundary.
Both ordinary binary64 dot reductions are zero, so the current continuous
quotient is `0/0` even though the exact rational quotient is one. Exact sign
resolution can recover the topology, but a sign-only Interface cannot and must
not invent a differentiable binary64 value for that quotient.

Second, with `ray_direction = (0, 2^-600, 1)` and
`plane_axis_y = (0, 0, 1)`, the represented Plane-local projection is
`(0, -2^-600, 0)`. It is nonzero, but the pre-correction ordinary Euclidean norm
squares the decisive component below the binary64 range and returns zero.
The pre-correction implementation therefore confused numerical underflow with
exact geometric degeneracy.

## Decision

The correction follows the project-local **SSRHM** rubric:

- **Sonnet:** fast classification resolves into one exact numerical owner;
  Plane-local actions validate, advance, derive one frame, reject at the
  owning action, apply their distinct law, verify, and construct.
- **Simple:** retain one narrow private exact-sign Interface and deepen the
  existing Plane-local numerical owner; do not create a public framework,
  general polynomial model, new frame package, or second test architecture.
- **Reliable:** decide finite-binary64 topology exactly, normalize continuous
  projections scale-first, and distinguish exact degeneracy, exact encounter
  topology, and continuous numerical non-representability.
- **Harnessed:** use one independent rational oracle, a bounded adversarial
  table, and real Plane and public Plane-local action regressions through
  existing test Seams.
- **Maintainable:** give each fact one owner, use intention-revealing names,
  delete superseded implementations, and preserve one-way dependencies.

The five affected predicate families are dot product, scalar triple product,
scaled squared-norm difference, quadratic discriminant, and scaled sum of root
factors. Their ordinary certified fast filters remain, but their certificates
cover both relative rounding and gradual underflow. For `n` rounded operations,
unit round-off `u`, smallest positive binary64 value `eta`, and a family-local
underflow amplification `A`, the filter forms `alpha = n * eta * A`, recovers a
conservative upper bound for its already-rounded magnitude envelope, and then
forms `B = gamma_n * recovered_envelope + alpha`. Every nonnegative arithmetic
step used to build this bound is rounded outward with `nextafter`; a sign is
accepted only when its absolute rounded value is strictly greater than `B`.
Invalid or nonfinite certificate inputs are ambiguous and therefore take the
exact path.

The frozen operation counts are `2*K - 1` for a `K`-term dot product,
`2*K + 4` for a `K`-component squared-norm difference, `18` for a scalar
triple product, and `8` for each quadratic discriminant and scaled root-factor
sum. Their underflow amplifications are respectively `1`, `1`, `9`, `4`, and
`max(1, abs(extra_factor))`. These numbers describe the existing operation
graphs; they are not a configurable policy surface.

Only ambiguous lanes use one private device-local exact-sign implementation
built from the original finite binary64 operands. CPU and CUDA use the same
PyTorch integer algorithm.
Meta enters the exact core once without reading values, allocates a conservative
structural workspace upper bound, and returns only shape and integer dtype so
Workstation preflight remains conservative. Existing float32 Meta callers are
accepted only by this unreadable structural branch; no value is decoded and no
float32 scientific execution is admitted. Readable CPU/CUDA execution retains
the strict binary64 assertion and the public fixed-double contract is unchanged.

Plane encounter topology consumes exact signs for both dot reductions:
`dot(ray_direction, plane_normal)` owns the parallel decision and
`dot(plane_origin - ray_origin, plane_normal)` joins it to own the forward
decision; the denominator sign also orients the returned normal. The
already-rounded scalar dot results never decide these topology facts.
The ordinary binary64 reductions remain the sole continuous distance path, so
ordinary lanes preserve their existing gradients. If exact topology is
nonparallel but the ordinary denominator is zero, the private encounter carries
zero distance, the incoming origin as its intersection placeholder, a harmless
inside-aperture placeholder, and
`is_continuous_distance_resolvable = False`. Shared
ray-surface advance rejects active consumption with the stable identity
`ray_surface_distance_unresolvable`; terminal and otherwise nonactive lanes do
not reject and preserve their prior state. The correction does not introduce an
exact quotient, exact value, custom-gradient, or second continuous path.

The Plane-local Jones frame remains private numerical support. It derives one
immutable fact containing named local axes, exact interaction-degeneracy state,
and projection-representability state. Exact collinearity is a topology fact;
continuous projection representability is a certified floating-point fact.
For normalized direction `d`, authored Plane axis `a`, products `a*d`, rounded
dot `s_hat`, axial projection `q_hat = s_hat*d`, and transverse projection
`p_hat = a-q_hat`, let `u = eps/2`, let `eta` be the smallest positive
subnormal, and let `gamma5 = 5u/(1-5u)`. The implementation evaluates

```text
dot_bound = gamma5 * sum(abs(products)) + 5*eta
raw = abs(d)*dot_bound + u*abs(q_hat) + u*(abs(a)+abs(q_hat)) + 3*eta
component_bound = (1+gamma5)*raw + 5*eta
```

At least one component must satisfy `abs(p_hat) > component_bound`. This is an
operation-derived forward-error certificate, not an empirical epsilon. A
certified projection is normalized scale-first, its residual longitudinal
component is removed, and both local axes are scale-first renormalized into a
finite right-handed frame. An interacting lane that is exactly non-collinear
but lacks this certificate or any finite nonzero construction stage fails with
an action-owned numerical-representation identity rather than being mislabeled
geometrically degenerate. A noninteracting lane never consumes that frame.

The following alternatives are prohibited:

- host `Fraction` or other CPU exactness fallback for production operands;
- operand transfer, per-lane host scalarization, or separate CPU/CUDA science;
- epsilon repair, clamping, or an arbitrary replacement reference axis;
- a public exact-arithmetic, polynomial, Plane-frame, or backend framework;
- an exact dot-ratio/value framework, detached exact distance, custom backward,
  or epsilon substitute for an unrepresentable continuous denominator;
- a test registry, universal executor, coverage quota, or parallel locality
  gate.

## Frozen boundaries

This correction adds no optical capability and changes no public optical
Interface. It preserves exactly two top-level public exports, twenty-four
public Optical Component actions, three directional owners, three closed
Terminal/diagonal enums, two Encounter references, existing state keys and
existing stable error identities, while adding the
shared stable representation failure `ray_surface_distance_unresolvable`.
It preserves Plane-only polarized-Ray
scope, the fixed-double regime, and the one-way cycle-free dependency
direction `workstation -> optics -> _numerics`. Wave/Ray conversion, coherent
Ray amplitude, curved polarized-Ray Elements, material-interface polarization,
and the other product exclusions remain out of scope.

The two-consumer Surface-label resolver present in the unsealed working tree
is removed because it fails the deletion test. The corrected Chinese docstring
in the public-contract evidence is retained because it changes no assertion or
public behaviour.

## Implementation status

Implemented present truth. One private device-local binary64 integer-limb owner
now resolves ambiguous signs from original operands, and Plane consumes exact
numerator and denominator signs while preserving one ordinary continuous value
path. Plane-local polarized-Ray actions derive one immutable frame fact from
exact collinearity, the certified projection bound, and scale-first frame
normalization, then own distinct geometric-degeneracy and
numerical-representation failures. The public surface,
twenty-four-Optical-Component inventory, separate three-owner/three-enum/
two-Encounter directional inventories, state contract, Assembly/Workstation
lifecycle, and one-way dependency direction are unchanged.
