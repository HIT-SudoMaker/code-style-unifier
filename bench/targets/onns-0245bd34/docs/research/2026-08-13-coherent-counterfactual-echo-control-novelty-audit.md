# Coherent Counterfactual Echo Control: novelty and priority audit

- Date: 2026-08-13
- Scope: primary academic literature available through 2026-08-13; no patent or unpublished-conference-priority search
- Proposal audited: fixed coherent reference; complementary/quadrature sensing; episode-specific measured optical twin; counterfactual search in calibrated delivered-action space; one trial delivery; repeated coherent measurement (“echo”); `commit` / `probe` / `abstain` / `revert`; a later raw reference-on science frame; nominal 5-frame fast and 9-frame robust protocols
- Evidence labels: **Established** = directly supported by a primary source; **Inference** = a conservative comparison derived from the cited sources; **Not established** = not demonstrated by the present project or not secured by the search

## Executive verdict

**The proposal is promising as a research programme, but it is not presently defensible as a wholly new optical-control architecture.** Almost every ingredient has a close and sometimes direct precedent:

- phase-shifted coherent field recovery dates at least to phase-shifting digital holography in 1997;
- an interferometer, SLM, feedback, and real-time aberration correction were demonstrated in 1996;
- four phase-shifted interferograms, self-referenced sensing, conjugate LC-SLM correction, and closed-loop operation were experimentally reported in 2010;
- a single SLM serving sensing and correction was reported in 2011;
- the self-coherent camera (SCC) already uses a spatially encoded coherent reference to recover the focal-plane complex field and close a correction loop at the science detector;
- pair-wise probing plus electric-field conjugation (PWP+EFC) already follows the practical sequence “complementary probes → field estimate → model-predicted actuator update → delivery → remeasurement,” while implicit EFC (iEFC) replaces the optical model with an empirical response matrix;
- Kalman focal-plane estimation already uses measurement history, covariance, fewer exposures, and control-informed probe selection;
- image-guided computational holographic wavefront shaping already measures complex scattered fields, emulates many virtual SLMs in software, and applies an optimized physical correction;
- calibrated optical digital twins, risk-aware candidate forecasting in autonomous microscopy, and camera-in-the-loop model correction are established ideas in adjacent optical and microscopy systems;
- single-shot learned physical phase bias followed by digital estimation and SLM correction was published in 2026.

The **potentially defensible novelty is therefore a system-level conjunction, not the ingredients**: a fixed coherent reference that remains active in the final imaging transfer; an episode-conditioned estimate used to score hardware-feasible actions for a future raw image; a preregistered prediction-versus-measurement audit after a trial delivery; and a selective policy that may acquire more evidence, decline correction, or reject the trial before admitting a later frame as the scientific endpoint.

That conjunction is **not yet top-journal-significant merely because it is unusual**. It becomes significant only if it produces a capability that SCC, PWP+EFC, iEFC, phase conjugation, sensorless AO, and learned wavefront sensing do not provide under matched cost. The decisive capability should be stated quantitatively:

> At a fixed acquisition, photon, actuation, and latency budget, the system improves prospective raw-image utility while bounding the rate of harmful optical interventions under object change, aberration ambiguity, drift, and model mismatch.

Current decision: **no-go for a “revolutionary new architecture” claim; conditional go for a “risk-aware, self-auditing coherent adaptive front end” claim.** The latter can plausibly support a strong paper only after the identifiability, causal endpoint, and matched-baseline tests below succeed.

## 1. Ingredient-by-ingredient priority audit

| Proposed ingredient | Closest primary precedent | Consequence for novelty |
|---|---|---|
| Four quadrature measurements recover a complex cross term | Yamaguchi and Zhang established phase-shifting digital holography in 1997 ([DOI](https://doi.org/10.1364/OL.22.001268)). | **Not new.** The demodulation is a measurement primitive, not the headline contribution. |
| Two-frame fast path using a fixed spatial carrier | Off-axis holography spatially separates cross terms and removes the zero order/twin image by Fourier filtering ([Cuche et al., 2000](https://doi.org/10.1364/AO.39.004070)). SCC likewise encodes the science-plane field with spatial fringes ([Galicher et al., 2010](https://doi.org/10.1051/0004-6361/200912902)). | **Not new, and conditional.** It requires sideband support separation and spends camera space–bandwidth product. Two frames may suppress common intensity terms, but off-axis complex recovery itself can be single-shot. |
| Interferometer + phase modulator + feedback correction | An interference phase loop using a high-resolution liquid-crystal SLM demonstrated diffraction-limited real-time correction of arbitrary input wavefronts in 1996 ([Neil et al., 1996](https://doi.org/10.1016/0030-4018(96)00336-7)). | **Priority-killing for any broad “first interferometric feedback correction” claim.** |
| Self-reference + four phase shifts + LC-SLM conjugate correction | Bai and Rao built a closed-loop self-referencing interferometric wavefront sensor, analysed four phase-shifted interferograms, and loaded the conjugate correction on a phase-only LC-SLM ([2010](https://doi.org/10.1016/j.optcom.2010.03.032)). | **The single closest precedent for the robust sensing/correction skeleton.** |
| One programmable element participates in sensing and correction | Martínez-Cuenca et al. proposed and demonstrated closed-loop AO in which a single SLM works as both correction unit and key wavefront-sensor element ([2011](https://doi.org/10.1364/OL.36.003702)). | **Not new.** Physical role reuse alone cannot carry the claim. |
| Fixed coherent reference, spatial carrier, focal-plane complex-field recovery, and closed-loop correction | SCC was proposed as a focal-plane wavefront sensor and differential imager ([Galicher et al., 2010](https://doi.org/10.1051/0004-6361/200912902)); laboratory SCC estimated phase/amplitude and compensated them in closed loop ([Mazoyer et al., 2013](https://doi.org/10.1051/0004-6361/201321706)); SCC and PWP+EFC were compared on the same testbed and both created dark holes in a few iterations ([Potier et al., 2020](https://doi.org/10.1051/0004-6361/201937015)); FAST-SCC later demonstrated closed-loop compensation of evolving residual turbulence down to 20 ms ([Gerard et al., 2022](https://doi.org/10.1117/1.JATIS.8.3.039001)). | **The strongest structural near-neighbour.** A reviewer will map the fixed-reference “echo” system to SCC unless the final reference-on transfer and selective scientific decision are shown to be physically and experimentally different. |
| Complementary actions estimate a focal-plane field | PWP applies positive and negative deformable-mirror probes and uses their difference to estimate the coherent field; PWP+EFC is a standard closed-loop pairing ([Potier et al., 2020](https://doi.org/10.1051/0004-6361/201937015)). | **Not new.** A (0/\pi) pair is a phase-shifting form of complementary probing. |
| A forward model predicts a correction without displaying every candidate | EFC uses a diffraction model/Jacobian to predict how actuator commands change the focal-plane electric field before selecting an update; this family is already standard in high-contrast testbeds. The PWP+EFC/SCC comparison gives direct laboratory evidence ([Potier et al., 2020](https://doi.org/10.1051/0004-6361/201937015)). | **“Counterfactual search” is not itself new.** In control language it is model-based action evaluation. |
| Empirically calibrated delivered-action response rather than an exact optical model | iEFC is explicitly a data-driven, empirically calibrated focal-plane controller that does not require an instrument model and was validated on MagAO-X ([Haffert et al., 2023](https://doi.org/10.1051/0004-6361/202244960)). | **Priority-killing for broad “first measured/model-free optical controller” wording.** |
| History-conditioned field estimation, uncertainty, and fewer probes | Groff and Kasdin used a Kalman estimator with prior state, estimation covariance, fewer exposures, and control-informed probe shapes for focal-plane correction ([2013](https://doi.org/10.1364/JOSAA.30.000128)). | **Uncertainty and adaptive probe selection are not new in focal-plane control.** Expected value of information would be a new policy formulation only if it improves decisions experimentally. |
| Measured field becomes an episode-specific virtual experiment; many virtual SLMs are optimized in software | Haim, Boger-Lombard, and Katz holographically measured fields under unknown illuminations, computationally emulated image-guided wavefront shaping with several virtual SLMs, corrected more than 190,000 modes using 25 compounded fields, and applied the result across several imaging modalities ([Nature Photonics, 2025](https://doi.org/10.1038/s41566-024-01544-6)). | **The strongest computational near-neighbour.** “Measure once, optimize many virtual actions, then correct physically” is already published at flagship level. |
| Few-measurement high-dimensional physical optimization without a clean guide star | Monin, Alterman, and Levin derived an optically measurable full gradient for guide-star-free wavefront shaping, updated all SLM parameters together, and demonstrated coherent confocal correction ([Nature Communications, 2026](https://doi.org/10.1038/s41467-025-68259-2)). Their implementation uses five phase-diversity images per sampling direction plus a line-search measurement per iteration. | **Frame count alone is not a novelty axis.** The proposed 5/9-frame episode must win on an outcome other than simply being “few-frame.” |
| Calibrated SLM digital twin | Schroff et al. fitted a digital twin of a Fourier SLM system from random speckle images, obtaining (\lambda/170) residual phase with ten SLM patterns and modelling pixel crosstalk ([Optics Express, 2024](https://doi.org/10.1364/OE.539548)). | **“Measured optical twin” is not new.** Novelty would need to reside in how an online episode update supports a consequential decision. |
| Forecast candidate microscope actions, uncertainty, and risk | Liu et al. explicitly formulate coupled sample/instrument twins that forecast candidate actions, expected outcomes, uncertainty, and risk for autonomous microscopy ([arXiv:2607.05758, 2026](https://arxiv.org/abs/2607.05758)). This is a primary preprint, not yet a peer-reviewed optics priority claim. | **The decision-language conjunction is already emerging.** The project must supply an optical mechanism and causal evidence beyond generic autonomous-microscopy decision making. |
| Learned physical encoding + one-shot digital inference + SLM correction | Baharlou et al. jointly optimized a physical phase bias and residual network for single-shot Zernike estimation and reported SLM/metasurface experiments with physical correction ([Nature Communications, 2026](https://doi.org/10.1038/s41467-026-72364-1)). | **Physical encoding plus digital inference plus SLM actuation is occupied.** The useful distinction is persistent unknown aberration, no truth leakage, selective action, and prospective extended-image evidence—not merely “our correction is optical.” |
| Learning-based sensorless AO across microscope types | Physics-based MLAO was embedded in multiple microscope control loops and outperformed conventional modal sensorless AO under challenging imaging conditions ([Hu et al., 2023](https://doi.org/10.1038/s41377-023-01297-x)). | **“Intelligent AO” and neural control are occupied.** Learning must earn its place against physics-only estimation under identical measurements. |
| Phase-only hardware yields richer complex-field control through coherent superposition | Coherent sums of phase-encoded waves and phase-only complex-field encoding are established; for example, Carbonell-Leal and Mendoza-Yero recover arbitrary amplitude and phase from coherently summed waves encoded by a phase-only SLM ([2019](https://doi.org/10.3791/59158)). | **The translated-circle geometry is an elementary and useful design law, but not a safe stand-alone novelty claim.** The new result would have to be an imaging-specific reachability theorem plus experimental consequence. |

## 2. The three papers that most tightly bracket the proposal

The proposal is best understood as lying inside a triangle rather than outside established fields.

### 2.1 Physical architecture neighbour: SCC + focal-plane control

SCC provides a coherent reference, spatial carrier, science-plane complex-field readout, physical actuator update, closed-loop residual remeasurement, and use of the focal plane that matters scientifically. Its later FAST implementation also removes any safe claim that a coherent-reference focal-plane loop is intrinsically slow.

**What SCC does not obviously provide:** a final reference-on transfer intentionally used as an affine imaging-control resource; task-facing benefit/harm prediction for an unknown extended scene; an explicit accept/reject gate for the correction; or risk–coverage reporting.

### 2.2 Computational architecture neighbour: image-guided computational holographic wavefront shaping

The 2025 Nature Photonics work already turns measured complex fields into a computational emulator, optimizes virtual modulators without physically trying every candidate, and then performs wavefront correction. This is extremely close to the proposed “measured twin + counterfactual search” concept and is stronger than a comparison only to conventional DNN restoration.

**What it does not obviously provide:** the proposed fixed reference as part of the final transfer, a prediction-conformity echo, or selective abstention/reversion before admitting a future raw frame.

### 2.3 Decision architecture neighbour: coupled twins for autonomous microscopy

The 2026 preprint explicitly moves from closed-loop optimization to candidate-action forecasting using coupled sample and instrument twins, including uncertainty and risk. It is not coherent optical AO, but it occupies the high-level language of “imagine before acting.”

**What it does not provide:** coherent interferometric observability, phase-only reachability, SLM wavefront correction, or an optical raw-image endpoint.

**Inference:** the proposed system-level conjunction may still be new, but a reviewer can construct it by combining these three mature lines. Therefore, the paper must demonstrate an unexpected capability produced by their coupling; architecture diagrams and terminology alone will look like aggregation.

## 3. What may actually be novel

No searched primary paper was found that simultaneously demonstrates all of the following in a coherent extended-image experiment:

1. a fixed reference that is deliberately retained as part of the final reference-on imaging transfer rather than used only for metrology or coronagraphic speckle tagging;
2. inference aimed at an **action-equivalence class** or future action value rather than full aberration reconstruction for its own sake;
3. optimization over a calibrated, delivered phase-only action set with device constraints inside the objective;
4. a prediction locked before trial delivery, followed by a repeated coherent measurement that tests prediction conformity;
5. a selective policy that can acquire another probe, accept the action for science, reject/revert it, or abstain;
6. a later raw frame that was not used to select its own correction and is the preregistered scientific endpoint;
7. harm–coverage, regret, acquisition cost, and model-mismatch calibration reported together.

This is **candidate conjunction novelty**, not established priority. An academic search cannot exclude unindexed papers, patents, or differently named control systems. “First” language would require a patent search and a structured citation search around SCC, EFC, holographic wavefront shaping, autonomous microscopy, and safe/selective control.

The most defensible scientific centre is not “a new way to estimate Zernike coefficients” and not “a new DNN.” It is:

> **Selective optical intervention under an unverifiable scene:** the system uses coherent evidence to predict whether a hardware-feasible action will improve the next raw measurement, audits the prediction against a physical echo, and withholds the action from the scientific endpoint when the evidence is inadequate.

That centre remains inside adaptive/coherent imaging, but it changes the comparison axis from coefficient RMSE or average image quality to **decision calibration and prevented harmful correction**.

### 3.1 Candidate deepening: make the echo an algebraic action audit

The generic detector-plane two-arm model is

\[
I_c(\mathbf{x})=
\left|E_r(\mathbf{x})+e^{ic}E_p(\mathbf{x})\right|^2+n_c(\mathbf{x}).
\]

Four quadrature states identify the arm-summed background and complex cross
term

\[
B=|E_r|^2+|E_p|^2,
\qquad
C=E_r^*E_p.
\]

Writing \(r=|E_p/E_r|\), the ratio

\[
\frac{B}{|C|}=r+\frac{1}{r}
\]

and \(\arg C=\arg E_p-\arg E_r\) determine the scene-conditioned relative
field \(q=E_p/E_r\), subject to the reciprocal \(r\leftrightarrow 1/r\)
ambiguity. A calibrated arm identity or known static imbalance can select the
physical branch. Pixels with weak cross-term support remain unidentifiable.
This is a relative detector-field result. It is not automatically an optical
transfer function, and it must not be moved between image, pupil, and Fourier
planes without the corresponding propagation model.

If the scene and reference field remain fixed during a trial action \(u\), a
regularized pre/post cross ratio is

\[
\rho_{u\leftarrow0}^{\mathrm{obs}}
=
\frac{C_u C_0^*}{|C_0|^2+\epsilon}
\approx
\frac{E_{p,u}}{E_{p,0}}
\]

where the approximation becomes exact on supported pixels as
\(\epsilon\rightarrow0\). This cancels the unchanged reference field and does
not require recovery of a clean object. A calibrated delivered-action model can
lock a prediction \(\widehat\rho_u\) before the trial. The echo statistic then
tests whether the **physical action effect**, rather than a reconstructed
aberration label, agrees with that prediction.

**Inference.** Basic recovery of relative amplitude and phase from
interferometric visibility is not new, and closed loops routinely remeasure a
residual. The present search did not locate a primary optical-control paper
that uses this normalized pre/post cross term as a preregistered
action-conformity statistic that gates `admit`, `probe`, or `reject` for a later
raw extended-image endpoint. This is therefore a candidate deepening, not a
priority claim. It survives only if the experiment shows that the statistic is
stable under scene and arm drift, predicts prospective utility beyond ordinary
residual sensing, and improves the matched-cost harm--coverage frontier.

## 4. Physics and logic blockers that can invalidate the story

### 4.1 The measured cross term is not automatically an optical twin

Under the project’s simplified Fourier-coordinate model,

\[
C(\mathbf{k})
=\frac{I_0-I_\pi+i(I_{3\pi/2}-I_{\pi/2})}{4}
=|X(\mathbf{k})|^2H_r^*(\mathbf{k})H_p(\mathbf{k};a).
\]

This does not identify (H_p) where (X) is unknown or spectrally null. It identifies an object-weighted relative product under the assumed multiplicative, mutually coherent, registered, differential-aberration model. Calling it a “measured optical twin” is justified only if the paper proves that the action value or predicted echo is identifiable from this product without illicitly dividing by unknown object content.

The derivation must also specify the physical plane of every variable. If the camera measures an image-plane field, multiplication in (\mathbf{k}) may become convolution in detector coordinates. If the SLM pixels live in a pupil or Fourier plane, their controls are generally coupled by propagation and finite aperture; one cannot assume an independently selectable circle at every science-image frequency without proving the mapping.

**Kill test:** construct pairs ((X,H_p)) that produce identical allowed measurements but require different optimal actions. If such pairs exist at the claimed operating conditions, restrict the claim to identifiable action classes, add probes, or abandon universal correction.

### 4.2 An echo audits prediction consistency, not restoration truth

A post-action coherent measurement can show that the delivered system responded as predicted. It cannot, without an independent target or task reference, prove that the image is correct. A wrong object/physics model can predict its own wrong echo.

Use **self-auditing** or **prediction-conformity checking**, not **self-verifying** or **certified restoration**, unless a theorem links the echo statistic to a bound on the prospective scientific loss.

The audit must be defined before observing the echo, for example

\[
T_{\mathrm{echo}}=
(y_{\mathrm{echo}}-\hat y_u)^\top
\widehat\Sigma_u^{-1}
(y_{\mathrm{echo}}-\hat y_u),
\]

with a held-out calibration procedure for its acceptance threshold. Otherwise the “echo” is merely the ordinary next measurement of a closed AO loop.

### 4.3 `Commit` occurs after a physical trial, so harm has already partly occurred

The candidate must be displayed to acquire its echo. `revert` can prevent a rejected configuration from generating the admitted science frame, but it cannot undo illumination dose, phototoxicity, saturation, sample motion, or irreversible exposure caused during the trial.

The protocol should say **trial → audit → admit/reject for science**, not “predict safely before ever acting.” Dose and peak intensity during trial states belong in the harm budget.

### 4.4 The later raw frame is good causal hygiene, not novelty by itself

AO systems routinely acquire images after correction. The prospective frame is valuable because it prevents calibration-frame reuse and target leakage, but it becomes a contribution only when coupled to a preregistered policy and compared with randomized safe/sham/opposite/equal-cost actions.

### 4.5 The 5- and 9-frame labels hide assumptions

- The 5-frame route assumes off-axis sidebands are separated at the required object bandwidth and SNR.
- The 9-frame route counts camera exposures, not SLM loads, settling, synchronization, transfer, computation, or a possible revert state.
- At 60 Hz, five and nine exposures have ideal acquisition floors of about 83 and 150 ms, respectively; these are not measured loop latencies.
- A reference carrier consumes detector bandwidth and dynamic range and can contaminate the final reference-on image with fringes.
- Mutual coherence, arm drift, polarization mismatch, LUT error, phase–amplitude coupling, and reference shot noise can dominate the claimed advantage.

The paper should report reads, SLM states, photon dose, wall time, and delivered—not nominal—phase separately.

### 4.6 The fixed reference may be the best physics, but its advantage is still unproved

For a simplified pointwise transfer (G=H_r+H_pe^{iu}), phase-only control traces a circle centred at (H_r), rather than a circle centred at the origin. This clearly visualizes an affine feasible set. However:

- coherent complex-field synthesis from phase-only modulation is established;
- the reference may improve some desired transfers while making others unreachable;
- reference intensity trades heterodyne gain against detector headroom and shot noise;
- a bypass/reference arm may carry uncorrected common-path or specimen terms;
- common-path aberrations and unknown object content may be invisible to differential sensing.

**Required result:** a theorem and bench measurement showing a task-relevant region that is unattainable reference-off, attainable reference-on, identifiable with the allowed probes, and beneficial in a newly acquired raw image. Without this four-part chain, the shifted-circle figure is explanatory rather than field-changing.

## 5. Evidence package required for a PhotoniX/LSA-level claim

### Gate A — mathematical identifiability and reachability

1. Declare all planes, fields, polarization/coherence assumptions, actuator coordinates, and nuisance variables.
2. Prove what two- and four-frame measurements identify under unknown extended objects.
3. State gauge freedoms, object spectral zeros, common-path nulls, finite aperture, pixel coupling, and phase-only constraints.
4. Derive the delivered feasible set after LUT, quantization, crosstalk, registration, and finite phase range.
5. Prove or empirically bound how echo conformity relates to future raw-image loss.

**No-go condition:** the allowed measurement history does not distinguish action classes that differ materially in prospective utility.

### Gate B — independent and prospective physical evidence

1. Leave an independently unknown, persistent aberrator physically in place while a separate delivered correction is applied.
2. Prevent commanded ground truth, clean images, and simulation truth from entering estimator or policy code.
3. Lock the candidate prediction and interval before trial delivery.
4. Acquire echo and science data as separate immutable records; the science frame must not select its own action.
5. Randomize safe, sham, opposite-sign, equal-RMS, and deliberately model-mismatched controls.

**No-go condition:** the headline corrected image is reconstructed digitally, selected retrospectively, or formed using the known aberration command.

### Gate C — nearest-neighbour comparisons at matched cost

At minimum compare:

- SCC-style spatial-carrier estimation and correction;
- PWP+EFC;
- iEFC or an empirical interaction-matrix controller;
- four-step phase conjugation;
- fixed phase diversity and an optimized fixed probe codebook;
- image-guided virtual-SLM optimization or the closest implementable surrogate;
- learned phase-bias/single-shot estimation;
- MLAO or a compact learned estimator;
- always-correct, never-correct, and oracle-action policies;
- the project’s archived fixed optical mask, pure digital restoration, and optical-plus-digital chain.

Match camera reads, photons, number of SLM states, calibration time, online compute, actuator degrees of freedom, and wall time. “Five frames versus one frame” is not fair if calibration, carrier bandwidth, or trial echo costs are omitted.

**No-go condition:** the proposed method does not improve the Pareto frontier of raw-image utility, harmful-action rate, coverage, dose, and latency over SCC/PWP+EFC/iEFC.

### Gate D — the selective-control result

Report, by measurement prefix and held-out session:

- utility gain and oracle regret;
- harmful-correction probability and magnitude;
- risk–coverage curve;
- calibration of predicted gain and echo residual;
- fraction of `probe`, `abstain`, `admit`, and `revert` decisions;
- acquisition/dose/latency cost;
- correction lifetime under drift;
- performance under object, aberration, SNR, session, and hardware shift.

The decisive figure is not the best restored example. It is a curve showing that selective control removes harmful interventions while retaining useful coverage at matched resource cost.

**No-go condition:** `abstain` and echo rejection do not reduce prospective harm, or coverage collapses to a trivial fraction.

### Gate E — broad scientific endpoint

Demonstrate extended scenes or specimens, not only Gaussian/OAM beams, USAF targets, or commanded single Zernike modes. At least one endpoint should measure preserved spatial information or a specimen-relevant quantity in the raw optical acquisition, not only PSNR against a clean digital target.

**No-go condition for a flagship claim:** evidence remains a low-order Zernike/USAF proof of concept on one session and one device.

## 6. Defensible and indefensible wording

### Defensible now as a hypothesis

> We investigate a risk-aware coherent adaptive front end that uses phase-shifted measurements to construct an episode-conditioned predictor of hardware-feasible optical actions, audits a trial action against a subsequent coherent measurement, and selectively admits a later raw frame as the scientific outcome.

> Unlike fixed optical restoration and coefficient-only AO, the proposed control objective is prospective action value under measurement, hardware, and model uncertainty.

> The candidate contribution is the tested conjunction of reference-on reachability, measurement-conditioned action inference, prediction-conformity auditing, and selective optical intervention.

### Defensible only after positive evidence

> At matched acquisition and actuation cost, selective echo-gated control reduced harmful corrections from (x\%) to (y\%) while retaining (z\%) coverage and improving a preregistered raw-image endpoint.

> The fixed reference enabled a measured transfer region that was inaccessible to the same phase-only actuator with the reference disabled.

### Avoid

- “the first interferometric adaptive correction”;
- “the first SLM that senses and corrects”;
- “the first counterfactual optical controller” without a much broader patent and citation search;
- “self-verifying restoration” unless the echo provably bounds scientific error;
- “safe before acting,” because echo acquisition requires trial delivery;
- “model-free” if a calibrated forward model, response matrix, or learned residual is used;
- “digital twin” for a static simulator that is not episode-updated and prediction-validated;
- “five-frame correction” without sideband, settling, dose, and latency qualifications;
- “beyond AO” or “outside the DNN/AO competition.” The system is best positioned as a new objective and evidence contract **within coherent adaptive imaging**.

## 7. How to create the one-glance advance

The architecture will not look “one generation ahead” because it has more named stages. It can look ahead if Figure 1 displays a capability missing from the nearest neighbours:

1. the measured episode contracts a hardware-feasible action region;
2. hundreds of virtual actions are scored without display;
3. one trial is delivered with a locked predicted outcome interval;
4. the physical echo falls inside or outside that interval;
5. the system visibly chooses `admit`, `probe`, or `reject`;
6. only then is a later raw image acquired;
7. across many episodes, the risk–coverage curve beats always-correct PWP+EFC/iEFC at the same budget.

The strongest compact title direction is therefore **“Self-auditing coherent adaptive imaging”** or **“Risk-aware coherent adaptive imaging”**, with “counterfactual echo control” retained as the algorithm name. This makes the scientific contribution legible without pretending that phase shifting, a reference beam, a digital twin, or closed-loop residual sensing is individually new.

## 8. Final go/no-go ladder

| Stage | Decision |
|---|---|
| Conceptual novelty | **Conditional go.** The complete conjunction was not found as one coherent extended-imaging system, but its components have strong, obvious precedents. |
| Broad “new architecture beyond AO/DNN” claim | **No-go.** Reviewers can map it to SCC/PWP+EFC plus holographic virtual optimization plus risk-aware digital twins. |
| Two-/four-frame sensing paper | **No-go for flagship novelty.** PSI, off-axis holography, SCC, and PWP occupy this space. |
| Measured-twin counterfactual optimization paper | **No-go by itself.** Nature Photonics 2025 and optical digital-twin/CITL work are direct competitors. |
| Echo-gated selective coherent imaging | **Conditional go.** It needs formal error semantics, prospective physical evidence, and a matched-cost harm–coverage advantage. |
| PhotoniX/LSA ambition | **Plausible but evidence-heavy.** Require an independent persistent aberrator, extended specimens/scenes, multiple sessions, delivered-hardware modelling, real latency/dose accounting, nearest-neighbour baselines, and a strong raw scientific endpoint. |
| Immediate manuscript claim | **No-go.** The current state is a disciplined hypothesis and experiment design, not a demonstrated advance. |

## Conclusion

The proposed system is not a clean escape from DNN, AO, or optical neural-network competition. Scientifically, it is a synthesis at their boundary, and experts will recognize its ancestry immediately. That is not fatal. Flagship work often comes from a conjunction—but only when the conjunction creates a new measurable regime.

Here the credible regime is **selective, prospective optical correction under uncertainty**. The fixed coherent reference may expose and alter the feasible transfer; the measured model may evaluate actions before exhaustive hardware search; the echo may reveal model mismatch; and the policy may refuse to admit a correction to science. None of those phrases is enough alone. The paper becomes distinctive only if their combination yields a calibrated reduction in harmful physical interventions while preserving useful raw-image gain at matched cost.

In short: **the architecture is interesting; the current novelty claim is too broad; the risk-aware self-auditing experiment is the part worth betting on.**

## Primary sources

1. Neil, M. A. A. et al. “High resolution adaptive optics using an interference phase loop.” *Optics Communications* 132, 494–502 (1996). [https://doi.org/10.1016/0030-4018(96)00336-7](https://doi.org/10.1016/0030-4018(96)00336-7)
2. Yamaguchi, I. & Zhang, T. “Phase-shifting digital holography.” *Optics Letters* 22, 1268–1270 (1997). [https://doi.org/10.1364/OL.22.001268](https://doi.org/10.1364/OL.22.001268)
3. Cuche, E., Marquet, P. & Depeursinge, C. “Spatial filtering for zero-order and twin-image elimination in digital off-axis holography.” *Applied Optics* 39, 4070–4075 (2000). [https://doi.org/10.1364/AO.39.004070](https://doi.org/10.1364/AO.39.004070)
4. Galicher, R. et al. “Self-coherent camera as a focal plane wavefront sensor: simulations.” *Astronomy & Astrophysics* 509, A31 (2010). [https://doi.org/10.1051/0004-6361/200912902](https://doi.org/10.1051/0004-6361/200912902)
5. Bai, F. & Rao, C. “Experimental validation of closed-loop adaptive optics based on a self-referencing interferometer wavefront sensor and a liquid-crystal spatial light modulator.” *Optics Communications* 283, 2782–2786 (2010). [https://doi.org/10.1016/j.optcom.2010.03.032](https://doi.org/10.1016/j.optcom.2010.03.032)
6. Martínez-Cuenca, R. et al. “Closed-loop adaptive optics with a single element for wavefront sensing and correction.” *Optics Letters* 36, 3702–3704 (2011). [https://doi.org/10.1364/OL.36.003702](https://doi.org/10.1364/OL.36.003702)
7. Groff, T. D. & Kasdin, N. J. “Kalman filtering techniques for focal plane electric field estimation.” *JOSA A* 30, 128–139 (2013). [https://doi.org/10.1364/JOSAA.30.000128](https://doi.org/10.1364/JOSAA.30.000128)
8. Mazoyer, J. et al. “Estimation and correction of wavefront aberrations using the self-coherent camera: laboratory results.” *Astronomy & Astrophysics* 557, A9 (2013). [https://doi.org/10.1051/0004-6361/201321706](https://doi.org/10.1051/0004-6361/201321706)
9. Potier, A. et al. “Comparing focal plane wavefront control techniques: numerical simulations and laboratory experiments.” *Astronomy & Astrophysics* 635, A192 (2020). [https://doi.org/10.1051/0004-6361/201937015](https://doi.org/10.1051/0004-6361/201937015)
10. Gerard, B. L. et al. “Laboratory demonstration of real-time focal plane wavefront control of residual atmospheric speckles.” *JATIS* 8, 039001 (2022). [https://doi.org/10.1117/1.JATIS.8.3.039001](https://doi.org/10.1117/1.JATIS.8.3.039001)
11. Haffert, S. Y. et al. “Implicit electric field conjugation: data-driven focal plane control.” *Astronomy & Astrophysics* 673, A28 (2023). [https://doi.org/10.1051/0004-6361/202244960](https://doi.org/10.1051/0004-6361/202244960)
12. Hu, Q. et al. “Universal adaptive optics for microscopy through embedded neural network control.” *Light: Science & Applications* 12, 270 (2023). [https://doi.org/10.1038/s41377-023-01297-x](https://doi.org/10.1038/s41377-023-01297-x)
13. Schroff, P. et al. “Rapid stochastic spatial light modulator calibration and pixel crosstalk optimization.” *Optics Express* 32, 48957–48971 (2024). [https://doi.org/10.1364/OE.539548](https://doi.org/10.1364/OE.539548)
14. Haim, O., Boger-Lombard, J. & Katz, O. “Image-guided computational holographic wavefront shaping.” *Nature Photonics* 19, 44–53 (2025). [https://doi.org/10.1038/s41566-024-01544-6](https://doi.org/10.1038/s41566-024-01544-6)
15. Monin, S., Alterman, M. & Levin, A. “Rapid wavefront shaping using an optical gradient acquisition.” *Nature Communications* 17, 1537 (2026). [https://doi.org/10.1038/s41467-025-68259-2](https://doi.org/10.1038/s41467-025-68259-2)
16. Baharlou, S. M. et al. “An end-to-end hybrid deep-learning approach for single-shot wavefront sensing and correction.” *Nature Communications* 17, 6340 (2026). [https://doi.org/10.1038/s41467-026-72364-1](https://doi.org/10.1038/s41467-026-72364-1)
17. Liu, Y. et al. “From Closed-Loop Optimization to Open Decision Making: Coupled Digital Twins for Predictive and Autonomous Microscopy.” arXiv:2607.05758 (2026). [https://arxiv.org/abs/2607.05758](https://arxiv.org/abs/2607.05758)
18. Carbonell-Leal, M. & Mendoza-Yero, O. “Shaping the amplitude and phase of laser beams by using a phase-only spatial light modulator.” *Journal of Visualized Experiments* 143, 59158 (2019). [https://doi.org/10.3791/59158](https://doi.org/10.3791/59158)
