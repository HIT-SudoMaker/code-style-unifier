# Correctability-aware intelligent optical front end

- Status: active argument and design contract
- Scope: local, quasi-static, narrowband coherent transmission or phase imaging
- Claim state: hypothesis pending simulation and prospective bench evidence
- Decision date: 2026-08-12

## One-sentence argument

In coherent image restoration, we test whether a fixed-reference interferometer
can use phase-shifted measurements to infer which phase-only corrections are
physically reachable, predict whether a delivered correction will help a later
raw observation, and autonomously choose to correct, probe again, or abstain.

This is deliberately narrower than claiming a generally intelligent microscope.
The intended advance is the joint physical and decision structure: **the same
interferometric port measures correction-relevant evidence, steers the optical
transfer, and tests whether intervention is warranted.**

## Terminology ledger

| Canonical term | Meaning | Do not substitute |
|---|---|---|
| intelligent optical front end | the complete measurement-conditioned optical decision system | smart optics, AI optics |
| fixed coherent reference | mechanically fixed reference arm whose effective phase is calibrated | zero-phase reference |
| relative optical transfer | coherent sum of the reference and processing-arm transfers | generic OTF |
| phase action | spatial processing-SLM command including any declared global piston | mask data, control info |
| hardware-feasible action set | delivered phase-only actions allowed by calibrated hardware | arbitrary phase space |
| correctability estimate | predicted benefit, harm, and uncertainty before full calibration | certificate |
| correction decision | one of `correct`, `probe`, or `abstain` | binary correction |
| prospective science observation | a later raw detector frame that did not select its own correction | corrected calibration frame |
| Fixed Measurement | archived learned fixed-transform study | failed experiment |
| Adaptive Measurement | active finite-budget measurement and correction protocol | neural restoration |

## Context

Image restoration matters in astronomy, microscopy, remote sensing, and
computational photography because image quality is bounded by both the optical
measurement and the inference applied after detection. Digital inverse methods
and neural restoration provide indispensable baselines, but they operate after
the detector has already integrated the field. They can infer plausible content;
they cannot retrospectively change which photons were transferred, rejected,
saturated, or mixed into the recorded measurement.

Optical neural networks and programmable Fourier filters move computation into
the optical path, while adaptive optics estimates or optimizes a corrective
wavefront. Both fields already contain phase-only SLMs, phase diversity,
self-referenced interferometry, learned wavefront estimation, and physical
correction. The novelty cannot therefore be “four-step phase shifting”, “one
SLM senses and corrects”, “deep learning controls an SLM”, or “correction occurs
before detection”.

The unresolved opportunity is a front end that connects three questions in one
auditable contract:

1. **Reachability:** what relative transfers can this phase-only interferometer
   physically produce?
2. **Identifiability:** which useful delivered action is supported by the finite
   measurement history, even if the complete aberration is not identifiable?
3. **Intervention:** is the expected prospective benefit large and reliable
   enough to correct now, worth another probe, or too uncertain to act?

## Problem

The archived Fixed Measurement route learned a static optical transform from a
replayed intensity field. It remains valuable evidence that the bench can
realize nontrivial coherent transforms, but matched comparisons did not show
that a fixed optical front end plus a small digital back end beats a credible
digital restoration network. The scientific lesson is not that optical
processing failed. It is that a fixed transform cannot condition its action on
the current specimen, aberration, hardware state, and cost of being wrong.

Conventional AO closes part of this gap, but a wavefront estimate alone does not
answer whether the available phase-only actuator can produce a materially
better task-facing observation under the current hardware constraints. A
high-confidence coefficient estimate can still map to a poor delivered action;
two uncertain latent states can still support the same useful action. The unit
of intelligence should therefore be the **prospective correction decision**,
not reconstruction of an idealized aberration map for its own sake.

## Principle

Physics defines the feasible set; measurements locate the current episode;
learning amortizes difficult inference; decision theory prices information and
harm; a later raw frame verifies the consequence. No layer may silently do the
job of another.

The user-specified fixed delay arm is compatible with phase shifting. The
mechanics remain fixed while the processing SLM adds a global phase piston
(c_t) to its spatial command. The physical relative phase must still be
calibrated because drift, polarization, LUT error, and phase--amplitude coupling
prevent “fixed at zero” from being a trustworthy delivered state.

## Architecture

### Physical model

Let (X(\mathbf k)) be the unknown object spectrum, (H_r(\mathbf k)) the
fixed-reference transfer, (H_p(\mathbf k; a)) the processing-arm transfer
under delivered action (a), and (c_t) a global SLM piston. A reference-on
measurement is

\[
I_t(\mathbf k)=
\left|X(\mathbf k)\right|^2
\left|H_r(\mathbf k)+H_p(\mathbf k;a_t)e^{ic_t}\right|^2+n_t.
\]

For the four quadrature pistons (c_t\in\{0,\pi/2,\pi,3\pi/2\}), the ideal
cross term is

\[
C(\mathbf k)=\frac{I_0-I_\pi+i(I_{3\pi/2}-I_{\pi/2})}{4}
=|X(\mathbf k)|^2H_r^*(\mathbf k)H_p(\mathbf k;a).
\]

The object phase cancels in this ideal multiplicative model, but the object
spectrum magnitude remains. This cancellation is conditional, not universal:
it requires mutual coherence, stable registration, the declared arm model, and
aberration that is differential with respect to the reference. It does not by
itself identify arbitrary common-path specimen aberration.

The reference-on relative transfer after correction (u) is

\[
G(\mathbf k;a,u)=H_r(\mathbf k)+H_p(\mathbf k;a)e^{iu(\mathbf k)}.
\]

If the processing-arm amplitude (b=|H_p|) is fixed and only phase is
controllable, each frequency lies on a circle of radius (b) centred at
(H_r). For a desired complex transfer (G_\star), the ideal phase projection
is

\[
u_\star(\mathbf k)
=\arg\!\left(G_\star(\mathbf k)-H_r(\mathbf k)\right)
-\arg H_p(\mathbf k;a),
\]

with irreducible pointwise residual

\[
\varepsilon_{\min}(\mathbf k)
=\left|\,|G_\star(\mathbf k)-H_r(\mathbf k)|-|H_p(\mathbf k;a)|\,\right|.
\]

This is the physical feasible envelope. The actual action must additionally
belong to the calibrated delivered set \(\mathcal A_{\mathrm{hw}}(h)\), which
includes finite phase range, LUT, quantization, crosstalk, registration,
settling, polarization, and drift.

### Measurement-conditioned algorithm

For calibration history

\[
\mathcal H_t=\{(c_j,a_j,I_j,h_j)\}_{j=1}^{t},
\]

the estimator returns a posterior over correction-relevant state (z) or
directly over delivered action value:

\[
q_\theta(z\mid\mathcal H_t),\qquad
p_\theta(\Delta(u)\mid\mathcal H_t),
\]

where \(\Delta(u)\) is the improvement of a future raw reference-on science
observation relative to a preregistered safe action. In simulation, aberration
truth is passed only to the evaluator, never to the estimator or policy.

The correction candidate is chosen in delivered-action space:

\[
u_t^*=\arg\max_{u\in\mathcal A_{\mathrm{hw}}(h)}
\mathbb E[\Delta(u)\mid\mathcal H_t]
-\lambda_{\mathrm{harm}}P(\Delta(u)<-\tau_{\mathrm{harm}}\mid\mathcal H_t)
-C(u).
\]

The policy compares three utilities:

\[
d_t=\arg\max_{d\in\{\mathrm{correct},\mathrm{probe},\mathrm{abstain}\}}
U(d\mid\mathcal H_t).
\]

`correct` requires a calibrated lower confidence bound on useful gain;
`probe` requires positive expected value of information after photon, read,
switching, settling, computation, and wall-clock costs; `abstain` executes the
safe action. The claim-facing result is then acquired prospectively:

\[
Y_{\mathrm{sci}}^{t+1}
\sim p\!\left(y\mid O,\psi,h,u(d_t),R=1\right).
\]

The policy has not completed its own test until this later frame exists.

### Deep-module design

The target Adaptive implementation exposes one external Interface:

```python
run_adaptive_episode(protocol, acquisition, phase_delivery) -> AdaptiveEpisodeRecord
```

This is a deep Module: callers supply a frozen protocol and the two physical
Adapters, while probe scheduling, history, estimation, correctability,
stopping, correction delivery, prospective acquisition, and evidence capture
remain inside. `acquisition` and `phase_delivery` are real seams because both
simulation and bench Adapters are required. Estimator and policy seams remain
internal until a second scientifically justified Adapter exists.

The episode record must preserve commanded and delivered phase, raw observation
identity, timestamps, budgets, uncertainty, candidate utilities, decision,
safe action, and prospective outcome. It must not expose simulated truth as a
policy input.

### Role of learning

Learning is optional and earns its place only when it beats a physics-only
estimator under the same measurements. Appropriate roles are:

- amortized inference from raw phase-shifted interferograms;
- a residual model for unmodeled hardware and specimen effects;
- calibrated prediction of prospective benefit and harm;
- selection of an additional probe by expected decision value.

The network never synthesizes the claim-facing image. Its output changes the
physical action or the decision not to act. This preserves the distinction from
single-shot digital restoration and from learned wavefront sensing followed by
an unexamined correction.

## Experimental storyboard

### Figure 1 — The decision becomes visible

Lead with the bench and one episode: unknown degradation enters; four to eight
reference-on observations update the relative-transfer estimate; the feasible
transfer set contracts; the policy chooses `correct`, `probe`, or `abstain`;
the SLM loads a correction; a later raw frame shows the consequence. The hero
plot is the motion of the measured/estimated transfer toward the task-acceptable
region, accompanied by a benefit--risk--cost decision trace.

### Figure 2 — Physics defines capability and limitation

Show the fixed interferometric path, the phase-only reachable circles, delivered
hardware contraction, and the archived Fixed Measurement bridge. Fixed results
serve two jobs: prove the bench can realize learned coherent transfer changes,
and show why a specimen-independent transform is information-bound against a
strong digital backend. They must not be relabelled as adaptive evidence.

### Figure 3 — Unknown aberration becomes an action decision

Validate four-step demodulation, blinded low-order aberrations, object texture
changes, correction-action agreement, and ambiguity classes. Compare direct
wavefront reconstruction with action-space inference. The central question is
whether distinct latent explanations collapse onto the same useful delivered
action.

### Figure 4 — Intelligence changes when the system acts

Compare fixed quadrature, optimized fixed probes, physics-only estimation,
learned estimation, active probing, always-correct, and abstaining policies at
each measurement prefix. Plot gain, harmful-correction risk, coverage, regret,
camera reads, SLM states, settling time, and wall time.

### Figure 5 — Prospective optical evidence and mechanism

Use newly acquired raw science frames across specimens, aberrations, SNR,
sessions, and drift. Include safe, sham, opposite-sign, equal-RMS, fixed-mask,
and digital baselines. Reference-off ablation tests the interferometric mechanism;
it does not replace the main reference-on endpoint.

## Introduction architecture

Use an application-first funnel:

1. Image restoration improves what an imaging system can resolve or measure,
   but reliability depends on where information loss occurs.
2. Digital and learned restoration are powerful after detection yet face
   calibration, domain-shift, and measurement-null limitations.
3. ONNs and programmable optics move processing forward, while AO measures and
   corrects wavefronts; neither phase-only optimization nor few-frame sensing
   alone supplies a physical performance envelope plus an intervention rule.
4. The gap is not another wavefront estimator. It is a front end that knows the
   hardware-feasible region, predicts whether correction will help the next raw
   measurement, and can spend information or abstain.
5. Here we test a fixed-reference interferometric system in which one optical
   port acts as residual input, sensing reference, transfer anchor, and
   prospective verification path.

Draft the final Introduction only after the decisive results exist. Until then,
paragraph 5 remains a hypothesis statement rather than “here we demonstrate”.

## Trade-offs and boundaries

- A fixed mechanical delay is simpler and more stable, but moves all rapid
  phase diversity onto the SLM and makes reference drift calibration mandatory.
- Reference-on science preserves the interferometric transfer-steering claim,
  but requires coherent stability and prevents broad transfer to fluorescence.
- `4 + 1` is the minimal transparent protocol; `8 + 1` offers decision-adaptive
  information at added read, settling, and motion cost.
- At a 60 Hz camera cadence, five, nine, and ten exposures occupy ideal lower
  bounds of approximately 83, 150, and 167 ms. These numbers do not equal loop
  latency until measured SLM settling, transfer, exposure, and online
  computation are included.
- Action-space inference may need fewer identifiable degrees of freedom than a
  full wavefront, but it cannot evade a genuine gauge or hardware null space.
- “Intelligent” raises the evidence burden: a neural estimator alone is
  insufficient; calibrated selective action and prospective benefit are needed.

## Prior-art boundary

The following primary sources establish that the ingredients are not individually
new and therefore define the comparison floor:

- four-step phase-shifting interferometry: [Yamaguchi and Zhang, 1997](https://opg.optica.org/ol/abstract.cfm?uri=ol-22-16-1268);
- self-referenced interferometric sensing with LC-SLM correction: [Bai and Rao, 2010](https://doi.org/10.1016/j.optcom.2010.03.032);
- one SLM used for sensing and correction: [Martínez-Cuenca et al., 2011](https://opg.optica.org/ol/abstract.cfm?uri=ol-36-18-3702);
- modal sensorless correction and identifiability: [Antonello et al., 2012](https://doi.org/10.1364/JOSAA.29.002428);
- self-coherent interferometric field estimation: [Mazoyer et al., 2013](https://doi.org/10.1051/0004-6361/201321706);
- empirical interaction-matrix correction: [Haffert et al., 2023](https://doi.org/10.1051/0004-6361/202244960);
- reinforcement-learning sensorless AO: [Hu et al., 2021](https://doi.org/10.1364/BOE.427970);
- learned microscopy AO: [Hu et al., 2023](https://www.nature.com/articles/s41377-023-01297-x);
- phase-only complex-field encoding: [Bolduc et al., 2014](https://opg.optica.org/ol/abstract.cfm?uri=ol-39-7-2137);
- correctability as a distinct optical quantity: [Lee, 2006](https://doi.org/10.1364/JOSAA.23.002602);
- learned phase-bias single-shot sensing with physical SLM residual correction:
  [Baharlou et al., 2026](https://www.nature.com/articles/s41467-026-72364-1).

The defensible candidate distinction is the tested conjunction of a fixed
reference, relative-transfer feasible set, measurement-only action inference,
prospective correctability prediction, selective `correct/probe/abstain`
control, and a later raw image endpoint. Literature breadth does not establish
novelty; the decisive experiments must.

## Claim–evidence map

| Claim | Required evidence | Current status |
|---|---|---|
| phase-only interferometric correction has a calculable feasible region | analytic projection, numerical identity, delivered-action contraction | needs targeted validation |
| four-step observations identify a useful action without truth leakage | blinded simulation and controlled bench aberrations | needs evidence |
| learning improves correction decisions | matched physics-only and learned estimators | optional, needs evidence |
| correctability can be predicted before acting | prospective calibration curves and benefit/harm outcomes | needs evidence |
| `probe` and `abstain` add value | matched fixed-codebook and always-correct ablations | needs evidence |
| the later raw image improves optically | prospective reference-on acquisitions and controls | needs evidence |
| Fixed Measurement motivates adaptation | archived matched results plus unified reanalysis | partly supported; bridge analysis needed |

## Conclusion

The strongest story is not “we built a faster AO loop” and not “we applied a
neural network to an interferometer”. It is that a coherent residual port can
be elevated from a passive summation path into a physical decision interface:
it exposes the attainable transfer, supplies correction-relevant evidence,
supports a selective intervention, and verifies the next measurement. That
story is promising, but it becomes flagship-grade only if the prospective
benefit, calibrated restraint, and matched-cost advantage survive the stated
kill tests.
