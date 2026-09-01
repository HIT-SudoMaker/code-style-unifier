# Exact polarized-Ray admissibility and closure

**Pose-vocabulary partial supersession:** The historical `axis_*` and
`launch_plane_*` Pose names and unchanged-public-state claims in this decision
are superseded by
[`0015-ssrhm-tangent-pose-migration.md`](0015-ssrhm-tangent-pose-migration.md).
Its numerical laws, binary64 admissibility, and exact-preservation contract
remain authoritative.

**Partially superseded by:**
`0013-ssrhm-exact-topology-and-plane-local-correction.md` (Accepted —
implemented present truth) replaces only the ambiguous-lane exact-sign and
Plane-local projection-degeneracy calculations. This ADR remains authoritative
for authored binary64 admissibility, exact preservation, polarized-Ray domain
boundaries, and the twenty-four-action Optical Component inventory.

**Status:** Accepted — implemented present truth. This ADR is the documentation
and truth record of the sonnet-polarized-ray-correction initiative: it adds no
optical capability, changes no public API, and changes no public optical
action. The frozen binary64 admissibility budgets, the strict authored-state
rejection, the private calculation conditioning, the exact Plane-local
projection degeneracy classification, and the exact-preservation contract have
landed in production under this frozen contract, and the independent public and
Assembly evidence has landed beside them. The former decimal tolerances
(`1e-5`, `1e-6`, `1e-12`) recorded in ADR-0009's qualitative wording are
displaced as the admissibility budgets of this contract; ADR-0009 carries an
honest forward partial-supersession banner pointing here, and its older
qualitative wording stays bannered as the frozen historical record rather than
unbannered present truth.

**Partial supersession of:** only the numerical-admissibility and
exact-preservation details of
`0009-polarized-ray-foundation.md`. ADR-0010 narrows two specific technical
surfaces of ADR-0009 and nothing else:

- the binary64 admissibility budgets that a public `RayBundle` and an authored
  basis must satisfy (ADR-0009 recorded the qualitative invariant but not the
  frozen binary64 residual formulae); and
- the exact-preservation contract and the Plane-local projection degeneracy
  classification (ADR-0009 recorded the qualitative preservation intent but
  not the explicit zero-degeneracy, zero-delta, and `torch.equal` definitions).

ADR-0010 does **not** replace the polarized-Ray domain decision of ADR-0009.
The mandatory per-ray `polarization_vector`, the explicit transverse Source
polarization with no hidden default, the polarization transport rules across
`TraceTo` / `ReflectAt` / `RefractAt`, Plane-local `RetarderAt`, and finite
Terminal-bound directional Encounters
remain the implemented Ray foundation recorded by ADR-0009; that
polarized-Ray domain decision stays in force and ADR-0010 depends on it rather
than reopening it. The Wave-to-Ray and Ray-to-Wave conversion exclusions, the
mixed Wave/Ray Assembly decision (ADR-0007), and the Wave-side ideal
polarization behaviours (ADR-0008) also stay in force. The older numerical
wording of ADR-0009 stays in place as the bannered frozen record, never
unbannered truth; ADR-0009 carries an honest forward partial-supersession
banner pointing here so the two ADRs cannot drift apart silently.

## Context

The following paragraphs record the pre-correction state that motivated this
ADR; they describe the production tolerances and clamp behaviour as they
stood at independent review time, before the cutover landed. They are the
frozen historical record of the defect reproduction, not a present-truth
description of the now-strict `RayBundle`.

Independent review of the implemented polarized-Ray foundation reproduced a
narrower but seal-blocking defect. The Plane-local Ray-polarization
calculation is not closed over the states that `RayBundle` then accepted.
`RayBundle` admitted direction and polarization norm residuals of `1e-5` and
transversality residuals of `1e-6`, while the Plane-local Jones-frame
implementation assumed an exactly unit direction and clamped every projection
norm below `1e-12` to `1e-12`. Through public actions this produced, for
example: a valid nonparallel near-grazing ray reaches `RetarderAt` and fails
with the existing `ray_bundle_polarization_vector_not_unit` stable identity
even at zero retardance; a direction admitted with norm `1.000005` fails
inside `RetarderAt`; an admitted near-unit direction can make `RefractAt`
return polarization rejected as longitudinal; and the existing Retarder test
oracle duplicates the production `1e-12` clamp, so it is not independent
evidence.

The same review found that one physical invariant was governed by three
unrelated tolerance regimes: Ray direction and polarization at `1e-5` /
`1e-6`, the Collimated Ray Source pose at `1e-6`, and the Surface Pose at a
documented binary64 forward-error budget `8 * gamma_3` where
`gamma_n = n*u/(1-n*u)` and `u = 2^-53`. The two decimal tolerances were not
tied to the real-operation count of the validated invariant. They could admit
visibly non-unit state and let a Source construct a value that a downstream
strict implementation could not consume.

This ADR froze the corrected contract before any production change so that
the implementation tickets could be reviewed against one frozen statement
rather than against shifting prose. It is accepted governance; the production
cutover has since landed under this contract, and this ADR now records the
contract as implemented present truth.

## Decision

### Binary64 admissibility model

The admissibility model is binary64 unit round-off, frozen exactly as:

```text
u = 2^-53
gamma_n = n*u / (1 - n*u)
```

The following maximum admissibility budgets are frozen for this correction:

```text
authored 3D orthonormal basis residual:            8 * gamma_3
Ray direction squared-norm residual:               16 * gamma_5
Ray complex-polarization norm-squared residual:    16 * gamma_11
real transversality residual:                      16 * gamma_5 * ||polarization|| * ||direction||
imaginary transversality residual:                 16 * gamma_5 * ||polarization|| * ||direction||
```

These are upper bounds, not tunable policy. An implementation may use a smaller
bound only if this ADR and independent boundary evidence state the complete
forward-error derivation. It may not enlarge a bound, replace it with a decimal
tolerance, read a global PyTorch tolerance, or introduce a runtime selector.

The factor sixteen is the frozen fixed-double safety factor for one admitted
input construction/conditioning step, one three-dimensional orthogonal
transport, and one output-invariant evaluation; `gamma_5` and `gamma_11`
still name the actual real-operation counts of the checked dot/norm
expressions. A planning calibration over 200,000–250,000 deterministic CPU
and CUDA samples observed normalized / Householder / minimal-rotation
residuals below `2.5e-15`, while the frozen maxima are approximately
`8.9e-15` and `2.0e-14`. That calibration is a regression target, not the
mathematical oracle and not permission to widen the bounds.

The former decimal tolerances `1e-5`, `1e-6`, and `1e-12` are rejected as
the admissibility budgets of this contract. They are not conservative
scientific budgets; they are not tied to the real-operation count of any
validated expression, and they are the mechanism by which an upstream
approximately-valid value reaches a downstream strict implementation and
fails. This ADR records them only as the displaced former tolerances.

### Squared-norm versus norm semantics; separate real and imaginary transversality

Direction is checked as a squared-norm residual: the admission compares
`|<direction, direction> - 1|` against `16 * gamma_5`, where `<.,.>` is the
real dot product. Polarization is checked as a complex-polarization
norm-squared residual: the admission compares
`|<polarization, polarization>_H - 1|` against `16 * gamma_11`, where
`<.,.>_H` is the Hermitian inner product on the complex polarization vector
(conjugate-linear in the first argument) — equivalently the real squared
magnitude `||polarization||^2 = <Re(polarization), Re(polarization)> +
<Im(polarization), Im(polarization)>`, the sum of two real non-conjugated
dot products. Norm checks use squared norms and introduce no square root
solely for validation.

Transversality is the non-conjugated physical dot product
`<polarization, direction>` between the complex polarization and the real
unit direction. For complex polarization, transversality is checked
separately on the real part and on the imaginary part: the real part residual
is bounded by `16 * gamma_5 * ||polarization|| * ||direction||` and the
imaginary part residual is bounded separately by the same
`16 * gamma_5 * ||polarization|| * ||direction||` scale-aware budget. The two
parts are not combined into a single complex residual; each is an independent
admission.

### Authored-state rejection is strict; private numerical calculation is conditioned

Admittance is a promise. Every state accepted by a public Physical Value must
either complete every applicable downstream equation while preserving its
invariants, or fail at the owning public boundary with a stable domain error.
A downstream action must never discover that an upstream value was only
approximately valid under an unrelated decimal tolerance.

Public constructors therefore reject outside-budget authored inputs using the
existing stable error identities. They never silently normalize, project,
rotate, or repair an authored vector at the Physical Value boundary.
Narrowing admissibility changes which values fail; it does not rename the
owning stable error, and no warning, fallback, recovery, or silent repair
closes a failure.

Private numerical implementations are the symmetric counterpart. A private
calculation may locally normalize an already-admitted direction when its
equation needs a unit direction, without replacing authored state. The
authored `RayBundle.direction` tensor is not mutated merely because it is
within the admission budget; the calculation conditions a derived calculation
direction and discards it when the equation is done. Derived action outputs
must themselves satisfy the frozen `RayBundle` budgets; conditioning of a
newly calculated output is permitted only as the final round-off control of
the action's own equation, it must preserve the mathematical direction and
complex polarization state, and it must not conceal an invalid authored input.

The resulting asymmetry is deliberate: boundary state is strict; internal
calculation is stable. This ADR forbids silent repair at the Physical Value
boundary and forbids replacing authored state inside a private calculation.

### Plane-local projection topology and representation are distinct

As corrected by ADR-0013, Plane-local geometric degeneracy means exact
collinearity of the original authored binary64 ray direction and Plane reference
axis. No physical epsilon or ordinary norm owns that topology. The private
Plane-local Jones frame derives, for each lane:

1. a locally normalized calculation direction from the admitted tensor;
2. exact collinearity from the original authored direction and reference axis;
3. the continuous transverse projection used only to construct the frame;
4. scale-first normalization by maximum absolute component and then norm;
5. a separate projection-representability fact;
6. a finite unit placeholder only where the lane is non-interacting; and
7. the second local Jones axis by the right-handed cross product.

A physically parallel ray is classified as non-interacting, and parallel and
otherwise non-interacting lanes retain finite history (their incoming
position, direction, refractive index, Optical Path, status, and polarization
direction are all retained exactly). If an interacting lane nevertheless has
exact projection degeneracy, the owning action raises one stable
action-specific geometric error. If exact topology is nondegenerate but the
continuous projection cannot form a finite nonzero binary64 frame, that action
raises its separate representation error. Neither case is silently projected,
clamped, or replaced, and Numerical Support exposes no physical error identity.

### Exact preservation contract

Exact means tensor-value preservation via an explicit selection or zero-delta
formulation, verified with `torch.equal` on each execution device; it is
explicitly NOT a claim of cross-device bitwise identity. CPU and available
CUDA run the same fixed-double equations, and exactness is checked per device,
but a bitwise-identical cross-device tensor is not asserted.

The following polarization paths preserve the input tensor value exactly:

- every `TraceTo` lane;
- zero-retardance `RetarderAt`;
- every missed, vignetted, already-Finished, TIR, or otherwise non-transformed
  lane;
- normal-incidence successful refraction, whose minimal rotation is the
  identity; and
- the transmitted branch of an ideal Ray NBS before any separately declared
  physical transformation.

`RetarderAt` applies a transformed delta to the incoming polarization rather
than projecting and re-embedding the whole incoming vector; with a strict
identity Jones matrix the delta is exactly zero and the incoming tensor value
is retained by explicit selection.

### Atomic strict cutover

The public cutover is atomic and strict. Formerly admitted vectors outside
the new budgets are rejected immediately with the existing stable error
identities. There is no warning period, no compatibility alias, no migration
shim, no automatic normalization, and no `strict=False` path. No public name
or calling shape changes; correctly constructed fixed-double vectors remain
admissible.

### Wave/Ray correspondence is ideal normalized port-power only

Wave and Ray retain a paired public vocabulary and a similar calling rhythm,
but their correspondence is ideal normalized port-power and interface-order
correspondence only. It is not identical tensor physics, not shared tensors,
not coherence, not phase, and not a shared diffraction algorithm. A Ray
Bundle is not a Wave input and never becomes one. This ADR inherits that
correspondence level unchanged from ADR-0009 and does not alter it.

## Exclusions kept explicit

This decision adds no optical capability. The following exclusions are kept
explicit and adjacent; they are not implicit and are not deferred to a later
ADR:

- No new optical action and no new public root export.
- No Wave-to-Ray conversion and no Ray-to-Wave conversion; no converter.
- No coherent Ray amplitude and no reflected Ray phasor; Ray power stays real
  and separate from the polarization direction.
- No Fresnel coefficients, coatings, extinction-ratio leakage, dichroism,
  Mueller calculus, or curved polarization-selective Elements (Retarder,
  Polarizing Beam Splitter, Nonpolarizing Beam Splitter remain Plane-only on
  the Ray side, as in ADR-0009).
- No arbitrary Jones matrices and no generic N-port scattering on the Ray
  side.
- No volume samples, multislice propagation, sensors, resampling, or noise.
- No public tolerance, generic vector, public Pose, public Frame, strategy
  framework, public Surface, graph framework, backend framework, or runtime
  framework abstraction. In particular, do not create a generic validation
  framework or a public tolerance object; the budgets live as frozen private
  constants owned by `RayBundle` and the shared authored-basis validator.
- No Assembly or Workstation refactor; the existing one-to-two role contract,
  mixed-independent Wave/Ray topology, meta replay, real replay, hosting,
  memory trace, and output schema are evidence targets only.

### Unchanged product boundary

The public inventory is exactly twenty-four Optical Component actions (four
Sources, nine Elements, eight Propagations, two Combinations, and one Wave
Detection), plus separate inventories of three directional owners, three
closed enums, and two Encounter references. The two top-level public exports (`Workstation`
and `install_state`) and the three production seams
(`workstation.py -> optics -> _numerics`) are unchanged. ADR-0010 introduces
no fourth seam, no new role package, and no new public name.

## Why this is surprising

ADR-0009 closed the polarized-Ray foundation as implemented truth and froze
its qualitative invariants (mandatory unit transverse polarization, exact
Trace preservation, Householder reflection, minimal proper rotation). It did
not freeze the binary64 residual formulae that those invariants imply, and it
left the Plane-local calculation dependent on a `1e-12` clamp inherited from
the implementation. It is therefore surprising that a foundation already
sealed as implemented truth is reopened at the numerical-admissibility and
exact-preservation surface only; the surprise is honest, and ADR-0009 carries
a forward banner so the reopening cannot be hidden.

## Rejected alternatives

- **Keep the decimal tolerances `1e-5` / `1e-6` / `1e-12` as conservative
  scientific budgets.** Rejected: they are not tied to the real-operation
  count of any validated expression, they admit visibly non-unit state, and
  they are exactly the mechanism by which an approximately-valid upstream
  value reaches a downstream strict implementation and fails. They are
  displaced by the binary64 budgets above.
- **Silently normalize, project, or repair authored vectors at the public
  boundary.** Rejected: silent repair breaks the promise that an admitted
  state is valid state, hides an upstream authoring error from the user, and
  is the failure mode this correction exists to remove.
- **Introduce a physical epsilon or clamp for Plane-local projection
  degeneracy.** Rejected: a nonzero projection is physically meaningful, and
  clamping it to `1e-12` shortens or rotates the local basis. Degeneracy is
  exact; only a lane already known to be non-interacting or exactly degenerate
  receives a finite placeholder.
- **Cross-device bitwise identity as the definition of "exact".** Rejected:
  CPU and CUDA run the same fixed-double equations, but asserting bitwise
  identical tensors across devices is stronger than the physics requires and
  blocks legitimate exactness evidence. Exactness is per-device
  `torch.equal`.
- **A public tolerance object, generic validation framework, or public
  Pose/Frame/vector abstraction.** Rejected: each budget has one owner
  (`RayBundle` for per-lane state; the shared private authored-basis validator
  for pose). A public tolerance generalizes a frozen scientific constant into
  a tunable API and is excluded.
- **A warning period, compatibility alias, migration shim, or `strict=False`
  path.** Rejected: any of these leaves a partially valid `RayBundle` in the
  wild, which is exactly the contract break this correction removes.

## Important cost

- **Atomic cutover rejects formerly admitted inputs.** The atomic cutover
  intentionally rejects direct Ray inputs that the former `1e-5` / `1e-6`
  gates admitted. This spends backward acceptance to make "unit" and
  "transverse" scientifically meaningful. The loss is bounded: no public name
  or calling shape changes, and correctly constructed fixed-double vectors
  remain admissible.
- **Strict boundary versus stable interior.** The deliberate asymmetry between
  strict public authored-state rejection and conditioned private calculation
  costs implementation discipline: each public constructor must reject and
  each private numerical function must condition, and the two must not be
  confused.
- **One additional ADR.** ADR-0010 adds governance surface. The accepted
  numerical set and exact-preservation behaviour are public scientific
  contracts; leaving the new policy only in private constants would be smaller
  in files and larger in ambiguity. The bidirectional partial-supersession
  link with ADR-0009 keeps the two ADRs honest about which surface each owns.

## Implementation status

Implemented present truth. The binary64 admissibility budgets, the strict
authored-state rejection, the private calculation conditioning, the exact
Plane-local degeneracy classification, and the exact-preservation contract are
installed in production under `src/chromatix_next/`, and the independent
public and Assembly evidence has landed beside them. This ADR adds no public
optical action and renames no public interface; it narrows the admissibility
and exact-preservation surface of ADR-0009 and concentrates the shared
numerical implementations (one real Householder map in `_numerics/reflection.py`,
one private authored-basis validator in `optics/_orthonormal_basis.py`, one
Plane-local Jones-frame and transport implementation in
`_numerics/ray_polarization.py`, and one shared surface advance in
`optics/_ray_surface_advance.py`). The initiative landed the contract in
dependency order (02 install strict admission; 03 close Plane-local and
refraction numerics; 04 concentrate the real Householder; 05 converge
mandatory-polarization Source lifecycle; 06 delete Plane-only hypothetical
seams; 07 close independent evidence; 08 converge active truth). The active
inventory remains the implemented twenty-four-action foundation of ADR-0009
(four Sources, nine Elements, eight Propagations, two Combinations, and one
Wave Detection); the former decimal tolerances recorded
in ADR-0009's qualitative wording are no longer in force as admissibility
budgets and stay bannered there as the displaced historical record. ADR-0010
became implemented present truth when the cutover ticket and its independent
evidence landed; that transition was owned by later tickets of this
initiative, not by the original truth ticket.

## Consequences

- The corrected admissibility and exact-preservation contract is frozen as
  the review benchmark of the correction initiative; later implementation
  tickets can be reviewed against this single ADR rather than against shifting
  prose.
- ADR-0009 carries an honest forward partial-supersession banner pointing to
  ADR-0010, and ADR-0010 records the reverse direction in its
  **Partial supersession of:** header. The bidirectional link is guarded by
  architecture truth evidence: removing the banner on either side, reverting
  ADR-0010 from `Accepted — implemented present truth` to an unmarked draft
  or back to an implementation-pending state, or widening a frozen budget
  must fail the truth test.
- The active ADR inventory lists ADR-0010 as implemented present truth; the
  implemented twenty-four-action inventory, the two top-level public exports, the three
  production seams, and the one-way cycle-free dependency direction are
  unchanged.
- No new optical equation, public capability, dependency seam, fourth role
  package, public tolerance object, or generic validation framework is
  introduced.
