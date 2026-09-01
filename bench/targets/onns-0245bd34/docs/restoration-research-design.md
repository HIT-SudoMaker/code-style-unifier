# Correctability-Aware Intelligent Optical Front End: Scientific Basis and Experimental Design

- Status: canonical research design
- Evidence verdict: `Narrow`
- Scope date: 2026-08-12
- Source basis: local mechanism analysis, verified literature, and the
  independent GPT Pro audit

This document is the first project document for restoration. It replaces the
local companion brief as the active synthesis of background, theory,
experimental design, comparison policy, and evidence limits. The original GPT
Pro delivery remains available as
[`restoration-audit-package.zip`](restoration-audit-package.zip); it is source
material, not decision authority.

ADR-0020 selects the fixed-mechanical-delay, reference-on branch. The concise
active argument and algorithm contract are in
[`restoration/intelligent-front-end.md`](restoration/intelligent-front-end.md).
Where an older research note retains a reference-off or `self-verifying`
narrative, this document and ADR-0020 take precedence.

## Executive Position

Image restoration is a measurement problem shared by astronomy, remote
sensing, computational photography, industrial inspection, biomedical
imaging, and microscopy. These fields differ in scale and modality, but each
must reason about a forward operator, a noise process, prior information, and
the point at which intervention occurs.

Digital restoration is the strongest practical performance baseline for many
conventional image-restoration tasks. Explicit inverse solvers, sparse and
low-rank methods, CNNs, Transformers, diffusion models, and object-specific
representations can compensate complex degradation after detection. Their
deployment may use CPUs, GPUs, NPUs, or dedicated accelerators; latency and
energy therefore have to be measured rather than inferred from the method
family.

The principled distinction is not that digital processing cannot compensate
optical degradation. It can. The distinction is that post-detection processing
cannot retroactively alter the measurement already formed at the detector.
Information rejected by an aperture, collapsed into an optical null space,
clipped by saturation, or buried below the effective noise floor can only be
inferred from additional measurements or prior information.

Adaptive optics (AO) intervenes before the claim-facing observation is formed.
Classical AO, sensorless AO, phase diversity, learning-assisted AO, optical
neural networks (ONNs), and programmable 4f filtering already occupy much of
this design space. Phase-only correction, few-image estimation, learned
wavefront inference, uncertainty, and programmable Fourier filtering are not
novel by themselves.

The remaining research question is narrower:

> In local, quasi-static, narrowband coherent transmission or phase imaging,
> can a fixed-reference, phase-only interferometer use at most eight
> independently read observations to estimate hardware-feasible
> correctability, choose to correct, probe again, or abstain, and improve a
> causally later raw reference-on science observation over strong fixed and
> adaptive baselines under a complete matched budget?

No candidate-specific hard gate has passed. The present programme is therefore
falsification-first. It does not yet authorize a general Adaptive Restoration
implementation or claims about fluorescence, nonlinear excitation, strong
multiple scattering, or fast live dynamics.

## 1. Background and Research Gap

### 1.1 Restoration across imaging domains

The application sequence should move from broad imaging systems to the
project's final microscopy setting:

1. **Astronomical imaging** combines pre-detection wavefront correction with
   post-detection deconvolution to mitigate dynamic atmospheric and
   instrumental point-spread functions.
2. **Remote sensing** combines acquisition coding, fusion, and reconstruction
   while preserving spatial, spectral, and radiometric validity.
3. **Computational photography** uses burst acquisition, exposure control, and
   digital fusion to trade photons, motion, dynamic range, and latency.
4. **Industrial and evidentiary imaging** emphasizes task validity: visually
   plausible enhancement is not sufficient when identity or defect evidence
   matters.
5. **Biomedical imaging** operates under dose, sampling, and biological-validity
   constraints; prior-driven restoration is powerful but must remain
   distinguishable from newly observed evidence.
6. **Microscopy** adds modality-specific coherence, depth, field, scattering,
   phototoxicity, and specimen dynamics. Coherent transmission, reflection,
   fluorescence detection, and nonlinear excitation require different forward
   models.

These domains motivate a common measurement view but do not justify direct
method transfer. Fast deformable-mirror astronomy does not establish the value
of a slower liquid-crystal spatial light modulator (LC-SLM) in microscopy, and
fluorescence restoration data do not establish a coherent-field model.

### 1.2 Three intervention points

Let \(O\) denote an object, \(\psi\) an unknown degradation or aberration state,
\(u\) a controllable optical action, \(\mathcal H_{\psi,u}\) the forward
operator, \(\mathcal D\) the detector, and \(\mathcal R_\omega\) a digital
restoration rule:

\[
O
\xrightarrow{\mathcal H_{\psi,u}}
Z
\xrightarrow{\mathcal D}
Y
\xrightarrow{\mathcal R_\omega}
\widehat O.
\]

The three intervention points are:

- pre-detection correction changes \(u\) before \(Y\) exists;
- coded acquisition changes the observations used to form \(Y\);
- post-detection restoration changes \(\mathcal R_\omega\) after \(Y\) exists.

A generic Poisson–Gaussian observation is

\[
K
\sim
\operatorname{Poisson}
\left(
\eta\,\mathcal Q[\mathcal H_{\psi,u}(O)]+b
\right),
\qquad
Y=K+
\epsilon_{\mathrm{read}},
\]

where \(\eta\) is detection efficiency, \(b\) is background, and
\(\mathcal Q\) maps a predicted field or radiance to intensity. The choice of
\(\mathcal Q\) is physical:

- coherent imaging may use \(\mathcal Q(E)=|E|^2\);
- incoherent fluorescence uses an intensity-PSF or mutual-intensity model;
- interferometric systems require explicit temporal, spectral, and
  polarization coherence.

If

\[
\mathcal D[\mathcal H_{\psi,u}(O_1)]
=
\mathcal D[\mathcal H_{\psi,u}(O_2)],
\]

then a single recorded observation cannot distinguish \(O_1\) and \(O_2\)
without another measurement or a prior. A digital model may select a plausible
solution, but the selected null-space component is not independently observed.

### 1.3 Digital restoration as the absolute comparator

Digital methods should be organized by how prior information enters the
inverse problem:

| Family | Prior or constraint | Strength | Principal risk |
|---|---|---|---|
| Richardson–Lucy, Tikhonov, TV | likelihood, smoothness, non-negativity | explicit objective and data term | forward-model mismatch and noise amplification |
| Sparse and low-rank methods | dictionary, patch recurrence, rank | interpretable structural prior | iterative cost and prior mismatch |
| Plug-and-play and unfolding | explicit data term plus learned proximal map | combines physics and learned priors | method-specific convergence and shift |
| CNN restoration | training distribution and architecture | strong amortized performance | degradation and specimen shift |
| GAN/perceptual restoration | adversarial or feature-space prior | perceptual detail | perception–distortion trade-off and hallucination |
| Transformer restoration | learned long-range interaction | strong non-local modelling | memory, data, and deployment cost |
| Diffusion/posterior restoration | learned score or generative prior | multi-modal posterior estimates | sampling cost and plausible but incorrect detail |
| Self-supervised/object-specific methods | internal statistics and per-instance fitting | reduced paired-data dependence | online cost and self-fitting to mismatch |

Representative foundations include Richardson–Lucy deconvolution
([Richardson, 1972](https://doi.org/10.1364/JOSA.62.000055);
[Lucy, 1974](https://doi.org/10.1086/111605)),
[total-variation restoration](https://doi.org/10.1016/0167-2789(92)90242-F),
[DnCNN](https://doi.org/10.1109/TIP.2017.2662206),
[content-aware image restoration](https://doi.org/10.1038/s41592-018-0216-7),
and [Restormer](https://doi.org/10.1109/CVPR52688.2022.00564).

These methods remain necessary baselines. A claimed optical advantage must be
visible on the raw optical endpoint before any optional digital processing,
while digital output remains an external absolute-performance comparator.

### 1.4 Adaptive optics

AO separates into four questions:

1. **Sensing:** Shack–Hartmann or other direct wavefront sensing, image-based
   sensorless metrics, phase diversity, interferometry, or learned inference.
2. **Representation:** Zernike modes, actuator-native modes, pixel-wise phase,
   neural fields, or other action-relevant coordinates.
3. **Control:** modal search, phase conjugation, sequential diversity,
   information-optimal probes, learned policies, or risk-aware stopping.
4. **Correction:** deformable mirror, LC-SLM, or another calibrated physical
   actuator.

Microscopy AO is established
([Booth, 2014](https://doi.org/10.1038/lsa.2014.46)). Recent systems include
deep-tissue localization AO
([Mlodzianoski et al., 2021](https://doi.org/10.1038/s41467-021-23647-2)),
embedded neural control
([Hu et al., 2023](https://doi.org/10.1038/s41377-023-01297-x)),
learning-assisted single-molecule AO
([Zhang et al., 2023](https://doi.org/10.1038/s41592-023-02029-0)),
fluorescence phase diversity
([Johnson et al., 2024](https://doi.org/10.1364/OPTICA.518559)), and
computational AO with neural representations
([Kang et al., 2024](https://doi.org/10.1038/s42256-024-00853-3)).

The present gap is not “AO with an SLM.” It is prospective decision reliability
under a strict observation budget: whether the system can determine that a
future physical correction is beneficial, harmful, or unsupported after
adaptive acquisition and optional stopping.

### 1.5 ONNs and programmable 4f filtering

Under coherent, linear, shift-invariant assumptions, an ideal 4f system applies

\[
E_{\mathrm{out}}(\mathbf r)
=
\mathcal F^{-1}
\left[
H(\mathbf k)\,
\mathcal F\{E_{\mathrm{in}}\}(\mathbf k)
\right].
\]

This gives a transparent frequency-domain interpretation
([Vander Lugt, 1964](https://doi.org/10.1109/TIT.1964.1053650)) and supports
programmable microscopy filters
([Fürhapter et al., 2005](https://doi.org/10.1364/OPEX.13.000689)).
Physical optical networks extend this idea to trainable propagation
([Lin et al., 2018](https://doi.org/10.1126/science.aat8084);
[Wright et al., 2022](https://doi.org/10.1038/s41586-021-04223-6)).

A single direct phase-only SLM implements

\[
H_{\Phi}(\mathbf k)
=
P(\mathbf k)e^{i\Phi(\mathbf k)},
\qquad
|H_{\Phi}|=P,
\]

not an arbitrary complex transfer function. Joint amplitude and phase control
normally requires encoding, multiplexing, multiple planes, or additional
filtering
([Zhu and Wang, 2014](https://doi.org/10.1038/srep07441);
[Song et al., 2012](https://doi.org/10.1364/OE.20.029844)).

Therefore:

- 4f filtering is interpretable but not inherently correct;
- an SLM makes a 4f system reconfigurable, not automatically adaptive;
- an OTF zero cannot be converted into observed evidence by inverse filtering;
- optical propagation time alone does not establish end-to-end speed or energy
  advantage;
- dynamic control is useful only when observations support the selected
  specimen-specific action.

## 2. Candidate Scope and Terminology

### 2.1 Frozen scope

ADR-0020 resolves the previously open science-endpoint choice. The candidate is
restricted to:

- local, quasi-static, narrowband coherent transmission or phase microscopy;
- a mechanically fixed reference/delay arm during each episode;
- calibrated effective arm-relative phase and drift treated as nuisance state,
  not as a mechanical action;
- a held pre-split HDSLM80RA Plus amplitude command \(A_0\);
- one HDSLM80R Plus as the only adaptive phase-only actuator;
- at most eight independently read calibration observations;
- reference-on calibration and a later raw reference-on science observation,
  both with \(R=1\);
- processing-SLM global piston as the phase-shifting mechanism, counted as a
  delivered SLM state;
- reference-blocked \(R=0\) acquisition only as a structural ablation;
- no claim-facing post-detection restoration network.

The role of \(A_0\) in a native microscope remains unresolved. It may provide
fixed illumination shaping, remain at an identity state, or reveal that the
replay topology does not transfer. It must never be silently relabelled as the
specimen.

### 2.2 Terminology ledger

| Canonical term | Definition |
|---|---|
| Fixed Restoration | completed historical replay-based fixed-measurement route |
| intelligent optical front end | complete measurement-conditioned system that measures, predicts, decides, corrects, and verifies |
| adaptive optical restoration | bounded candidate that changes a future raw optical observation |
| calibration observation \(C_t\) | independently read reference-on observation used before the decision |
| science observation \(Y_{\mathrm{sci}}\) | causally later, reference-on, claim-facing raw detector frame |
| phase action \(u_t\) | delivered phase-only SLM action \(e^{i\Phi_t}\) |
| correctability estimate | predicted prospective benefit, harm, and uncertainty before complete empirical calibration |
| safe action \(a_{\mathrm{safe}}\) | preregistered zero, system-only, or validated last-trusted correction |
| prospective benefit \(\Delta\) | later science-metric difference relative to the safe action |
| harmful correction \(H\) | event that prospective benefit crosses a negative repeatability-derived margin |
| episode | one calibration history, decision, correction delivery, settling, and independent science evaluation |

## 3. Theoretical Framework

### 3.1 Unified variable relation

Let:

- \(O\) be the unknown specimen;
- \(\psi\) be the specimen and system aberration;
- \(h\) be hardware state and mismatch;
- \(A_0\) be the held amplitude-SLM command;
- \(u=e^{i\Phi}\) be a phase-only action;
- \(R\in\{0,1\}\) be the reference-arm state.

The shared variable relation is

\[
Y
\sim
p\!\left(y\mid O,\psi,h,A_0,u,R\right).
\]

This relation does not unify physical modalities. The present derivation is
only for the narrowed coherent branch.

### 3.2 Historical replay principle

The original local system begins from a detected degraded intensity \(D\) and
replays it as a zero-phase coherent field:

\[
E_{\mathrm{in}}(\mathbf r)
=
\sqrt{D(\mathbf r)}\,e^{i0}.
\]

The fixed reference and process arms are

\[
E_r(\mathbf r)
=
\sqrt{\rho_r}\,g_r
e^{i\delta_{\mathrm{ref}}}
E_{\mathrm{in}}(\mathbf r),
\]

\[
E_{p,t}(\mathbf r)
=
\sqrt{\rho_p}\,g_p
\mathcal F^{-1}
\left[
P(\mathbf k)e^{i\Phi_t(\mathbf k)}
\mathcal F\{E_{\mathrm{in}}\}(\mathbf k)
\right].
\]

Intensity detection gives

\[
Y_t
=
|E_r+E_{p,t}|^2
=
|E_r|^2+|E_{p,t}|^2
+
2\operatorname{Re}(E_rE_{p,t}^{*}).
\]

This establishes:

\[
\text{detected image}
\rightarrow
\text{coherent amplitude replay}
\rightarrow
\text{Fourier-plane phase filtering}
\rightarrow
\text{reference-assisted interference}
\rightarrow
\text{second detected intensity}.
\]

It does not establish a native specimen field, an aberration model, adaptive
probing, a later independent science frame, or transfer to fluorescence or
nonlinear microscopy. Fixed Restoration remains historical mechanism evidence,
not evidence that the adaptive candidate works.

### 3.3 Native coherent candidate

Let \(t_O(\mathbf r)\) be specimen complex transmittance,
\(E_0(\mathbf r;A_0)\) a known held illumination state, and
\(\mathcal P_\psi\) specimen-plus-system propagation:

\[
E_s
=
\mathcal P_\psi
\left[
t_O E_0(A_0)
\right].
\]

The calibration reference arm is

\[
E_r(t)
=
\sqrt{\rho_r}\,
\mathcal L_r[E_s]\,
e^{i[\delta_0+\epsilon_{\mathrm{ref}}(t)]},
\]

where the mechanical delay fixes \(\delta_0\) during an episode and
\(\epsilon_{\mathrm{ref}}(t)\) is residual delivered drift. Neither term is
assumed to be numerically zero; both must be calibrated or tracked.

The processed calibration arm is

\[
E_{p,t}
=
\sqrt{\rho_p}\,
\mathcal L_p^{-1}
\left[
P(\mathbf k)e^{i\Phi_t(\mathbf k)}
\mathcal L_p[E_s]
\right].
\]

For \(t\leq T\leq8\), the calibration observation is

\[
K_t^{\mathrm{cal}}
\sim
\operatorname{Poisson}
\left(
\eta |E_r(t)+E_{p,t}|^2+b_1
\right),
\qquad
C_t=K_t^{\mathrm{cal}}+
\epsilon_{\mathrm{read}}.
\]

After the decision, the chosen correction is loaded, allowed to settle, and a
new science frame is acquired with the coherent reference still present. The
primary science model is

\[
K_a^{\mathrm{sci}}
\sim
\operatorname{Poisson}
\left(
\eta\,g_1 |E_r(t_{\mathrm{sci}})+E_{p,a}|^2+b_1
\right),
\qquad
Y_{\mathrm{sci}}(a)=K_a^{\mathrm{sci}}+
\epsilon_{\mathrm{read}}.
\]

The reference phase at \(t_{\mathrm{sci}}\) is a measured or predicted nuisance
state. A separate reference-off observation may be acquired as a mechanism
ablation:

\[
K_{a,R=0}^{\mathrm{abl}}
\sim
\operatorname{Poisson}
\left(
\eta\,g_0 |E_{p,a}|^2+b_0
\right).
\]

The separate \(g_0\), \(g_1\), \(b_0\), and \(b_1\) terms are essential.
Blocking the reference may alter throughput, background, polarization, or
detector mapping; \(R=1\) and \(R=0\) are not assumed to differ only by removal
of an ideal cross term. The ablation therefore cannot replace the primary
reference-on endpoint.

### 3.4 Global piston and gauge

Decompose a phase command into spatial phase and global piston:

\[
\Phi_t(\mathbf k)
=
\widetilde\Phi_t(\mathbf k)+c_t.
\]

In the ideal scalar model,

\[
Y(\delta_{\mathrm{ref}},\Phi+c)
=
Y(\delta_{\mathrm{ref}}-c,\Phi).
\]

Thus a fixed delay command does not fix the effective arm-relative phase if
SLM piston is allowed to vary. The final correction should default to a
pupil-weighted zero-mean piston gauge. Any calibration piston stepping must be
an explicit SLM state counted in the probe, switching, and settling budget.
Phase–amplitude coupling, leakage, quantization, and polarization may break the
ideal identity and require measurement.

### 3.5 Hardware-feasible phase

The delivered action is not the commanded array. A measured model is

\[
\Phi_{\mathrm{delivered}}
=
\mathcal W_{2\pi}
\left[
\mathcal C_h
\left(
\mathcal Q_L
\left[
\operatorname{LUT}_{\lambda,\mathrm{pol},T,h}
(\Phi_{\mathrm{cmd}})
\right]
\right)
\right]
+
\epsilon_{\mathrm{drift}},
\]

where \(\mathcal Q_L\) is finite-level quantization, \(\mathcal C_h\) includes
spatial response and crosstalk, and the LUT depends on wavelength,
polarization, temperature, and device state.

The hardware-feasible action set is

\[
\mathcal A_{\mathrm{hw}}(h)
=
\left\{
e^{i\Phi_{\mathrm{delivered}}}:
\Phi_{\mathrm{cmd}}\ \text{is admissible}
\right\}.
\]

Every oracle, estimator, policy, and baseline must ultimately be evaluated in
delivered-action space rather than command space.

### 3.6 Three oracle levels

Define:

- \(\mathcal A_1\): ideal complex-field control;
- \(\mathcal A_2\): ideal continuous phase-only control;
- \(\mathcal A_3=\mathcal A_{\mathrm{hw}}(h)\): calibrated delivered
  phase-only control.

For a preregistered raw-science metric \(M\),

\[
\Delta_{\mathrm{oracle}}^{(j)}
=
\max_{a\in\mathcal A_j}
M[Y_{\mathrm{sci}}(a)]
-
M[Y_{\mathrm{sci}}(a_{\mathrm{safe}})],
\qquad
j\in\{1,2,3\}.
\]

The O1–O2 gap measures the cost of phase-only control. The O2–O3 gap measures
hardware delivery loss. If O3 has no robust positive headroom over a material
specimen–aberration–SNR region, no learned estimator or active policy can
rescue the candidate.

### 3.7 Adaptive measurement

The episode history after \(t\) calibration reads is

\[
\mathcal H_t
=
\{(\Phi_1,C_1),\ldots,(\Phi_t,C_t)\}.
\]

A belief over action-relevant latent state \(z\) is

\[
q_t(z)
=
p(z\mid\mathcal H_t,h),
\]

where \(z\) may include object nuisance, aberration, registration, background,
reference drift, and delivered-phase uncertainty.

Let \(U(a,z)\) be expected prospective science utility relative to the safe
action, and define

\[
V(q)
=
\max_{a\in\mathcal A_{\mathrm{hw}}\cup\{a_{\mathrm{safe}}\}}
\mathbb E_{z\sim q}[U(a,z)].
\]

A decision-value probe rule is

\[
\Phi_{t+1}
=
\arg\max_{\Phi\in\mathcal A_{\mathrm{probe}}}
\left\{
\mathbb E_{C\sim p(\cdot\mid q_t,\Phi)}
\left[
V\!\left(
\operatorname{Bayes}(q_t;\Phi,C)
\right)
\right]
-
V(q_t)
-
\boldsymbol\lambda^\top\mathbf c(\Phi)
\right\},
\]

where \(\mathbf c(\Phi)\) contains photons, a camera read, an SLM state,
settling, compute, and wall time. This differs from minimizing wavefront
coefficient error: a probe is useful only if it can change the final physical
decision enough to justify its cost.

### 3.8 Action identifiability

Full aberration identifiability is stronger than necessary. What must be
identified is a correction-action equivalence class.

Let

\[
U^*(z)=\max_{a\in\mathcal A_{\mathrm{hw}}}U(a,z)
\]

and define the \(\varepsilon\)-optimal action set

\[
\mathcal A_\varepsilon(z)
=
\left\{
a:
U^*(z)-U(a,z)\leq\varepsilon
\right\}.
\]

For a credible latent set \(\mathcal Z_{1-\beta}(q_t)\), a common correction is
action-identifiable only if

\[
\bigcap_{z\in\mathcal Z_{1-\beta}(q_t)}
\mathcal A_\varepsilon(z)
\neq
\varnothing.
\]

If this intersection is empty at \(T=8\), the system cannot justify a common
correction and must abstain; persistent failure is a hard kill for the main
decision policy. Evaluation must therefore compare delivered action agreement
and future utility, not only Zernike-coefficient RMSE.

### 3.9 Prospective benefit, harm, and abstention

Let \(a_{\mathrm{safe}}\) be preregistered. Prospective benefit is the
potential-outcome contrast

\[
\Delta(a)
=
M[Y_{\mathrm{sci}}(a)]
-
M[Y_{\mathrm{sci}}(a_{\mathrm{safe}})].
\]

The two outcomes cannot be observed on the same exact science event.
Randomized paired or crossover episodes on quasi-static specimens are required
to estimate this contrast while modelling drift, bleaching, and order.

Define harmful correction by

\[
H(a)
=
\mathbb 1
\left[
\Delta(a)<-\tau_{\mathrm{harm}}
\right],
\]

where \(\tau_{\mathrm{harm}}\) is derived from independent repeatability and has
the units of \(M\), not radians.

A harm gate is

\[
\Pr
\left[
H(a)=1\mid\mathcal H_t
\right]
\leq\alpha,
\]

or, under a compatible calibrated procedure,

\[
\operatorname{LCB}_{1-\alpha}
\left[
\Delta(a)\mid\mathcal H_t
\right]
\geq
-\tau_{\mathrm{harm}}.
\]

A useful positive-gain claim requires a separate threshold:

\[
\operatorname{LCB}_{1-\alpha_{\mathrm{gain}}}
\left[
\Delta(a)\mid\mathcal H_t
\right]
>
\tau_{\mathrm{gain}}.
\]

At step \(t\):

1. `correct` only if the required harm and gain gates pass;
2. `probe` only if \(t<8\) and the expected decision value of another probe
   exceeds its complete cost;
3. otherwise `abstain` and execute \(a_{\mathrm{safe}}\).

The policy and stopping rule must be frozen before held-out evaluation.
Nominal calibration does not automatically survive adaptive acquisition and
optional stopping; the chosen risk procedure must be valid under the induced
episode distribution.

### 3.10 Complete budget

The comparison budget is

\[
B=
\left(
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
\right).
\]

Frame count alone is not a matched budget. Incident and detected photons,
calibration and science exposures, every camera read, every SLM state,
settling, transfer, online computation, wall time, and correction lifetime must
be reported. Offline training, tuning, hardware metrology, precision, memory,
and energy are reported separately.

An amortized efficiency claim requires

\[
N_{\mathrm{usable\ science\ frames}}
G_{\mathrm{per\ frame}}
>
C_{\mathrm{calibration}},
\]

where gain and calibration cost are expressed in the same preregistered utility
units, using measured correction lifetime rather than assumed stability.

## 4. Experimental Programme

### 4.1 Evidence order

Experiments must follow the dependency order:

\[
\text{topology and coherence}
\rightarrow
\text{oracle headroom}
\rightarrow
\text{action identifiability}
\rightarrow
\text{calibration-to-science transfer}
\rightarrow
\text{active-policy value}
\rightarrow
\text{risk and lifetime}.
\]

Training a complex policy before the first four stages pass is not justified.

### 4.2 E0 — topology and coherence

Document the native optical schematic and verify:

- the physical role of the held amplitude SLM;
- reference provenance and optical path difference;
- fringe or cross-term visibility at the deployed wavelength and
  polarization;
- reference drift \(\epsilon_{\mathrm{ref}}(t)\);
- reference-on stability during calibration and prospective science acquisition;
- arm power, background, and throughput changes between \(R=1\) and the
  reference-off mechanism ablation;
- SLM pupil conjugation, registration, LUT, and settling.

Failure to preserve the frozen topology without introducing a tunable
mechanical delay or dynamic amplitude control kills the frozen candidate rather
than silently changing it. The persistent coherent reference is part of the
selected primary topology, not an unauthorized extension.

### 4.3 E1 — O1/O2/O3 oracle headroom

Use controlled phase, amplitude, and weak-scattering conditions. For each
specimen, aberration, SNR, and hardware session:

1. optimize ideal complex control;
2. optimize ideal continuous phase-only control;
3. optimize calibrated delivered phase-only control;
4. acquire new \(R=1\) raw science frames under each held action and the safe
   action, with matched reference-state tracking;
5. report the distribution and lower confidence bound of headroom.

The required result is robust positive O3 headroom over a scientifically
material region. A single optimized example is insufficient.

### 4.4 E2 — action identifiability under `T <= 8`

Inject blinded known aberrations using Zernike and device-native modes and
combine them with unknown object textures. Evaluate prefixes
\(t=1,\ldots,8\):

- posterior or candidate latent ambiguity;
- delivered correction-action agreement;
- regret relative to the O3 oracle;
- correct/probe/abstain decision;
- future reference-on benefit and harm.

Include opposite-sign, conjugate, piston, tilt, defocus, registration, and
object-spectrum ambiguities. Surviving latent explanations are acceptable only
when they share a useful delivered action.

### 4.5 E3 — prospective reference-on science transfer

For every episode:

1. acquire only preregistered calibration observations;
2. freeze the action;
3. load the correction;
4. wait for measured settling;
5. retain and track the fixed coherent reference;
6. acquire a new raw science frame;
7. compare against randomized safe, sham, opposite-sign, and equal-RMS actions;
8. acquire a separately budgeted reference-off ablation where required to test
   the interferometric mechanism.

Frame identifiers and timestamps must prove that no science frame selected,
tuned, or thresholded its own correction.

### 4.6 E4 — adaptive policy against fixed design

Only after E1–E3 pass, compare:

- optimized fixed probe codebook;
- hardware-constrained Fisher-information codebook;
- active decision-value probes;
- conventional fixed phase diversity;
- classical modal sensorless AO;
- learning-assisted fixed-probe estimator.

Every method is evaluated at each prefix \(1,\ldots,8\), with identical
per-read photon rules and complete state/settling accounting. The same
estimator and action representation should be shared where possible so the
comparison isolates probe selection.

If the strongest fixed or Fisher codebook matches the active policy, AO may
remain feasible but the active-probing claim is removed.

### 4.7 E5 — risk, coverage, OOD, and lifetime

Freeze the complete policy and evaluate held-out specimen-by-session episodes:

- harmful-correction risk at matched coverage;
- minimum useful coverage;
- abstention frequency and causes;
- always-correct, never-correct, system-only, last-trusted, and simple-threshold
  policies;
- specimen, aberration, SNR, LUT, polarization, registration, and drift shifts;
- target and adjacent field/depth harm;
- correction lifetime and amortized benefit.

An almost-never-correct policy cannot win by trivially reducing harm. Risk must
be reported on a common coverage grid with uncertainty bands.

### 4.8 Statistical contract

- The independent unit is at least a specimen-by-session episode. Frames from
  one episode are repeated measurements, not independent \(n\).
- One raw-science primary endpoint, or one preregistered multiplicity family,
  is selected before testing.
- Known injected phase or an independent interferometer/wavefront sensor is
  used as truth where possible; model self-consistency is not truth.
- Safe, selected, sham, opposite, and equal-RMS science actions are randomized
  or balanced.
- Effect, harm, gain, risk, and coverage thresholds come from independent
  repeatability, scientific utility, and power analysis.
- Raw frames, device maps, probe histories, decisions, abstentions, negative
  cases, and complete budgets are retained.

## 5. Comparison Set

| Group | Comparator | Scientific role |
|---|---|---|
| Safe | no AO | primary fallback when no stable system correction exists |
| Safe | independently validated system-only correction | preferred fallback when its lifetime is established |
| Oracle | known-aberration phase conjugation | separates estimator error under known phase |
| Oracle | ideal complex control | upper bound on the optical geometry |
| Oracle | ideal continuous phase-only control | upper bound on the actuator class |
| Oracle | calibrated delivered phase-only control | hard attainable-headroom test |
| Classical AO | modal sensorless AO | simple controller under the same read ceiling |
| Phase diversity | conventional fixed phase diversity | core fixed-sequence competitor |
| Fixed design | optimized fixed probe codebook | hard active-probing kill test |
| Information design | Fisher-optimized fixed probes | tests value beyond coefficient information |
| Learned AO | MLAO/MeNet-style fixed-probe estimator | rapid learned-inference comparator |
| Direct sensing | Shack–Hartmann/interferometric truth where available | independent sensing and truth comparator |
| Computational | computational AO | external processed-output capability comparator |
| Digital | strong inverse/CNN/Transformer/diffusion restoration | external absolute-performance comparator |
| Decision | always/never correct, last trusted, simple metric threshold | tests whether policy complexity is necessary |

No method name is sufficient by itself. Observable, action representation,
calibration data, photon/read/state budget, compute, hardware, and output type
must be specified for every comparator.

## 6. Current Data Readiness

### 6.1 Dataset audit

The current package exposes ten registered sources. Their evaluation roles are
not equivalent.

| Source | Local public sample count | Current truth | Split status | Valid role now | Invalid interpretation |
|---|---:|---|---|---|---|
| MNIST | 60,000 train / 10,000 test | class label | official independent split | toy texture and pipeline control | microscopy or biological evidence |
| Fashion-MNIST | 60,000 train / 10,000 test | class label | official independent split | harder toy texture and pipeline control | microscopy or optical truth |
| BioSR | 670 exposed clean images | SIM-derived clean intensity | current train/test flags expose the same records | biological texture proxy, replay target, simulated object panel | coherent complex field, aberration truth, or native AO evidence |
| FMD | 288 exposed averaged images | average-based low-noise intensity | current train/test flags expose the same records | fluorescence texture proxy; potential digital denoising baseline after paired assets are exposed | coherent field or wavefront truth |
| BBBC038 | 670 exposed images | instance masks exist on disk but are not returned | current train/test flags expose the same records | morphology/OOD texture; future segmentation endpoint | clean restoration target or optical truth |
| BBBC039 | 200 exposed images | official masks and splits exist upstream but are not present in the current sample contract | current train/test flags expose the same records | nuclear morphology texture | currently valid segmentation or restoration benchmark |
| USAF target | 1 | deterministic pattern | no split needed | resolution and contrast validation | biological generalization |
| Siemens star | 1 | deterministic pattern | no split needed | angular resolution and anisotropy validation | biological generalization |
| Slanted edge | 1 | deterministic pattern | no split needed | edge-spread and MTF validation | specimen restoration |
| Line pairs | 1 | deterministic pattern | no split needed | spatial-frequency transfer validation | specimen restoration |

The counts above were measured through the current `data.load` public API, not
inferred from archive size.

### 6.2 Latent value in the raw archives

The immutable raw assets contain more information than the current adapters
expose:

- The FMD archives contain raw, 2-, 4-, 8-, and 16-frame averages plus
  average-based ground truth. The current adapter exposes only 288 averaged
  images. The source dataset was designed for Poisson–Gaussian denoising
  ([Zhang et al., 2019](https://openaccess.thecvf.com/content_CVPR_2019/html/Zhang_A_Poisson-Gaussian_Denoising_Dataset_With_Real_Fluorescence_Microscopy_Images_CVPR_2019_paper.html)).
- BioSR contains paired low/high-resolution SIM observations across biological
  structures and photon levels, while the current adapter exposes 670 clean
  images only
  ([BioSR official record](https://doi.org/10.6084/m9.figshare.13264793)).
- BBBC038 provides diverse nuclei images and per-nucleus masks
  ([official record](https://bbbc.broadinstitute.org/BBBC038)).
- BBBC039 provides 200 fluorescence fields, instance masks, and recommended
  train/validation/test metadata upstream
  ([official record](https://bbbc.broadinstitute.org/BBBC039)); the local
  adapter currently does not consume those masks or splits.

These assets should not be deleted. They may support later digital baselines
or biological endpoints after an explicit experiment-owned pairing and split
contract is implemented.

### 6.3 Current pipeline limitations for AO evidence

The current `data` design is correctly task-neutral, but its generic outputs do
not yet constitute an adaptive-optics episode:

- file-backed microscopy sources have no independent split enforcement;
- BioSR and FMD are intensity datasets, not measured coherent complex fields;
- the PSF perturbation records kernel shape and sum, not pupil phase,
  aberration coefficients, wavelength, NA, pixel scale, or action truth;
- `prepare` normalizes sensor values and may resize then zero-pad them, so
  absolute photon counts and physical sampling are not preserved as an
  evaluation contract;
- metrics over the full padded array would be dominated by artificial support
  unless the image ROI is declared;
- calibration history, delivered action, settling, hardware state, and later
  science identity do not belong to a static image sample.

These are not reasons to redesign `data`. They show why restoration must own
task assembly.

### 6.4 Evidence tiers for existing data

The present assets support four distinct tiers:

1. **Optical metrology:** USAF, Siemens star, slanted edge, and line pairs for
   registration, MTF, contrast, anisotropy, and delivered-action checks.
2. **Controlled simulation:** targets plus BioSR/FMD/BBBC textures as object
   proxies under an explicitly declared coherent simulation model, with
   injected phase, amplitude loss, noise, and hardware mismatch.
3. **Replay bench:** the same images may drive the amplitude SLM, but the result
   remains replay evidence and must be labelled as such.
4. **Native candidate evidence:** new coherent transmission or phase-microscopy
   measurements are required for topology, coherence, O3, prospective
   reference-on transfer, reference-off mechanism ablation, drift, and
   correction lifetime.

Consequently, the existing datasets are sufficient to begin E0 simulation,
optical-target validation, and the numerical part of E1/E2. They are not
sufficient to complete the decisive candidate evaluation or support a native
microscopy claim.

### 6.5 Restoration-owned episode contract

Without changing the generic `data` package, a future restoration experiment
will need an episode record containing at least:

- specimen, modality, session, field, and depth identity;
- raw detector counts and detector calibration;
- physical pixel scale, wavelength, NA, polarization, and exposure;
- injected or independently measured aberration truth when available;
- commanded and delivered phase states;
- calibration frame identities and timestamps;
- decision and stopping state;
- load and settling completion;
- new science frame identities;
- safe, sham, opposite, and equal-RMS action labels;
- complete budget coordinates.

Splits must be made at the specimen and session level. Frame-level random
splits are invalid for risk calibration and would create leakage.

## 7. Claim and Decision Ladder

### Established

- Digital restoration is a strong and necessary comparator.
- Pre-detection AO, phase-only correction, phase diversity, learned AO,
  programmable 4f filtering, and physical optical computing are established.
- The local historical mechanism is coherent amplitude replay, Fourier-plane
  phase filtering, reference-assisted interference, and second intensity
  detection.
- A direct phase-only mask does not implement arbitrary complex control.
- A zero reference command does not remove global-piston diversity.

### Hypotheses requiring evidence

- O3 provides material positive headroom in the narrowed domain.
- A useful correction action is identifiable under `T <= 8`.
- Reference-on calibration predicts prospective reference-on science benefit.
- Active probing exceeds the strongest fixed/Fisher codebook.
- Risk remains calibrated after adaptive acquisition and optional stopping.
- Abstention reduces harm at nontrivial coverage.
- Held correction lasts long enough to amortize calibration.

### Prohibited

- a global-first claim;
- general superiority of LC-SLM over deformable mirrors;
- claims that digital restoration cannot compensate optical degradation;
- claims that optical propagation alone proves speed or energy superiority;
- general fluorescence, two-/three-photon, strong-scattering, or fast-live
  transfer from the narrowed coherent model;
- use of the calibration frame as its own science evidence;
- use of replayed images as native-microscopy evidence;
- use of normalized, registered, averaged, denoised, or deconvolved output to
  supply the claimed raw optical gain.

### Decision rule for the programme

- `Kill` if the frozen topology is infeasible, O3 lacks headroom, the action is
  unidentifiable, prospective reference-on transfer fails, causal independence
  fails, or the material advantage disappears under a complete budget.
- Remain `Narrow` when the gates pass only within an explicit specimen,
  aberration, SNR, field/depth, hardware, or lifetime region.
- Consider `Continue` only after every critical unresolved item has
  candidate-specific evidence and a decisive matched-budget test.

## 8. Immediate Work Order

1. Freeze the reference-on optical schematic, fixed mechanical delay, role of
   \(A_0\), and processing-SLM piston convention.
2. Define the exact coherent modality, wavelength, NA, pixel scale, reference
   provenance, differential-aberration scope, and safe action.
3. Build a restoration-owned simulation episode from existing optical targets
   and proxy textures; do not modify the generic `data` contracts.
4. Verify four-step cross-term extraction, phase-only reachable envelopes, and
   calibrated delivered-action contraction before any learned policy.
5. Execute E0 and O1/O2/O3 with aberration truth available only to the
   evaluator.
6. Compare `4 + 1` and bounded `8 + 1` truth-blind correct/probe/abstain
   policies against the strongest fixed codebook.
7. Acquire native coherent calibration/science episodes for prospective
   reference-on transfer and separately budgeted reference-off ablation.
8. Expose FMD/BioSR pairs or BBBC annotations only when their digital or
   biological comparator is formally scheduled.

The project should not begin by selecting a neural architecture. It should
begin by determining whether the physical action is feasible, identifiable,
causally beneficial, and worth its complete cost.
