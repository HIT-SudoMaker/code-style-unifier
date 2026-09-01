# Intelligent Optical Restoration Research Context

This context defines the scientific language for frozen reusable data and
optical building blocks, archived Fixed Measurement evidence, and the active
correctability-aware intelligent optical front end. It is a terminology ledger,
not a second architecture specification; current decisions live in ADR-0019,
ADR-0020, ADR-0021, ADR-0024, and `docs/restoration/`.

## Current Restoration Contract

**Intelligent Optical Front End**:
The complete reference-on system that uses a finite measurement history to predict a hardware-feasible action, audit a delivered trial through a later coherent measurement, and selectively admit or revert that action before a prospective raw observation.
_Avoid_: Smart optics, neural image restorer, wavefront estimator alone

**Fixed Coherent Reference**:
A mechanically fixed reference arm whose effective relative phase and drift are calibrated nuisance state during an episode. Rapid phase diversity is applied by global piston on the processing SLM.
_Avoid_: Perfect zero-phase reference, tunable delay scan

**Shared Interferometer Topology**:
The calibrated reference-arm and Fourier-processing-arm optical arrangement whose 638 nm wavelength, 100 mm focal length, sampled geometry, aperture, splitter, arm gains, and coherent recombination are common to Fixed Measurement and Adaptive Measurement even though their input and evidence protocols differ. The frozen simulation is the compact ideal 4f equivalent; an element-by-element V-relay claim requires separate calibration.
_Avoid_: Shared input model, shared experiment protocol, universal restoration scene

**Fixed Replay Input**:
A detected degraded intensity replayed as a zero-phase coherent amplitude field for target-supervised offline evaluation of a specimen-independent action.
_Avoid_: Unknown episode field, native adaptive observation, clean optical field

**Adaptive Episode Input**:
An unknown coherent field available to the policy only through causally earlier reference-on observations from the current episode; its clean reference and aberration truth remain evaluator-only.
_Avoid_: Fixed replay input, target-visible optimization, oracle phase input

**Relative Optical Transfer**:
The coherent transfer produced by the sum of the fixed-reference and phase-controlled processing-arm transfers. It is the primary reference-on correction object.
_Avoid_: Generic OTF, processing-arm transfer alone

**Hardware-Feasible Action Set**:
The delivered phase-only corrections reachable after measured phase range, LUT, quantization, crosstalk, registration, polarization, settling, and drift are applied.
_Avoid_: Arbitrary phase mask space, commanded phase set

**Fourier-Grid Phase Action**:
The full 512 by 512 phase-only action defined on the Computational Fourier-Phase Grid and optimized or inferred from measurement-supported physics before hardware projection.
_Avoid_: Zernike-only control, native SLM bitmap, unconstrained pixel search

**Correctability Estimate**:
A measurement-conditioned prediction of prospective benefit, harmful-correction risk, and uncertainty relative to a preregistered safe action. Use `certificate` only after prospective calibration has been established.
_Avoid_: Guaranteed correction, uncalibrated confidence, certificate by construction

**Pre-Echo Decision**:
Exactly one of `probe`, `trial`, or `abstain`, selected before an action-conformity measurement from the evidence and budget available at that time.
_Avoid_: Correction decision, unconditional correction

**Action Trial**:
A hardware-feasible phase action physically delivered after its predicted response and prospective value have been locked, but before it is eligible to become the science state.
_Avoid_: Final correction, harmless virtual action, counterfactual observation

**Action Echo**:
A coherent observation acquired after an Action Trial to test whether the delivered field change conforms to its locked prediction; it does not by itself establish image benefit.
_Avoid_: Science observation, restoration truth, residual image

**Post-Echo Decision**:
Exactly one of `admit` or `revert`, selected from the locked prediction and Action Echo before the Prospective Science Observation is acquired.
_Avoid_: Correct/reject switch, post-hoc thresholding on the science frame

**Episode Harm**:
The cumulative adverse cost of every probe, trial, echo, revert, exposure, and final science state in one Adaptive Optics Episode.
_Avoid_: Final-frame harm alone, rejected-trial cost omission

**Prospective Science Observation**:
A causally later raw reference-on detector frame that did not select, tune, or threshold its own correction. A reference-off frame is a structural mechanism ablation, not the default science endpoint.
_Avoid_: Corrected calibration frame, post-processed output, default reference-free frame

**Truth-Blind Policy**:
An estimator and decision rule that receive only declared observations, actions, calibration state, and hardware metadata. Simulated aberration truth is available only to the evaluator.
_Avoid_: Oracle policy, truth-assisted adaptation

## Shared Data and Optics Language

**Raw Sample**:
A source-native image observation with its label, category, and provenance preserved before project preparation.
_Avoid_: Prepared sample, clean target

**Prepared Sample**:
A normalized, resized, and padded image that defines the canonical computational canvas before an intentional experimental transform.
_Avoid_: Perturbed sample, degraded observation

**Perturbed Sample**:
An intentionally transformed prepared sample paired with the prepared reference from which it was derived.
_Avoid_: Prepared sample, universally degraded image

**Encoded Sample**:
A real input image paired with the complex optical field that represents it.
_Avoid_: Task dataset, detected intensity

**Data Stage**:
A composable data block with one fixed position in the source-to-optical-field semantic sequence.
_Avoid_: Complete dataset factory, task dataset

**Optical Primitive Layer**:
A reusable differentiable representation of one optical operation, independent of task topology and readout policy.
_Avoid_: Optical frontend, complete ONN, task model

## Validation Evidence

**Data Validation Figure**:
A regenerable presentation artifact that shows how sample meaning changes across ordered data stages and whether each stage preserves its declared data contract.
_Avoid_: Task-performance figure, complete experiment figure

**Layer Validation Figure**:
A regenerable presentation artifact that shows the physical response and numerical reliability of one optical primitive independently of any task-specific optical system.
_Avoid_: Complete ONN figure, task-performance figure

**Data Validation Sequence**:
The ordered validation view of `Raw -> Prepared -> Perturbed -> Encoded`, combining stage-local evidence with one compact cross-stage summary.
_Avoid_: Scenario-based figure collection, task-recipe gallery

**Canonical Data Validation Sample**:
One deterministically selected FMD microscopy region used throughout the data validation sequence so that visual differences remain attributable to stage transformations.
_Avoid_: Source gallery, MNIST proxy, randomly changing example

**Data Evidence Row**:
An aligned sequence of equal-sized stage views in which every image panel shows the same field of view and carries its own semantically correct colorbar.
_Avoid_: Hero layout, unequal image scale, missing stage colorbar

**Active Image View**:
The disclosed presentation crop that removes numerical padding from `Prepared`, `Perturbed`, and `Encoded` views while leaving the underlying computational canvas unchanged.
_Avoid_: Padded-canvas display, undisclosed crop, modified sample data

**Intensity Encoding Evidence**:
A single encoded field-amplitude view whose deterministic \(A=\sqrt{I}\) relationship is stated in the title or figure legend; its zero-phase contract remains numerical rather than visual evidence.
_Avoid_: Zero-phase image, standalone response curve, duplicate recovered-intensity panel

**Validation Perturbation View**:
One validation-owned, fixed, and explicitly parameterized combination of defocus and photon noise used only to demonstrate the `Perturbed` stage independently of task profiles.
_Avoid_: Restoration profile, task experiment condition, implicit degradation

**Degradation Response Figure**:
A five-row image plate whose rows are Gaussian noise, Poisson–Gaussian noise, Gaussian blur, defocus, and PSF convolution, and whose columns are `Prepared`, `Light`, `Medium`, and `Heavy`. Each row shares one fixed-scale intensity colorbar placed at its far right; severity labels are ordinal within an operator rather than physically equivalent across operators.
_Avoid_: One figure per operator, colorbars between images, raw-image baseline, cross-operator severity equivalence

**Publication-Grade Validation Figure**:
A validation artifact whose composition, typography, and export quality are suitable for publication without making it a task-experiment result.
_Avoid_: Restoration figure, manuscript evidence by appearance alone

## Research Structure

**Restoration Study**:
A complete investigation of one restoration question, including its controlled conditions, evaluations, and claim-facing evidence. It is broader than one run and narrower than the full paper.
_Avoid_: Single run, paper-wide master experiment

**Training Condition**:
One fixed combination of input representation, trainable components, backend architecture, degradation profile, and training protocol.
_Avoid_: Model name, training replicate, benchmark row

**Training Replicate**:
An independently initialized optimization run for the same training condition, differing only in its preregistered training seed.
_Avoid_: Model variant, degradation realization, best-seed run

**Exploratory Prototype**:
A bounded experiment used to accept or reject a mechanism or architecture before formal multi-profile, multi-seed confirmation.
_Avoid_: Formal evidence, failed production model

**Formal Evidence**:
Evidence generated under a frozen protocol across every declared profile and replicate required by a paper claim.
_Avoid_: Single-seed pilot, post-hoc best result

**Research Evidence Chain**:
A traceable sequence from a declared research question and controlled protocol through quantitative evidence to a bounded conclusion and mechanism interpretation. It expresses the substance of completed work without treating activity counts as scientific evidence.
_Avoid_: Workload list, file count, experiment pile

**Canonical Experimental Record**:
The structured, traceable evidence binding a training condition to its data identity, split, seed, frozen protocol, optimization trajectory, per-sample measurements, aggregate metrics, and artifact provenance. It is the primary experimental product from which claims and presentation artifacts are derived.
_Avoid_: Figure folder, checkpoint alone, console log

**Regenerable Presentation Artifact**:
A plot, table, or comparison image deterministically derived from canonical experimental records. It communicates evidence but is not itself the authoritative experimental record.
_Avoid_: Primary data, irreplaceable result, manually edited evidence

**Reusable Model State**:
A checkpoint bound to a canonical experimental record that supports continuation, evaluation, or deployment. It is valuable computational state but is insufficient evidence when detached from its protocol and provenance.
_Avoid_: Complete experiment, metric source of truth, unbound weights

**Claim-Complete Core Matrix**:
The smallest formal training matrix that closes the
`trained_phase_frontend_only`, `digital_backend_only`,
`frozen_frontend_serial`, and `joint_frontend_serial` claims across all
three canonical profiles and three preregistered seeds: 36 runs in total.
_Avoid_: Smoke test, capacity challenge

**Digital Capacity Challenge**:
Nine additional `digital_backend_only` studies using NAFNet-M across the same
three profiles and seeds. They challenge the optical-plus-small-digital claim
with a larger conventional backend without creating a fifth role or expanding
the serial branches. Together with the core, they form the 45-run Fixed archive.
_Avoid_: Fifth role, full capacity ladder, post-hoc model shopping

**Exploratory Hyperparameter Screen**:
A bounded pilot activity used only to choose a stable optimization policy. Its trials and selected checkpoints are not formal evidence and are not runtime dependencies of the fixed-measurement protocol.
_Avoid_: Formal training stage, required calibration, paper result

**Sealed Fixed Training Policy**:
The version-controlled learning and loss policy applied without reading Optuna
or selection artifacts. The 36-run primary matrix uses NAFNet-S and the 6,000-
update ceiling; the nine-run digital-only capacity challenge uses the archived
NAFNet-M 3,000-update boundary. Both serial roles use the seed-matched trained
frontend.
_Avoid_: Runtime calibration, open-ended capacity ladder, eleven-parameter backend, model shopping

**Archived Fixed Training Policy**:
The historical 144-run policy retained only to verify existing core, capacity,
and mechanism artifacts under their original identity.
_Avoid_: New Fixed run, active claim matrix, rewritten archive

**Fixed-Measurement Protocol Archive**:
The read-only, content-hashed data and characterization evidence retained to reproduce the retired fixed-measurement finding. It is historical evidence rather than an active runtime dependency or starting point for adaptive-optics experiments.
_Avoid_: Active training input, adaptive implementation dependency, disposable results folder

**Update-Matched Training Budget**:
A declared training budget expressed as optimizer updates at a fixed effective
batch size, independent of epoch count or device micro-batch packing. All
conditions in the sealed Fixed matrix share the 6,000-update ceiling.
_Avoid_: Epoch-matched budget, wall-clock-matched budget, role-specific advantage

**Archived Budget-Normalized Reporting Cutoff**:
The historical 3,000-update comparison boundary retained for interpreting old
capacity and mechanism trajectories. It does not govern the sealed matrix and
never relabels a later checkpoint as a 3,000-update model.
_Avoid_: Active Fixed budget, early stopping rule, checkpoint rewriting

**Minimal Core Trainable Boundary**:
The preregistered parameter boundary under which
`trained_phase_frontend_only` trains only `phase_mask_fourier`,
`digital_backend_only` trains only its backend, `frozen_frontend_serial`
trains only its backend, and `joint_frontend_serial` trains
`phase_mask_fourier` together with that backend. Reference phase, arm splits
and gains, and connection topology remain fixed.
_Avoid_: All-parameter optimization, architecture-dependent freedom, hidden trainable controls

**Seed-Matched Optical Warm Start**:
The `trained_phase_frontend_only` checkpoint from the same degradation profile
and training seed used to initialize both serial conditions.
`frozen_frontend_serial` keeps its phase mask fixed;
`joint_frontend_serial` continues optimizing it.
_Avoid_: Best-checkpoint reuse, cross-seed initialization, independently initialized serial phases

## Imaging Roles

**Input-Amplitude SLM**:
The pre-split HDSLM80RA Plus that converts a digital target command into the coherent amplitude-encoded input field and remains fixed during one dynamic calibration episode.
_Avoid_: Phase-probe SLM, Fourier-phase SLM, interchangeable HDSLM80R

**Fourier-Phase SLM**:
The independent HDSLM80R Plus in the V-shaped 4f processing arm that carries time-varying spatial phase probes and the held correction.
_Avoid_: Input-image SLM, amplitude encoder, HDSLM80RA Plus

**Phase Command**:
The requested phase-only action before lookup-table response, quantization, spatial crosstalk, drift, or other delivery effects are applied. It records intent and is not evidence of the phase that reached the optical system.
_Avoid_: Delivered phase, displayed bitmap as assumed truth, held correction evidence

**Delivered Phase State**:
The measured or explicitly modelled phase state after declared delivery effects; this is the optical action attached to an observation record.
_Avoid_: Raw phase command, ideal phase assumed after hardware delivery, unnamed SLM state

**Pupil Aberration State**:
A declared pupil-plane phase state represented by normalized modal coefficients or a calibrated physical phase map in a fixed piston gauge.
_Avoid_: Image degradation label, arbitrary Fourier mask, unregistered SLM texture

**Reference-Assisted Dynamic Bench**:
The two-arm coherent bench in which a mechanically fixed reference relay interferes with a V-shaped 4f phase-processed arm before the current science camera. Processing-SLM piston supplies rapid phase diversity; the bench validates a replayed-field optical mechanism and is not by itself native-specimen microscopy AO.
_Avoid_: Single-SLM 4f path, real-time AO, native fluorescence AO

**Monochrome Interference Observation**:
The intensity-only frame recorded by the ASI585MM after the reference and processing fields have coherently recombined. Relative phase or complex field is inferred from multiple declared optical states rather than measured directly by the camera.
_Avoid_: Camera complex field, phase image, Fourier-SLM raster

**Simulation Observation Grid**:
The 512 by 512 detector-coordinate grid used for bounded scientific simulation independently of the native camera raster.
_Avoid_: Native ASI585MM frame, Fourier-phase grid, assumed one-to-one camera mapping

**Native Camera Frame**:
The original ASI585MM intensity acquisition retained before any calibrated crop, registration, or resampling into an analysis grid.
_Avoid_: Simulation observation, pre-aligned science image, complex-field measurement

**Fixed Measurement**:
Target-supervised restoration in which clean references may guide offline
optimization of one specimen-independent optical action and any declared
digital backend, while the deployed optical action is frozen and cannot depend
on observations from the current episode.
_Avoid_: Historical archive, per-sample target-conditioned phase, adaptive restoration

**Fixed Input-Mode Comparison**:
A target-supervised four-role comparison:
`trained_phase_frontend_only` establishes the capacity of one
specimen-independent trained phase; `digital_backend_only` provides the direct
restoration reference; `frozen_frontend_serial` isolates the representation
change by training the common digital backend behind a fixed, seed-matched
front end; `joint_frontend_serial` tests whether co-adaptation of that front end
and the same backend can overcome the mismatch. `reference_arm_only`,
`zero_phase_processing_arm_only`, and `trained_phase_processing_arm_only` are
recorded branch controls rather than extra digital training conditions. Their
coherent sums with the reference field are named zero-phase and trained-phase
interference outputs, never processing-arm-only observations.
_Avoid_: `digital_from_*`, parameter-count competition, eleven-parameter claim, adaptive episode

**Frozen Serial Restoration**:
A target-supervised optical--digital condition named
`frozen_frontend_serial` and initialized from the seed-matched
`trained_phase_frontend_only` checkpoint. The phase is held constant while only
the common digital backend is trained, isolating the effect of the optical
representation presented to that backend.
_Avoid_: Joint optimization, adaptive phase update, zero-phase digital baseline

**Joint Serial Restoration**:
A target-supervised optical--digital condition named `joint_frontend_serial`
and initialized from the same seed-matched `trained_phase_frontend_only`
checkpoint. The phase and common digital backend are optimized together
offline, while the deployed phase remains independent of the specimen observed
at inference time.
_Avoid_: Per-sample phase, adaptive episode, independently initialized serial phase

**Fixed Physical Control Record**:
An evaluation-only record of `reference_arm_only`,
`zero_phase_processing_arm_only`, and `trained_phase_processing_arm_only`.
Each arm-only name means that the other arm is physically or numerically
blocked. The corresponding zero-phase and trained-phase interference outputs
are derived or acquired with both arms enabled. These records characterize the
shared optical topology; they do not create additional training roles.
_Avoid_: Frontend used as an arm name, six-peer training matrix, learned backend, omitted arm-blocking state

**Mixed-Measurement Restoration**:
Restoration in which conventional and optical observations are distinct, energy-matched measurements under scene- or realization-dependent physical degradation.
_Avoid_: Replacement data bus, fixed-measurement restoration

**Adaptive Measurement**:
Measurement-conditioned restoration in which each phase decision may use only
earlier acquired observations, delivered actions, calibration state, and
hardware metadata from the current episode. Clean references and aberration
truth remain evaluator-only during deployment, even when an estimator was
trained offline with labelled episodes.
_Avoid_: Temporal burst restoration, target-visible online optimization, oracle correction

**Quasi-Static Prescan-and-Hold AO**:
A microscopy protocol in which independently read phase-diverse calibration observations select a locally deployable correction that is held fixed for one or more later science observations. Its validity requires the specimen and aberration to remain stable over the complete calibration-and-acquisition cycle.
_Avoid_: Real-time AO, long-exposure temporal coding, eight-mask integrated exposure

**Adaptive Optics Episode**:
One causally ordered cycle of pre-action sensing, prediction locking, optional probing, physical trial, Action Echo, admission or reversion, and a separate Prospective Science Observation within a declared calibration scope.
_Avoid_: Training batch, integrated coded exposure, fixed-measurement run

**Pre-Detection Correction**:
Physical wavefront intervention applied before the science observation is detected, so that recoverable light is redirected by the optical system rather than reconstructed only from an already measured image.
_Avoid_: Digital deblurring, image re-display, post-detection optical encoding

**Science Observation**:
A later raw reference-on observation acquired only after the selected correction has been loaded and settled; it evaluates pre-detection correction and cannot causally select its own mask. A reference-off observation is a separately named mechanism ablation.
_Avoid_: Final calibration probe, self-corrected eighth frame, reconstruction target

**Calibration Scope**:
The declared reuse boundary of a correction: instrument-wide, slide-wide, or local to one isoplanatic field and depth. A local correction must not be reported as slide-wide without validation on independent fields.
_Avoid_: Universal calibration, unqualified pre-calibration, globally adaptive mask

**Active Identification Measurements**:
Independently read calibration observations whose declared low-dimensional probes reduce uncertainty about aberration and nuisance state before a confidence gate stops acquisition.
_Avoid_: Fixed six-frame prefix, arbitrary SLM masks, direct 262,144-variable phase search

**Uncertainty-Resolving Measurement**:
An optional calibration observation selected from the remaining posterior uncertainty to distinguish degradation explanations that would imply materially different corrections.
_Avoid_: Mandatory seventh exposure, validation-set image, science observation

**Held Correction State**:
The calibrated, physically deployable optical state selected after identification and held unchanged while one or more causally separate science observations are acquired.
_Avoid_: Mandatory eighth probe, self-correcting exposure, unconstrained phase tensor

**Degraded Observation (D)**:
The already-degraded, already-noisy image produced by the upstream microscope and available to the restoration system.
_Avoid_: Raw image, clean input

**Historical Fixed Optical Front End**:
The archived coherent Fourier-plane transformation whose trainable element is a fixed phase mask and whose detected output is derived from a replayed degraded observation.
_Avoid_: Intelligent optical front end, optical backend, generic image-to-image network

**Numerical Fourier-Plane Sampling Pitch**:
The physical-coordinate interval represented by one FFT-grid sample, computed as wavelength times focal length divided by the input sample count and input-plane pixel pitch. Under the canonical 638 nm, 0.1 m, 512-sample, and 8 micrometre configuration it is 15.576171875 micrometres; it is not the physical SLM2 pixel pitch.
_Avoid_: SLM pixel size, learned phase value, optical resolution

**Computational Fourier-Phase Grid**:
The canonical 512 by 512 coordinate lattice on which `phase_mask_fourier` is optimized. Each index is aligned with one centred FFT sample and carries the corresponding 15.576171875 micrometre Fourier-plane coordinate; the grid is independent of the native SLM2 raster.
_Avoid_: Camera grid, SLM2 active window, index-stretched hardware texture

**Fourier-Grid Phase Solution**:
The canonical 512 by 512 trained phase solution in which each `phase_mask_fourier` value belongs to one numerical Fourier sample at its derived physical coordinate. It is the optimization result retained in checkpoints and remains independent of any particular SLM rasterization.
_Avoid_: SLM bitmap, 16 micrometre hardware macropixel model, stretched phase texture

**Direct Fourier-Grid Training**:
The canonical training policy in which the 512 by 512 learned phase is multiplied elementwise with the equally sized centred Fourier spectrum. Its physical sample pitch is the geometry-derived 15.576171875 micrometres, and no SLM rasterization, deployment interpolation, phase quantization, or hardware lookup table participates in optimization.
_Avoid_: Hardware-aware fine-tuning, 16 micrometre training pitch, train-time SLM upsampling

**SLM2 Deployment Projection**:
A physical-coordinate transformation that places a Fourier-Grid Phase Action onto the native 8 micrometre SLM2 canvas using optical geometry and measured registration. The canonical 15.576171875 micrometre Fourier sampling is approximately, but not exactly, two SLM pixels per axis and therefore cannot be implemented as integer pixel replication.
_Avoid_: Index-only image resize, implicit two-times upsampling, four-pixel replication

**Physical SLM2 Pixel Pitch**:
The centre-to-centre spacing of the Fourier-plane SLM hardware pixels, currently 8 micrometres. Phase masks are mapped between this hardware coordinate system and the numerical Fourier grid rather than treating their pitches as identical.
_Avoid_: Numerical Fourier-plane sampling pitch, FFT bin spacing

**Optical Restoration Representation (O)**:
The physics-shaped intensity representation produced by the optical frontend. It may improve restoration metrics without being a clean-image-domain estimate.
_Avoid_: Clean optical image, optically restored ground truth

**Digital-Only Baseline**:
A digital restoration backend trained and evaluated directly on the degraded observation under the shared data, budget, and metric protocol.
_Avoid_: No-optics ablation of a hybrid checkpoint, numerical upper bound

## Coupling and Attribution

**Naive Serial Coupling**:
An optical-digital arrangement in which the optical restoration representation is the digital backend's sole image input.
_Avoid_: Optical-digital synergy, relay

**Optical-Digital Relay**:
A coupling mechanism that preserves the degraded observation as an anchor while exposing separately attributable optical cues to the digital backend.
_Avoid_: Naive serial coupling, unqualified feature concatenation

**Matched D-Only Control**:
An independently trained control with the same digital architecture, capacity, data, seed policy, and budget as a hybrid condition, but without optical inputs.
_Avoid_: Same-checkpoint optical zeroing, unmatched digital baseline

**Same-Checkpoint Optical Zeroing**:
An inference intervention that neutralizes optical channels without changing a trained hybrid checkpoint. It measures optical dependence of that checkpoint, not unique optical performance value.
_Avoid_: Matched D-only control, proof that optics improve accuracy

**Optical Residual Gate**:
A trainable scalar \(\gamma\) in \(D+\gamma(O-D)\), bounded to the open unit interval by a sigmoid parameterization. It measures whether a coupled restoration model retains the optical increment relative to the degraded observation. \(\gamma=0\) is the limiting degraded-observation path and \(\gamma=1\) is the limiting full-optical path. Its training curve is mechanism evidence, while same-checkpoint interventions at zero, the learned value, and one are required to establish optical dependence.
_Avoid_: Process-path field gain, optical attribution gap, proof of unique optical value

**Process-Path Field Gain Probe**:
A sensitivity intervention that rescales the processed optical field relative to the reference field before coherent detection. A zero perturbation preserves the original process-path gain and does not remove the optical frontend.
_Avoid_: Optical residual gate, optical channel zeroing, digital fusion weight

**Optical Attribution Gap**:
The paired performance change of one trained system when optical cues are available versus neutralized. It must be reported separately from the comparison against an independently trained matched D-only control.
_Avoid_: Hybrid gain, independently trained model difference

**Process-Arm Perturbation Coefficient**:
A diagnostic coefficient that changes the process-arm complex-field amplitude around the fixed splitter-defined operating point. Zero preserves the original optical frontend and therefore cannot represent collapse of the direct optical image passthrough.
_Avoid_: Optical residual gate, trainable splitter ratio, optical image gain

**Mechanism Evidence**:
Controlled evidence that distinguishes why an optical-digital system succeeds or fails, including phase interventions, arm controls, spectral analysis, and input-domain diagnostics.
_Avoid_: Uncontrolled benchmark delta
