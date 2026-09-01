# GPT Pro Deep Research Prompt: Dynamic Adaptive Optical Restoration

## Role

Act as an adversarial interdisciplinary research team with expertise in:

- computational imaging and inverse problems;
- digital image restoration;
- Fourier optics and interferometry;
- adaptive optics for microscopy;
- optical neural networks and physical neural networks;
- active experimental design and phase retrieval;
- uncertainty calibration, selective prediction, and safe decision-making;
- scientific hardware validation.

You are not being asked to endorse a proposed method, write promotional
manuscript prose, or generate implementation code. Your task is to determine
whether the proposed research direction is physically feasible, scientifically
distinctive, and experimentally defensible.

## Input Material

You will receive this prompt together with a companion attachment titled
**Restoration Foundations**.

Treat the companion attachment as a provisional, locally prepared research
brief. It is not an authority and must not be cited as external evidence.
Decompose it into atomic claims and independently verify, qualify, or reject
each claim using web-accessible sources.

Do not assume access to a code repository, local paths, internal documents,
or unpublished result folders. The only local implementation evidence
available to you is reproduced verbatim in the companion attachment.

## Mission

Perform a deep, source-grounded comparison across:

1. the cross-domain history and applications of image restoration;
2. digital post-detection restoration;
3. classical and modern adaptive optics;
4. optical neural networks and physical optical computing;
5. classical and programmable 4f spatial filtering;
6. the fixed optical-restoration evidence summarized in the attachment;
7. the proposed dynamic, active, risk-aware optical measurement scheme.

The central question is:

> Under unknown specimens and finite photons, exposures, camera reads, SLM
> states, settling time, computation, and calibration overhead, can a
> fixed-reference, phase-only adaptive optical system decide what to measure,
> when to stop, and when not to apply a correction, while improving a causally
> later reference-free raw science observation?

Do not reduce this question to “is adaptive optics useful?” That is already
established. Determine whether the complete causal and decision contract is
new, physically valid, and advantageous against the strongest existing
methods.

## Frozen Candidate Contract

Treat the following as immutable constraints for the main candidate, not as
design suggestions.

| Invariant | Required interpretation | Forbidden silent change |
|---|---|---|
| Reference command | \(\delta_{\mathrm{ref}}^{\mathrm{cmd}}=0\) rad | tuning, learning, scanning, or adapting the delay-line phase |
| Delivered reference phase | drift \(\epsilon_{\mathrm{ref}}(t)\) is measured or modelled as a nuisance, never controlled during an episode | assuming exact zero without evidence or compensating drift by adapting the delay line |
| Adaptive actuator | one HDSLM80R Plus phase-only SLM in the V-shaped 4f processing arm | replacing it with a DM, amplitude modulator, or arbitrary complex modulator |
| Input-amplitude device | an independent pre-split HDSLM80RA Plus, fixed throughout an episode, with its own response model and LUT | using it as an additional dynamic probe or treating the two SLMs as interchangeable |
| Acquisition ceiling | at most eight independently read calibration observations before the decision; probe count is adaptive | prescribing eight probes, exceeding the ceiling, or using later science frames as calibration |
| Reference arm | calibration observations only | retaining it in the claim-facing science observation |
| Science observation | acquired after correction loading and settling | using a calibration frame to choose or prove its own correction |
| Core output | physically corrected raw detector frame | adding a post-detection restoration network to obtain the claimed output |
| Core scope | local, quasi-static microscopy | silently changing to fast atmospheric AO or an unrelated imaging regime |

Any method that requires relaxing one of these constraints must be reported as
an **incompatible alternative**, not substituted for the main candidate.

The command and delivered reference phases are distinct:

\[
\delta_{\mathrm{ref}}^{\mathrm{cmd}}=0,\qquad
\delta_{\mathrm{ref}}^{\mathrm{delivered}}(t)
=\epsilon_{\mathrm{ref}}(t).
\]

The nuisance \(\epsilon_{\mathrm{ref}}\) may be estimated and used for
uncertainty or abstention, but not corrected through episode-level delay-line
control. Science exposures are causally separate from the \(T\leq8\)
calibration ceiling and must still be included in the total budget.

### Important phase distinction

The fixed reference-arm command is not the same as the effective arm-relative
phase. In the ideal scalar compact-4f model, and only when the delivered piston
acts as a uniform phase factor over the admitted spectrum, let the dynamic SLM
pattern be

\[
\Phi_t(\mathbf k)=\widetilde\Phi_t(\mathbf k)+c_t,
\]

then its global piston \(c_t\) changes the processing-arm phase even though the
delay line remains fixed:

\[
Y(\delta_{\mathrm{ref}},\Phi+c)
=
Y(\delta_{\mathrm{ref}}-c,\Phi).
\]

You must decide whether the global piston should:

- remain an explicit, budgeted SLM probe dimension; or
- be gauge-fixed while spatial phase diversity supplies identifiability.

Do not describe SLM piston as delay-line adjustment.
Test whether phase–amplitude coupling, zero-order leakage, quantization, or
polarization mismatch invalidates the ideal identity on the real device.

## Non-Negotiable Research Rules

1. Search first; write the narrative only after completing evidence tables.
2. Prefer peer-reviewed primary papers and official publisher pages.
3. Use reviews for navigation, not as the sole support for novelty.
4. Label preprints explicitly and do not merge them with peer-reviewed
   evidence.
5. For every strong claim, provide a DOI or stable official article URL and,
   when full text is available, a section, figure, table, or supplementary
   location.
6. Record inaccessible full texts and unreported fields as `NR`; never infer a
   favorable result from missing information.
7. Separate author-reported fact, direct data support, reviewer inference, and
   hypothesis.
8. “No exact match found” is not permission to claim global first.
9. Do not invent pilot thresholds, effect sizes, phase ranges, timings, or
   correction budgets.
10. Do not generate implementation code or a code architecture. Produce
    implementation-shaping scientific requirements only.
11. Write the final report in Chinese while preserving established English
    technical terms, symbols, paper titles, and search queries.

## Required Workflow

Complete the stages below in order. A missing required table or analysis means
the next stage is not yet authorized.

End every stage with:

- `Gate status: Pass / Fail / Unresolved`;
- blocking questions and their evidence IDs;
- the consequence for later stages.

A structurally complete table containing `NR` is not an evidentiary pass.
Critical unresolved gates cannot produce an unconditional `Continue`.

### Stage 0 — Contract Audit

Begin by reproducing an
`Invariant / Physical meaning / Allowed operation / Forbidden deviation`
table.

Confirm that your interpretation preserves:

- \(\delta_{\mathrm{ref}}^{\mathrm{cmd}}=0\) while delivered drift remains an
  uncontrolled nuisance;
- two independent SLMs with separate locations, roles, response models, and
  LUTs;
- one dynamic phase-only SLM;
- a held amplitude SLM;
- \(T\leq8\) independently read pre-decision calibration observations without
  prescribing eight;
- calibration-only reference interference;
- reference-free independent science acquisition;
- no claim-facing digital restoration output.

List any ambiguity before research begins. Do not resolve ambiguity by silently
changing the contract.

### Stage 1 — Search Protocol

Report:

- databases and publisher platforms;
- date of search;
- full query strings;
- time range;
- inclusion and exclusion criteria;
- backward and forward citation tracing;
- deduplication rule;
- API, rate-limit, paywall, and full-text failures.

Use DOI as the primary deduplication key. When DOI is unavailable, use
normalized title plus first author and mark the match as metadata-based.

Search foundational literature without a date cutoff. For the competitive AO,
ONN, and active-imaging landscape, prioritize 2015–2026 while retaining
earlier direct ancestors.

### Stage 2 — Cross-Domain Search Scope

Define the search and evidence matrix in this order:

1. astronomy;
2. remote sensing;
3. computational photography and low-light imaging;
4. industrial, security, and scientific imaging;
5. biomedical imaging;
6. microscopy as the final target family.

For every domain, identify:

- dominant degradation and measurement model;
- whether restoration is pre-detection, acquisition-coded, or post-detection;
- scientific or task-level objective;
- primary evidence;
- limits on transferring its conclusions to microscopy.

Do not use a list of applications as decoration. Explain how the measurement
and evidence contract changes between fields. At this stage, identify
questions, queries, and required evidence only; do not write findings or a
literature narrative before Stage 5.

### Stage 3 — Method-Family Search Scope

Define the method-family queries, comparison fields, and evidence requirements
below. Do not issue a method verdict or write the synthesis before Stage 5.

#### 3A. Digital restoration

Cover at minimum:

- Richardson–Lucy and explicit inverse methods;
- Tikhonov/TV and statistical regularization;
- sparse representation and low-rank priors;
- plug-and-play and deep unfolding;
- CNN/U-Net/ResNet restoration;
- GAN/perceptual restoration;
- Transformer restoration;
- diffusion/posterior-sampling methods;
- self-supervised, zero-shot, and object-specific neural representations.

For each family, compare:

- forward-model dependence;
- prior source;
- data fidelity;
- OOD behavior;
- hallucination or null-space risk;
- training requirement;
- latency and memory;
- hardware used.

Use the following safe compute wording unless evidence supports something more
specific:

> High-capacity digital restoration may use high-performance computing devices
> such as GPUs, NPUs, or dedicated AI accelerators; actual latency and energy
> depend on model, resolution, precision, compiler, I/O, and deployment
> platform.

Do not relabel a mobile CPU/GPU pipeline as NPU-based without evidence. Do not
generalize a result measured on one GPU to all GPUs or NPUs.

#### 3B. Classical adaptive optics

Separate:

- sensing: direct WFS, sensorless metric optimization, phase diversity,
  learning-assisted sensing;
- representation: Zernike, other modal bases, influence functions,
  device-native modes, pixel phase;
- control: open loop, closed loop, fixed probe, active probe,
  prescan-and-hold, recalibration;
- corrector: DM, LC-SLM, and other devices.

Zernike is a representation, not a wavefront sensor.

Compare DM and LC-SLM by bandwidth, stroke, spatial degrees of freedom,
polarization, wavelength, efficiency, LUT, crosstalk, and stability. Do not
declare either device universally superior.

#### 3C. Optical neural networks

Cover:

- passive diffractive networks;
- programmable Fourier processors;
- optical convolution/matrix multiplication;
- hybrid optoelectronic networks;
- physics-aware, in-situ, and fully forward training;
- optical image reconstruction and denoising.

Audit end-to-end rather than optical-core-only latency and energy. Include
source, encoding, modulator refresh, conversion, detector, ADC/DAC, electronic
control, calibration, and error correction.

Determine whether existing work merely reports optimized points or explicitly
maps a hardware-feasible, failure, or safe operating region.

#### 3D. 4f spatial filtering

Cover:

- complex spatial filtering;
- matched and correlation filtering;
- low/high/band-pass filtering;
- phase contrast and differentiation;
- inverse filtering;
- programmable SLM filtering;
- phase-only encoding of complex transfer functions.

Explicitly test these propositions:

1. a 4f system is not inherently static;
2. a single direct phase-only mask is not an arbitrary complex transfer
   function;
3. an OTF zero cannot be inverted into measured evidence without additional
   information;
4. interpretability of \(H(\mathbf k)\) does not guarantee correctness or
   stability.

### Stage 4 — Exact-Neighbor and Adjacent-Prior Search

Search both complete combinations and component combinations. Do not search
only the candidate’s custom terminology.

#### Exact-neighbor queries

Adapt syntax to each database and preserve the exact queries in the search log.

```text
("fluorescence microscopy" OR "two-photon microscopy" OR
 "multiphoton microscopy" OR "widefield microscopy" OR
 "phase microscopy")
AND ("adaptive optics" OR "sensorless adaptive optics")
AND ("phase diversity" OR "image-based wavefront sensing")
AND ("spatial light modulator" OR SLM OR "phase-only")
```

```text
microscopy AND "adaptive optics"
AND ("adaptive probe" OR "active probe" OR "next probe" OR
     "sequential phase diversity" OR "adaptive phase diversity")
AND (uncertainty OR confidence OR posterior OR stopping)
```

```text
microscopy AND "adaptive optics"
AND (abstain OR abstention OR "reject correction" OR
     "safe correction" OR "harmful correction" OR
     "failure detection")
```

```text
("unknown extended object" OR "extended fluorescent object")
AND ("phase diversity" OR "wavefront sensing")
AND ("phase-only" OR SLM)
AND ("physical correction" OR "pre-detection correction")
```

```text
microscopy AND ("reference arm" OR interferometric)
AND ("adaptive optics" OR "wavefront correction")
AND ("calibration only" OR "calibration phase")
AND (SLM OR "phase modulator")
```

```text
microscopy AND SLM AND "adaptive optics"
AND (LUT OR quantization OR crosstalk OR polarization OR
     registration OR conjugation OR settling OR drift)
```

#### Adjacent-prior queries

```text
("wavefront sensing" OR "phase retrieval")
AND ("Bayesian experimental design" OR "optimal experiment design" OR
     "adaptive measurement" OR "sequential design")
AND (probe OR diversity OR modulation)
```

```text
("phase diversity" OR "focal plane wavefront sensing")
AND (Fisher OR information OR Bayesian OR posterior)
AND (adaptive OR sequential OR optimized)
```

```text
microscopy AND ("adaptive acquisition" OR "active acquisition")
AND (uncertainty OR conformal OR confidence OR risk)
```

```text
microscopy AND ("selective prediction" OR abstention OR
                "risk coverage" OR "conformal risk control")
```

```text
("spatial light modulator" OR "phase-only SLM")
AND (calibration OR interferometry)
AND (LUT OR "phase response" OR crosstalk OR drift OR
     flicker OR settling OR registration)
```

```text
("phase-only correction" OR "phase-only wavefront shaping")
AND ("amplitude scattering" OR "multiple scattering" OR
     depolarization OR "complex field")
AND (limit OR bound OR failure)
```

#### Mandatory seed papers

Use these only as seeds for citation tracing:

- [REALM](https://doi.org/10.1038/s41467-021-23647-2)
- [MLAO](https://doi.org/10.1038/s41377-023-01297-x)
- [DL-AO](https://doi.org/10.1038/s41592-023-02029-0)
- [Label-free AO-SMLM](https://doi.org/10.1038/s41467-023-39896-2)
- [Phase-diversity fluorescence microscopy](https://doi.org/10.1364/OPTICA.518559)
- [CoCoA](https://doi.org/10.1038/s42256-024-00853-3)
- [Uncertainty-driven adaptive scanning](https://doi.org/10.1364/OE.542640)
- [Fisher-information sensorless AO, preprint](https://doi.org/10.48550/arXiv.2506.07482)
- [NeAT](https://doi.org/10.1038/s41592-026-03053-6)
- [MeNet-AO, peer-reviewed early-access](https://doi.org/10.1038/s41467-026-73389-2)

For each possible novelty component, search it alone, in pairs, in triples, and
as the full combination. Report `Found / Partially found / Not found`, together
with missing components.

### Stage 5 — Evidence Extraction

Complete the evidence table before writing the literature narrative. Use one
row per paper and never omit a field.

| Field group | Required fields |
|---|---|
| Identity | title, authors, year, venue, DOI/URL, peer-reviewed/preprint, full-text status |
| Claim | author claim, exact evidence location, supportable scope |
| Scene | modality, specimen, depth, FOV/isoplanatic scope |
| Observation | observable, probe/frame count, fixed/adaptive sequence |
| Model | unknowns, nuisance variables, assumptions |
| Action | representation, corrector, optical position, phase-only or not |
| Causality | calibration/science relation, independence of science evidence |
| Truth | injected phase, SHWS/DWS, interferometer, phase retrieval, or none |
| Hardware | LUT, stroke, quantization, registration, conjugation, polarization, loss, settling, drift |
| Budget | calibration/science dose and detected photons, exposures, reads, device states, acquisition/settling/online-compute/wall time, offline compute, correction lifetime and amortization |
| Comparison | baselines, tuning fairness, same specimen/distribution, matched budget |
| Outcome | wavefront, raw-science, transfer, biological metrics, statistical unit and repeats |
| Failure | SNR/SBR, aberration range, motion, OOD, spatial variation, harmful cases |
| Risk | uncertainty type, calibration, stopping, abstention, safe action |
| Competition | exact overlap, remaining difference, novelty threat |
| Missing | every `NR` field and its impact |

Tag each extracted statement:

- `Author-reported fact`
- `Directly supported by data`
- `Reviewer inference`
- `Not reported`

Only after the evidence table is complete, write the cross-domain background
and method-family synthesis specified in Stages 2 and 3. Every substantive
sentence in that synthesis must map to evidence-table IDs.

### Stage 6 — Formula and Identifiability Audit

#### 6A. Unified measurement chain

Start from

\[
Y\sim
p\!\left(
y\mid O,\psi,h,A_0,u,R
\right),
\]

where:

- \(O\) is the unknown specimen/object;
- \(\psi\) is sample and system aberration;
- \(h\) is hardware state and mismatch;
- \(A_0\) is the episode-held, pre-split amplitude-SLM state on the replay
  bench;
- \(u=e^{i\Phi}\) is the phase-SLM action;
- \(R\) is the calibration reference-arm state.

Derive separate candidate models for:

- coherent transmission/phase microscopy;
- reflection microscopy;
- incoherent fluorescence detection;
- two-/three-photon excitation AO;
- the replayed-field compact 4f bench.

Do not force them into one coherent-field equation.
For native microscopy, determine whether the input-amplitude device has a
fixed illumination role, is held at identity, or makes the replay topology
inapplicable. Never treat \(A_0\) as a native specimen.

#### 6B. Calibration and science observations

The candidate calibration observation is

\[
C_t\sim
p\!\left(
c\mid O,\psi,h,A_0,u_t,R=1,
\delta_{\mathrm{ref}}^{\mathrm{cmd}}=0,
\delta_{\mathrm{ref}}^{\mathrm{delivered}}
=\epsilon_{\mathrm{ref}}(t)
\right).
\]

The science observation is

\[
Y_{\mathrm{sci}}(a)
\sim
p\!\left(
y\mid O,\psi,h,A_0,u_a,R=0
\right).
\]

Audit the domain shift created by removing the reference arm. Determine whether
the action identifiable from \(C_{1:t}\) is beneficial for \(Y_{\mathrm{sci}}\).

#### 6C. Prospective benefit and harm

\[
\Delta(a)
=
M[Y_{\mathrm{sci}}(a)]
-M[Y_{\mathrm{sci}}(a_{\mathrm{safe}})].
\]

Define \(M\) so that larger is always better.

\[
H(a)
=
\mathbb 1[
\Delta(a)<-\tau_{\mathrm{harm}}
].
\]

Keep \(\delta_{\mathrm{ref}}\) and \(\tau_{\mathrm{harm}}\) distinct.
\(\delta_{\mathrm{ref}}^{\mathrm{cmd}}=0\) is a frozen optical command in
radians. \(\tau_{\mathrm{harm}}\geq0\) has the units of \(M\). A strict
no-harm analysis uses \(\tau_{\mathrm{harm}}=0\); a nonzero practical margin
must come from preregistered detector/system repeatability, never test-set
tuning.

Evaluate a harm-risk gate such as

\[
\Pr[
H(a)=1
\mid C_{1:t}
]
\leq\alpha
\]

or, under a compatible calibrated bound,

\[
\operatorname{LCB}_{1-\alpha}
[
\Delta(a)\mid C_{1:t}
]
\geq
-\tau_{\mathrm{harm}}.
\]

If the method claims a minimum positive benefit, define a different threshold
\(\tau_{\mathrm{gain}}\geq0\) and require

\[
\operatorname{LCB}_{1-\alpha_{\mathrm{gain}}}
[
\Delta(a)\mid C_{1:t}
]
>
\tau_{\mathrm{gain}}.
\]

If a required gate fails, determine when another probe has positive expected
decision value and when the system should abstain.

#### 6D. Required identifiability questions

1. Can unknown object and aberration be separated from the available
   intensities?
2. Are global piston, phase sign, conjugation, defocus, or symmetric modes
   ambiguous?
3. Do object-spectrum or OTF zeros hide action-relevant modes?
4. Are reference amplitude/phase, specimen aberration, system aberration, LUT
   error, and registration error confounded?
5. If the full state is not identifiable, is the correction action
   identifiable as an equivalence class?
6. Does SLM global piston help phase diversity, or merely exchange gauge with
   the fixed reference phase?
7. Does removing the reference arm change the optimal action?
8. What is the phase-only oracle bound under amplitude scattering,
   depolarization, and multiple scattering?
9. Does a held correction improve one ROI while harming adjacent field/depth?
10. Is uncertainty calibrated to future \(\Delta\), or only to coefficient
    error or reconstruction loss?

### Stage 7 — Hardware, Causality, and Budget Audit

#### Hardware

Require evidence for:

- separate response models and LUTs for the pre-split HDSLM80RA Plus and the
  Fourier-plane HDSLM80R Plus;
- wavelength- and polarization-specific LUT;
- phase range, wrapping, quantization, and phase–amplitude coupling;
- pixel crosstalk, fill factor, and zero-order leakage;
- pupil conjugation and camera/SLM registration;
- insertion loss and arm-energy split;
- refresh, settling, flicker, temperature, and session drift;
- delivered phase rather than commanded phase.

#### Causality

Audit the chain:

\[
\text{calibration observations}
\rightarrow
\text{decision}
\rightarrow
\text{delivered correction}
\rightarrow
\text{settling}
\rightarrow
\text{independent raw science observation}.
\]

Identify every route by which exposure, gain, background subtraction,
normalization, registration, averaging, or post-processing could explain an
apparent benefit.

#### Budget

Use the full vector

\[
B=
(
N_{\gamma,\mathrm{cal}},
N_{\gamma,\mathrm{sci}},
N_{\mathrm{exposures,cal}},
N_{\mathrm{exposures,sci}},
N_{\mathrm{reads}},
N_{\mathrm{SLM\ states}},
T_{\mathrm{acquisition}},
T_{\mathrm{settling}},
T_{\mathrm{online\ compute}},
T_{\mathrm{wall}},
L_{\mathrm{correction}}
).
\]

Report incident dose and detected photons separately where meaningful.
Also report offline training data and compute, calibration lifetime and
amortized overhead, and compute platform, precision, memory, and energy when
making speed or efficiency claims.

Only call a comparison matched-budget when all material coordinates are
matched. If a preregistered exchange or normalization rule is scientifically
valid, report both the raw coordinates and that rule. Otherwise, report a
resource–performance frontier rather than calling it matched-budget.

### Stage 8 — Companion Report Audit

Split the companion brief into atomic claims. The number of atomic claims
identified must equal the number of audit rows; do not hide several claims in
one row. Produce:

| Claim ID | Atomic claim | Type | Verdict | Primary source ID and exact anchor | Evidence status | Counterevidence | Missing evidence | Frozen-contract check | Corrected wording | Design consequence | Confidence |
|---|---|---|---|---|---|---|---|---|---|---|---|

Allowed verdicts:

- `Agree`
- `Qualify`
- `Reject`

Rules:

- `Type` must be one of `fact / mechanism / performance / novelty / scope /
  inference / recommendation`.
- `Evidence status` must be `supported / contradicted / NR`.
- `Agree` requires primary evidence supporting the same scope and causal
  strength.
- `Qualify` is required when evidence is insufficient but not contradictory,
  or when modality, specimen, hardware, budget, publication status, or causal
  interpretation differs. Use `Qualify — not established` for an unresolved
  claim.
- `Reject` is required when the claim conflicts with data, depends on an
  uncontrolled confound, violates the frozen contract, or turns absence of
  evidence into global novelty.
- A preprint-only basis cannot receive an unqualified mature-field `Agree`.

Also report:

1. conclusions present in the companion brief but unsupported;
2. important literature or failure modes omitted from it;
3. citations whose metadata, status, or interpretation is incorrect;
4. a corrected replacement outline for the background and working-principles
   document.

### Stage 9 — Experimental Contract and Kill Tests

#### Required baselines

- no AO;
- system-only correction;
- known-aberration phase-conjugate oracle;
- classical modal sensorless AO;
- conventional phase diversity;
- strongest optimized fixed probe codebook;
- Fisher-information-optimized probes;
- MLAO/MeNet-style learning-assisted AO;
- direct wavefront sensing where available;
- computational AO;
- strong digital restoration as an external absolute-performance comparator.

For each baseline, specify its observable, action representation, tuning
budget, calibration/science dose and exposures, reads, device states, settling,
online compute, end-to-end wall time, hardware, and output type. An algorithm
name alone is not a baseline specification. Digital restoration remains an
external absolute-performance comparator; do not merge its processed output
with the raw-science causal comparison.

#### Kill tests

Evaluate at minimum:

- exact peer-reviewed prior;
- three oracle levels: ideal complex-field, ideal phase-only, and calibrated
  hardware-delivered phase-only headroom;
- correction-action identifiability under the frozen reference command,
  phase-only actuator, and allowed probes;
- best fixed codebook;
- Fisher-optimal probes;
- reference-on calibration to reference-off science transfer;
- uncertainty calibration after adaptive acquisition;
- selective risk at matched coverage;
- always-correct, never-correct, last-trusted, and simple-threshold policies;
- calibration/science circularity;
- photons/reads/states/settling/compute confounding;
- delivered-phase hardware gap;
- sham, random-phase, opposite-sign, and equal-RMS controls;
- optimized-metric versus independent-science Goodhart failure;
- specimen, aberration, SNR, LUT, polarization, registration, and drift OOD;
- isoplanatic field/depth harm;
- held-correction lifetime and amortization;
- replayed-field versus native-specimen transfer;
- hidden post-processing dependence.

For each kill test, state:

- what evidence currently exists;
- the minimum decisive experiment;
- endpoint and direction;
- preregistered threshold;
- sample or replicate unit;
- confidence interval or risk bound;
- the identity of the independent science observation;
- the complete matched budget;
- whether it is a hard kill or a scope-narrowing test;
- which claim is killed if it fails;
- whether the route should Continue, Narrow, or Kill.

State-action ambiguity is acceptable only when an action-equivalence class is
identifiable. If the correction action itself is not identifiable, kill the
main candidate. Uncertainty must be calibrated to future
\(\Delta/H\) after adaptive acquisition and optional stopping, not merely to
wavefront coefficients. Compare risk–coverage policies on a shared coverage
grid and require a nontrivial minimum coverage so “almost never correct” cannot
win artificially.

An exact prior kills the occupied novelty claim; it does not by itself refute
physical feasibility.

### Stage 10 — Verdict

Only after completing Stages 0–9, issue one of:

- **Continue** — authorize the next decisive experiment; this does not mean
  the paper claim is established;
- **Narrow** — only a specific modality, aberration family, field/depth,
  hardware state, or weaker contribution remains;
- **Kill** — the main candidate requires violating the contract, lacks oracle
  headroom, is occupied by prior art, or fails causal/raw-science evidence.

Do not use “promising” as a substitute for a verdict.

If the verdict is Narrow, provide exact narrowed wording including modality,
specimen, aberration family, acquisition budget, and hardware scope.

If the verdict is Kill, identify the strongest defensible residual
contribution without retaining the killed claim.

Aggregate test-level verdicts with hard-gate priority:

- `Kill` if the frozen contract must be violated, the hardware-delivered
  phase-only oracle has no headroom, the correction action is unidentifiable,
  reference-on calibration fails to transfer to reference-off science,
  calibration/science circularity remains, or raw-science benefit cannot be
  separated from material budget confounding;
- `Narrow` when the hard gates pass only for an explicitly bounded modality,
  specimen, aberration, field/depth, acquisition budget, or hardware state;
- `Continue` only when no hard gate has failed, no critical item is `NR`, and
  every remaining uncertainty has a decisive matched-budget experiment.

Do not use `Narrow` to rescue a frozen-contract violation.

## Required Final Deliverables

Return one structured Chinese research report containing:

1. a one-page `Continue / Narrow / Kill` executive summary;
2. the frozen-contract audit table;
3. a search log with databases, queries, dates, result counts, and failures;
4. a deduplicated evidence table in Markdown;
5. the same evidence table in a copyable CSV code block;
6. the cross-domain restoration background;
7. the digital/AO/ONN/4f method comparison;
8. an exact-neighbor and adjacent-prior competition map;
9. a claim–evidence–counterexample matrix;
10. modality-specific forward models and a complete symbol table;
11. an identifiability and action-equivalence audit;
12. a phase-only oracle and hardware-feasible-domain analysis;
13. a calibration-to-science causal graph with confounders;
14. a matched-budget benchmark protocol;
15. a baseline specification table;
16. risk–coverage, harmful-correction, stopping, and abstention protocols;
17. ranked kill tests and decisive experiments;
18. the atomic `Agree / Qualify / Reject` audit of the companion brief;
19. safe claim wording: established, conditionally supportable, and prohibited;
20. verified DOI bibliography and a BibTeX code block;
21. all `NR`, inaccessible full texts, metadata conflicts, and unresolved
    questions.

## Final Quality Gate

Before returning the report, confirm:

- every frozen invariant was preserved;
- commanded and delivered reference phase were distinguished;
- \(\delta_{\mathrm{ref}}\), \(\tau_{\mathrm{harm}}\), and
  \(\tau_{\mathrm{gain}}\) were never conflated;
- the \(T\leq8\) calibration ceiling remained adaptive rather than becoming a
  fixed eight-probe protocol;
- the two SLM devices, locations, response models, and LUTs remained distinct;
- SLM global piston was treated explicitly;
- calibration and science observations remained causally distinct;
- coherent and incoherent microscopy models were not conflated;
- peer-reviewed papers and preprints were separated;
- every major conclusion has primary evidence;
- all missing fields are marked `NR`;
- complete acquisition and compute budgets were audited;
- exact neighbors and adjacent priors were both searched;
- negative results and harmful cases were retained;
- every stage reported `Pass / Fail / Unresolved`, and critical `NR` did not
  become unconditional `Continue`;
- no global-first statement was made;
- the final verdict is unambiguous.
