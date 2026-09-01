# Mission: a compact PyTorch optical core for local workstations

ChromatixNext is an independent PyTorch optical-simulation system for local
workstations. The current Release Descriptor validates Windows; Linux remains
an architecture target until native checks exist. The project is not an
official successor to upstream Chromatix and does not copy its runtime
architecture. Upstream source and paper material are attributed scientific
inputs for independent reconstruction.

The mission is one compact optical core that can be read in physical order,
assembled into checked optical paths, hosted explicitly on a Workstation,
differentiated through ordinary PyTorch, and taught through plain executable
Examples.

## Reading path

The documentation keeps three orders distinct, and each is stated in full at
exactly one owner rather than repeated here. Cognitive order — the order in
which a reader meets concepts — is owned by `CONTEXT.md`. Dependency
direction and researcher execution order are owned by `docs/architecture.md`.
The three are never conflated, and no reading path loops from Workstation
through physics back to Workstation.

## Explicit execution

A Workstation selects one explicit CPU or CUDA device. The numerical regime is
fixed double (every real floating quantity is `torch.float64`, every complex
quantity is `torch.complex128`); there is no precision selector. The
researcher authors either a frozen `Assembly` or a hosted module-level calculation;
`docs/architecture.md` owns the full execution mechanics. There is no
automatic device, memory, or propagation-method fallback: unsupported
devices, `float32`/`complex64` state that violates fixed double, sampling,
memory demands, or non-finite results fail at their owning interface, and an
unexpected out-of-memory error passes through unchanged.

## Research workflows

Optimization, loss, iteration history, and optimizer selection belong only to
Examples. There is no project optimization framework, no default optimizer,
and no second scientific subsystem. Each Example is one executable program
with paired English and Chinese documentation and exact scientific provenance;
it teaches the public researcher path without becoming a second validation
framework.

## Assurance

Repository checks mirror optics, numerical support, workstation execution, and
Examples through ordinary pytest modules with independently justified
references. Every public Component requires four evidence layers: physical
invariants, an independent analytic or numerical reference, gradient evidence
per trainable claim, and consistency under the fixed-double regime across any
claimed native CUDA path. Assurance adds no installed scientific role or
parallel governance taxonomy.

## Combination and evidence convergence

ChromatixNext remains an independent architectural successor rather than a
runtime copy or official upstream continuation. The foundation retains only
capabilities that fit its declared Physical Values, explicit lifecycle, and
single dependency direction; volume, sensor, workflow, and universal
framework concerns remain foundation-inadmissible and belong to separate
contexts.

Combination language follows the value being combined. Coherent Combination
combines `OpticalField` values, while Intensity Combination combines already
detected `Intensity` observables. Intensity Combination does not represent
field combination and does not claim to establish mutual incoherence.

The project applies a minimum sufficient evidence principle: each scientific
claim keeps one decisive physical witness and only the integration evidence
needed to prove a distinct architectural seam. Test count and coverage
percentage do not replace claim-specific evidence. The rule is that
performance claims are deferred until a separate benchmark contract exists,
and there is no universal superiority claim.

## Success criteria

- The production package carries exactly three seams — one optical core, one
  private numerical support, and one execution seam — with one-way,
  cycle-free dependencies and no legacy compatibility surface; the
  authoritative file inventory is owned by `docs/architecture.md`.
- Common optical elements compose into independently validated Assemblies that
  run on one explicit Workstation.
- CPU and CUDA use the same declared physics and never silently substitute one
  another; PyTorch remains the sole implementation until a complete
  independently qualified second slice exists.
- Examples remain directly executable with paired English and Chinese
  documentation; optimization appears only inside Examples through ordinary
  PyTorch.
- The project makes only claims supported by exact current evidence, and
  production growth is governed by hard interface budgets — two top-level
  public exports, twenty-four Optical Component actions, three directional
  owners, three closed enums, two Encounter references, three production seams, one dependency
  direction, no cycle, and no new public framework — plus independent review
  of any net production-line increase.

## Comparison scope

ChromatixNext is an independent reconstruction. It does not claim feature,
speed, memory, or performance superiority over the local Chromatix v0.4 and
v0.6 snapshots. The comparison evidence is pinned to two exact local
snapshots: Chromatix v0.4 commit
`727d7a39e9a0054cfe3a102440fcf931d31fd11a` and Chromatix v0.6 commit
`d24bdf0022835bb8ce1cdcc6aeafbc7fcb39daee`. Coverage is assessed by
behaviour family, never by exported-name parity. The permitted positive claim
holds only within a declared audited scope: fixed-double sampled Wave optics
with ideal lumped transverse polarization behaviour, polarized geometric Ray
optics at Plane-local encounters, independent mixed Assembly, explicit state
lifecycle, and direct scientific evidence. Within that scope ChromatixNext
offers a more unified and explicit architecture and scientific contract — one
implementation regime, one dependency direction, one owner per physical fact,
explicit applicability failure, closed Wave/Ray ownership, differentiable
evidence, and an immutable checkpoint/hosting lifecycle — not feature, speed,
memory, performance, ecosystem, or universal-accuracy superiority.

| Upstream v0.4/v0.6 behaviour family | Foundation treatment |
| --- | --- |
| Plane, Gaussian, and point illumination | Direct retained Sources |
| Scalar/vector sampled fields and multiple wavelengths | Direct retained Physical Values and Wave actions within the declared representation contract |
| Amplitude, phase, pupil, and ideal-lens actions | Direct retained Elements |
| Named ideal waveplates and polarizers | Composed from Retarder and Polarizing Beam Splitter; no convenience duplicates |
| Ideal directional splitting and recombination | Terminal-bound Cube Encounters plus ordinary Coherent/Intensity Combination; composed through typed Assembly topology |
| Scalar and vector free-space propagation | Direct retained propagation methods under method-owned sampling and applicability contracts |
| Thin scalar transmission/sample behaviour | Composed from amplitude transmission and optical-path modulation |
| Linear, branched, interferometric, and analyser systems | Composed through Assembly rather than public microscope/system classes |
| Geometric ray tracing | Direct polarized Ray Bundle, surface, reflection, refraction, TraceTo, Plane-local RetarderAt, and finite directional Cube/Mirror Encounters with typed physical Terminals |
| Volume/multislice/multiple scattering, fluorescence, Modified Born | Excluded: separate material/volume context |
| Sensor integration, resampling, quantization, filters, stochastic noise | Excluded: separate measurement context |
| Microscope/application/workflow classes | Excluded: examples or future upper contexts, not foundation physics |

The claim does not extend to excluded v0.4/v0.6 behaviours: volume samples,
multislice, multiple scattering, fluorescence, sensor integration, pixel
resampling, stochastic noise, microscope classes, material waveplate
thickness, dispersive retardance, dichroism, Mueller calculus, arbitrary
Jones matrices, geometry-aware Wave reflection, incidence-angle/coating/Fresnel
PBS, curved polarization-selective devices, polarized material interfaces,
Wave-to-Ray/Ray-to-Wave conversion, Ray amplitude/coherence, Ray reciprocal
coherent mixer, standalone linear polarizer, QWP/HWP convenience classes,
generic N-port scattering, or a second
precision/backend/runtime/graph/optimizer/device-fallback.
`docs/adr/0008-active-polarization-foundation.md` and
`docs/adr/0009-polarized-ray-foundation.md` hold the frozen wording and the
complete exclusion lists.
