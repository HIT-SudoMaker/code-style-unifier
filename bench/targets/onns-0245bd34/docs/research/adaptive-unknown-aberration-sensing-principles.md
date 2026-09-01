# Adaptive unknown-aberration sensing: principles and evidence boundary

## Status and scope

This note defines the physical and evidential boundary for the next Adaptive
Restoration experiments. It addresses one question only:

> How can an optical system infer and correct an *unknown* aberration from no
> more than eight calibration exposures without using the ideal image or the
> true aberration during decision-making?

The conclusions below distinguish facts reported by primary sources from
inferences for this project. They do not promote the current oracle experiment
to an Adaptive estimator.

## Conclusion first

An unknown-aberration experiment needs three logically separate quantities:

1. the hidden aberration used by a simulator or an external validation
   instrument;
2. known phase or illumination probes that the experiment intentionally
   delivers;
3. measured intensities available to the estimator.

The estimator may use items 2 and 3. Item 1 is evaluation-only information. A
method that uses the hidden aberration to construct its correction, or compares
candidates with a diffraction-limited image to select an action, is an oracle
upper-bound calculation rather than Adaptive wavefront sensing.

There are credible routes within eight exposures, but they apply to different
physical regimes:

- Classical phase diversity can jointly estimate an unknown intensity object
  and pupil aberration from a small image stack under a spatially incoherent,
  locally shift-invariant image-formation model. A 2024 microscopy experiment
  used five images in one correction cycle.
- A calibrated model-based sensorless-AO metric can estimate `N` low-order
  modes with `N + 1` measurements. Eight exposures therefore cover at most
  seven identifiable modes under that model.
- For a strictly coherent system with an unknown complex object, same-pupil
  phase diversity alone does not generally separate object phase from pupil
  phase. A known guide target, a stronger object prior, or non-commuting
  illumination diversity is required before a joint estimate can be claimed.

## Diagnosis of the current oracle experiment

The current `oracle_headroom` implementation is useful as a delivery-model
sanity check, but not as an Adaptive policy:

- It constructs `correction_phase = -aberration_phase` from the simulator's
  hidden aberration.
- Its delivered-phase search starts from the same true correction.
- It evaluates 85 candidates against a noiseless diffraction-limited intensity
  and selects the candidate with the smallest mean-square error.
- Its final PSNR, SSIM and gain are also evaluated against a simulated
  diffraction-limited observation.

This establishes only a conditional statement:

> If the aberration and desired output were already known, the simulated
> phase-only delivery model has enough correction headroom.

That is a legitimate oracle ceiling. It does not demonstrate aberration
identification, probe selection, posterior uncertainty, closed-loop control, or
an eight-frame correction policy.

The evidence rule for all subsequent experiments is therefore:

| Information | May select the action? | May score the result? |
| --- | --- | --- |
| Delivered probe commands | Yes | Yes |
| Raw calibration intensities | Yes | Yes |
| Predeclared system calibration | Yes | Yes |
| Hidden simulated aberration | No | Yes |
| Diffraction-limited target image | No | Yes, simulation or external validation only |
| Independently measured wavefront | No | Yes, after freezing the policy |

No tensor, loss, search score, early-stop rule, or candidate ranking derived
from evaluation-only information may enter the policy path.

## What phase diversity actually knows

Phase diversity does **not** know the aberration. It knows the intentional probe
added to each exposure. Under a spatially incoherent, shift-invariant model,

\[
d_k = f * h(\phi + \theta_k) + n_k,
\]

where `f` is the unknown non-negative object intensity, `phi` is the unknown
pupil phase, `theta_k` is the known delivered diversity and `d_k` is the
measured image. Multiple images share `f` and `phi` but use different known
`theta_k`. Their common structure makes joint maximum-likelihood estimation of
the object and aberration possible under the assumed model.

The distinction is essential:

- **known probe**: an intervention chosen by the instrument;
- **unknown aberration**: the state inferred from the response to those probes;
- **known truth**: validation information withheld from the estimator.

## Strictly coherent unknown-object caveat

The established unknown-object phase-diversity result above is an incoherent
intensity-convolution result. For a coherent system, let `X(q)` be an unknown
complex object spectrum, `A(q) exp(i phi(q))` the unknown pupil, and
`exp(i theta_k(q))` a known probe applied in that same pupil plane. The measured
intensity is

\[
I_k = \left|\mathcal F^{-1}\left\{
A e^{i\phi} e^{i\theta_k} X
\right\}\right|^2.
\]

For any phase function `psi(q)`, define

\[
X' = X e^{-i\psi}, \qquad \phi' = \phi + \psi.
\]

Then every `I_k` remains unchanged. This is a gauge freedom between unknown
object phase and unknown pupil phase. Adding more masks in the same plane does
not by itself remove it.

This derivation is a project inference from the coherent forward equation, not
a claim quoted from the incoherent phase-diversity papers. It gives a concrete
falsification requirement: before an unknown coherent specimen is used, the
nuisance-projected Jacobian or Fisher information for the proposed probe set
must be full rank over the declared aberration basis.

There are three defensible ways to remove or avoid this ambiguity:

1. **Known-target prescan.** Use a point source, bead, USAF target, or another
   independently characterized input field to estimate the pupil, then hold
   the correction while the aberration remains valid.
2. **Non-commuting diversity.** Change illumination angle, amplitude, spatial
   support, or object-plane encoding as well as the pupil phase. The two SLMs
   must create genuinely different forward operators, not two names for
   multiplicative masks in the same latent plane.
3. **Metric optimization without phase-identification claims.** Optimize a
   prevalidated object-insensitive image metric and report a correction action,
   without claiming that the full physical pupil phase was uniquely recovered.

## Why the current reference is not automatically a guide star

A reference flag, a baseline frame, or a noiseless image generated inside the
same simulator is not automatically a known guide star.

A guide reference needs independent provenance. At least one of the following
must be true:

- its object field is known by construction;
- its wavefront is measured by an independent instrument;
- its diffraction-limited state is established by a traceable calibration;
- or it is reserved strictly for post-policy evaluation.

An image acquired through the same unknown optical path is a self-reference. It
may normalize drift or establish a baseline, but it does not supply the missing
unaberrated object or pupil phase. Likewise, a simulator's
`diffraction_limited` observation is valid scoring truth only because the
simulator created it. An actual microscope does not obtain this truth merely by
setting `is_reference_enabled = false` or by naming an observation
`reference`.

Every future record should therefore store `reference_provenance` with one of
the following semantics:

- `known_calibration_target`;
- `independent_wavefront_measurement`;
- `simulation_truth_scoring_only`;
- `self_reference_not_ground_truth`.

## Low-order sensorless principle within eight frames

The `N + 1` result can be understood without an oracle. Suppose prior Fixed or
bench experiments have identified a stable local metric model

\[
J(u) = c - (a + u)^T H(a + u),
\]

where `a` is the unknown aberration coefficient vector, `u` is a known
delivered probe and `H` is a calibrated positive-semidefinite metric curvature.
Relative to the zero-probe image,

\[
J(u_j)-J(0)
=-2u_j^T H a-u_j^T H u_j.
\]

The left side is measured; `u_j` and `H` are known. `N` linearly independent
probes plus one baseline can therefore estimate an `N`-dimensional `a`. Paired
probes provide the more drift-resistant relation

\[
J(+u)-J(-u)=-4u^T H a,
\]

but require two exposures per measured projection.

This model fails if the metric curvature changes materially with the specimen,
the SLM delivery differs from calibration, the aberration evolves during the
burst, or the response is no longer locally quadratic. The Fixed results may
calibrate `H`, the low-order basis, the delivered-phase model and uncertainty
thresholds; they must not provide the runtime value of `a`.

## Five-frame and eight-frame prototypes

### Prototype A: five-frame incoherent phase diversity

This is appropriate only after experimentally validating a spatially
incoherent, locally shift-invariant intensity-convolution model.

| Frame | Delivered state | Purpose |
| --- | --- | --- |
| 1 | zero diversity | Shared aberrated baseline |
| 2 | positive oblique astigmatism | Diversity observation |
| 3 | negative oblique astigmatism | Diversity observation |
| 4 | positive vertical astigmatism | Diversity observation |
| 5 | negative vertical astigmatism | Diversity observation |

The estimator jointly fits the unknown object and a declared low-order pupil
phase from these five images. It may rank solutions only by measured-data
likelihood, regularization fixed before the run, reprojection residual, and
uncertainty. It may not use the diffraction-limited image or hidden
coefficients.

Required conditions:

- the object and aberration are approximately unchanged over all five frames;
- the actual delivered diversities are known, not merely the requested SLM
  commands;
- photon count and camera noise are modeled or measured;
- the field is locally isoplanatic;
- the object contains spatial-frequency information for the declared modes;
- piston and the tip/tilt-versus-translation gauge are excluded or handled by
  a separate registration contract.

### Prototype B: eight-exposure correction episode

The five calibration frames above can be embedded in an eight-exposure episode:

| Frame | Role |
| --- | --- |
| 1--5 | Blind calibration stack |
| 6 | First observation after loading the estimated correction |
| 7 | Independent no-probe science observation (`R = 0`) |
| 8 | Predeclared validation exposure, second science exposure, or abstention retry |

Frame 8 must have a preregistered role. It cannot be chosen retrospectively to
hide a failed result. At 60 Hz, eight bare frame periods equal approximately
133 ms. Total correction latency also includes SLM settling, camera exposure
and readout, data transfer, estimation, command upload and confirmation. A
frame-count claim is not a latency claim until these quantities are measured.

### Coherent version

For strictly coherent operation, the same schedule is acceptable only if the
five-frame stack uses a known calibration field, or if the two-SLM encoding has
passed a joint object/pupil identifiability audit. Otherwise the episode may be
reported as metric-based image improvement, not wavefront identification.

## Information-guided probe selection

The diversity pattern and amplitude should be optimized offline using the
actual delivered-phase model, noise model and representative object family.
The primary literature shows that information depends on both aberration and
object: too little diversity produces nearly redundant images, while too much
defocus can reduce sensitivity.

For joint object and aberration parameters, probe design should use the Fisher
information remaining after treating the object as a nuisance variable. Useful
criteria include maximizing the minimum eigenvalue or log determinant of the
nuisance-projected aberration information matrix. The design must include total
photon budget, quantization, crosstalk, settling time and permissible phase
range.

Online outputs should include:

- the estimated low-order coefficients or correction command;
- posterior covariance or a calibrated uncertainty proxy;
- nuisance-projected Jacobian/Fisher condition number;
- measured-data reprojection residual;
- the decision: `correct`, `probe_again`, or `abstain`.

## Kill rules

The Adaptive claim must stop or be downgraded when any of the following occurs:

1. **Truth leakage:** hidden aberration, diffraction-limited image, or
   independently measured wavefront affects probe selection or correction.
2. **Wrong image-formation regime:** an incoherent convolution estimator is
   applied to data whose coherent behavior is not negligible.
3. **Unidentifiable design:** the nuisance-projected Jacobian/Fisher matrix is
   rank-deficient or exceeds the preregistered condition-number threshold.
4. **Unknown delivery:** delivered probe phase is not supported by an SLM LUT,
   pupil registration and repeatability measurement.
5. **Unqualified reference:** a self-reference is described as a known guide
   star or diffraction-limited truth without independent provenance.
6. **Temporal violation:** object motion, phase drift, or illumination drift
   over the calibration burst exceeds its preregistered tolerance.
7. **Correction-lifetime violation:** the aberration decorrelates before the
   correction is loaded and the science exposure completes.
8. **Isoplanatic violation:** one correction is generalized outside the field
   region over which a shared pupil model was validated.
9. **Insufficient information:** signal level, object spectrum, or probe
   response cannot constrain every claimed mode with calibrated uncertainty.
10. **No blind improvement:** an independently acquired, no-probe science
    observation fails to improve the preregistered raw-image metric beyond its
    uncertainty interval.
11. **Budget violation:** measured end-to-end latency or exposure count exceeds
    the declared five/eight-frame protocol.
12. **Non-generalization:** a learned estimator succeeds only on the training
    target family or simulator and fails the preregistered held-out object,
    aberration, noise, or hardware-mismatch strata.

Failure of a kill rule is a useful result. It identifies whether the next work
should improve optics, calibration, probe design, inference, or the scope of
the scientific claim.

## Primary-source evidence

### Phase diversity and identifiability

1. R. A. Gonsalves, "Phase retrieval and diversity in adaptive optics,"
   *Optical Engineering* **21**, 829--832 (1982).
   <https://doi.org/10.1117/12.7972989>
2. R. G. Paxman and J. R. Fienup, "Optical misalignment sensing and image
   reconstruction using phase diversity," *JOSA A* **5**, 914--923 (1988).
   Two simultaneous images: focused and intentionally defocused.
   <https://doi.org/10.1364/JOSAA.5.000914>
3. R. G. Paxman, T. J. Schulz and J. R. Fienup, "Joint estimation of object
   and aberrations by using phase diversity," *JOSA A* **9**, 1072--1085
   (1992). Gaussian and Poisson joint estimation for an incoherent imaging
   system and an arbitrary number of diversity images.
   <https://doi.org/10.1364/JOSAA.9.001072>
4. R. G. Paxman *et al.*, "Phase-diverse adaptive optics for future
   telescopes," Proc. SPIE **6711** (2007). Discusses practical success,
   unresolved modes and the absence of a general uniqueness proof.
   <https://doi.org/10.1117/12.734665>
5. D. J. Lee, M. C. Roggemann and B. M. Welsh, "Cramér--Rao analysis of
   phase-diverse wave-front sensing," *JOSA A* **16**, 1005--1015 (1999).
   The bound depends on the true aberration; extended targets can contain much
   less aberration information than point sources.
   <https://doi.org/10.1364/JOSAA.16.001005>
6. B. H. Dean and C. W. Bowers, "Diversity selection for phase-diverse phase
   retrieval," *JOSA A* **20**, 1490--1504 (2003). Shows that useful defocus
   depends on aberration spatial frequency and that excessive diversity can
   reduce sensing performance.
   <https://doi.org/10.1364/JOSAA.20.001490>
7. C. Johnson *et al.*, "Phase-diversity-based wavefront sensing for
   fluorescence microscopy," *Optica* **11**, 806--820 (2024). Reports
   saturation at four nonzero diversities, five total images, under an
   incoherent spatially invariant fluorescence model.
   <https://doi.org/10.1364/OPTICA.518559>
8. S. Echeverri-Chacón *et al.*, "Vortex-enhanced coherent-illumination phase
   diversity for phase retrieval in coherent imaging systems," *Optics
   Letters* **41**, 1817--1820 (2016). Demonstrates coherent-system
   characterization with controlled illumination; it is not a proof of joint
   recovery for an arbitrary unknown complex specimen.
   <https://doi.org/10.1364/OL.41.001817>

### Sensorless and learned low-frame correction

9. D. Débarre, M. J. Booth and T. Wilson, "Image based adaptive optics through
   optimisation of low spatial frequencies," *Optics Express* **15**,
   8176--8190 (2007). Uses a low-frequency metric and three measurements per
   mode in an incoherent transmission microscope.
   <https://doi.org/10.1364/OE.15.008176>
10. J. Antonello *et al.*, "Semidefinite programming for model-based
    sensorless adaptive optics," *JOSA A* **29**, 2428--2438 (2012). Gives an
    `N + 1` correction rule once a semidefinite quadratic metric model has been
    identified.
    <https://doi.org/10.1364/JOSAA.29.002428>
11. H. Ren and B. Dong, "Improved model-based wavefront sensorless adaptive
    optics for extended objects using N + 2 images," *Optics Express* **28**,
    14414--14427 (2020).
    <https://doi.org/10.1364/OE.387913>
12. H. Ren and B. Dong, "Fast dynamic correction algorithm for model-based
    wavefront sensorless adaptive optics in extended objects imaging,"
    *Optics Express* **29**, 27951--27960 (2021). Uses a sequential `2N`
    scheme; each mode is corrected after two measurements.
    <https://doi.org/10.1364/OE.435171>
13. H. Ren and B. Dong, "Self-calibrated general model-based wavefront
    sensorless adaptive optics for both point-like and extended objects,"
    *Optics Express* **30**, 9562--9577 (2022). Reports `N + 1` simultaneous
    correction after a separate Gram-matrix calibration.
    <https://doi.org/10.1364/OE.454901>
14. Q. Hu *et al.*, "Universal adaptive optics for microscopy through embedded
    neural network control," *Light: Science & Applications* **12**, 270
    (2023). Builds specimen-reduced pseudo-PSFs from opposite bias images and
    demonstrates physics-informed learned estimation with as few as two input
    images, while documenting modality-specific training and low-SNR limits.
    <https://doi.org/10.1038/s41377-023-01297-x>

## Decision for the next simulation

The next Adaptive simulation should not optimize the existing oracle. It should
replace oracle access with an estimator whose only runtime inputs are delivered
probe records and noisy measured intensities. The first simulation gate is not
"large PSNR gain"; it is:

> Can a preregistered five/eight-frame policy recover or correct held-out
> low-order aberrations with calibrated uncertainty, while the truth remains
> inaccessible until scoring?

Only after this gate passes across held-out objects, noise levels, delivery
mismatch and temporal drift should the same policy advance to a known-target
hardware prescan. Unknown biological specimens come after the coherent versus
incoherent image-formation regime and the reference provenance have been
experimentally resolved.
