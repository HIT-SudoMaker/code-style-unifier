# Adaptive Restoration: Competitive Gap

Date: 2026-07-26
Status: working research synthesis
Decision authority: none; this document informs the Wayfinder scientific-contract ticket

## Conclusion

The earlier candidate claim is rejected:

> Adaptive correction reshapes the system transfer function and restores
> information before detection, whereas fixed modulation treats all samples
> uniformly.

This describes why adaptive optics can be useful. It does not establish a new
method. Direct wavefront sensing, sensorless phase diversity, learning-assisted
AO, computational AO, and phase-SLM microscopy already cover its individual
parts.

The strongest conditional gap found in the present search is instead:

> **Self-verifying active adaptive optics:** under unknown specimen structure,
> limited calibration exposure, and hardware mismatch, the system actively
> decides what to measure next, when evidence is sufficient to load a
> correction, and when correction should be refused because improvement of a
> future independent science observation is not reliable.

This is a research hypothesis, not a novelty declaration. The search found
close work in phase diversity, few-image learning, uncertainty-aware control,
and information-guided probe design. A defensible paper therefore requires the
complete decision-and-verification loop, matched-budget comparisons, and
hardware evidence.

## Scope And Evidence Labels

The search covered microscopy AO, sensorless and image-based AO,
phase-diversity wavefront estimation, computational AO, learning-assisted
physical correction, and recent active-probe design. Publisher pages, PubMed or
PMC records, and arXiv primary manuscripts were used where available.

The search was broad but not a systematic review. In particular, failure to
find an identical method must be reported as a conditional gap as of the search
date, never as proof of a global first.

The following labels govern this document:

- **Established:** directly supported by the cited work.
- **Inference:** a comparison or consequence derived from multiple sources.
- **Hypothesis:** a project idea requiring decisive experiments.

## Competitive Landscape

### Direct wavefront sensing

Direct sensing can measure and physically correct specimen-induced aberrations
in demanding microscopy. It is fast and supplies a wavefront reference, but it
adds optical complexity and may require a usable guide star. It therefore
remains an important oracle or measurement baseline, not a weak opponent.

### Image-based phase diversity

Johnson et al. estimate the unknown wavefront of extended fluorescence samples
from known phase-diversity observations. They report wavefront-sensing accuracy
below \(\lambda/35\) RMS, severe-aberration correction, and roughly
100-ms-scale sensing in their implementation. Thus, "unknown extended object,"
"few measurements," and "physical correction" are already occupied
capabilities.
Source: [Phase diversity-based wavefront sensing for fluorescence microscopy](https://doi.org/10.1364/OPTICA.518559).

### Physics-informed learning-assisted AO

Hu et al. use predefined biased observations, pseudo-PSF preprocessing, and a
small physics-informed network to estimate correction coefficients across
multiple microscopy modalities. Some demonstrated configurations use only two
or four biased images, and the learned estimator is embedded in the physical AO
control path. Few-shot estimation and specimen-structure suppression are
therefore not sufficient claims by themselves.
Source: [Universal adaptive optics for microscopy through embedded neural network control](https://doi.org/10.1038/s41377-023-01297-x).

MeNet-AO goes further: three modulated image pairs are used to decode seven
Zernike modes, including large aberrations, with reported correction below five
seconds and in vivo validation. It explicitly combines structure-independent
features, frequency-domain regularization, and a multi-encoder estimator.
"Several probes," "high-order modes," "frequency awareness," and
"cross-structure generalization" are consequently crowded territory.
Source: [Physics-informed multi-encoder adaptive optics enables rapid aberration correction for intravital microscopy of deep complex tissue](https://doi.org/10.1038/s41467-026-73389-2).

### Self-supervised and computational AO

CoCoA jointly estimates sample structure and aberration from a three-dimensional
widefield stack using coordinate-based neural representations. It demonstrates
that self-supervision and unknown-object joint inference are already substantial
computational-AO directions. Its digitally reconstructed output, however, is
different from an independent raw science observation acquired after physical
correction.
Source: [Coordinate-based neural representations for computational adaptive optics in widefield microscopy](https://doi.org/10.1038/s42256-024-00853-3).

NeAT estimates aberration and sample structure from a three-dimensional
two-photon stack, models motion and conjugation errors, and then performs
physical adaptive correction in vivo. Therefore, "self-supervised estimator
plus later physical correction" is also no longer empty territory.
Source: [Adaptive optical correction for in vivo two-photon fluorescence microscopy with neural fields](https://doi.org/10.1038/s41592-026-03053-6).

### Uncertainty-aware learning

Deep learning-driven AO for single-molecule localization microscopy already
uses inference uncertainty to select among estimators and a Kalman filter to
stabilize correction. Adding an uncertainty head is not a paper-level novelty.
The remaining question is whether uncertainty is calibrated against a
prospective harmful-correction event and whether the system may abstain.
Source: [Deep learning-driven adaptive optics for single-molecule localization microscopy](https://doi.org/10.1038/s41592-023-02029-0).

### Prescan, load, and hold

Label-free AO-SMLM measures aberration using intrinsic reflection, loads the
opposite phase on a liquid-crystal SLM, and then collects long fluorescence
science sequences with the correction held for a fixed specimen. It also
reports simultaneously acquired raw AO-off and AO-on observations. Prescan,
phase-SLM correction, held state, and raw optical improvement are therefore
necessary protocol features, not new mechanisms.
Source: [Label-free adaptive optics single-molecule localization microscopy for whole zebrafish](https://doi.org/10.1038/s41467-023-39896-2).

### Information-guided probe design

A 2025 preprint introduces Fisher-information analysis to optimize image-based
sensorless AO measurement strategies. "We optimize the phase probes" is
therefore already too weak. A new method must show that online
decision-relevant probe selection differs materially from an optimized fixed
codebook or Fisher-information design.
Source: [Information-guided optimization of image-based sensorless adaptive optics methods](https://doi.org/10.48550/arXiv.2506.07482).

## Claims That Are Already Too Weak

None of the following should carry the paper:

- a phase-only SLM performs physical aberration correction;
- correction occurs before detection;
- no digital restoration network is used after detection;
- calibration and science acquisition are causally separated;
- a correction is held for later observations;
- the specimen is unknown or extended;
- only a small fixed number of phase-diverse images is used;
- a neural network predicts Zernike coefficients;
- training uses simulated aberrations;
- the method is self-supervised;
- the method reasons in the Fourier domain;
- the corrected image has improved PSF, Strehl ratio, OTF, or image quality.

These remain important ingredients and evidence. They are not individually a
defensible novelty.

## Candidate Primary Axis: Self-Verifying Active AO

### Scientific question

Can an image-based physical AO system control the risk of making a future
science observation worse, while spending less calibration dose and time than
fixed phase-diversity protocols?

### Decision model

An adaptive episode contains:

1. an unknown specimen and aberration state;
2. nuisance state, including brightness, background, registration, SLM lookup
   table error, quantization, crosstalk, and settling;
3. a history of calibration observations and applied probe phases;
4. one of four next actions:
   - acquire another probe;
   - stop and apply a correction;
   - abstain and retain zero or safe correction;
   - after deployment, request recalibration when the held correction is no
     longer trustworthy;
5. an independent science observation that was unavailable when the action was
   selected.

The target is not merely minimum wavefront mean-square error. The target is a
decision with controlled prospective optical harm.

### Required distinction from existing uncertainty work

A credible method needs more than a predicted variance:

- uncertainty must be calibrated under specimen, aberration, SNR, and hardware
  shifts;
- the correction rule must use a lower confidence bound or an equivalent
  risk-sensitive decision criterion for expected science benefit;
- the system must be allowed to abstain;
- the reported event is whether an independent raw science observation
  improved, not whether a synthetic phase target was estimated accurately;
- calibration quality and coverage must be audited on hardware.

### Candidate paper statement

Only after successful experiments could the claim take this form:

> We introduce self-verifying image-based adaptive optics that actively selects
> calibration probes and applies phase-only correction only when a calibrated
> lower bound predicts positive benefit on a subsequent science observation.
> Under matched photon, readout, SLM-switch, and time budgets, the method reduces
> harmful corrections and calibration cost relative to fixed phase diversity,
> information-optimized fixed probes, and learning-assisted AO.

The statement is deliberately conditional. It dies if the risk guarantee does
not survive real hardware shift or if a strong fixed codebook performs
equivalently.

## Supporting Axes

### Decision-centric active phase diversity

Select the next probe by its expected value for the correction decision, not by
its ability to identify every wavefront parameter. Object structure and
hardware state are nuisance variables; wavefront states that imply equivalent
feasible corrections may belong to the same decision class.

This axis can support the primary claim if it produces different probes,
earlier stopping, or fewer harmful actions than Fisher-information and
fixed-codebook baselines. Without that separation it is incremental probe
optimization.

### Event-triggered held correction

A low-dose sentinel observation may test whether a held correction remains
valid across time, position, depth, temperature drift, or SLM drift. Its value
is not "we hold a mask"; it is an explicit decision about when the mask should
be retained, withdrawn, or recalibrated.

This is probably a secondary contribution unless long-duration biological
imaging shows a substantial gain in useful science frames per calibration cost.

### Higher-order correction from bounded intensity probes

Recovering high-order or non-modal phase from a small number of unknown-object
intensity observations may be valuable, especially with a high-resolution
phase SLM. It is nevertheless close to current phase-diversity and learning AO.
It becomes a paper axis only if identifiability, unseen-structure
generalization, and physical science-frame improvement are all demonstrated.

### Worst-band transfer evidence

Worst-band MTF, directional transfer, FRC, or robust bandwidth may explain why
a correction helps. These quantities should be mechanism panels and diagnostic
losses. "Frequency-domain restoration" alone is too crowded to define the
paper.

## Decisive Comparison Contract

The primary comparison set should include:

- no AO and system-only correction;
- known inverse-phase oracle;
- classical modal sensorless AO;
- strong fixed phase diversity;
- an optimized fixed probe codebook;
- MLAO- or MeNet-like learning-assisted estimation;
- Fisher-information-guided probes;
- direct wavefront sensing where available as measurement reference;
- computational AO as contextual comparison, clearly separated from physical
  raw-output methods.

Every comparison must account for:

- total detected photons;
- number of camera readouts;
- number of SLM state changes;
- SLM settling and total wall-clock time;
- calibration dose separate from science dose;
- equal aberration and specimen test distributions.

## Evidence And Kill Tests

### Primary outcomes

- harmful-correction rate on independent science observations;
- calibration or interval coverage of the predicted science benefit;
- expected calibration observations and elapsed calibration time;
- residual wavefront error against an independent reference where available;
- raw PSF, Strehl, FRC, and two-dimensional transfer evidence;
- usable science observations per unit calibration dose and time.

### Stress tests

- unseen specimen morphology;
- unseen combinations and amplitudes of aberrations;
- SNR and brightness shifts;
- background and motion;
- SLM LUT, quantization, registration, polarization, and settling mismatch;
- spatial and temporal drift after the correction is held.

### Kill conditions

The primary axis should be abandoned or demoted if:

- confidence is not calibrated on real hardware;
- abstention does not reduce harmful correction under matched budgets;
- a strong fixed or Fisher-optimized codebook matches the acquisition cost and
  failure rate;
- the apparent gain disappears when photons, reads, switches, and time are
  matched;
- improvements exist only after digital post-processing;
- the correction helps calibration frames but not causally later science
  observations.

No numerical success threshold should be invented before pilot distributions
and biological relevance are measured. Thresholds must be preregistered after
that pilot.

## Consequences For Restoration

- `data` and `layers` remain generic building blocks.
- `restoration` must own adaptive episodes, probe histories, correction
  decisions, abstention, held states, and independent science observations.
- The core adaptive method ends at the physically corrected detector output.
- Fixed restoration remains a reproducible historical baseline behind a
  compatibility adapter; its protocol assets and hashes remain unchanged.
- Probe count is a budget variable, not a fixed `T=8` architecture.
- The canonical research prompt must ask for counterexamples, matched-budget
  baselines, prospective risk, hardware shift, and kill tests. It must not ask
  a model to decorate an assumed novelty.

## Open Decisions

The literature does not decide:

- whether the first implementation should use a learned posterior, a
  physics-based posterior, or a hybrid estimator;
- which microscopy modality and specimen provide the strongest real
  demonstration;
- whether event-triggered recalibration belongs in the first paper;
- which hardware non-idealities can be identified with the present bench;
- whether a direct wavefront reference is available for quantitative truth;
- the final paper claim.

These questions belong to the Wayfinder scientific-contract ticket.
