# History

This document compresses the superseded governance architecture and its 223
non-durable Architecture Decision Records into concise lessons. It exists so
previous decisions remain available without controlling the new architecture.
Active work uses the language in `CONTEXT.md`, `MISSION.md`,
`docs/architecture.md`, and the sixteen active ADRs authoritatively enumerated
in `docs/architecture.md`.

The 2026 scientific-foundation cutover removed the earlier lumped splitter
surface atomically. Ideal cube beam splitters and the planar mirror are now
state-only directional owners referenced by finite Assembly-issued Encounters
at typed physical Terminals. The active budget is twenty-four Optical Component
actions, three directional owners, three closed enums, two Encounter reference
types, and two top-level lifecycle exports. Structural Assembly closure,
observational Detection/Example-evidence closure, and Workstation execution
closure are independent; owner reuse never implies recurrence.

ADR numbers below refer to the original `docs/adr/` sequence (0001-0227),
which has been removed. Each lesson is one to three lines. Where a lesson is
now owned by a durable ADR, the cross-reference is given.

## Foundation, platform, and language

- **0001 — Use Python and PyTorch exclusively.** Python + PyTorch only; JAX
  and Rust excluded. *Now durable: ADR-0001.*
- **0002 — Vendor an inert upstream snapshot.** Keep upstream source as inert
  reference, never as a runtime dependency.
- **0003 — Initialize one root repository after arranging the layout.**
  Repository identity is separate from upstream layout.
- **0004 — Separate package versions from Git tags.** Version text lives in
  the Release Descriptor, not in Git tags or scientific symbols.
- **0005 — Name the project across local, public, and Python contexts.** One
  canonical project name across all contexts.
- **0006 — Audit two upstream baselines and vendor one.** Upstream v0.4 and
  v0.6 are evidence, not specification.
- **0007 — Target local workstations with Linux-only multi-GPU.** Product
  scope is single-host workstations; multi-node stays out.
- **0024 — Use paired, natural domain language.** Equivalent concepts get
  paired names; different concepts get exact natural names.
- **0053 — Take one pre-release vocabulary break.** One clean vocabulary
  cutover beats prolonged mixed naming.
- **0054 — Calibrate CSU to the project contract.** CSU is the authoritative
  format + architecture command.
- **0055 — Enforce zero hard and review CSU findings.** Release requires zero
  hard violations and zero under-review items.
- **0192 — Separate platform targets from validated release platforms.**
  Windows CPU + available CUDA are required release evidence; Linux is an
  architecture target until native checks exist. *Now reflected in
  `docs/architecture.md` Completion gates.*
- **0199 — Keep one small active architecture language.** Active architecture
  is one document plus its authoritative active ADR set.
- **0223 — Keep Sonnet philosophy out of runtime language.** Teaching
  philosophy never enters production symbols.

## Scientific specification versus resource planning (legacy governance)

These decisions built the scientific-governance framework (Operations,
Contracts, Catalogs, Manifests, Strategies) that the refactor removes. They
are recorded as lessons only.

- **0008 — Separate scientific specification from resource planning.** Keep
  physics separate from execution-resource decisions. *Lives on as: `optics`
  owns physics, `workstation.py` owns resources.*
- **0010 — Separate scientific, local, and resolved-run files.** Authoring,
  workstation, and run artifacts stay distinct.
- **0014 — Make propagation an operator family inside the Simulator.**
  Propagation is one physical role with explicit method selection.
- **0015 — Model optical composition as a typed DAG.** Branched, merged paths
  are first-class. *Now durable as Assembly: ADR-0002.*
- **0018 — Reject implicit scientific conversions.** No silent unit or
  normalization conversion.
- **0021 — Identify Optical Operators through one registry.** Retired by
  0063: no operator registry; Components live in role packages.
- **0022 — Freeze the Operator Catalog before each run.** Replaced by
  `Assembly.freeze()`. *Now durable: ADR-0002.*
- **0023 — Use two authoring paths and one canonical graph.** Replaced by one
  Assembly grammar; no graph/node framework.
- **0025 — Separate Node Identity from display name.** Stable Component names
  anchor parameters, errors, and random streams. *Lives on in Assembly
  authoring.*
- **0032 — Require named scientific Field operations.** Replaced by direct
  Component calls.
- **0033 — Require whole-graph Preflight.** Replaced by Assembly Check +
  Workstation Check.
- **0034 — Require reasoned Warning Acknowledgements.** Removed: failures are
  hard at the owning boundary.
- **0035 — Place local scientific validation with Optical Operators.**
  Validation lives in ordinary pytest, not in Components.
- **0036 — Separate Contract Resolution from computation.** Replaced by
  Assembly Check (tensor-free) + Component execution (tensor).
- **0037 — Keep the Optical Graph acyclic.** Replaced by Assembly topology
  rules.
- **0038 — Never degrade scientific semantics on memory failure.** OOM passes
  through unchanged. *Now durable in `docs/architecture.md`.*
- **0039 — Freeze the Execution Plan before running.** Replaced by
  `Assembly.freeze()`; no separate plan object.
- **0040 — Require exact identity for checkpoint recovery.** Ordinary PyTorch
  `state_dict`; no project checkpoint type.
- **0041 — Publish results atomically.** Replaced by Named Outputs + Run
  Record from one `run()`.
- **0043 — Expose one deep Simulator interface.** Retired: no Simulator; the
  Workstation is the single execution boundary.
- **0050 — Prepare reusable operator resources per frozen plan.** Replaced by
  `host()` + non-persistent numerical caches.
- **0051 — Bind qualification to the graph runtime.** Retired: qualification
  is ordinary pytest evidence beside each Component.
- **0052 — Organize optics by Scientific Capability Family.** Retired: optics
  is organized by Physical Value modules + singular role packages.
- **0056 — Make Named Scientific Operations the minimum physical unit.**
  Retired: the minimum unit is one Component call.
- **0057 — Bind qualified variants to Named Scientific Operations.** Retired:
  a new propagation class needs a genuinely distinct kernel, not a variant
  registry.
- **0058 — Compose independent optical effects explicitly.** Direct calls +
  Assembly composition. *Now durable: ADR-0002.*
- **0059 — Derive Catalog and Qualification from Family Declarations.**
  Retired: no catalog, no qualification framework.
- **0060 — Load Family Declarations through a Verified Manifest.** Retired:
  no manifest.
- **0061 — Make Function Path a Semantic Operation Entry.** Retired: one
  Component call form, no function/object split.
- **0062 — Keep Graph Path Adapters narrow.** Retired: no graph path.
- **0063 — Retire the Optical Operator vocabulary.** Components, not
  operators; direct calls, not catalog invocations.
- **0064 — Organize each Capability as a shallow vertical module.** Flattened
  further: singular role packages with `__init__.py` exports only.
- **0065 — Standardize the shallow Family layout.** Retired: role packages
  replace family modules.
- **0066 — Represent Scientific Operations as frozen values.** Retired:
  Components are `torch.nn.Module`s; Parameters/Buffers follow PyTorch rules.
- **0067 — Require explicit named Optical Functions.** Retired: direct
  Component call is the one form.
- **0068 — Share Semantic Role Names across both Paths.** Retired: one path,
  the five singular roles.
- **0069 — Use paired Semantic Role Names.** Paired naming retained; the
  function/graph split is gone.
- **0070 — Use one strong Parameter value per Operation.** Replaced by
  PyTorch-native Component State (Parameter / Buffer).
- **0071 — Give each Validation Rule one owner.** Retired: tests own
  validation, one owner per assertion.
- **0072 — Separate scientific Diagnostics from program defects.** Retired:
  two domain exceptions only (`AssemblyError`, `WorkstationError`).
- **0073 — Separate Execution Strategies from Scientific Operations.**
  Retired: no Execution Strategy type at all.
- **0074 — Keep Family Execution in an optional peer module.** Retired.
- **0075 — Derive Qualification Candidates from Declarations.** Retired: no
  qualification taxonomy.
- **0076 — Derive Implementation Identity from Source Closures.** Retired:
  implementation identity is not a scientific concept.
- **0077 — Plan Scientific Value Lifetimes before execution.** Replaced by
  conservative Memory Check inside Workstation Check.
- **0078 — Release references before qualifying Buffer Reuse.** Retired:
  Buffer reuse planning is gone; immutable Fields throughout.
- **0079 — Pair Scientific Values with strong Contract Results.** Retired:
  Physical Values return Physical Values; no contract object.
- **0080 — Preserve reciprocal two-port Beam Splitter semantics.** Lesson
  retained: the Reciprocal Beam Splitter is one Element with unitary
  two-port behaviour.
- **0089 — Split only at Scientific Seams.** Lesson retained: split at
  physical role boundaries, not at governance categories.
- **0097 — Enforce one-way scientific support boundaries.** *Now durable:
  ADR-0003.*
- **0098 — Map each Scenario across support roots.** Retired: no scenario
  framework.
- **0099 — Organize tests by proof role.** Retained: tests mirror optics,
  `_numerics`, workstation, Examples.
- **0100 — Scale support artifacts by scientific claim.** Retired: evidence
  scales with the Component claim, in ordinary tests.
- **0155 — Reconstruct the foundation through vertical replacement.** Lesson
  retained: migrate via runnable vertical slices; no compatibility alias.
- **0156 — Make the complete Scientific Value payload identity-bearing.**
  Simplified: Physical Values carry their own invariants; no separate payload
  identity type.
- **0158 — Publish Scientific Values through deterministic payload manifests.**
  Retired: no manifest.
- **0159 — Classify optical families by scientific role.** Collapsed into the
  five singular Optical Roles.
- **0160 — Use one scientific operation grammar.** Retired: one Component call
  form, one Assembly grammar.
- **0161 — Separate Candidate and Qualified Catalogs.** Retired: no catalogs.
- **0162 — Let Scientific Contracts own complete payload schemas.** Retired:
  no contract objects; Physical Values own their own shape.
- **0164 — Let Family Declarations own lifecycles directly.** Retired.
- **0165 — Freeze the paired Scientific Operation interface.** Retired.
- **0166 — Represent Family Declarations as Scientific Families.** Retired.
- **0167 — Freeze the paired Execution Strategy interface.** Retired: no
  Strategy type.
- **0168 — Supersede the builder-shaped Qualification Declaration.** Retired.
- **0169 — Reduce the Family Manifest to an integrity index.** Retired.
- **0170 — Defer the Capability Provider seam.** Lesson retained: no
  speculative provider/plugin seam until two real adapters exist.
- **0171 — Separate Catalogs without inheritance.** Retired.
- **0172 — Qualify Variants and demonstrate Scenarios.** Retired.
- **0173 — Cut over complete Reconstruction closures atomically.** Retired as
  governance; the atomic-cutover habit stays for migration waves.
- **0176 — Separate Scientific Qualification from performance recommendation.**
  Retired: no qualification framework; performance is out of scope.
- **0177 — Distinguish deterministic control from numerical parity.** Retired.
- **0178 — Let Qualification Specifications own Scientific Tolerances.**
  Retired: tolerances live beside the exact test assertion.
- **0184 — Contract the legacy foundation atomically.** Lesson retained:
  delete legacy without compatibility aliases once slices pass.
- **0185 — Qualify science through complete observed cases.** Lesson retained:
  four evidence layers per Component.
- **0186 — Measure reconstruction by Ledger obligation.** Retired: no
  Reconstruction Ledger; upstream is evidence, not the product inventory.
- **0187 — Build one qualified Optical Graph sequence.** Retired.
- **0188 — Cut over science in dependency-complete Reconstruction Waves.**
  Retired as governance; migration still proceeds dependency-first.
- **0189 — Require independent evidence for Scientific Qualification.**
  Retired framework; the independent-reference requirement stays in Component
  Evidence.
- **0193 — Index scientific operations without families.** Retired.
- **0194 — Pair operation identity, parameters, and physical action.**
  Collapsed into Component + Physical Value.
- **0195 — Verify operations and validate scenarios.** Retired.
- **0196 — Separate scientific nouns from optical actions.** Retained as
  lesson: Physical Values (nouns) versus Components (actions).
- **0198 — Organize optical actions by physical order.** Retained: the public
  reading order in `docs/architecture.md` is execution boundary, Physical
  Values, roles, Assembly, hosting, run.
- **0200 — Preserve science while changing architecture identities.** Lesson
  retained: migrate via atomic vertical slices; no compatibility alias; the
  scientific equations are preserved while module paths and identities
  change.
- **0201 — Keep scientific granularity lightweight.** Retired framework.
- **0202 — Name each Operation as one physical stanza.** Retired.
- **0224 — Retain one Operation Contract through execution.** Retired: no
  contract object; Assembly Check + Component execution replace it.
- **0226 — Keep realization-resolved detection on the Function Path.**
  Retired: one Component call form for detection too.

## Physical Values (Fields, Spectrum, Polarization, Medium, Grids, Phase)

The durable physics decisions here are absorbed into `CONTEXT.md` Physical
contracts and the Component Evidence tests; they are not re-stated as ADRs.

- **0009 — Support exactly complex64 and complex128.** *Now in `Precision`:
  `docs/architecture.md`.*
- **0016 — Separate coherent and incoherent combination.** Two distinct
  Components; never a mode flag.
- **0017 — Require logically immutable Optical Fields.** Optical Field is
  immutable.
- **0019 — Require named, strongly typed Optical Ports.** Ports named only
  when ambiguous; role + port matching in Assembly.
- **0020 — Use compact Scientific Value Categories.** Physical Values own
  their invariants; no category taxonomy.
- **0028 — Promote Parameter Estimates explicitly.** Estimate categories
  deferred (fluorescence); no estimate type in the core.
- **0030 — Require explicit physical units.** SI throughout.
- **0031 — Make axis and coordinate semantics explicit.** Fixed axes
  `[batch..., spectrum, polarization, height, width]`.
- **0042 — Use micrometres as the canonical optical length.** Refined: SI
  metres throughout; Examples may define local conversion constants.
- **0044 — Model beam splitters as two-port unitaries.** Reciprocal Beam
  Splitter is one Element Component.
- **0047 — Derive coherence from source lineage.** Coherent Combination
  verifies frequency, spectrum, polarization, medium, grid, normalization,
  axes, Precision, lineage.
- **0048 — Fix the time-harmonic phase convention.** `Re{E exp(-i omega t)}`;
  positive propagation accumulates positive phasor phase; `z` stays local to
  equations.
- **0081 — Separate Axis Layout from Spatial Grid.** Axis layout fixed;
  SpatialGrid is one Physical Value.
- **0082 — Unify Spectral Components under Optical Field.** One Optical Field
  with ordered spectrum; no mono/poly subclass.
- **0083 — Separate Spectral Weight from Optical Power.** Spectral weights
  live on the Field; power is a normalization choice.
- **0084 — Model Polarization as a closed State.** PolarizationState is one
  Physical Value; scalar/transverse/full are explicit representations.
- **0085 — Require one Spectral Component per wavelength.** Each spectral
  entry has one wavelength.
- **0086 — Separate Field, Intensity, and Measurement.** Intensity is the one
  observable now; measurement/camera deferred.
- **0087 — Preserve Spectral Intensity until detection.** Intensity carries
  spectral reduction semantics.
- **0088 — Separate Detector Expectation from Measurement.** Camera/sensor
  models deferred.
- **0090 — Name independent simulation axes.** Fixed axes; Components never
  squeeze/reorder.
- **0091 — Separate Field Generation from Field Import.** Import converts
  once at its boundary.
- **0092 — Separate Field Amplitude from Power Normalization.** Source
  requires exactly one of `relative_amplitude` / `total_power`; no default.
- **0093 — Separate Directional and Phase-Gradient Plane Waves.** Plane Wave
  takes exactly one Propagation Direction or Transverse Wavevector.
- **0094 — Name Point Source approximation levels.** Out of current scope.
- **0095 — Expand Objective Point Source as an Assembly.** Out of current
  scope.
- **0096 — Separate Gaussian apodization from Gaussian Beam Generation.** Out
  of current scope.
- **0101 — Separate Optical Path and Common Phase Modulation.** Optical Path
  Modulation is one Element.
- **0102 — Distinguish Amplitude and Intensity Transmission.** Amplitude
  Transmission Map; intensity transmission = |amplitude|² never accepted as
  input.
- **0103 — Separate Physical Aperture, Pupil, and Angular Acceptance.** Pupil
  is one Element.
- **0104 — Add Laterally Shifted Angular Spectrum Propagation.** Destination
  Grid geometry owns scale/shift/orientation.
- **0105 — Limit Shifted Propagation gradients by spectral support.** Trainable
  `axial_distance` honoured in tests.
- **0106 — Organize propagation by physics and destination-grid contract.**
- **0107 — Separate radiative, near-field, and reconstruction semantics.** One
  named propagation method per Component; no automatic substitution.
- **0109 — Model Fourier-conjugate destination grids.** DestinationGrid owns
  the input/destination relationship.
- **0110 — Preserve spectral grids while optimizing storage.** Spectral axis
  is always present; batching is a `_numerics` concern.
- **0114 — Represent fields with optical path references.** Optical Path
  Reference is part of the Field.
- **0115 — Split optical path reference into anchor and adjustment.**
- **0116 — Inherit coherent output reference from first input.**
- **0117 — Factor field transformations into reference and envelope effects.**
- **0119 — Separate axial displacement from plane separation.** Signed
  `axial_distance`, not `z`.
- **0120 — Use axial displacement for Fresnel propagation.** Physical naming
  retained; method arrives only when its own slice qualifies.
- **0121 — Use complete axial Fraunhofer propagation.** Physical naming
  retained; method arrives only when its own slice qualifies.
- **0122 — Use axial displacement and intrinsic sampling for scalable angular
  spectrum.** Physical naming retained; AngularSpectrum is the first
  propagation Component.
- **0123 — Decompose optical path profiles without inference.** Optical Path
  Profile is one Physical Value.
- **0124 — Separate ideal thin and physical lenses.** Ideal Thin Lens is one
  Element; physical lens out of scope.
- **0125 — Separate ideal retardance and physical birefringent plates.** Out
  of current scope.
- **0131 — Resolve material responses before execution.** Medium resolved at
  the Source; downstream consumes it.
- **0132 — Use linear vacuum-wavelength interpolation for material tables.**
  TabulatedMedium range rule.
- **0133 — Fix the Sellmeier coefficient convention.** SellmeierMedium.
- **0134 — Use assigned or direct spectral volume materials.** Applies to
  deferred multi-slice work.
- **0157 — Use one canonical public scientific tensor layout.** Fixed Field
  axes.
- **0163 — Freeze Field Normalization and Precision ownership.** Workstation
  owns Precision; normalization is on the Field.
- **0174 — Separate spatial Parameters from device Operations.** Components
  hold spatial Parameters; no device-op split.
- **0175 — Make Propagation Medium part of the Field Contract.** Medium on the
  Field; no duplicate refractive-index argument.
- **0179 — Reject invalid and non-finite numerical results.** Fail at the
  owning boundary.
- **0180 — Publish phase only through explicit observation.** No implicit
  phase output.
- **0181 — Qualify gradients and Execution Strategies independently.**
  Retired: no Strategy type; gradients verified per trainable claim in
  Component Evidence.
- **0182 — Require exact Execution Strategy selection before planning.**
  Retired: explicit Workstation factory selection; no strategy planning.
- **0183 — Bind estimated detection through named plan state.** Retired:
  estimated detection is deferred with the rest of fluorescence.
- **0221 — Deepen radiative propagation with Shifted Destination Grids.**
  DestinationGrid Shifted form declares absolute first-sample position.
- **0222 — Model Destination Grids as closed physical relations.** Aligned and
  Shifted forms preserve counts, spacing, orientation.

## Propagation methods and sampling (physical lessons retained)

- **0108 — Assess propagation regimes without switching models.** Method
  validates applicability, never substitutes another method.
- **0111 — Freeze qualified spectral execution strategies.** Retired as
  governance; one Component per named method.
- **0119-0122 (axial displacement family).** Signed `axial_distance` naming
  for Fresnel, Fraunhofer, and scalable Angular Spectrum; preserved as
  physical naming in `docs/architecture.md` and the propagation tests.
- **0126 — Model thin isotropic samples as material contrast.** Out of
  current scope.

## Native acceleration and execution strategy

- **0011 — Require upstream behavioral audit before implementation.** Upstream
  is evidence, not specification.
- **0012 — Treat upstream tests as evidence, not specification.**
- **0049 — Permit qualified custom CUDA adapters.** *Now durable: ADR-0001 —
  no public native selector until a complete slice is independently
  qualified.*
- **0111 — Freeze qualified spectral execution strategies.** Retired.
- **0112 — Keep native acceleration optional.** *Now durable: ADR-0001 —
  PyTorch is the sole implementation on CPU and CUDA; native arrives only as a
  complete equivalent slice.*
- **0113 — Separate user target from developer strategy.** Retired: explicit
  Workstation factory selection; no auto-discovery.

## Qualification, gradients, and release identity

- **0026 — Keep release identity out of source code.** Version in the Release
  Descriptor, not in scientific symbols.
- **0027 — Separate forward models from optimization problems.** *Now durable:
  ADR-0004 — Examples own optimization.*
- **0029 — Make randomness explicit and execution-invariant.** *Now durable:
  Workstation-owned seed 42, local generators, name-derived streams.*
- **0118 — Require three-part phase qualification.** Replaced by four-layer
  Component Evidence.
- **0176-0183 (qualification framework).** Retired; Component Evidence and
  ordinary tests replace the framework. Tolerances stay beside the exact
  assertion. Gradients verified by `gradcheck` per trainable claim.

## Fluorescence and volume estimation — DEFERRED

Fluorescence emission, fluorescence volume propagation, and estimated
detection were a substantial governance and physics investment (ADR-0127
through ADR-0154). The refactor defers them entirely: legacy `emission/` and
`propagation/_fluorescence_volume_*` modules are removed with the rest of the
legacy architecture in Task 16. Fluorescence may return only via a later,
separately designed complete slice with its own Optical Role semantics and
four-layer evidence. The lessons below are preserved so that future work does
not repeat upstream's category errors.

- **0127 — Model multi-slice volumes as a deep solver.** Out of scope; would
  be a separate solver locality, not a god file.
- **0128 — Use a centered slice recurrence.** Lesson retained for any future
  volume work.
- **0129 — Start multi-slice volumes with radiative angular spectrum.**
- **0130 — Reuse explicit propagation exteriors for volumes.**
- **0135 — Start volume optimization with full gradients.** Optimization
  belongs in Examples only.
- **0136 — Model volume fields as explicit observation branches.**
- **0137 — Separate fluorescence emission from volume propagation.** Hard
  scientific seam: source construction versus stochastic transport.
- **0138 — Separate absolute and relative fluorescence emission.**
- **0139 — Partition isotropic fluorescence by destination half-space.**
- **0140 — Discretize isotropic emission by solid-angle measure.**
- **0141 — Key fluorescence randomness by stable scientific identity.**
- **0142 — Use a centered emission recurrence.**
- **0143 — Publish only boundary fluorescence intensity estimates.**
- **0144 — Publish spatial intensity and boundary flux statistics.**
- **0145 — Start fluorescence optimization with fixed-source gradients.**
- **0146 — Apply ideal detection before ensemble reduction.** Detector
  response before Monte-Carlo summary; never on a summary mean alone.
- **0147 — Do not sample instrument noise from estimated expectations.**
  Instrument noise models remain out of scope.
- **0148 — Separate absolute and relative estimated detection.**
- **0149 — Start random-phase fluorescence with isolated exterior.**
- **0150 — Parallelize fluorescence only by realization.**
- **0151 — Defer multi-GPU fluorescence gradients.**
- **0152 — Qualify fluorescence through five evidence layers.** Future
  fluorescence must meet Component Evidence; the five-layer ladder is not
  re-implemented as governance.
- **0153 — Split fluorescence emission, volume, and detection families.**
  Future fluorescence, if it returns, organizes under the same Physical Value
  + singular-role rules, not under a fluorescence umbrella package.
- **0154 — Freeze fluorescence operation and role names.** Retired.

## Examples, teaching, and distribution

- **0013 — Keep the Illustrator presentation-only.** Illustration is
  presentation; no scientific claim lives there.
- **0045 — Separate examples from benchmarks through shared validation
  scenarios.** Retired: no benchmark framework; Examples carry smoke tests
  only.
- **0046 — Adopt strict configuration adapters for the graph path.** Retired:
  no graph path; authored values may come from configuration but configuration
  is never a required runtime.
- **0190 — Make common composable optics the product goal.** *Now durable:
  ADR-0004 and `MISSION.md`.*
- **0191 — Start with a common composable optical core.** The first stable
  scope is the Common Optical Core in `docs/architecture.md`.
- **0197 — Adapt upstream cases into the first workstation slice.** Upstream
  inspires; it does not define the product.
- **0203 — Treat Mach-Zehnder as an Example-backed integration case.**
- **0204 — Treat focusing as an Example-backed integration case.**
- **0205 — Publish executable Python Examples outside the runtime library.**
  *Now durable: ADR-0004.*
- **0206 — Cover Operations through physical questions.** Examples ask one
  physical question each.
- **0207 — Illustrate only Published Example results.**
- **0208 — Author formal Examples from portable scientific YAML.** Refined:
  Examples are ordinary Python programs; configuration may supply authored
  values but is never a required runtime.
- **0209 — Keep Workstation configuration outside Examples.** Workstation
  selection is explicit in the Example program.
- **0210 — Separate upstream Example audit from case provenance.**
- **0211 — Make core Examples scientifically adequate on Local CPU.**
- **0212 — Load science and Workstation through paired owners.** Refined into
  canonical import paths.
- **0213 — Keep Example CLI out of science and resource configuration.**
- **0214 — Check Example publication without owning Example science.**
- **0215 — Load Scientific Specifications through Operation-owned parameter
  stanzas.** Retired: no specification loader.
- **0216 — Load explicit Workstation Configurations without activation.**
  Retired: explicit `Workstation.cpu(...)` / `Workstation.cuda(...)`.
- **0217 — Publish Examples as source-bundled sonnets.** Refined: each
  Example is one executable program + paired EN/ZH README + provenance.
- **0218 — Distribute teaching through source and runtime through wheel.**
  *Now in `docs/architecture.md` Product boundaries.*
- **0219 — Teach Foundation science as five ordered physical questions.**
- **0220 — Reserve Scientific Sonnets for scientific questions.** Refined:
  Examples stay focused on one physical question each.
- **0225 — Enforce one-way core runtime dependencies.** *Now durable:
  ADR-0003 — `workstation -> optics -> _numerics`.*
- **0227 — Keep the product to the scientific platform and Published
  Examples.** *Now durable: ADR-0004.*

## Proposals that contradicted an existing ADR

Per the domain rule that any proposal contradicting an existing ADR is called
out explicitly, the following reversals are recorded:

- **0049** partially superseded **0001** (admitting a narrow CUDA seam). The
  refactor re-closes that seam: PyTorch is the sole implementation until a
  complete slice is qualified (ADR-0001).
- **0063** superseded the Optical Operator vocabulary (**0021**, **0022**,
  **0023**, **0067**). The refactor completes that retirement: no operator
  registry or graph path remains.
- **0190** superseded **0186** where the Reconstruction Ledger was treated as
  the product definition. The refactor removes the Ledger entirely.
- **0192** refined **0007** and superseded the fixed four-platform matrix in
  **0112**. The refactor keeps Windows CPU + available CUDA as required
  evidence and Linux as an architecture target.

No durable decision in the active ADR set is silently dropped. Decisions that
do not fit its durable topics are captured above as lessons.

## Task 17 — final-gate cleanup dispositions

The final gate removed the last physical artifacts of the retired governance
frameworks so the repository matches the active language in `CONTEXT.md`:

- **`evidence/` tree removed (1,131 files).** The whole tree
  (`acceleration/`, `independent/`, `qualification/`, `qualification_history/`,
  `upstream/`) was the physical realization of the retired Scientific
  Qualification / Qualified Catalog / Evidence-Key governance framework
  (ADRs retired above: 0051, 0059, 0075, 0168, 0176, 0178, 0185, 0186, 0189,
  0201). It is the "Old governance evidence ... do not remain as active
  repository structure" named in `CONTEXT.md`. The active Component Evidence
  (physical invariants, independent reference, gradient evidence, Precision +
  native-CUDA consistency) lives beside each Component as ordinary pytest
  suites under `tests/optics`, `tests/element`, `tests/propagation`,
  `tests/combination`, `tests/detection`, `tests/source`, `tests/_numerics`;
  the Windows CPU + available CUDA release evidence is recorded in the
  `RunRecord` assertions of `tests/workstation/test_cuda_path.py`. No active
  test, document, wheel, or sdist cited `evidence/`; removal is conservative.
- **`PyYAML` dependency removed.** No production source, test, tool, or
  build script imported `yaml`; the dependency was stale.
- **Release identity stays in `release.toml`.** The wheel ships only
  `chromatix_next` plus `release.toml`; the version string does not leak into
  scientific symbols (verified by the fresh `tests/release/` gate).
