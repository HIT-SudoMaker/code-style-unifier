# Architecture

This is the single active architecture document for ChromatixNext. It draws
from `CONTEXT.md` (the authoritative domain language) and the active
optical-core hardening specification. It introduces no new decisions;
superseded governance lessons live in `docs/history.md`, and the durable
decisions live in `docs/adr/` (the frozen ADR set is enforced by the
architecture truth tests, so this document stays count-agnostic as that set
grows).

## Scope

ChromatixNext is an independent PyTorch optical-simulation system for local
workstations. The current release validates Windows; Linux remains an
architecture target until native checks exist. The product is one compact
optical core that can be read in physical order, assembled into checked
optical paths, hosted explicitly on a Workstation, differentiated through
ordinary PyTorch, and taught through plain executable Examples.

Workstation ownership is external to researcher modules and weakly held.
`host` claims one complete Component or frozen Assembly root; `release`
explicitly clears that exact claim without moving state. Windows permits one
live CUDA Workstation, while Linux is designed for independent device-local
Workstations without cross-device tensor splitting inside a run.

## Current-truth reading path

The active documentation has one scientific reading path. Read the production
seams here first, then follow the domain language in `CONTEXT.md` in this
order:

1. [Architecture and production seams](#three-production-seams)
2. [Physical Values](../CONTEXT.md#physical-values)
3. [Source](../CONTEXT.md#source)
4. [Element](../CONTEXT.md#elements)
5. [Propagation](../CONTEXT.md#propagation)
6. [Combination](../CONTEXT.md#combination)
7. [Detection](../CONTEXT.md#detection)
8. [Assembly](../CONTEXT.md#assembly)
9. [Workstation](../CONTEXT.md#workstation-execution)
10. [Numerical and testing evidence](#assurance)

Wave and Ray are separate physical accounts inside Source, Element and
Propagation. They coexist only as independent subgraphs at the Assembly
topology; no reading path or document implies a Wave--Ray conversion. The
architecture owns dependency direction, production seams and execution
lifecycle. `CONTEXT.md` owns domain definitions and applicability. ADRs retain
accepted decisions and visible supersession history. Source docstrings own
call-level Interface facts. No generated symbol catalogue is an active
chapter.

## Three production seams

The installed package contains exactly three production seams. No other
production layer exists.

### 1. Optical core — `chromatix_next/optics/`

The sole scientific base. It owns strong Physical Values, state-owning
Optical Components, stateless Optical Functions only where the pair contract
is complete, and one thin Assembly authoring layer. Physical Value modules
never depend on action modules; Functions and Components depend on Physical
Values.

```
chromatix_next/
  errors.py          # sole public failure owner
  optics/
    __init__.py        # exports: Assembly + Physical Values
    field.py           # field, path reference, normalization
    intensity.py       # Intensity
    grid.py            # SpatialGrid, PropagationExterior
    spectrum.py        # Spectrum
    medium.py          # vacuum, constant, tabulated, Sellmeier media
    polarization.py    # representation and normalized source state
    assembly.py        # Assembly: ordinary authoring plus finite directional Encounters and Route Ends
    _orthonormal_basis.py  # authored three-vector admission and basis facts
    _source_lifecycle.py   # shared Source state encoding and validation
    _role_contract.py  # private role/signature semantic authority
    source/            # Plane Wave, Gaussian Beam, Point Source, Collimated Ray Source in collimated_ray.py
    element/           # transmission, pupils, lens, retarder, directional Cube/Mirror owners, ray refraction/reflection
    propagation/       # scalar/vector/scaled spectrum, Fresnel, scaled Fresnel, aplanatic focus, ray trace
    surface/           # Plane, Sphere, Conic Even Asphere adapters
    combination/       # CoherentCombination, IntensityCombination
    detection/         # IntensityDetection
```

A new directory is justified only by a demonstrated scientific boundary that
cannot remain clear within this structure.

`_role_contract.py` is an internal deep module, not a fourth production seam
and not a public import. It is the sole owner of closed role and callable
signature validation used by both `Assembly.include` and `Workstation.host`.

Two other private optical owners remove repeated admission and state-writing
mechanics without introducing a public Pose or Source framework.
`_orthonormal_basis.py::_materialize_authored_three_vector` admits authored
Cartesian three-vectors for both Collimated Ray Source Pose and Surface Pose;
the two domains retain their own requirement wording and physical validation.
`_source_lifecycle.py::_encode_source_identity_fields` writes the common
Spectrum, Polarization, and Medium identity fields for all four Sources;
Source-specific state remains in each Source adapter. The direct public module
for `CollimatedRaySource` is `source/collimated_ray.py`; no forwarding
`source/collimated.py` module or compatibility import exists.
The direct qualified Cube-response numerical owner is
`_numerics/cube_response.py`; the removed lumped response module has no
forwarder or compatibility import.

The three Surface adapters `Plane`, `Sphere`, and `Conic Even Asphere` carry
the ray-geometric encounter (analytic forward root, certified signed
discriminant, or certified polynomial topology followed by safeguarded
device-local refinement). The Ray Propagation action is `TraceTo` (advances a Ray Bundle to a
posed Plane, Sphere, or Conic Even Asphere through the nearest forward
intersection), and the three Ray Element actions are `ReflectAt`, `RefractAt`
(at any of the three Surfaces), plus Plane-only `RetarderAt`. Each surface
Ray action advances active rays to the certified intersection, accumulates the
per-ray incident refractive index times geometric distance into the per-ray
Optical Path through one shared advance, and updates direction by vector
Snell or the law of reflection; the per-ray polarization direction is
transported under the ADR-0009 rules (Trace preserves it exactly, Reflection
applies the real Householder map component-wise, successful Refraction
applies the unique minimal proper rotation); power is unchanged because ideal
geometric interaction invents no Fresnel, coating, or polarization loss.

### 2. Private numerical support — `chromatix_next/_numerics/`

Private tensor algorithms used by Sources and by paired Optical Functions and
Components.
Every calculation has one PyTorch reference implementation; an optional
accelerated implementation must preserve the same physical and numerical
meaning. `_numerics` owns every substantive tensor equation, sampling rule,
mask synthesis, reduction, and multi-value mixing kernel. A cache belongs
there only when production calculation consumes it. It is private: no public
numerical framework, no Component-owned backend selection, no utilities
collection.

`_numerics/optical_path_reference.py` is the sole numerical owner of
device-local `float64` Optical Path Reference normalization, increment
accumulation, relative-reference expression, reference-carrier phase, and
complex-envelope addition in one destination reference. The numerical owner
accepts numerical values only and owns no Optical Field, Propagation Medium,
Source Lineage, or composition policy. Combination owns compatibility policy,
stable errors, and output construction; the numerical module owns only the
reference algebra and `sum_envelopes_in_optical_path_reference`.

`_numerics/intensity.py::sampled_field_power_amplitude` is the single
sampled-field POWER normalization owner used by Gaussian Beam and Point
Source. Their envelope equations, sampling policy, caches, and stable failures
remain Source-specific. `_numerics/cube_response.py` owns the private qualified
complex Cube response used by the directional Wave Encounter adapter. The Ray
Encounter adapter does not consume that complex response: it owns the distinct
real-power and polarization-projection law, including deterministic geometric
transport. This is deliberate Wave/Ray asymmetry, not a second Wave response
implementation or forwarding path.
The wave-propagation kernels live in the `_numerics/wave_propagation/`
subpackage (the scalar, vector, scaled, and scalable angular spectra, the
Fresnel transform and scaled Fresnel, chirp-z transform, spatial frequency,
radiative spectrum, and aplanatic focus), and the surface encounter owners
live in the `_numerics/surface_geometry/` subpackage (Plane, Sphere, Conic,
and the certified Conic roots); both expose no re-export surface, and the
physical Adapters import the exact leaf numerical Interface they consume.

Phase is cycles-only: every authored or runtime-variable numerical phasor is
built from a cycle count by the single `_unit_phasor_from_cycles` authority,
so no production kernel constructs or accepts a radian phase argument. An
exact algebraic coefficient fixed by an equation may use `0`, `1`, `-1`,
`1j`, or `-1j` directly as a literal; these literals are not a second phase
regime and do not authorize arbitrary runtime phasor construction. Topological sign decisions
(parallel/forward Plane encounter, Sphere discriminant and root, Conic
polynomial-asphere proof, aperture boundary, total internal reflection,
runtime Plane-local collinearity of the ray direction against the Plane
tangent axis, angular-spectrum support) delegate to certified exact-sign
predicates that return a proven `-1/0/+1` rather than an epsilon or
`isclose` approximation, while differentiable distance, intersection, and
optical path remain on the original trainable operands. Pose tangent
validity is two separate facts: authored Pose acceptance admits authored
unit and tangent vectors within the `8γ₃`
`AUTHORED_BASIS_ADMISSIBILITY_BUDGET` of `optics/_orthonormal_basis.py`,
and only the runtime Plane-local ray-direction-versus-tangent-axis
collinearity is decided by the certified exact-sign determinants of
`_numerics/ray_polarization.py`.

Implemented SSRHM deepening (ADR-0014) retains `conic_encounter` as the sole
Conic numerical Interface. Private named geometry facts feed either the
analytic base-conic owner or the certified polynomial owner; the existing
Fraction/Sturm proof bridge certifies polynomial root topology, and
device-local refinement constructs the differentiable encounter. The public
Conic Even Asphere remains a passive Surface adapter and exposes no solver
choice.

### 3. Execution seam — `chromatix_next/workstation.py`

The single public execution seam that owns platform and device selection,
memory-boundary policy and comparison, placement decisions, run randomness,
execution, Named Outputs, and Run Record. It is the only seam
that selects CPU or one CUDA device, and the only owner of run randomness.
The numerical regime is fixed double (`torch.float64` real / `torch.complex128`
complex, see ADR-0005); there is no precision selector, no `Simulator`, no
`Runner`, no automatic target selection, no device fallback, and no mandatory
configuration file.

Two private modules sit at the top-level execution boundary as cohesive support.
`_execution_memory.py` owns physical-capacity discovery, default boundary
facts, tensor-storage lifetimes across meta and real replay, and conservative
peak derivation. Workstation selects or accepts the boundary and compares the
derived peak with it; it does not duplicate operating-system memory facts.
`_ownership.py` is the second private root support: it owns the
host-ownership registry, weak references, locks, the Windows CUDA singleton,
claim/release/assert operations, and the atomic preflight-placement-commit
protocol that places a module tree and registers its claim as one transaction.
Workstation owns platform, device, and fixed-double preflight policy and
describes how a module tree is placed; `_ownership.py` owns registry state and
the transactional ordering of preflight, placement, and commit, and its locks
never leak across the seam. A failed placement leaves no registered claim,
because placement runs inside the ownership transaction before the claim is
recorded. Neither module is a fourth public seam.

## Canonical public imports

Public import paths follow the one-way dependency stated fully under
"One-way dependency" below. The top-level package exposes only `Workstation` and `install_state`;
Physical Values and `Assembly` come from `chromatix_next.optics`; every
Component comes from its singular role package.

```python
from chromatix_next import Workstation
from chromatix_next.optics import (
    Assembly,
    Intensity,
    OpticalField,
    SpatialGrid,
    Spectrum,
    ...
)
from chromatix_next.optics.detection import IntensityDetection, intensity_detection
from chromatix_next.optics.source import PlaneWave
from chromatix_next.optics.element import IdealThinLens, ideal_thin_lens
from chromatix_next.optics.propagation import ScalarAngularSpectrum, scalar_angular_spectrum
from chromatix_next.optics.propagation import VectorAngularSpectrum, vector_angular_spectrum
from chromatix_next.optics.propagation import AplanaticFocus, aplanatic_focus
from chromatix_next.optics.combination import (
    CoherentCombination,
    coherent_combination,
)
from chromatix_next.optics.element import (
    IdealNonpolarizingCubeBeamSplitter,
    IdealPlanarMirror,
    IdealPolarizingCubeBeamSplitter,
    Retarder,
)
```

There is no duplicate re-export, no `import *` module, no public registry,
and no dynamic name lookup. The cognitive order in which a reader meets
these concepts is owned by `CONTEXT.md`, not by this section; this section
owns only the dependency-direction mapping from public names to modules.

## One-way dependency

The only allowed dependency direction is:

```
workstation.py  ->  optics  ->  _numerics
```

- `_numerics` imports nothing from `optics` or `workstation`.
- `optics` imports nothing from `workstation`.
- `workstation.py` may import from both, as the top of the chain.

Physical meaning therefore stays independent of devices, memory, and release
workflow. Tests, Examples, and release tooling may consume the production
package; production modules never import them.

Frequency-transfer propagation shares one private numerical sequence:
transform the final two spatial axes, apply one per-spectrum transfer, and
transform back. That sequence requires the fixed-double pair and one device,
while each propagation method still owns its transfer, exterior, padding,
crop, and output grid. Grid-changing transform methods such as Fresnel
transform, scaled angular spectrum, and scaled Fresnel keep a separate
numerical shape instead of entering this sequence through exceptions.

`ScalarAngularSpectrum.diagnose(field)` is a pure, optional query over the same
prepared transfer used by propagation. It reports retained input power and
surviving frequency count without storing a last result, changing the
propagation return type, or entering Assembly and Workstation execution.

## Physical Value invariants

Physical Value 定义——Optical Field 轴序、Optical Path Reference、Spectrum、
Polarization State、Unit System、Fixed Double、Field Normalization、Propagation
Medium——以 `CONTEXT.md` 为唯一权威。本文档只重述其架构后果：Physical Value
模块绝不依赖 action 模块；每个公开 Physical Value 在其归属接口拒绝非有限态，
并按 ADR-0005 固定双精度拒绝非 float64/complex128 的物理 dtype；
hosting 把整棵模块树迁到目标设备（不改写 dtype，固定双精度由预检承担）。
定义性内容（轴布局、SI 单位、Jones 约定、路径参考载波公式等）不在本文件复述，
以免与 `CONTEXT.md` 漂移。

## Component state

A user-supplied `torch.nn.Parameter` remains the registered trainable
Parameter; an ordinary tensor or number becomes a fixed Buffer; derived caches
are non-persistent Buffers. Components preserve Parameter identity. Examples
select optimization values through `Assembly.named_parameters()`. A Component
is never copied, never given a `trainable` flag, and never wrapped in a
project optimizer value.

Each role package owns one small structural Protocol. Every Component declares
exactly one immutable Optical Role. One private semantic authority supplies
both the public Protocol adapters and Assembly validation when the Component is
included. There is no universal Component base; shared numerical behaviour is
private composition, not inheritance.

A private Field Transformation constructs every derived Optical Field. It
inherits unchanged spectral, polarization, medium, normalization, and Source
Lineage meaning while requiring Grid and Optical Path Reference changes to be
named explicitly by the calling Component.

Each Source owns one private Source Lineage. Repeated calls to the same Source
preserve that identity; independent construction or copying creates a new
identity. Source therefore has no stateless paired Function, no public lineage
parameter, and no lineage registry.

The four Sources (`PlaneWave`, `GaussianBeam`, `PointSource`,
`CollimatedRaySource`) share one private `_LifecycleSource` owner for the four
PyTorch lifecycle operations (`get_extra_state`, `set_extra_state`, `__copy__`,
`__deepcopy__`). The three sampled Wave Sources additionally use the restricted
private `_SampledWaveSource` owner accepted by ADR-0014. It coordinates only
the shared mechanical reading order: validation and normalization dispatch,
single-slot unit-envelope caching, fixed-double Optical Field construction,
and Source Lineage preservation. `CollimatedRaySource` remains on the generic
lifecycle owner alone. Every concrete Source retains its physics,
normalization kernel, sampling and applicability, cache-key facts, authored
state, stable failures, and Parameter and Buffer identities. Neither private
owner is exported; there is no universal Source framework, shared physical
equation, config object, descriptor DSL, registry, or error unification.

Each Source owns one local closed stateless capsule that defines its exact
extra-state schema, Source-specific stable error identities, structure and
physical-buffer-projection validation, variable-spectrum resize preparation,
derived-envelope cache invalidation, and fresh Source Lineage reconstruction on
copy. The capsule exposes exactly one private pure planning function
(`_plan_<source>_state_installation`); given the concrete Source and a candidate
checkpoint state, the function validates schema, structure, projection, and
resize request, and returns one frozen local plan of validated metadata plus
Buffer names/shapes to stage. The planning function does not allocate, resize,
mutate the cache, change lineage, or perform native load. Installing state into
an existing Source preserves that target Source's Lineage; checkpoint state
never transfers it. Copy creates fresh Source Lineage. This closed four-function
bridge is consumed by the public top-level `install_state(root, state_dict)`
function: the private `_state_installation.py` owns the closed
`_plan_state_installation -> _StateInstallationPlan` full-tree seam, dispatches
to the four Source planners plus the Conic-owner
`_validate_conic_state_installation` by exact type, and runs the 14-step
critical section inside `_ownership._run_unhosted_state_installation`, ending in
the single unbound `torch.nn.Module.load_state_dict(..., strict=True,
assign=False)`. `install_state` is unhosted-only and strict; the four Source
leaf-load hooks are retired. This is private root support, not a fourth seam:
`optics` and `_numerics` never import `_state_installation`. The supported
lifecycle is therefore `install_state -> host -> run`, all on one Workstation;
because a host claim is exclusive, a root must be explicitly released before
it can be installed or hosted again, and installation never serves as a host
or device move.

## Composition

The primary scientist-facing expression is direct calls in physical reading
order: a paired stateless Function, where exported, for a one-off
calculation, or the Component when state, training, reuse, or Assembly
membership is required. The complete optical structure is one `Assembly`.
Its ordinary authoring surface remains source compatible:

- `include` registers one Component under a unique stable semantic name.
- `connect` declares Physical Value flow and names ports only when the
  connection is ambiguous. It validates source and destination membership,
  port tokens, declared ports, Physical Value compatibility, source-output
  occupancy, and destination-input occupancy before appending the connection,
  so a rejected connection leaves the prior valid authored state unchanged.
- `expose` assigns one non-consuming user-facing name (an Authored Exposure)
  to one computed Physical Value output that becomes a final Named Output.

Finite directional routes extend that same Assembly authoring surface without
replacing the ordinary operations:

- `include_directional` registers one of the three state-only Cube/Mirror
  owners exactly once;
- `wave_encounter` or `ray_encounter` issues a state-free finite Encounter
  reference to that registered owner;
- the existing `connect` and `expose` use Ports for Component endpoints and
  explicit physical Terminals for Encounter endpoints;
- `end_route` records a Route End for an outgoing Terminal that leaves the
  modeled system.

Routes remain finite and acyclic. An owner reused by several named Encounters
still appears once in the registered module tree; Assembly does not infer
passes, recurrence, or a convergence policy.

Assembly retains authored exposures and their order, but does not construct a
pre-run result object. Populated Named Outputs are created only after a
successful Workstation Run. An Authored Exposure is not an Optical Role, not a
splitter, not a Detection, not a sensor, not a tap, and not a loss; it may name
a topologically intermediate output and may coexist with one downstream
connection on the same output, while remaining physically non-consuming. A
physically non-consuming intermediate exposure is honestly retained through run
completion and counted in the conservative Memory Estimate, so a non-consuming
readout is not a hidden zero-cost computation claim. One stable
Component-output anchor has at most one Authored Exposure; Detection remains
the only Wave role that derives Intensity.

`freeze()` first performs Assembly Check, then permanently locks topology
without freezing Parameter or Buffer values. `check()` succeeds with `None` or
raises one `AssemblyError` that reports all discovered problems in physical
reading order. There is no public Graph, Node, Builder, or port-reference
wrapper; no universal Component base class; and no inheritance family.

Topology traversal, coherent-compatibility aggregation, execution ordering,
and memory traversal remain private implementation. Ordinary authoring keeps
`include`, `connect`, `expose`, `check`, and `freeze`; directional authoring
adds only `include_directional`, `wave_encounter`, `ray_encounter`, Terminal-
aware use of the existing connection/exposure operations, and `end_route`.

The researcher cognitive order (ADR-0011, owned here as the active refinement
of the higher lifecycle below) is:

```text
include -> connect -> expose -> check/freeze -> host -> run -> Named Outputs
```

and the validation order frozen by ADR-0011 is:

```text
author-operation atomicity
-> base topology closure
-> exposed-path reachability
-> immutable frozen facts
-> isolated meta replay and Memory Check
-> real replay and Named Outputs
```

Author-time feedback delegates to the same private topology predicates that
`check` and `freeze` use, so early feedback cannot drift from final validation;
exposed-path reachability is computed only after base topology validation has
succeeded. This is a refinement of, not a competitor to, the higher
researcher lifecycle preserved verbatim under "Execution" below.

One Assembly may contain independent Wave and Ray subgraphs (ADR-0007):
Wave Sources, Elements, Propagations, Combinations, and Detections consume
and produce `OpticalField` or `Intensity`, while Ray-producing Sources,
`TraceTo`, and the three Ray Elements (`ReflectAt`, `RefractAt`, `RetarderAt`)
consume and
produce `RayBundle`. Wave-only, Ray-only, and mixed-independent Assemblies all
check, freeze, host, and run through the ordinary-preserving extended
authoring grammar and the
single private replay implementation. A direct Wave-to-Ray or Ray-to-Wave
connection is rejected at authoring time in both directions; no converter
exists, because this initiative admits structural coexistence, not physical
unification.

## Propagation geometry

One destination `SpatialGrid` expresses scale, shift, and orientation. It does
not select a propagation method. `ScalarAngularSpectrum` executes only destination
geometry and sampling supported by its scalar Helmholtz implementation and
rejects unsupported scale or orientation before expensive calculation. Future
scaled or transformed methods reuse the same destination geometry interface;
no method silently substitutes another.

`SpatialGrid` keeps structural sample counts and zero-dimensional real Tensor
pairs for sample spacing and first-sample position. A centered grid stores only
independent spacing and derives its origin on every read, so trainable spacing
does not retain a stale graph. Module-owned grids enter ordinary PyTorch
Parameter/Buffer lifecycle through one private state adapter; this does not
create a second public grid type. Coordinate compatibility always uses the
explicit physical-equivalence operation, never generated dataclass equality.

The differentiable Optical Path Reference semantics are owned by `CONTEXT.md`
as the current domain term, with the decision rationale recorded in ADR-0002.
The architectural consequence is one numerical owner and one propagation
writer. `optics/propagation/_field_state.py` is the sole writer for Scalar and
Vector Angular Spectrum, Fresnel Transform, and Aplanatic Focus reference
advances. It evaluates reference-side wavelengths and refractive responses
directly in `float64`, then delegates accumulation to
`_numerics/optical_path_reference.py`. Optical Path Modulation delegates its
uniform baseline to that same numerical owner. Aplanatic Focus therefore keeps its
axial carrier contribution in the autograd graph. Destination translation and
Propagation Exterior do not write the reference, and no second accumulation
or alignment implementation exists.

`FresnelTransform` is the distinct single-transform paraxial method. It accepts
one spectral component and derives its centered output Grid from wavelength,
Medium, signed distance, sample counts, and input spacing. Its direct execution
and Assembly grid precheck call the same resolver. The private transform uses
the shared centered orthogonal FFT and quadratic-phase numerical support; it
preserves integrated power and keeps the signed-distance gradient.

`ScaledAngularSpectrum` and `scaled_angular_spectrum` are the scalar radiative
angular-spectrum actions for a parallel destination Grid whose sample counts,
spacing, first-sample position, and orientation are all authored and may differ
from the source. The inverse discrete-Fourier sum is evaluated at the authored
destination positions by a separable Bluestein chirp-z, so the method is
physically distinct from `ScalarAngularSpectrum`, which permits translation
only and crops a centred IFFT. Evanescent and alias support come from the
single radiative-spectrum owner; the isolated-footprint, narrow-alias-band, and
orientation-mismatch failures are stable identities, never method substitution.

`ScaledFresnel` and `scaled_fresnel` are the paraxial Collins/Fresnel
actions for a destination Grid that may carry magnification; magnification is
expressed by destination geometry and signed axial distance together, with no
independent magnification parameter. Its transfer kernel is the input and
output quadratic phase chirp, not the Helmholtz `exp(i k_z d)` kernel, so it
has no evanescent branch and shares no equation with `ScaledAngularSpectrum`.
A non-isolated footprint, paraxial chirp beyond the sampling Nyquist,
orientation mismatch, or zero axial distance fails with a stable identity;
negative distance propagates backward by a conjugate flip. The name states
the equation (Fresnel) and the destination geometry (Scaled) and replaces the
earlier Collins-as-scalable-spectrum wording, which was a misnomer.

`ScalableAngularSpectrum` and `scalable_angular_spectrum` are the genuine
scalable angular-spectrum (SAS) actions. The method applies the SAS
precompensation — the ratio of the exact angular-spectrum residual transfer
`exp(i (k_z − k) d)` to the conjugate of the paraxial Fresnel residual
transfer `exp(+i d (k_x² + k_y²)/(2k))`, equal to
`exp(i k d [√(1 − s²) − (1 − s²/2)])` — in the Fourier domain, then runs
the paraxial Collins/Fresnel stage of `ScaledFresnel` on the precompensated
envelope. The precompensation transfer and its residual alias support are
owned by the SAS numerical owner
`_numerics/wave_propagation/scalable_angular_spectrum.py`,
which reuses the radiative wave-number facts but band-limits the residual
phase transverse derivative `d (s_a/s_z - s_a)` per axis as a SAS-specific
support distinct from the standard-AS displaced support; the radiative
(evanescent) support still comes from the single radiative-spectrum owner.
The paraxial stage
reuses the same computational-window and chirp-z infrastructure as
`ScaledFresnel` without sharing its kernel equation. Applicability is
scalar, homogeneous-medium, paraxial-scaling, and sampling-bounded: the SAS
correction equals the exact transfer only on the radiative and alias
support band, and the destination magnification is carried by the paraxial
Collins stage, so the correction stays small only while that stage itself
stays paraxial. The method is therefore a propagation with stated
approximations, not an exact solver. Negative distance propagates by the
forward order with a signed-distance precompensation transfer
(`p(d<0) = conj(p(|d|))`) and the `scaled_fresnel` conjugate flip; the
same-grid round trip is the SAS-correction paraxial approximation of an
exact inverse, not a bit-exact inverse, because the SAS literature's strict
inverse order is defined only for same-source-and-destination geometry. A
narrow precompensation band, a paraxial chirp beyond the sampling Nyquist,
a non-isolated footprint, an orientation mismatch, or a zero axial distance
each fails with a stable identity, never substitution by another method.

`Retarder` is an Element, not propagation policy. It is the ideal zero-mean
SU(2) transverse polarization transformer: spatially uniform, achromatic, and
transverse-only (scalar and full-vector representations are rejected). Its
physical parameters are `retardance_cycles` (differential phase in cycles, not
radians), `retarded_eigenstate_azimuth_radians`, and
`retarded_eigenstate_ellipticity_radians`; the retarded eigenstate receives
the positive half of the authored differential phase and its orthogonal
eigenstate receives the negative half, so zero retardance is exactly the
identity. The Field retains only Polarization Representation; transformed
Jones components remain solely in the envelope.

Implemented numerical correction (ADR-0013) leaves the architecture and action
inventory unchanged. One private device-local binary64 integer-limb owner
resolves ambiguous topology signs from original operands. Its ordinary fast
certificate covers relative rounding and gradual underflow with one mechanical,
device-local bound helper; operation counts and underflow amplification remain
local facts of the five existing predicate graphs. Only a rounded sign strictly
outside the outward-rounded bound is accepted, while invalid or nonfinite
certificate inputs take the exact path. Plane consumes exact
dot signs for topology but retains one ordinary continuous value path and
explicitly rejects active unrepresentable distance. Plane-local polarized-Ray
actions derive one immutable frame fact from exact collinearity, an
operation-derived projection error bound, and scale-first normalization, then
own distinct geometric and representation failures. No host
exactness fallback, epsilon repair, arbitrary reference axis, public framework,
or parallel test architecture was added.

The completed behavioural basis contains twenty-four Optical Component actions:
four Sources, nine Elements (six Wave Elements and three Ray Elements:
`ReflectAt`, `RefractAt`, and Plane-local `RetarderAt`), eight Propagations,
two Combinations, and one Wave Detection. Separate public inventories contain
three state-only directional owners, three closed Terminal/diagonal enums, and
two Assembly-issued Encounter reference types (see ADR-0008 for
the Wave polarization-basis derivation and ADR-0009 for the implemented
polarized-Ray foundation: the mandatory per-ray `polarization_vector`, the
explicit transverse Source polarization, the polarization-preserving
transport across `TraceTo` / `ReflectAt` / `RefractAt`, and Plane-local
`RetarderAt`). The strict binary64 `RayBundle`
admissibility budgets and exact-preservation contract are owned by ADR-0010.
ADR-0013 owns the corrected exact Plane-local topology classification and the
certified continuous-projection representation boundary; this document does
not duplicate either decision's frozen formula table.

`VectorAngularSpectrum` is the radiative vector Helmholtz action between
parallel planes. Its paired Function is `vector_angular_spectrum`. It accepts
TRANSVERSE or physically transverse FULL relative fields, reconstructs or
propagates explicit `(Ex, Ey, Ez)` content, removes evanescent and grazing
support without division, and rejects scalar or POWER fields. Its supported
gradients are the input envelope and signed axial distance; hard support,
Medium, and Grid geometry remain fixed.

`AplanaticFocus` and `aplanatic_focus` map one sampled transverse exit pupil
through an ideal energy-preserving aplanatic objective to one authored focal
plane. The output is a FULL relative Optical Field. Medium dispersion
determines wavelength-resolved numerical aperture, while fixed objective
geometry and hard sample-centred pupil support delimit applicability.
The production CZT is one private separable Bluestein calculation under
`_numerics`; it never becomes a public method selector. Independent
direct angular quadrature and Fourier-Bessel constructions are test evidence,
not alternative production paths. The fixed-double numerical regime and
available Windows CUDA run the same PyTorch equations. Linux execution remains
unqualified and is not represented by a skipped result.

`paraxial_ray_transfer` is a separate first-order qualification Module, not a
Propagation action or exact-Ray backend. Its complete public vocabulary names
ray-transfer matrices directly; the historical `abcd` module and abbreviated
callables are absent without compatibility aliases. The Module shares no
numerical kernel with Ray actions and appears in scientific evidence only as an
independent small-height, small-angle reference (ADR-0016).

## Execution

`Workstation.cpu()` / `Workstation.cuda(device_index)` are the only creation
interfaces. They select CPU or one CUDA device and require no numerical-regime
argument (the regime is fixed double, ADR-0005); direct device construction is
not supported.

- `host(component_or_assembly)` places one independent Component or one frozen
  Assembly once, before optimizer creation. A read-only ownership preflight
  first validates the complete module tree; a fixed-double preflight then
  rejects any `float32`/`complex64` registered state before device movement;
  only a wholly unhosted tree is then moved and claimed atomically. Hosting
  preserves Parameter identity and moves device only (it never rewrites
  floating or complex dtype), is idempotent only for the same complete root,
  rejects partial or foreign ownership without mutation, and never writes
  ownership into `state_dict`.
- `check(assembly)` runs after Assembly Check and combines device and
  conservative peak-memory feasibility.
- `run(...) -> (NamedOutputs, RunRecord)` is the sole replay boundary. It
  accepts either a frozen Assembly or one explicitly hosted module-level
  calculation with a replayable input factory. Both request forms use the
  same Meta preflight, memory check, real replay, Named Outputs, and immutable
  Run Record path.

The highest researcher seam remains:

```text
construct -> freeze -> host -> run -> Named Outputs + Run Record
```

For a direct module-level calculation, freeze is inapplicable rather than a
second runtime; hosting and running still use the same Workstation seam.

The numerical regime is fixed double: floating Module state is `torch.float64`
and complex Module state is `torch.complex128`, including Field Envelopes,
Intensity values, Spatial Grid tensors, and Ray Bundle real state. Dynamic
Tensor Optical Path References and per-ray Optical Path remain `float64` on the
same execution device; under fixed double this is the same regime, not a
second one, and Workstation validates dtype placement in both replay paths.
`RunRecord` carries no precision or decorative numerical-format field.

Run randomness is Workstation-owned, defaults to seed `42`, uses local
generators without changing global random state, and derives independent
streams from stable Component names. An unexpected out-of-memory error passes
through unchanged: no retry, no device/regime/science change, no fallback.
`chromatix_next.errors` is the sole public owner of the six-name failure
hierarchy:

```text
OpticalError
  -> OpticalTypeError
  -> OpticalValueError
  -> OpticalRuntimeError
  -> AssemblyError
  -> WorkstationError
```

`AssemblyError` and `WorkstationError` are the two boundary-specific failures:
the first owns invalid Assembly authoring, topology, compatibility, or named
outputs; the second owns unavailable platform, device, fixed-double preflight
violation, or failed Memory Check. They do not replace the three physical type/value/runtime
specializations or their common `OpticalError` base.

The same isolated meta execution traces public PyTorch factory results,
operator inputs and results, and final Physical Value tensor-storage
lifetimes; no Component declares a second memory model. A factory allocation
is recorded even when a Component reads only its structure and discards it
before another operator can consume it. Explicit real-device requests are
rejected before the factory is invoked, so preflight itself cannot allocate
CPU or CUDA storage.
Component-owned Parameter and Buffer storage is excluded from the dynamic trace
and added once. Allocations live through their Component call; final values
follow Assembly release facts, derived caches live through the run, and
gradient-enabled calls conservatively retain each Component allocation with its
outputs. The estimate is deterministic and independent of Python garbage
collection. Workstation only compares it with its device boundary.

## Native acceleration

PyTorch is the sole implementation on CPU and CUDA. No public
native-acceleration selector exists until a complete, useful Assembly slice
has independently qualified native kernels. When a second implementation is
admitted, its public choice must remain explicit, scientifically equivalent,
recorded, and free of silent partial fallback. One-option selectors,
hypothetical backend seams, and per-Component backend choice are excluded.

## Research workflows and Examples

Optimization, loss, iteration history, and optimizer selection belong only to
Examples. There is no project optimization framework or default optimizer.
Each Example is one executable program with paired English and Chinese
documentation and exact scientific provenance. Examples are the only project
form for teaching, experimental demonstration, optimization workflows, and
capability display; they add no experiment runtime role.

## Assurance

Repository checks mirror optics, numerical support, workstation execution, and
Examples through ordinary pytest modules with independently justified
references. Every public Component requires four evidence layers: physical
invariants, an independent analytic or numerical reference, gradient evidence
for every trainable claim, and consistency under the fixed-double regime
across any native CUDA path. Small traceable reference data stays beside its
test.

The architecture Harness contains thirteen claim-owner tests, two shared
mechanical fact modules (import facts and symbol facts), and its empty
package marker:

```text
tests/architecture/
  _python_import_facts.py
  _python_symbol_facts.py
  test_assembly_topology_ownership.py
  test_csu_source_structure.py
  test_dependency_ownership.py
  test_domain_failure_language.py
  test_execution_memory_ownership.py
  test_function_component_role_contract.py
  test_numerical_fact_ownership.py
  test_phase_authority.py
  test_physical_tensor_execution_boundary.py
  test_production_naming_policy.py
  test_python_import_facts.py
  test_python_symbol_facts.py
  test_scientific_evidence_independence.py
  __init__.py
```

The shared import-facts and symbol-facts modules own only fail-closed
mechanical Python import and symbol facts; each consumer owns its domain
policy. Physical laws, public behavior, and
independent oracles remain with their physical or package owners rather than
being restated as architecture shape. Exact-sign evidence is partitioned by
tested interface into `test_exact_binary64_sign.py`,
`test_binary_rounding_certificate.py`, and
`test_public_certified_predicates.py`; the exact core and public predicates do
not share an expected-result oracle. Durable story names state the fact under
test: `test_householder_reflection.py`, `test_source_state_lifecycle.py`, and
`test_source_polarization_state.py`. Temporary transition narratives and
retired private paths are not Harness owners.

The authoritative formatting and architecture command is the repository CSU
checker, followed from the repository root by:

```text
python -m isort --check-only src tests tools setup.py \
  --skip tests/package_contract/test_examples.py
```

The explicit inventory covers project-owned production, test, tool, and setup
Python while preserving the frozen Example boundary. CSU does not own import
ordering; isort is its sole authority. Black is not used. Pyright is the
independent static type gate.

### Source prose ownership

CSU treats documentation as an Interface boundary rather than as decorative
text. Every symbol reached through an active `__all__` path owns an AST-local
docstring. The docstring identifies the physical meaning of every constructor
or callable argument, the returned physical value, and the stable failure
conditions. Type annotations own Python types; docstrings do not repeat them.
Function/Module pairs split responsibility: the Function documents the
physical calculation, while the Module adapter documents authored state and
invocation semantics.

Implementation prose uses standalone single-line comments without terminal
sentence punctuation. Durable private classes that own long-lived state,
facts, or transaction meaning retain one concise class docstring; incidental
private classes need not acquire one, and private functions do not acquire
docstrings. Modules do not begin with comment dossiers, and long derivations
or ownership narratives do not remain embedded in the execution path. Durable scientific definitions
and applicability statements belong to the ordered chapters in `CONTEXT.md`;
architecture ownership and execution boundaries belong here; accepted
decisions belong in `docs/adr/`; and independent numerical, scientific and
lifecycle evidence belongs beside the owning test or in the retained
research note that explains its physical question. The source file and test
name remain selective indexes, never the reading order.

The former mechanically generated implementation and testing ledgers were
removed. Their unique content has these dispositions:

- numerical derivations and conditioning remain in the relevant retained
  research notes and accepted ADRs, while repeated symbol-level entries were
  redundant with the numerical owners and are not active prose;
- optical Interface facts remain in AST-local public docstrings and the
  `CONTEXT.md` domain chapters, while generated concatenations were redundant;
- tool ownership remains in this document's Assurance section and the CSU
  gate, while helper inventories were implementation detail;
- architecture, lifecycle and scientific evidence remain with the claim-owner
  tests and the architecture, Assembly and Workstation chapters, while the
  old evidence ledgers were mechanical indexes rather than independent
  evidence.

Source and test files retain only a short local pointer when a maintainer must
know that a non-obvious proof exists. Test names, parameters, and assertions
remain the executable owners of claims. CSU rejects missing local Interface
sections, generated or inherited docstring substitutes, sentence-style
comments, multiline comment blocks, and leading test prose.

## Product boundaries

The installed wheel contains only `chromatix_next`, its required Python
metadata, and `release.toml`. The source distribution additionally contains
the complete Example tutorial, paired documentation, workstation inputs, and
provenance. Tests and repository tools remain development assets. Release
identity lives in the Release Descriptor and human release metadata, never in
scientific source symbols.

## Completion gates

The refactor is complete only when:

- Production source contains the accepted `optics`, `_numerics`, and
  `workstation.py` seams with one-way, cycle-free dependencies and no
  legacy compatibility surface.
- CSU reports zero hard violations and zero unadjudicated items under review.
  Review-only findings are acceptable only when the project gate records an
  explicit owner, rationale, and blocking decision that is exercised by an
  architecture test; raw findings remain visible in the CSU evidence. The
  exact project isort command above, Pyright, pytest, package installation,
  and Example smoke checks pass.
- Production growth is governed by hard interface budgets — two top-level
  public exports (`Workstation`, `install_state`), twenty-four public Optical
  Component actions, three directional owners, three closed enums, two
  Encounter references, three
  production seams (`workstation.py -> optics -> _numerics`), one dependency
  direction, no cycle, and no new public framework — not by a numeric
  line-count target. Deterministic production physical-line movement is
  measured and reported; any net increase requires independent
  Depth/Leverage/Locality and deletion-test review. No correctness,
  performance, or simplicity inference is made from LOC alone.
  In compact form: twenty-four public Optical Component actions remain.
- Every public Component satisfies Component Evidence under the fixed-double
  regime and any claimed CUDA acceleration.
- Assembly meta preflight and real execution agree, and invalid physics,
  sampling, non-finite values, memory, or method applicability fail at the
  owning interface.
- Windows CPU and available CUDA execution are required release evidence;
  Linux remains an architecture target until it passes on a native Linux
  environment.
- All compatibility copies, temporary transition evidence, and superseded
  evidence are removed.

## Active documentation set

The active documentation is exactly:

- `CONTEXT.md` — authoritative domain language.
- `MISSION.md` — the mission in the three-boundary language.
- `docs/architecture.md` — this document.
- `docs/history.md` — superseded governance lessons, compressed.
- `docs/adr/0001-one-pytorch-optical-core.md`
- `docs/adr/0002-component-and-assembly-composition.md`
- `docs/adr/0003-optics-numerics-workstation-boundary.md`
- `docs/adr/0004-example-owned-research-workflows.md`
- `docs/adr/0005-fixed-double-scientific-core.md`
- `docs/adr/0006-state-installation-and-immutable-hosting.md`
- `docs/adr/0007-mixed-independent-wave-ray-assembly.md`
- `docs/adr/0008-active-polarization-foundation.md`
- `docs/adr/0009-polarized-ray-foundation.md` (implemented present truth:
  the mandatory per-ray `polarization_vector`, the explicit transverse Source
  polarization, the polarization-preserving transport across `TraceTo` /
  `ReflectAt` / `RefractAt`, and Plane-local `RetarderAt` are the installed Ray
  Component foundation; directional devices execute only as finite Encounters)
- `docs/adr/0010-exact-polarized-ray-admissibility-and-closure.md`
  (Accepted — implemented present truth: the frozen binary64 per-Ray
  admissibility budgets and exact-preservation contract have landed in
  production. Its exact-sign fallback and Plane-local degeneracy calculation
  are narrowly corrected by implemented ADR-0013. Partially supersedes
  only the numerical-admissibility and exact-preservation details of
  ADR-0009; the polarized-Ray domain decision, the implemented twenty-four-action
  inventory, the two top-level public exports, and the three production seams are
  unchanged. ADR-0009's qualitative numerical wording is bannered there as the
  displaced historical record.)
- `docs/adr/0011-assembly-topology-contract.md`
  (Accepted — implemented present truth: the Assembly topology contract — the
  typed acyclic multi-source DAG shape, atomic `connect`, one-name Authored
  Exposure per stable Component-output anchor, and exposed-path reachability —
  has landed in production. Adds no optical capability and no new public
  surface; preserves the twenty-four public actions, the two top-level public exports, the
  `construct -> freeze -> host -> run` lifecycle, and the one-way dependency
  direction. The older "final Physical Value only" wording in ADR-0002 and the
  "final Physical Values" memory category in ADR-0003 are narrowed by visible
  partial-supersession banners there, not silently rewritten.)
- `docs/adr/0012-sonnet-combination-and-evidence-contract.md`
  (Accepted — implemented present truth: Physical-Value-specific Combination
  language, paired cognitive order, and replace-don't-layer evidence.)
- `docs/adr/0013-ssrhm-exact-topology-and-plane-local-correction.md`
  (Accepted — implemented present truth: corrects only the ambiguous-lane exact
  predicate fallback and Plane-local projection-degeneracy calculation; no
  public capability, action inventory, or dependency boundary changes.)
- `docs/adr/0014-ssrhm-conic-and-sampled-wave-deepening.md`
  (Accepted — implemented present truth: deepens the sole Certified Conic
  Encounter behind its passive Surface adapter, then gives the three sampled
  Wave Sources one restricted private mechanical synthesis owner; equations,
  public capability, action inventory, state identities, and dependency
  boundaries remain unchanged.)

- `docs/adr/0015-ssrhm-tangent-pose-migration.md` (Accepted — implemented
    present truth: hardens authored Pose vocabulary to `tangent_x`/`tangent_y`,
    adds Source-owned consume/install validation, and authorizes only the
    corrected Collimated coordinate mapping.)
- `docs/adr/0016-paraxial-ray-transfer-vocabulary-cutover.md` (Accepted —
    implemented present truth: replaces the historical `abcd` public module
    and abbreviated callables with complete ray-transfer vocabulary, without a
    compatibility surface or a shared exact-Ray execution path.)

Old governance evidence, superseded architecture documents, task logs, caches,
and temporary environments do not remain as active repository structure.

## Post-seal stop line

After terminal seal, architecture work stops unless a reproducible physical
defect, an explicit scientific-scope decision, or independently demonstrated
Depth, Leverage, and Locality evidence reopens it. Style preference, line
count, symmetry alone, test quantity, or a historical module path does not
justify another production seam or compatibility layer.
