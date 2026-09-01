# ChromatixNext

ChromatixNext is an independent PyTorch optical-simulation system for local
workstations. It provides a compact scientific base for composing, checking,
and evaluating optical paths without copying the runtime architecture of
upstream Chromatix.

This document is the authoritative domain language. It defines every domain
term once, in cognitive order: Physical Values first, then the identity-owning
Source, then Element and Propagation transformations, then Combination, then
Detection, then Assembly, then Workstation execution, then scientific practice.
The dependency direction (`workstation -> optics -> _numerics`) and the
researcher execution order (`construct -> freeze -> host -> run`) are owned by
`docs/architecture.md`, not by this document.

## Scientific language

**Natural Physical Language**:
Names identify exact physical values, physical actions, optical structures,
and execution results. Scientific rigor describes evidence; it does not create
generic product roles.
_Avoid_: Scientific Input, Scientific Study, generic Scientific-prefixed role

**Semantic Pairing**:
Genuinely equivalent values, ports, actions, and states receive concise
parallel names; physically different concepts receive exact natural names.
_Avoid_: decorative mirror type, wrapper created only for naming symmetry

**Scientific Validity Contract**:
Every scientific claim states the model and applicability under which it is
valid. A claim is either Model-Exact, Stated-Domain Approximate, or an
Applicability Rejection. Numerical representation error and physical-model
error are different claims and are never presented as one another.
_Avoid_: absolute real-world correctness, unstated approximation, numerical
certificate presented as universal physical accuracy

**Model-Exact Behaviour**:
A physical law, invariant, or ideal action that is exact within its explicitly
stated model. Exactness does not claim that the model includes every material,
interface, volume, coherence, or detector effect found in an experiment.
_Avoid_: ideal equation presented as complete material reality, feature scope
presented as scientific superiority

**Stated-Domain Approximation**:
A physical approximation whose geometric, spectral, or dimensionless
small-parameter conditions are explicit and whose limiting behaviour is
supported by convergence toward a more exact in-scope reference when one
exists. An arbitrary runtime cutoff is not part of the approximation unless
the physical model independently requires that cutoff.
_Avoid_: hidden paraxial assumption, invented epsilon applicability policy,
test-count or coverage percentage presented as approximation evidence

**Applicability Rejection**:
The stable failure owned by the physical concept whose representation or
stated applicability does not admit the requested operation. Rejection occurs
before an inapplicable numerical law is evaluated; it never clamps, repairs,
falls back, or silently changes representation.
_Avoid_: late NaN, silent fallback, automatic representation conversion,
Assembly structure treated as proof that a chosen physical model applies

**Physical Value**:
A strong immutable value with independent physical invariants, units,
coordinates, and legal operations. Current optical results are Optical Field
and Intensity; numerical intermediates are not Physical Values.
_Avoid_: untyped payload, arbitrary tensor output, generic value container

**Finite Physical State**:
Every public numerical value is finite when created and whenever mutable
Parameter state is consumed. A non-finite value fails at the physical concept
that owns it.
_Avoid_: deferred NaN failure, silent Inf propagation, solver-owned validation
of invalid input state

## Physical Values

**Spatial Grid**:
The immutable uniform transverse sampling value: structural sample counts,
sample spacing, orientation, and first-sample position as paired
zero-dimensional real Tensors in SI metres. A centered Grid derives its
first-sample position from its current spacing on demand. Coordinate identity
participates in physical compatibility; physical equivalence is explicit,
exact, cross-device, and detached from autograd, so ordinary object equality
never stands in for coordinate equivalence.
_Avoid_: Python-valued spacing, batched Grid, cached derived origin,
dataclass Tensor equality, implicit coordinate change

**Spectrum**:
The immutable ordered spectral wavelengths and their nonnegative reduction
weights. Wavelengths are positive SI metres and weights contain no hidden
normalization.
_Avoid_: implicit wavelength, mutable spectral table, trainable wavelength in
the base Spectrum

**Propagation Medium**:
The wavelength-resolved positive real refractive response carried by an
Optical Field. Medium change requires an explicit physical action.
_Avoid_: implicit vacuum, duplicate refractive-index parameter, silent
extrapolation

**Field Normalization**:
The meaning of an Optical Field amplitude. `RELATIVE` is dimensionless;
`POWER` is a power-flux amplitude whose weighted squared magnitude is power
density and whose spatial integral is total power.
_Avoid_: simultaneous amplitude and power, silent renormalization, physical
unit claim on relative intensity

**Polarization State**:
The explicit normalized Polarization Physical Value authored by every Source
in canonical `(Ex, Ey, Ez)` order under the `exp(-iωt)` time convention, and
registered as the shared `polarization_state` checkpoint buffer by all four
Sources (the three Wave Sources and the Collimated Ray Source). A Wave Source
writes the selected Jones components into the Optical Field envelope; the
derived Field carries only Polarization Representation, never a second Jones
state that could diverge from that envelope. The Collimated Ray Source
authors one transverse Polarization with no hidden default and embeds its
Jones components into `RayBundle.polarization_vector` (see Ray Bundle), so
`polarization_state` is not a Wave-only quantity. For propagation along `+z`,
left-circular is `(1, -i, 0)/sqrt(2)` and right-circular is
`(1, +i, 0)/sqrt(2)`; the explicit vectors take precedence over ambiguous
handedness terminology. Scalar, transverse, and full-vector representations
retain one, two, and three explicit components respectively.
_Avoid_: scalar boolean, implicit component order, shape-only polarization,
unnormalized Jones state, framing `polarization_state` as a Wave-only buffer

**Wave Polarization Frame**:
The laboratory frame attached to a Spatial Grid in which a Wave Source authors
its Polarization State. `TRANSVERSE` carries the two Grid-plane components and
does not by itself claim transversality to every local wavevector. `FULL`
carries an explicit three-component sampled boundary field; it is not by that
fact an exact vector-radiation solution. A Vector Propagation owns the
Maxwell-transversality applicability of the field it propagates. Ray
polarization uses a different, explicit pose-local Jones frame that is embedded
as a global vector transverse to the ray direction.
_Avoid_: component count presented as a Maxwell solution, Source silently
projecting each local wavevector, Wave and Ray frame meanings conflated

**Optical Path Reference**:
The immutable per-spectrum optical path length, in SI metres, carried by an
Optical Field. The Field Envelope excludes the spatially uniform carrier
`exp(i 2π optical_path_length / wavelength)`. A Source starts at zero;
homogeneous propagation over signed distance `d` adds `n(wavelength) * d`.
Destination-grid translation and Propagation Exterior do not change it.
Different deterministic references do not break coherence; a Coherent
Combination expresses every input carrier in the first input's reference
before adding complex envelopes.
Before Tensor arithmetic, a fixed per-spectrum length may remain a Python
float. Once represented by a Tensor, every fixed or trainable length is a
zero-dimensional real `float64` accumulator on its current device and
never collapses back to a Python float. A trainable length also retains its
graph; structural immutability of the container is not autograd detachment.
Reference-side wavelengths and refractive responses are evaluated directly in
that same `float64` domain rather than computed at a different regime and
widened afterward. A trainable uniform baseline or propagation distance keeps
its gradient through the factored uniform carrier, observable once a Coherent
Combination aligns two references and the relative carrier phase re-enters the
complex envelope. An isolated single field carries only a global phase, so its
intensity need not show a nonzero gradient; the carrier gradient is observable
through coherent recombination, not through isolated intensity.
_Avoid_: tensor-collapse to Python float, structural immutability conflated
with autograd detachment, geometric-distance alias, full carrier duplicated
in the envelope, single scalar for a dispersive Spectrum, reference equality
as coherence, post-hoc `float64` widening, hidden differentiable bypass
outside the reference tuple

**Source Lineage**:
The private immutable origin identity created by each independent Source
instance and carried unchanged by its Optical Field, Elements, Propagation,
and same-source splitting. Loading identical
`state_dict` values never transfers lineage; copying a Field preserves lineage,
while copying or separately constructing a Source creates an independent
lineage. No researcher-supplied identifier or public registry exists. This
identity ownership is why Source Components do not expose stateless paired
Optical Functions.
_Avoid_: value hash, Optical Path Reference alias, serialized lineage,
user-controlled coherence token

**Optical Field**:
The canonical immutable sampled complex field envelope together with Spectrum,
Polarization Representation, Spatial Grid, Propagation Medium, Field Normalization,
axis meaning, Source Lineage, and Optical Path Reference.
_Avoid_: bare complex tensor, mutable field, ScalarField/VectorField hierarchy

**Field Axes**:
The sole Optical Field layout is
`[batch..., spectrum, polarization, height, width]`. Spectrum and polarization
axes are always present and never inferred from shape, but their lengths are
decided by content: a scalar monochromatic field is `(1, 1, height, width)`
and a vector polychromatic one is `(wavelengths, 2, height, width)`. Optical
Components broadcast over both lengths rather than being written once per
field shape.
_Avoid_: optional spectral axis, optional polarization axis, channel-last
field, shape-based axis guessing, unused polarization length

**Polarization Action Contract**:
The explicit Wave-action account of four independent facts: which
Polarization Representations are applicable, whether accepted components are
preserved, mixed, or projected, how the resulting field is routed across
ports, and whether its polarization frame is preserved or explicitly
transformed. A polarization-neutral action applies the same physical law to
every accepted component; a polarization-transforming action owns its stated
coupling; a polarization-routing action owns both its component law and its
named output ports. An inapplicable representation is rejected with a stable
domain error. No action silently drops, invents, or reinterprets a
polarization component.
_Avoid_: ignored polarization axis, implicit projection, generic mode flag,
one preserve/transform/reject label standing in for port or frame behaviour

**Intensity**:
The immutable finite nonnegative real observation derived from an Optical
Field. It explicitly preserves Spatial Grid, spectral reduction, Field
Normalization, units, and axis meaning.
_Avoid_: bare real tensor, implicit spectral sum, invented physical unit,
premature camera or sensor model

**Ray Bundle**:
The immutable geometric-ray Physical Value that carries three-dimensional
sequential ray state: per-ray position, direction, a per-ray normalized
transverse `complex128` polarization direction, real power, refractive index,
Optical Path, and finite termination status, together with reused Spectrum
metadata. The refractive index travels as a per-ray tensor aligned with the
batch, spectrum, and ray axes, replacing one shared Propagation Medium
object, so mixed active, missed, vignetted, and totally internally reflected
rays each retain their own physical medium history through refraction. The
polarization direction is a transverse complex direction orthogonal to the
real unit ray direction for every active and terminal ray; it is a direction,
not a field amplitude, and the real per-ray power stays a separate
`torch.float64` quantity from this complex direction. It deliberately omits
complex amplitude, Wave coherence, Source Lineage, and Spatial Grid; ray
position and direction come from explicit Source pose, not from a transverse
field sample. Physical per-ray termination is a status, never a NaN payload:
inactive rays retain their finite last physical values (including their
finite polarization direction), while invalid interface state or numerical
solver failure raises a stable domain error through `chromatix_next.errors`.
Implemented numerical correction (ADR-0013): one private device-local
binary64 integer-limb owner resolves ambiguous topology signs from original
operands. Plane uses exact numerator and denominator signs for topology while
ordinary binary64 remains the sole continuous distance path; an active exact
encounter whose distance is not representable fails explicitly. Plane-local
polarized-Ray actions derive one private frame fact from exact collinearity and
scale-first projection normalization, separating geometric degeneracy from
continuous projection non-representability. No epsilon, host exactness fallback,
arbitrary reference axis, public capability, or inventory change was added.

Implemented present truth (ADRs 0009, 0010, and 0013, with the directional
cutover recorded across ADRs 0007–0012): the active Optical Component inventory
is twenty-four actions (four Sources, nine Elements, eight Propagations, two
Combinations, and one Wave Detection). Separately, the public directional
surface contains three state-only owners, three closed Terminal/diagonal enums,
and two Assembly-issued Encounter reference types. `TraceTo` preserves
polarization exactly; `ReflectAt` applies the same real Householder reflection
map to direction and complex polarization; successful `RefractAt` applies the
unique minimal proper rotation (normal incidence is identity); `RetarderAt`
remains the sole Plane-local polarized-Ray Element. Ideal cube beam splitters
and the ideal planar mirror are directional owners referenced by finite,
state-free Wave or Ray Encounters. Their typed physical Terminals replace
relative branch Ports; one owner may be referenced by several Encounters but
appears once in the registered module tree. Under
ADR-0010 the authored `RayBundle` direction, complex polarization, and
transversality residuals, together with the Collimated Ray Source and Surface
authored basis, are admitted under frozen binary64 forward-error budgets
(`u = 2^-53`, `gamma_n = n*u/(1-n*u)`); public constructors reject
out-of-budget authored state with the existing stable error identities and
never silently normalize, project, or repair it, while private numerical
implementations may locally condition an already-admitted calculation
direction. Plane-local projection degeneracy means exact authored-direction/
reference-axis collinearity, not ordinary norm zero. Nonzero projections are
normalized scale-first; a separately unrepresentable continuous frame is
rejected by the owning action. The polarization paths that do not transform a lane
(`TraceTo`, zero-retardance `RetarderAt`, missed/vignetted/already-finished/TIR
lanes, and normal-incidence refraction) preserve the input tensor value exactly
via `torch.equal` on each
execution device. ADR-0010 owns the frozen budget expressions and the
complete exact-preservation set; this domain entry states the contract once
and does not duplicate the formula table.
_Avoid_: bare real tensor, generic Optical State, wave-field batch posing as
rays, NaN termination, second complex amplitude, hidden ray registry, shared
Medium object rewritten across a mixed-status bundle, longitudinal or
non-unit polarization direction, decimal `1e-5`/`1e-6`/`1e-12` admissibility
budget, silent authored-state normalization at the Physical Value boundary

**Ray Axes**:
The sole Ray Bundle layout is `[batch..., spectrum, ray, xyz]` for position
and direction, and `[batch..., spectrum, ray]` for power, refractive index,
Optical Path, and status. The trailing `xyz` axis has length three and
denotes the global right-handed Cartesian SI frame; spectrum and ray axes
are always present and never inferred from shape.
_Avoid_: optional spectrum axis, channel-last ray tensor, shape-based axis
guessing, mixing position and power ranks

**Ray Status**:
The non-floating per-ray termination encoding carried by a Ray Bundle. The
fixed `uint8` bitmask names exactly one of active, surface missed,
vignetted, and total internal reflection per ray; zero state, unknown bits,
combined active/terminal states, and multiple terminal states are rejected
at construction, so every ray has an unambiguous single state. A ray that
has terminated keeps its finite last position, direction, power, refractive
index, and Optical Path; status, not a non-finite payload, expresses the
physical stop.
_Avoid_: floating status dtype, NaN status payload, unbounded status enum,
silent bit outside the named mask, zero status word, combined active and
terminal bits

**Ray Optical Path**:
The per-ray device-local `float64` optical-path accumulator carried by a Ray
Bundle. It starts at zero at the Source and accumulates the per-ray incident
refractive index times geometric distance along the sequential path. Like the
Optical Path Reference of an Optical Field, it is an invariant accumulator;
under Fixed Double it shares the same `float64` regime as ray position,
direction, power, and refractive index, so it is not a second numerical
regime.
_Avoid_: post-hoc widening, geometric distance reported as optical path,
single scalar for a dispersive Medium

## Source

The Source role owns field identity. A Source is the Optical Component that
creates an Optical Field together with the Source Lineage it carries; because
Lineage must persist across calls and differ between instances, a Source has
no stateless paired Optical Function (see Element and Propagation
transformations for the paired Function/Component contract). The current
Source vocabulary is the Plane Wave and its authored directional carrier.

**Plane Wave**:
The wave Source of a spatially uniform transverse field on a Grid, carrying
one declared normalization, Propagation Medium, and Polarization State. Its
direction is authored either as a unit Propagation Direction shared by every
spectral component, or as an explicit Transverse Wavevector whose
magnitude-and-direction follows wavelength and Propagation Medium. Sampling is
strict: each axis must resolve the per-spectrum transverse wavevector at
strict Nyquist and each spectral component must stay radiative, checked by
exact sign primitives before synthesis, so an undersampled or evanescent
component rejects the whole Source without epsilon softening.
_Avoid_: epsilon-softened evanescent clipping, wavelength-independent
transverse wavevector magnitude, silent aliasing of a tilted carrier

**Propagation Direction**:
The explicit unit direction shared by the spectral components of a Plane Wave;
wavevector magnitude follows wavelength and Propagation Medium.
_Avoid_: ambiguous tilt pair, wavelength-independent magnitude

**Transverse Wavevector**:
The explicit radians-per-metre spatial carrier of a Plane Wave. A shared
carrier may produce wavelength-dependent directions.
_Avoid_: `kykx`, unitless carrier, silent evanescent clipping

**Gaussian Beam Source**:
The paraxial wave Source producing a Gaussian beam envelope on a
transverse Grid with explicit waist, waist axial location, one declared
normalization, Propagation Medium, and Polarization State. The beam axis
aligns with the Grid normal; the uniform axial carrier stays in the
Optical Path Reference, while Gouy phase and wavefront curvature remain
in the envelope. Under the repository `exp(-iωt)` time convention, the
forward beam envelope uses a negative Gouy phase `exp(-i arctan(z/zR))`
and a positive wavefront-curvature phase `exp(+i k r²/(2R(z)))` once the
shared axial carrier is removed, matching forward Wave propagation in
the complex field; negative `z` follows the conjugate symmetry
`env(-z) = conj(env(z))`. A waist that drives any spectral component's
Rayleigh range nonpositive is rejected without epsilon softening.
When authored with `FULL` Polarization Representation, the result is a
component-wise paraxial sampled boundary field; it does not claim to be an
exact vector-radiation solution. A consuming Vector Propagation owns any
additional Maxwell-transversality applicability.
_Avoid_: divergence hidden in amplitude, second wavelength-dependent
waist, POWER and RELATIVE supplied together, sign selector or convention
flag, compensating downstream phase, full component count presented as an
exact vector Gaussian solution

**Point Source**:
The wave Source producing a spherical wave envelope on a transverse Grid
from an explicit three-dimensional `(y, x, z)` origin, with one declared
normalization, Propagation Medium, and Polarization State. The Grid is
the `z=0` plane; the point-to-grid optical path stays in the envelope
under the same Optical Path Reference convention as the other wave
Sources. Fresnel-zone sampling preserves the per-spectrum index–wavelength
pairing `n(λ_i)/λ_i` of the Propagation Medium, never a cross-paired
`max(n)/min(λ)`; the Source rejects an origin on the Grid plane and a Grid
too coarse to resolve the nearest Fresnel zone, without epsilon softening.
When authored with `FULL` Polarization Representation, the result is a
component-wise spherical sampled boundary field; it does not claim the
near-field, longitudinal structure, or radiation pattern of an exact vector
emitter. A consuming Vector Propagation owns any additional
Maxwell-transversality applicability.
_Avoid_: epsilon-softened singularity, origin inferred from a grid
sample, silent acceptance of an undersampled spherical wave, sampled scalar
spherical law presented as an exact vector emitter

**Sampled Wave Source Synthesis**:
Implemented present truth (ADR-0014): the shared physical reading order by
which a sampled Wave Source validates its
authored state and Grid, resolves normalization, synthesizes its own unit
envelope, and constructs one Optical Field. Plane Wave, Gaussian Beam Source,
and Point Source share this order while each retains sole ownership of its
equation, sampling applicability, parameters, and stable failures.
_Avoid_: universal Source behaviour, shared Source equation, method selector,
Source physics hidden in a generic callback framework

**Collimated Ray Source**:
A Ray-producing Source that maps an authored Spatial Grid into the global
right-handed Cartesian SI frame as a grid of launch samples, with explicit
Ray Pose, a single shared launch direction, and an explicit transverse
Polarization with no hidden default. Pose is an ordered pair of finite unit
orthogonal basis vectors plus an origin; the launch direction is the derived
cross product of that ordered pair, so it always agrees with the launch-plane
normal. The ordering defines the orientation; there is no independently
authored right-handedness claim. The first basis is physical `launch_tangent_x`
and the second is
physical `launch_tangent_y`; Grid coordinates remain stored in `(y, x)`
indexing order, while x displacement maps to `launch_tangent_x` and y
displacement maps to `launch_tangent_y`. The Source authors one transverse
`Polarization` whose Jones x component maps to `launch_tangent_x` and whose
Jones y component maps to `launch_tangent_y`; the default pose
(`tangent_x = (1,0,0)`, `tangent_y = (0,1,0)`, launch direction `(0,0,1)`) reproduces the global
`(Ex, Ey, Ez)` ordering and the repository `exp(-iωt)` handedness. The same
polarization direction is broadcast across every spectrum and ray without a
second amplitude or coherence value. Each ray starts with the authored scalar
ray power, the authored named Medium evaluated at the bundle wavelengths as
the per-ray refractive index, zero Optical Path, and an active status. The
Source owns three-dimensional pose and direction interpretation; it still
does not invent complex amplitude, Wave coherence, or a transverse grid for
the Ray Bundle.
_Avoid_: wavelength-independent ray direction, pose hidden in mutable trace
state, grid-less ray batch, ray direction supplied separately from pose,
hidden default polarization, scalar or full polarization representation

**Ray Pose**:
The explicit three-dimensional placement of a collimated launch plane in the
global SI frame: a real origin together with two orthonormal ordered basis
vectors `tangent_x` and `tangent_y` that span the launch plane. Their
names denote physical local Cartesian directions rather than Tensor index
order; the launch direction is `tangent_x × tangent_y`. Pose belongs to the Source, and the
launch direction is derived rather than authored separately, so a Ray Bundle
never carries an implicit or mutable pose.
_Avoid_: implicit launch plane, pose stored on a mutable tracer, separate
direction vector that can disagree with the plane normal

## Surface adapters

A Surface is a passive state adapter, not a sixth Optical Role: it owns global
Cartesian SI pose with an ordered tangent pair, shape parameters, and an optional circular
clear aperture, embedded as PyTorch state beneath its owning Element or
Propagation action. Surface local coordinates, nearest-forward intersection,
oriented unit normal, and aperture projection live in private Numerical
Support; a Surface exposes no public custom-intersection adapter and no solver
selector. The three concrete adapters are Plane, Sphere, and Conic Even
Asphere; Ray Refraction and Ray Reflection share one Surface seam across all
three.

**Surface Pose**:
A real vertex origin plus two orthonormal ordered basis vectors expressed in
the global SI frame. `tangent_x` and `tangent_y` name the physical local
Cartesian directions tangent to the Surface at its vertex; sampled `(y, x)`
index order does not reverse their meaning. The vertex unit normal is
`tangent_x × tangent_y`, so it always agrees with the declared
surface facing.
Pose parameters may be trainable (for example, axial spacing), letting an
inverse-design gradient reach a Surface vertex through ordinary autograd.
_Avoid_: pose stored on a mutable tracer, surface normal authored separately
from basis, local-only coordinates returned to the caller

**Plane Surface**:
The infinite flat Surface adapter. It owns pose and an optional circular clear
aperture; the intersection is the analytic forward root, with parallel or
rear-facing rays marked surface missed. A ray whose direction is certified
parallel to the plane is missed, including the coplanar case where the ray
origin already lies in the plane; a non-parallel ray is taken at its certified
nearest forward parameter, with an origin exactly on the plane certified as a
zero-distance hit. A ray whose intersection lies exactly on the aperture
circle is inside the aperture, so the aperture boundary is exact rather than
epsilon-open.
_Avoid_: implicit aperture plane, axis-aligned-only plane, silent acceptance of
a rear-facing root, epsilon-open aperture boundary

**Sphere Surface**:
The signed-curvature spherical Surface adapter. The vertex normal points along
`tangent_x × tangent_y`; the centre of curvature lies at `vertex + R × normal`, so a
positive radius of curvature is convex toward the incident medium and a
negative radius is concave. The physical radius is the absolute curvature
radius.
_Avoid_: unsigned curvature, centre hidden in mutable trace state, ambiguous
sign convention

**Conic Even Asphere Surface**:
The modern aspheric Surface adapter with curvature, conic constant, optional
even-asphere coefficients, and a clear aperture. The standard sag
convention is `z = c·r²/(1 + √(1 − (1+k)·c²·r²)) + Σ α_i·r^(2i)` in surface
local coordinates; with `k = 0` and no even terms it degenerates to the
spherical sag and shares the Sphere sign convention. A finite positive clear
aperture is required whenever any polynomial even-asphere term is present,
because the intersection proof derives its bounded ray-parameter search
interval from the aperture cylinder; a base conic with no even terms leaves
the aperture optional. Intersection delegates to the Certified Conic Encounter
defined below: base conics use analytic root selection, while polynomial
aspheres certify root topology before safeguarded device-local refinement.
Rays outside the real-sag domain are marked surface missed, and a genuinely
non-converged in-domain candidate raises a stable domain error rather than
producing a non-finite payload.
_Avoid_: public iterative solver, sag derivative that diverges silently at the
domain edge, polynomial coefficients indexed from zero, aperture-free
polynomial even asphere

**Certified Conic Encounter**:
Implemented present truth (ADR-0014): the nearest-forward encounter between a
Ray Bundle and a Conic Even Asphere. A base conic uses analytic root selection;
a polynomial asphere certifies its root topology before device-local continuous
refinement. Both paths return distance, position, and oriented normal through
the same encounter rather than exposing public solver choices.
_Avoid_: public solver selector, uncertified nearest root, host-computed
continuous result, separate encounter contract for polynomial aspheres

## Element and Propagation transformations

This section first defines the cross-role action vocabulary shared by every
role package, then the Element entries, then the Propagation entries. An
Optical Function and its paired Optical Component share one physical
implementation; a Field Transformation constructs every derived Optical Field;
Optical Composition names the ordinary reading order in which these actions
transform strong Physical Values.

**Optical Function**:
The stateless direct-call expression of one identity-free physical action. It
is co-located and name-paired with its Optical Component, consumes the role's
Physical Values before the Component-owned physical parameters, and returns
only strong Physical Values. A Source is not an Optical Function because it
must own stable Source Lineage across calls.
_Avoid_: public numerical kernel, generic callable wrapper, duplicate physics

**Optical Component**:
The PyTorch state-owning expression of one physical action. It conforms
structurally to exactly one Optical Role, acts only on the Physical Values
required by that role, and owns trainable and fixed state. When its role
package exports a paired Optical Function, the Component delegates the same
calculation.
_Avoid_: universal Component base, inheritance family, generic callable
wrapper, public numerical kernel

**Optical Role**:
Exactly one physical navigation role held by an Optical Component: Source,
Element, Propagation, Combination, or Detection. Its public structural call
signature and runtime validation express one role contract.
Its one private semantic authority supplies both adapters. A Role declares no
runtime policy and creates no inheritance hierarchy.
_Avoid_: capability family, runtime group, support aggregate, ambiguous role

**Component Call**:
The state-owning physical calculation performed by one Optical Component.
The same `forward` path serves real execution and isolated Meta Inference.
For a paired action, `forward` is a single delegation to the same physical
implementation as its Optical Function.
_Avoid_: duplicate apply verb, universal input payload, forced common arity

**Component State**:
The distinction between trainable physical values, fixed physical values, and
derived disposable state. User trainable identity is preserved; fixed state
moves with its Optical Component; derived state never defines release identity.
_Avoid_: trainable boolean, copied trainable value, fixed trainable value

**Field Transformation**:
The private immutable construction seam for a derived Optical Field. It
inherits Spectrum, Polarization Representation, Medium, Field Normalization, and Source
Lineage, while every intended Grid or Optical Path Reference change remains a
named choice at the calling Optical Component.
_Avoid_: public mutable field update, repeated metadata reconstruction,
implicit Grid or path-reference change

**Optical Composition**:
The ordinary physical reading order in which Optical Functions or Optical
Components transform strong Physical Values. Simple one-off calculations use
a paired function when present; reusable, trainable, or assembled paths use
Components. Neither form needs an installed orchestration role.
_Avoid_: mandatory configuration runtime, catalog-first authoring, generic
callable pipeline

**Sequential Ray Prescription**:
A transparent PyTorch module root that reads one physical action per line in
authored order — a Ray-producing Source, followed by Ray Trace, Ray Refraction,
and Ray Reflection actions on named Surfaces, ending at a Named Output — with
no public Sequential Tracer, event list, graph, or solver runtime. The root
declares no Optical Role and its direct children are legal Optical Components,
so Workstation Host accepts it and Workstation Run returns the traced Ray
Bundle as a Named Output through a module-level calculation. Ray paths may
also enter a mixed Assembly; see Mixed Wave and Ray Assembly.
_Avoid_: public sequential tracer, prescription event registry, solver
selector, linear Ray path forcing a second graph model

### Elements

**Retarder**:
The ideal lossless zero-mean SU(2) transverse polarization transformer. It is
spatially uniform, achromatic, and transverse-only: scalar and full-vector
representations are rejected rather than silently projected. Its physical
parameters are `retardance_cycles` (the differential phase in cycles, not
radians), `retarded_eigenstate_azimuth_radians`, and
`retarded_eigenstate_ellipticity_radians`. The retarded eigenstate receives
the positive half of the authored differential phase and its orthogonal
eigenstate receives the negative half, so zero retardance is exactly the
identity. `orthogonal_eigenstate_projector` equals
`polarization_identity_matrix - retarded_eigenstate_projector`;
`retarded_eigenstate_phasor` and `orthogonal_eigenstate_phasor` are the
cycles-only phasors at `+retardance_cycles / 2` and
`-retardance_cycles / 2` respectively, and `retarder_matrix` is the sum of
each named phasor multiplied by its named eigenstate projector. Under
`exp(-iωt)` the retarded eigenstate owns the positive half-cycle contribution.
`retardance_cycles` is not silently reduced modulo one: under the zero-mean
gauge, integer-cycle shifts can differ by a field-observable common phase even
when they describe the same point on the Poincaré sphere, which is an explicit
SU(2) convention rather than an accidental branch. Quarter-wave behaviour is
expressed by Retarder parameters; the former Quarter-Wave Plate convenience
action and its arbitrary common-phase convention are intentionally removed
without alias.

**Optical Path Profile**:
A baseline and spatial variation of optical path length, in SI metres,
registered to one Spatial Grid. It already represents optical path and is not
geometric material thickness; its spatial phase is
`exp(i 2π optical_path_variation / wavelength)`.
_Avoid_: geometric-thickness alias, second multiplication by Propagation
Medium, unitless phase map

**Amplitude Transmission Map**:
A dimensionless nonnegative real amplitude multiplier in the closed interval
`[0, 1]`, registered to one Spatial Grid. A passive complex transmission is
expressed by composing this amplitude action with Optical Path Modulation;
neither Component silently assumes the other's physical meaning.
Its intensity transmission is the squared amplitude magnitude, not an
alternative constructor input.

**Ideal Thin Lens**:
The paraxial quadratic-phase Element with explicit focal length, centre,
Propagation Medium, and Optical Path Reference behaviour. It owns no pupil,
propagation, or sensor.

**Pupil**:
A binary amplitude-aperture Element that multiplies the incident field
envelope pointwise by a closed-boundary mask registered to one Spatial Grid.
A circular pupil uses the transverse radius and a square pupil the transverse
half-width as its single extent; a sample exactly on the aperture boundary is
inside. The aperture geometry is fixed state, so a pupil owns no trainable
parameter and invents no phase.

**Directional Cube Beam Splitters and Planar Mirror**:
Three state-only directional owners carry fixed physical geometry and response
state but no Optical Role or standalone action. Cube Terminals are `LEFT`,
`TOP`, `RIGHT`, and `BOTTOM`; the coating diagonal is `RISING` or `FALLING`.
The planar Mirror has only the `FRONT` Terminal in this increment. Assembly
issues finite state-free `WaveEncounter` and `RayEncounter` references to one
registered owner, derives Terminal frames and Route segments, and rejects any
energized output without a connection, exposure, or Route End.

Cube response coefficients own coating phase; homogeneous Propagation owns
Optical Path Reference advance; the ideal Mirror owns its gauge-fixed `-1`
Wave scalar. Route geometry owns none of those phases. Structural Assembly
closure, observational Detection/Example-evidence closure, and Workstation
execution closure are independent and cannot compensate for one another.
Routes are finite and acyclic: owner reuse creates additional named Encounters,
never recurrence, automatic pass discovery, or a convergence solver.
_Avoid_: relative device Ports, lumped splitter action, public scattering
matrix, inferred passes, phase owned by Route

**Ray Refraction at Surface**:
The paired `refract_at` and `RefractAt` Element actions refract a Ray Bundle
at a Plane, Sphere, or Conic Even Asphere into an explicitly named destination
Medium by vector Snell. Active rays advance to the global intersection, accumulate
the per-ray incident refractive index times geometric distance into the
per-ray Optical Path, and adopt the refracted direction; power is unchanged
because ideal geometric interactions invent no Fresnel, coating, or
polarization. Only rays that successfully transmit switch their per-ray
refractive index to the destination Medium evaluated at the bundle
wavelengths; total internal reflection, vignetted, surface-missed, and
already inactive rays retain their incident refractive index exactly. Total
internal reflection terminates that authored transmitted path with a finite
status and retains the incident direction; it never rewrites the authored
refraction into a reflection. A non-finite refracted output raises a stable
domain error named `refract_at_output_state_nonfinite`.
_Avoid_: automatic reflection fallback, implicit destination Medium, TIR
rewriting the action, Fresnel coefficient invented by the kernel, mixed-status
ray having its incident index rewritten by the destination Medium

**Ray Reflection at Surface**:
The paired `reflect_at` and `ReflectAt` Element actions reflect a Ray Bundle
at a Plane, Sphere, or Conic Even Asphere by the law of reflection. The ray
advances to the global intersection, accumulates the per-ray incident
refractive index times geometric distance into the per-ray Optical Path, and
adopts the reflected direction; the per-ray refractive index is unchanged
because reflection is an authored event that stays in the incident medium,
and power is unchanged. Reflection is an authored independent event, never an
automatic fallback from a failed refraction, so total internal reflection is
not a reflection status. A non-finite reflected output raises a stable domain
error named `reflect_at_output_state_nonfinite`.
_Avoid_: reflection as refraction fallback, Medium transition at a mirror,
Fresnel coefficient invented by the kernel

### Propagation

**Destination Grid**:
The explicit Spatial Grid requested at a propagation destination. It expresses
scale, shift, and orientation without selecting or changing the Propagation
method.
_Avoid_: aligned/shifted wrapper hierarchy, off-axis boolean, scaled boolean

**Propagation Exterior**:
The authored field meaning outside a sampled transverse window. Periodic
Exterior repeats the window; Isolated Exterior treats the exterior as zero.

**Propagation Choice**:
The scientist's explicit selection of one Propagation Component. Each method
accepts a Destination Grid but executes only geometry and sampling within its
own scientific applicability; failure never substitutes another method.
Scalar Wave propagation may act component-wise on scalar and transverse
fields only under its declared homogeneous, isotropic, polarization-neutral
approximation. A full-vector field requires a Vector Propagation whose
interface owns transversality and longitudinal-component behaviour; a scalar
method rejects it rather than silently treating three components as unrelated
scalar fields.
_Avoid_: automatic solver, hidden fallback, propagation mode boolean

**Scalar Angular Spectrum Propagation**:
Scalar Helmholtz propagation of radiative spatial frequencies between
parallel planes with signed axial distance, explicit Destination Grid, and
explicit Propagation Exterior. Evanescent and alias support follow the
two-dimensional displaced transfer phase owned by the radiative-spectrum
numerical owner, not a rectangular per-axis cutoff; per-spectrum
refractive-index and wavelength pairing is preserved.

**Vector Angular Spectrum Propagation**:
Radiative vector Helmholtz propagation between parallel planes. The paired
public interfaces are `vector_angular_spectrum` and
`VectorAngularSpectrum`. They accept transverse or physically transverse full
fields, return explicit `(Ex, Ey, Ez)` content, reject scalar fields,
evanescent or grazing division, and non-relative normalization, and use the
same authored Destination Grid and Propagation Exterior language as the scalar
action. Supported gradients belong to the input envelope and axial distance;
hard radiative support and geometry remain fixed.

**Aplanatic Focus Propagation**:
The paired `aplanatic_focus` and `AplanaticFocus` interfaces map one sampled
transverse exit pupil through an ideal energy preserving aplanatic objective
to one authored focal plane with explicit `(Ex, Ey, Ez)` content. The action
accepts uniform grids and relative normalization, derives wavelength-resolved
numerical aperture from Medium and maximum convergence angle, preserves the
factored objective carrier in Optical Path Reference, keeps the axial-distance
contribution graph-bearing, and rejects unsupported support, sampling,
geometry, or normalization without fallback.

**Fresnel Transform Propagation**:
Single-transform scalar paraxial propagation of one spectral component over a
finite nonzero signed axial distance. Vacuum wavelength, Propagation Medium,
input sampling, sample counts, and distance determine the centered output
Grid. Forward execution and Assembly grid inference share that one physical
resolver; a multispectral Field is rejected because its wavelengths require
different output sampling.

**Scaled Angular Spectrum Propagation**:
Scalar radiative angular-spectrum propagation to a parallel destination
Grid whose sample counts, spacing, first-sample position, and orientation
are all authored and may differ from the source. The envelope keeps only
the longitudinal-wave-number residual phase; the per-spectrum uniform
carrier stays in the Optical Path Reference. The inverse discrete-Fourier
sum is evaluated at the authored destination positions by a separable
Bluestein chirp-z, distinct from the IFFT-centre-crop path of
`ScalarAngularSpectrum`, which permits translation only. Evanescent and
alias support come from the single radiative-spectrum owner.
_Avoid_: scaled boolean, magnification parameter, shared transfer kernel
with the paraxial Collins method

**Scaled Fresnel Propagation**:
Paraxial Collins/Fresnel propagation to a destination Grid that may carry
magnification, expressed by the destination geometry and signed axial
distance together; there is no independent magnification parameter. The
paired public interfaces are `scaled_fresnel` and `ScaledFresnel`. Its
transfer kernel is the input and output quadratic phase chirp of the
Collins integral, not the Helmholtz `exp(i k_z d)` kernel, so it has no
evanescent branch and shares no equation with `ScaledAngularSpectrum`.
The uniform axial carrier stays in the Optical Path Reference; negative
distance propagates backward by a conjugate flip. The name states the
equation (Fresnel) and the destination geometry (Scaled, author-grid
magnification) and replaces the earlier Collins-as-scalable-spectrum
wording, which was a misnomer.
_Avoid_: paraxial selector, shared kernel with the radiative scalar
method, magnification as a declared parameter

**Scalable Angular Spectrum Propagation**:
Genuine scalable angular-spectrum (SAS) propagation to a parallel
destination Grid whose sample counts, spacing, first-sample position, and
orientation are all authored and may differ from the source. The method
applies the SAS precompensation — the ratio of the exact angular-spectrum
residual transfer `exp(i (k_z − k) d)` to the conjugate of the paraxial
Fresnel residual transfer `exp(+i d (k_x² + k_y²)/(2k))`, equivalently
`exp(i k d [√(1 − s²) − (1 − s²/2)])` — in the Fourier domain, then runs
the paraxial Collins/Fresnel stage of `ScaledFresnel` on the
precompensated envelope. The paired public interfaces are
`scalable_angular_spectrum` and `ScalableAngularSpectrum`. Evanescent
support and radiative wave-number facts come from the single
radiative-spectrum owner; alias support is the SAS method's own, derived
from the residual precompensation phase above, and is distinct from the
standard-AS support owner. The paraxial stage shares no equation with that
owner but consumes the same computational-window and chirp-z infrastructure
as `ScaledFresnel`.
Applicability is scalar, homogeneous-medium, paraxial-scaling (the
destination magnification is carried by the paraxial Collins stage, so the
SAS correction stays small only while the Fresnel stage itself stays
paraxial), and sampling-bounded (radiative and alias support define the
band on which the precompensation equals the exact transfer); the method
is not an exact solver outside that band. The uniform axial carrier stays
in the Optical Path Reference. Negative distance propagates by the
forward order with a signed-distance precompensation transfer
(`p(d<0) = conj(p(|d|))`) and the `scaled_fresnel` conjugate flip; the
same-grid round trip is therefore the SAS-correction paraxial
approximation of an exact inverse, not a bit-exact inverse, because the
SAS literature's strict inverse order is defined only for same-source-and-
destination geometry.
_Avoid_: presenting the SAS correction as exactness outside the declared
band, selector or fallback to `ScaledFresnel` or `ScaledAngularSpectrum`,
a second precompensation owner, magnification as a declared parameter.

**Ray Trace to Surface**:
The paired `trace_to` and `TraceTo` Propagation actions advance a Ray Bundle
to a posed Plane, Sphere, or Conic Even Asphere through the nearest forward
intersection. The direction, per-ray refractive index, and power are
unchanged; the per-ray Optical Path accumulates that ray's own incident
refractive index times geometric distance. Parallel or rear-facing rays are
marked surface missed; rays beyond the clear aperture are marked vignetted;
inactive rays keep their prior state, including their incident refractive
index. The action owns no Medium transition and no authored branch. A
non-finite advanced position raises a stable domain error named
`trace_to_output_position_nonfinite`.
_Avoid_: hidden image-plane special module, implicit Medium transition,
aperture handled outside the encountered Surface, mutable current Surface

## Combination

**Coherent Combination**:
Complex-field combination allowed only when frequency, spectral weighting,
Polarization Representation, Propagation Medium, Spatial Grid, Field Normalization,
axes, envelope dtype, and Source Lineage are compatible. Unequal deterministic
Optical Path References contribute their explicit relative carrier phase and
are not a coherence failure.

**Intensity Combination**:
Pointwise addition of two already-detected, compatible `Intensity` observables.
It does not determine mutual incoherence: the caller must already know that the
cross-coherence term vanishes on the relevant statistical or integration scale,
or must have detected the two inputs independently. It never adds complex fields
or invents a relative phase.

After Intensity Combination, no propagatable Optical Field remains. If later
Wave propagation is required, the two Optical Fields must instead be propagated
independently to Detection and only then may their compatible intensities be
added.

Normalization is explicit. `POWER + POWER` is a physical W/m² sum.
`RELATIVE + RELATIVE` is only a relative sum on one caller-authored common
dimensionless scale. A mixed normalization is rejected; there is no automatic
conversion or renormalization.

## Detection

Detection is the role that applies Intensity (defined under Physical Values)
to an Optical Field. Its public Component form is `IntensityDetection` and its
stateless paired Function is `intensity_detection`; both share the same
physical implementation through the paired Function/Component contract defined
under Element and Propagation transformations. The Detection role owns no
separate physical value of its own.

## Assembly

**Assembly**:
The canonical complete optical structure. It owns Optical Components,
Physical Value connections, authored exposures, topology, and whole-path
compatibility, but owns no optical law, device, optimizer, presentation, or
public replay method. It remains a PyTorch Module only to register the authored
Component and Parameter tree. Connections, exposures, and frozen execution
facts refer only to stable Component names; current Module instances are
resolved from that registered tree, so copying or same-version serialization
cannot retain stale Python identity. An included name cannot be replaced or
deleted outside the authoring grammar. Workstation privately replays a frozen
Assembly.
_Avoid_: public Optical Graph, arbitrary pipeline, second runtime

**Mixed Wave and Ray Assembly**:
One frozen Assembly may contain independent Wave and Ray subgraphs. Wave
Sources, Elements, Propagations, Combinations, and Detections consume and
produce Optical Field or Intensity; Ray-producing Sources, `TraceTo`, and
the `ReflectAt`/`RefractAt`/`RetarderAt` Ray Elements consume and produce Ray
Bundle. Directional owners execute only through Assembly-issued Wave/Ray
Encounters, whose finite routes may coexist with ordinary Component subgraphs.
The independent subgraphs may coexist without a converter, but a direct Wave-to-Ray or
Ray-to-Wave connection is rejected at authoring time in both directions,
because this initiative admits structural coexistence, not physical unification.
The single authoring grammar, the single frozen fact, and the single private
replay implementation are unchanged from the Wave-only Assembly.
_Avoid_: Wave-to-Ray converter, Ray-to-Wave converter, parallel Ray runtime,
forced all-Wave or all-Ray Assembly

**Assembly Authoring**:
The three-step grammar Include, Connect, and Expose. Include gives one
Optical Component a unique stable name; Connect declares Physical Value flow;
Expose gives one computed Physical Value output a non-consuming user-facing
name (an Authored Exposure; see below). Connect validates source and
destination membership, port tokens, declared ports, Physical Value
compatibility, source-output occupancy, and destination-input occupancy
before appending the connection, so a rejected authoring operation has no
effect. The researcher cognitive order is fixed as
`include -> connect -> expose -> check/freeze -> host -> run -> Named Outputs`.
_Avoid_: public node, builder, string path connection, implicit registration

**Authored Exposure**:
One non-consuming user-facing name, authored by Expose, for one computed
Physical Value output that becomes a final Named Output. An Authored Exposure
may name a topologically intermediate output and may coexist with one
downstream connection on the same output, while remaining physically
non-consuming and computationally retained through run completion. It is
explicitly not an Optical Role, not a splitter, not a Detection, not a sensor,
not a tap, and not a loss: naming an exposure changes no power, phase,
polarization, direction, status, or Optical Path. One stable Component-output
anchor has at most one Authored Exposure; a second name for the same anchor is
rejected before exposure state changes. Distinct ordinary Component output
ports remain independently exposable, and authored exposure order is the Named
Outputs order. Detection remains the only Wave role that derives Intensity; an
Authored Exposure cannot be mistaken for a detector or sensor.
_Avoid_: physical detector, sensor, tap, branch, energy-consuming observation,
alias for one physical fact, arbitrary Tensor as Named Output

**Future Directional Change Radius**:
DOE and phase-only SLM remain local Elements; amplitude/polarization SLM needs
an explicit local Jones/intensity law. Thick Sample remains a deep Propagation
with hidden slices. Finite cavities add an authored finite Encounter sequence,
never recurrence. Characterized coatings replace response only behind the
qualified typed adapter; silicon-photonic devices may define a different small
Terminal algebra. Ray observational closure waits for a real Ray Detection.
Common/global-phase claims require heterodyne or external-reference Detection.
CUDA kernels remain private Numerical Support and never select physics.

**Assembly Freeze**:
The permanent transition from authored topology to executable topology.
Physical Parameters remain trainable; changing topology requires a new
Assembly.
_Avoid_: implicit freeze, unfreeze, execution-time topology mutation

**Assembly Check**:
Deterministic whole-path validation of topology, Optical Role, ports, and
Physical Value compatibility before field allocation. Its isolated-meta walk
and Workstation meta/real execution consume one private frozen fact and one
private replay implementation rather than mirrored traversals.
_Avoid_: device choice, resource policy, numerical-method substitution

**Assembly Error**:
The sole domain failure for invalid Assembly authoring, topology,
compatibility, or named outputs. One failure reports all discoverable defects
in physical reading order.
_Avoid_: diagnostic object hierarchy, issue registry, leaked implementation
exception

**Named Outputs**:
The ordered, populated mapping returned by Workstation Run from authored
output names to final Optical Field, Intensity, or Ray Bundle values. An
Assembly owns Authored Exposure names, not a pre-run Named Outputs value; a
physically non-consuming Authored Exposure on a topologically intermediate
output is honestly retained through run completion and counted in the
conservative Memory Estimate, so a non-consuming readout is not a hidden
zero-cost computation claim. Execution metadata is not a Named Output.
_Avoid_: arbitrary Tensor, generic result object, unnamed retained
intermediate, implicit output order, unpopulated output registry

## Workstation execution

**Workstation**:
The explicit local-computation owner for one CPU or one CUDA device and one
Memory Boundary. The numerical regime is fixed double (see Fixed Double); the
Workstation carries no precision selector. It never changes optical meaning or
selects a fallback. Windows permits one live CUDA Workstation per process;
Linux may hold independent Workstations for different local CUDA devices,
while every individual run remains on one device.
_Avoid_: Simulator, Runner, automatic device selection, scientific parameter

**Workstation Host**:
The exclusive placement of the complete module tree rooted at one
independent Optical Component or frozen Assembly before optimization or
execution. A tree is wholly unhosted or wholly owned by one Workstation;
hosting preserves trainable identity and rejects partial or foreign ownership.
Hosting moves device only; it never rewrites floating or complex dtype. A
fixed-double preflight rejects any `float32` or `complex64` registered state
(whole-module legacy checkpoint or manually mutated state) before device
movement. Ownership lives outside researcher modules through weak references.
The owning Workstation may explicitly release the exact hosted root without
moving its state, after which the root may be hosted again.
_Avoid_: implicit placement, partial hosting, copied ownership, hidden
instance tag, hosting an unfrozen Assembly, silent dtype promotion on host

**State Installation**:
The supported authored-state transition: applying a `state_dict` to a wholly
unhosted module root through the top-level `install_state(root, state_dict)`
before any host. Installation is unhosted-only and strict — it is not a host,
not a device move, and not an assign — and a fixed-double preflight plus
per-owner revalidation (dtype, shape, exact-alias partitions, Source schema,
Conic physical state) must complete before the state copy. The root stays
unhosted after installation, so the supported lifecycle is `install_state ->
host -> run`, with an explicit release before a reinstall. Source Lineage is
preserved and never transferred.
_Avoid_: hosted install, partial install, assign-based copy, install that
transfers Source Lineage, reinstall without a prior release

**Workstation Check**:
The deterministic decision that one valid frozen Assembly can execute on the
selected local device and Memory Boundary.
_Avoid_: optical validation, automatic tuning, fallback

**Workstation Run**:
The single replay boundary for a hosted module root. A module-level
calculation receives that root and values from an explicit `inputs(device)`
factory, or a frozen Assembly supplies the same replay through its authored
topology. Workstation validates ownership, runs the calculation on an isolated
meta root, rejects an infeasible conservative peak before real inputs exist,
and only then runs the same calculation on the selected device. Successful
real outputs become Named Outputs.
_Avoid_: closure-owned Module, callable object, runtime-created Module,
second runner, preflight real allocation outside bounded grid metadata

**Workstation Error**:
The sole domain failure for an unavailable device, a `float32`/`complex64`
state that violates Fixed Double, or a failed Memory Check. A runtime
out-of-memory failure remains the original PyTorch or CUDA failure.
_Avoid_: wrapped OOM, retry policy, device or numerical-regime fallback

**Memory Estimate**:
The conservative peak of the complete replay derived by the private execution
storage-lifetime tracer. Registered module state is counted once; input,
temporary, alias, cache, output, and autograd-saved storage share one weak
lifetime model. Meta inference deliberately cold-misses value-dependent
caches, so a warm real replay may use less memory; it may never exceed the
meta conservative peak. Output names, types, shapes, dtypes, and required
device placement remain isomorphic across both replays.
_Avoid_: Assembly-owned estimator, strongly retained temporary Tensor,
real peak above meta peak, allocator-workspace equality claim, automatic
batching

**Memory Check**:
The comparison of a Memory Estimate with the selected Workstation Memory
Boundary before the largest field allocation.
_Avoid_: problem resizing, scientific substitution, numerical-regime reduction

**Fixed Double**:
The single numerical regime: every public real floating quantity is
`torch.float64` and every public complex quantity is `torch.complex128`.
Integer counts, boolean state, and the `uint8` Ray Status retain their
physical dtype; the per-ray Optical Path and Tensor Optical Path Reference
lengths are `float64` accumulators on their current device, not a second
regime. Python real scalars materialize as `float64` and complex scalars as
`complex128`. Explicit `float32` or `complex64` public input is rejected,
never widened; user Parameters must already have the required dtype and retain
identity. `torch.get_default_dtype()` never changes product behaviour. The
former public `Precision` selector is removed, not deprecated: there is no
precision argument, no precision property, no `RunRecord.precision` field, no
compatibility alias, no one-option numerical-format field, no autocast mode,
and no fallback. A Workstation Host preflight rejects any `float32`/`complex64`
registered state before device movement; single-precision `state_dict`
rejection at project-state installation is owned by the top-level
`install_state(root, state_dict) -> None`, the strict fixed-double
unhosted-only checkpoint authority. `install_state` and `host` are the two
execution-seam lifecycle entries: `UNHOSTED --install_state--> UNHOSTED
--host--> HOSTED`. Source Lineage is preserved across installation, never
transferred.
_Avoid_: Component-chosen precision, hard-wired default, silent promotion or
reduction, decorative NumericalFormat field, autocast, mixed precision

**Run Randomness**:
One Workstation-owned root seed, defaulting to `42`, from which stable
Optical Component or calculation names derive independent device-local
streams without changing global random state. `Workstation.generator` exposes
the same explicit named derivation for research code. Meta and real replay
recreate separate generators from the same seed, so preflight never advances
the real stream.
_Avoid_: hidden Component seed, global random state, order-dependent stream

**Run Record**:
The immutable account of implementation, device, seed, relevant environment
facts, and Memory Check outcome emitted beside Named Outputs. It carries no
precision or decorative numerical-format field; the regime is Fixed Double
and recorded nowhere on the run record.
_Avoid_: optical payload, Published Result, evidence bundle, mandatory storage,
decorative precision field

**Meta Inference**:
Assembly first asks each Component owner to revalidate mutable physical state,
then evaluates the same Component `forward` methods on isolated `meta` copies
of the complete module tree through the sole private sandbox in
`optics/_meta_inference.py`. Root execution support reuses that sandbox from
above; optics never imports execution policy. Meta Inference derives Physical
Value shape, dtype, compatibility, and conservative tensor-memory demand
without creating a handwritten twin or mutating researcher-owned Components.
The sole exception is the Component-owned `_output_grid_for` phase: an
exception- and thread-local guard may evaluate single-element real grid
metadata so continuous coordinates remain exact. It rejects arrays and never
allocates field-scale storage.
_Avoid_: Field Description, `describe` twin, local-memory declaration,
preflight mutation, real field-scale allocation

## Scientific practice

**Unit System**:
All public physical numbers use SI: metres, radians, radians per metre, watts,
and watts per square metre; refractive index and relative amplitude are
dimensionless.
_Avoid_: mixed units, per-parameter unit suffix, runtime quantity wrapper

**Numerical Support**:
The private cohesive PyTorch tensor algorithms that implement optical
equations, sampling rules, masks, reductions, or multi-value mixing for
paired Optical Functions and Components. A numerical implementation never
chooses a different physical method, and a kernel with no production owner is
not Numerical Support.
_Avoid_: public kernel framework, Component-owned backend selection, utility
collection, one-line delegation invented only to satisfy a package boundary

**Chirp-Z Numerical Support**:
The private Chirp-Z Numerical Support is a separable, unnormalised Bluestein
transform used by `AplanaticFocus` to evaluate its fixed Fourier-type
Richards-Wolf integral on an authored uniform focal-plane Grid. It is not a
public propagation method, selector, or radial approximation. Direct angular
quadrature and Fourier-Bessel constructions remain independent test evidence,
not production implementations.
_Avoid_: public CZT utility, solver selector, automatic radial reduction

**Numerical Cache**:
Disposable derived state consumed by its owning Optical Component or Numerical
Support. Its identity contains every fixed physical input and device on which
it depends; trainable-dependent values are recomputed so
differentiation stays complete.
_Avoid_: Parameter-dependent cache, incomplete identity, persistent cache,
generic cache without a production consumer

**First-order Paraxial Ray-Transfer Optics**:
The independent paraxial qualification module and analytic reference supplied
by `optics/paraxial_ray_transfer.py`. It provides free-space, thin-lens, and spherical-
refraction ray-transfer matrices over the `(y, θ)` ray vector, plus a compose helper
for a sequential prescription. It is explicitly paraxial: it has no
`exact|paraxial` selector, consumes no Ray Bundle, Medium, or Spectrum, and
shares no numerical kernel with exact Ray tracing, so it cannot act as the
execution backend and is not called a geometric ray tracer. Exact Ray results
are checked against it only in the small-height, small-angle limit, where the
familiar focal and principal-plane behaviour anchors the nonparaxial
implementation.
_Avoid_: `exact|paraxial` selector, paraxial ray transfer as execution backend, paraxial ray transfer named as
a ray tracer, shared kernel with exact Ray tracing

**Component Evidence**:
The four test layers required before an Optical Component is public: physical
invariants, an independent analytic or numerical reference, gradient evidence
for every trainable claim, and consistency across the supported native
execution paths under Fixed Double.
_Avoid_: qualification runtime, assurance ledger, public unverified Component

**Example**:
A source-distributed executable system case that asks one physical question
using ordinary Optical Components or one Assembly, paired English and Chinese
documentation, exact scientific provenance, and an independently checkable
observable. Examples teach the researcher path, demonstrate end-to-end
composition, and provide unchanged inputs for optional performance measurement
without replacing Component Evidence. A linear path uses a hosted root and a
module-level calculation written one Component per physical line; Assembly is
the recommended form for branched, merged, or multi-output structures.
_Avoid_: notebook state, experiment runtime, production system class,
duplicated scientific validation, benchmark-specific optical path

**Optimization Workflow**:
An Example-owned PyTorch procedure that chooses trainable values, defines an
objective, applies an optimizer, and records its own history.
_Avoid_: inverse-problem runtime, project optimizer framework, graph-owned loss

**Release Descriptor**:
The sole non-Python resource containing release identity and compatibility
facts. Version text does not enter scientific source symbols or configuration.
