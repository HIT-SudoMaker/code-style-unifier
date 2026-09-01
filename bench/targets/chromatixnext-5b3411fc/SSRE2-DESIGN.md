# Scalar Multislice Scientific Foundation — Converged Design

**Decision state:** ready to implement through the local Markdown tickets

**Baseline:** commit `a8dc9855c372b173380981eec477f04a65b78f47`, tree
`7b65fa0a3943b8580341294cb009d1f102853c4c`

## Decision

ChromatixNext will deepen its scientific foundation with one scalar,
isotropic, unidirectional thick-sample Wave Propagation named
`scalar_multislice` / `ScalarMultislice`.

This initiative does four things together:

1. admits one finite-volume Wave model without creating a universal Sample;
2. preserves Wave and Ray as teammate tracks that share Spectrum and explicit
   polarization only where the physics permits;
3. makes fixed `float64` / `complex128`, public SI units, local numerical
   scaling, differentiability, and fail-closed publication explicit parts of
   the scientific Interface;
4. qualifies the result on Windows CPU and one native CUDA device without
   claiming WSL2, Linux, multi-GPU, distributed FFT, or JAX performance.

DOE, optical-neural-network, microscopy, optimisation-framework, and
distributed-execution work remain later specifications or Examples. They do
not shape this first thick-sample Module.

## Why this is the right seam

The baseline already has five Optical Roles, strong Physical Values, explicit
polarization, typed Assembly composition, fixed-double Workstation execution,
and paired Function/domain `Component` actions. It does not have a
finite-volume propagation owner.

A thick sample is not a sequence of user-authored thin Elements. Its slice
ordering, common propagation support, padding, FFT recurrence, local scales,
material attenuation, background phase, and Optical Path Reference advancement
must agree as one scientific calculation. If the Module were deleted, that
knowledge would reappear in every caller. The Module therefore passes the
deletion test and earns a public Interface.

The same test rejects the following premature seams:

- a public `Volume`, `Sample`, solver, kernel, or backend abstraction with one
  implementation;
- a `method=` or `vector=` switch hiding materially different equations;
- an intermediate-depth result or `return_stack` without a real caller;
- a project-owned optimiser, loss, history, or distributed runtime;
- a universal Optical State spanning Wave and Ray.

## Foundation architecture

```text
Shared physical vocabulary
    Spectrum + explicit Polarization facts + Spatial Grid + Medium
        │
        ├── Wave Physical Values
        │     Source -> Element -> Propagation -> Combination -> Detection
        │                       └── Scalar Multislice (this initiative)
        │
        └── Ray Physical Values
              Source -> Element -> Propagation -> Combination -> Detection

Assembly owns authored topology.
Workstation owns one-device placement, replay, memory admission, and
publication.
User code owns objectives, optimisers, and experiment loops.
```

Wave and Ray are architecturally aligned without pretending their physical
behaviour is identical. This Wave action has no Ray twin and performs no
Wave/Ray conversion.

## Public Module

The public Interface contains one Function and one domain `Component`:

```python
def scalar_multislice(
    field: OpticalField,
    *,
    grid: SpatialGrid,
    refractive_index_contrast: torch.Tensor | torch.nn.Parameter,
    extinction_coefficient: torch.Tensor | torch.nn.Parameter,
    slice_thickness: float | torch.Tensor,
    exterior: PropagationExterior,
) -> OpticalField: ...


class ScalarMultislice(torch.nn.Module):
    def __init__(
        self,
        *,
        grid: SpatialGrid,
        refractive_index_contrast: torch.Tensor | torch.nn.Parameter,
        extinction_coefficient: torch.Tensor | torch.nn.Parameter,
        slice_thickness: float | torch.Tensor,
        exterior: PropagationExterior,
    ) -> None: ...

    def forward(self, field: OpticalField) -> OpticalField: ...
```

The Function owns identity-free physics and applicability. The domain
`Component` owns registered physical state, preserves a caller-supplied
Parameter identity, and delegates to the Function. Both cross the same
validation owners and the same recurrence.

The Implementation hides:

- state and Field-dependent validation;
- background transfer preparation and common support resolution;
- padding, cropping, frequency ordering, and FFT normalization;
- spectrum, batch, and polarization broadcasting;
- SI-to-local dimensionless phase formation;
- the split-step recurrence and material attenuation;
- Optical Path Reference advancement;
- immutable Field transformation and final strong-value validation.

Private helper values are permitted only when they remove repeated work inside
this Module. They are not new public seams.

## Physical model

The sample is a centre-sampled complex refractive-index volume with equal,
positive slice thickness. The volume state is expressed with full scientific
names:

- `refractive_index_contrast`: real index contrast relative to the Field-owned
  background Medium;
- `extinction_coefficient`: nonnegative absorptive part;
- `slice_thickness`: physical axial spacing in metres.

Opaque aliases such as delta-N, K, or DZ are not part of the Interface,
Implementation vocabulary, tests, or documentation.

For `slice_count` material planes, the recurrence is:

```text
background propagation by one half slice
-> material transmission at slice 0
-> background propagation by one full slice
-> ...
-> material transmission at the final slice
-> background propagation by one half slice
```

For vacuum wavelength `wavelength`, the material transmission is:

```text
exp(
    imaginary_unit * 2 * pi
    * refractive_index_contrast
    * slice_thickness / wavelength
    - 2 * pi
    * extinction_coefficient
    * slice_thickness / wavelength
)
```

The declared model is the projected unidirectional scalar Helmholtz
split-step recurrence. It is not a full inhomogeneous Helmholtz, backward-
scattering, multiple-reflection, vector-anisotropic, or experimental-validity
claim.

## Applicability and asymmetry

- Material volumes have shape `[depth, height, width]`, nonzero depth, exact
  transverse Grid registration, finite fixed-double contents, one device, and
  matching shape.
- Extinction is nonnegative and slice thickness is finite and positive.
- Total real refractive index is positive for every admitted wavelength and
  voxel.
- The first model is nondispersive: one material volume applies to all
  Spectrum members.
- The Field-owned Medium supplies the background response; the action accepts
  no second background-index parameter.
- SCALAR Fields are admitted.
- TRANSVERSE Fields use the same isotropic polarization-neutral recurrence
  independently for both transverse components.
- FULL Fields are rejected. A future Vector Multislice is a different named
  Propagation.
- All propagation steps use support admitted for the complete sample
  thickness. Unsupported computational windows and alias bands fail closed.
- Frequencies created by the declared discrete material step outside admitted
  support are projected out; the Module does not silently expand support per
  slice.

A zero-material volume equals homogeneous background propagation over total
thickness, not identity. Optical Path Reference advances by the background
contribution; material contrast remains in the Field envelope.

## Numerical policy

Public lengths and material quantities use SI units. The Implementation forms
dimensionless phase cycles and normalized frequency coordinates locally so
metre-scale nanophotonic inputs do not create avoidable ill-conditioning.

Production scientific tensors use:

- `float64` for real values;
- `complex128` for coherent fields and complex transfers.

There is no precision selector or silent promotion/fallback. A joint
`float32` / `complex64` counterfactual repeats the same operation graph and
must violate a budget that fixed double passes. It is evidence for the policy,
not a supported production mode.

The recurrence reuses the existing numerical owner for unit-complex phasor
construction and the existing radiative-spectrum/support facts. It does not
call the public plane-to-plane Propagation once per slice, because that would
repeat admission, Field construction, cropping, and path-reference updates.

## Differentiability contract

The smooth path supports gradients with respect to:

- the input Field envelope;
- refractive-index contrast;
- extinction coefficient;
- slice thickness while the discrete support decision remains fixed.

Grid, depth, Exterior, Polarization Representation, and support transitions
are discrete. The Module validates physical values but does not hide optimiser
parameterisations or constraints. A future Example may map latent variables to
valid physical state outside this Interface.

Thickness evidence observes both the local material envelope and a coherent
combination with a fixed reference arm. This prevents a detached or constant
Optical Path Reference carrier from passing an isolated-intensity test.

## Failure and lifecycle

One private state validator owns material Grid registration, tensor type,
precision, rank, shape, readable finite values, nonnegative extinction, and
positive thickness. One private applicability validator owns Field type,
polarization representation, Grid/device compatibility, positive total index,
computational window, and common support.

Construction, call-time applicability, and final publication are separate
fail-closed checks. There is no clipping, solver substitution, precision
fallback, device fallback, or unsupported-physics fallback.

The initiative reuses the existing State Installation contract from ADR-0006
and `_state_installation.py`; it does not invent another transaction layer.
Existing installation already takes an application snapshot, restores it on
native application failure, and has stable application/rollback failure
identities. Ticket 05 adds the missing fault evidence for the new Component
state and preserves the documented honest-atomicity boundary: project-owned
registered state is protected, while arbitrary external hook side effects are
not advertised as ACID.

Workstation publication must revalidate complete strong Physical Value
invariants, including finite tensor contents mutated after construction. A
runtime failure publishes neither Named Outputs nor Run Record and never falls
back to CPU.

## Evidence architecture

The product specification is the sole semantic owner of the fourteen claim
IDs, their contracts, and their implementation owners. Design and tickets
refer to that table; they do not duplicate it. Tests contain an independently
authored exact claim manifest and named expected-action set. Completeness is
checked in both directions.

Evidence must challenge the Implementation through the public Interface:

- analytic zero-material, uniform-phase, and Beer-Lambert limits;
- an independent frequency-bin support oracle;
- a direct two-slice spatial recurrence that detects wrong order and signs;
- refinement of one fixed continuous material object;
- the joint low-precision counterfactual;
- finite-difference gradients and detach mutants;
- Function/domain `Component`, Meta/real, installation, hosting, release, and
  retry lifecycle checks;
- CPU/CUDA value and gradient comparison plus a real CUDA failure witness.

Original Chromatix is an auxiliary matched-convention cross-check, never the
sole oracle. Numeric budgets are written with their analytic or operation-
count rationale before the corresponding production implementation is changed.
A counterfactual outside each budget proves that the test can fail.

Resource evidence is descriptive: one exit Field, no explicit depth stack,
and a predeclared workload matrix. This initiative makes no latency, peak-
memory, linear-scaling, superiority, or JAX-performance pass claim.

## Implementation method

Implementation uses the local tracker and ordinary Git evidence:

1. record the exact clean baseline and ticket scope;
2. select the lowest unblocked ticket;
3. allow one production writer at a time in one dedicated worktree;
4. for numerical tickets, commit the failing public-Interface witness and its
   budget rationale before changing production calculation;
5. implement only the ticket, run focused tests, then the repository CSU and
   isort gates;
6. independently review the real diff and evidence before marking the ticket
   completed;
7. proceed to the next ticket only after its blockers are completed.

A stopped writer leaves its commits and test output for ordinary Git
inspection. The next writer either continues that exact ticket state or starts
from its last independently accepted commit. No project-specific scheduler or
process transaction is part of the product specification.

## Ticket architecture

| Ticket | Outcome |
| --- | --- |
| 01 | Replace permanent action cardinality with named action/claim authorities. |
| 02 | Close strong Physical Value publication. |
| 03 | Add the Scalar Multislice Interface, admission, and analytic limits. |
| 04 | Close order, support, refinement, and fixed-double evidence. |
| 05 | Close gradients, Parameter identity, and State Installation lifecycle. |
| 06 | Qualify Assembly, Workstation, resource observations, and one CUDA device. |
| 07 | Converge exports, domain documentation, ADR, and complete regression evidence. |
| 08 | Review the actual implementation diff and close admission findings. |

## Future change routes

- Thin ideal DOE remains an Element and composes with Propagation in later
  Examples.
- Vector anisotropy becomes a named Vector Multislice Propagation.
- A different recurrence becomes another named Propagation, not a selector.
- A shared public volume model requires a second real consumer and a deletion
  test.
- Intermediate observation requires a demonstrated caller and a separately
  designed strong result or Detection.
- Optimisation support requires at least two real Examples with the same
  durable need.
- WSL2/Linux and multi-GPU require their own environments, failure contracts,
  numerical evidence, and performance experiments.

## Supersession

The former r2–r16 preimplementation scopes and dimension reports remain local
historical evidence of how the plan was challenged. Their custom coordinator
state machine is superseded and must not be implemented. This document,
`.scratch/scalar-multislice-foundation/spec.md`, and active Tickets 01–08 are
the current plan.
