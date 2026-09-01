# Restoration Foundations

- Status: superseded audit input
- Search date: 2026-07-26
- Decision authority: none
- Active synthesis:
  [`../restoration-research-design.md`](../restoration-research-design.md)

This brief is designed to be uploaded together with the companion GPT Pro
research prompt. It is self-contained: it does not assume access to a local
repository, internal documentation, experiment folders, or unpublished raw
results.

Its purpose is not to prove the proposed method. It establishes a
source-grounded starting point, exposes the strongest physical and competitive
risks, and gives GPT Pro a concrete body of claims to confirm, qualify, or
reject.

## Executive Position

Image restoration is a cross-domain problem spanning inverse problems,
computer vision, statistical inference, optical engineering, and scientific
imaging. Its methods intervene at different points in the measurement chain:

1. **pre-detection correction** changes the optical field before the detector;
2. **measurement coding** changes how information is acquired;
3. **post-detection restoration** estimates an object from recorded data.

Modern digital restoration is the strongest practical performance baseline in
many conventional benchmarks. Classical inverse solvers, CNNs, Transformers,
diffusion models, and object-specific neural representations can compensate
complex degradations after acquisition. High-capacity implementations often
use high-performance computing devices such as GPUs, NPUs, or dedicated AI
accelerators, although lightweight and classical methods can also run on CPUs
or edge hardware. Latency and energy therefore have to be measured rather than
assumed.

The principled limitation of a digital backend is not that it “cannot correct
optical degradation.” It can. The limitation is that it cannot retroactively
change the measurement already formed at the detector. Information removed by
an optical null space, clipped by saturation, buried below the effective noise
floor, or never admitted by the aperture can only be inferred from a prior; it
cannot be turned into a newly observed photon by post-processing.

Adaptive optics (AO) acts earlier. It measures or infers aberrations and uses a
deformable mirror (DM), liquid-crystal spatial light modulator (LC-SLM), or
another corrector to improve the physical observation. Optical neural networks
(ONNs) add trainable physical transformations, while 4f spatial filtering
provides a particularly transparent frequency-domain model. None of these
families alone supplies the complete answer:

- conventional AO can be measurement- and calibration-intensive;
- ONNs can optimize a point solution without mapping its deployable and harmful
  regions;
- classical 4f filters are interpretable but are often task-fixed;
- phase-only SLMs impose a strict hardware-feasible set;
- a successful simulation or replayed-image optical bench is not yet native
  microscopy AO.

The candidate research direction is therefore:

> A decision-centric, feasible-domain-aware adaptive optical restoration
> system that uses a fixed reference-arm phase, actively selects phase-only SLM
> probes, decides whether to continue, correct, or abstain, and demonstrates
> benefit only on a causally later raw science observation.

The aggressive candidate claim is not “AO restores frequencies” or “an SLM is
trainable.” Those are established. The potentially distinctive question is
whether the system can predict the prospective benefit and harm of a physical
correction under unknown specimens, finite acquisition budgets, and real
hardware errors.

The current verdict is **research-worthy but unproven**. Three issues can kill
the route before implementation:

1. the target microscopy modality may not support the assumed reference-arm
   coherence;
2. reference-assisted calibration may not transfer to reference-free science
   acquisition;
3. a phase-only oracle or the best fixed probe codebook may already reach the
   attainable benefit.

## 1. Evidence Discipline

The report uses four evidence labels:

- **Established** — directly supported by peer-reviewed primary literature or
  an exact local implementation excerpt reproduced here.
- **Qualified** — supported only under a stated modality, dataset, hardware, or
  comparison condition.
- **Hypothesis** — a proposed interpretation or method that still requires
  decisive evidence.
- **Unresolved** — insufficient information is currently available.

“Not found” never means “globally first.” Preprints are labelled and cannot
alone establish a mature field consensus.

The scoping search used PubMed, CrossRef, arXiv, publisher pages, DOI records,
and peer-reviewed open-access articles. Rate-limited or inaccessible services
were not treated as negative evidence. This is a structured scoping search,
not a PRISMA systematic review.

The working evidence pool contained 44 de-duplicated core records spanning:

- cross-domain restoration applications;
- classical, learned, and posterior digital restoration;
- direct, sensorless, phase-diversity, and learning-assisted AO;
- active acquisition, uncertainty, stopping, and abstention;
- ONNs and physical optical computing;
- 4f filtering, phase-only encoding, and SLM hardware limits.

DOI was the primary de-duplication key. Records without a DOI were matched by
normalized title and first author, and official publisher or conference pages
were preferred over secondary summaries. The companion prompt contains the
exact-neighbor and adjacent-prior query families needed to extend and
independently audit this pool.

## 2. Image Restoration as a Cross-Domain Measurement Problem

### 2.1 A unified observation model

Let \(x\) denote the object, \(\theta\) the unknown degradation state, \(u\) a
controllable optical action, \(\mathcal H_{\theta,u}\) the forward operator,
\(\mathcal D\) the detector response, and \(n\) the aggregate noise:

\[
y=\mathcal D\!\left[\mathcal H_{\theta,u}(x)\right]+n.
\]

For a photon-limited detector, a more explicit abstraction is

\[
Y\sim
\operatorname{Poisson}
\left(
\eta\,\mathcal Q[\mathcal H_{\theta,u}(x)]+b
\right)
+\epsilon_{\mathrm{read}},
\]

where \(\eta\) is detection efficiency, \(b\) is background,
\(\epsilon_{\mathrm{read}}\) is read noise, and \(\mathcal Q\) converts the
predicted field or radiance into detected intensity.

The form of \(\mathcal Q\) is modality-dependent:

- coherent imaging may use \(\mathcal Q(E)=|E|^2\);
- incoherent fluorescence generally requires an intensity-PSF or mutual
  intensity model, not a single deterministic specimen complex field;
- partially coherent and interferometric systems require an explicit
  coherence model.

This distinction is not cosmetic. A method derived under coherent field
propagation cannot be transferred to fluorescence microscopy merely by
changing the input image.

### 2.2 Where a method intervenes

The measurement chain can be written as

\[
x
\xrightarrow{\;\mathcal H_{\theta,u}\;}
z
\xrightarrow{\;\mathcal D\;}
y
\xrightarrow{\;\mathcal R_\psi\;}
\hat x .
\]

- AO changes \(u\) before \(y\) exists.
- Coded imaging changes the acquisition operator used to produce \(y\).
- Digital restoration changes \(\mathcal R_\psi\) after \(y\) exists.

If two objects satisfy

\[
\mathcal D[\mathcal H_{\theta,u}(x_1)]
=
\mathcal D[\mathcal H_{\theta,u}(x_2)],
\]

then no post-detection algorithm can distinguish them from that observation
without additional measurements or priors. A digital model can select a
plausible solution, but the selected null-space component is not independently
observed evidence.

Pre-detection control is therefore potentially valuable when it changes the
future observation operator, avoids saturation, redistributes signal into
measurable bands, or improves photon use. It is not automatically superior:
the correction may be wrong, the corrector may be insufficient, and the
calibration dose may cost more than the science benefit.

### 2.3 Application sequence

| Domain | Representative degradation | Restoration objective | Important qualification |
|---|---|---|---|
| Astronomy | atmospheric turbulence, instrumental PSF, low photon counts | deconvolution, wavefront correction, source recovery | dynamic atmospheric AO often demands bandwidth better suited to DMs than slow LC-SLMs |
| Remote sensing | platform motion, atmospheric effects, defocus, spatial–spectral trade-offs | deblurring, fusion, pansharpening | scientific validity requires spectral as well as visual fidelity |
| Computational photography | low light, motion, small pixels, limited dynamic range | burst fusion, denoising, HDR, deblurring | deployed digital pipelines show that post-processing can be fast on specialized hardware |
| Industrial and security imaging | motion, blur, compression, low resolution | inspection, detection, recognition | generative enhancement can alter task-relevant or identity-relevant details |
| Biomedical imaging | dose limits, noise, undersampling, system blur | denoising, deconvolution, quantitative recovery | perceptual quality is not equivalent to biological truth |
| Microscopy | specimen-induced aberration, scattering, local field/depth variation | preserve contrast, resolution, signal, and raw scientific evidence | this is the target family, but the exact modality remains a feasibility decision |

Richardson–Lucy deconvolution emerged from astronomical/statistical imaging
([Richardson, 1972](https://doi.org/10.1364/JOSA.62.000055);
[Lucy, 1974](https://doi.org/10.1086/111605)). Domain-aware deep restoration
appears in satellite pansharpening
([PanNet](https://openaccess.thecvf.com/content_iccv_2017/html/Yang_PanNet_A_Deep_ICCV_2017_paper.html)),
mobile burst photography
([HDR+](https://research.google/pubs/burst-photography-for-high-dynamic-range-and-low-light-imaging-on-mobile-cameras/)),
and fluorescence microscopy
([CARE](https://doi.org/10.1038/s41592-018-0216-7)).

These examples support a broad motivation, not a claim that one restoration
architecture transfers unchanged across domains.

## 3. Digital Post-Detection Restoration

### 3.1 Method families

Digital restoration is better organized by how prior information enters the
inverse problem than by a simple chronology of network names.

| Family | Representative mechanism | Strength | Principal boundary |
|---|---|---|---|
| Explicit inverse and regularization | likelihood/data fidelity plus Tikhonov, TV, non-negativity, or known noise | transparent assumptions and strong physical linkage | model mismatch and hand-designed priors |
| Sparse and low-rank models | learned dictionaries, sparse codes, non-local patch groups | effective structured priors without very large networks | expensive iterative inference and limited prior expressiveness |
| CNN restoration | amortized local/non-local mappings | high throughput after training and strong benchmark performance | training-distribution and degradation-model dependence |
| GAN/perceptual restoration | adversarial and feature-space objectives | visually plausible high-frequency detail | perception–distortion trade-off and hallucination risk |
| Transformer restoration | windowed, channel, or global attention | strong long-range interaction modelling | memory, latency, and model-size cost |
| Diffusion/posterior sampling | iterative denoising or conditional score inference | represents multi-modal solution uncertainty | conventional sampling is expensive; fast variants change this boundary |
| Deep unfolding / plug-and-play | learned prior inside an explicit optimizer | keeps a visible data-consistency structure | convergence and prior mismatch still require analysis |
| Object-specific implicit priors | optimize a network or neural field for the current object | no large paired training set required | per-instance computation and possible self-fitting to noise/model error |

Foundational examples include TV regularization
([Rudin–Osher–Fatemi](https://doi.org/10.1016/0167-2789(92)90242-F)),
K-SVD sparse modelling
([Aharon et al.](https://doi.org/10.1109/TIP.2006.881969)), weighted
nuclear-norm minimization
([Gu et al.](https://doi.org/10.1109/CVPR.2014.366)), DnCNN
([Zhang et al.](https://doi.org/10.1109/TIP.2017.2662206)), the Deep Image
Prior ([Ulyanov et al.](https://doi.org/10.1109/CVPR.2018.00984)), SwinIR
([Liang et al.](https://openaccess.thecvf.com/content/ICCV2021W/AIM/html/Liang_SwinIR_Image_Restoration_Using_Swin_Transformer_ICCVW_2021_paper.html)),
and Restormer
([Zamir et al.](https://doi.org/10.1109/CVPR52688.2022.00564)).

Diffusion restoration is a moving target. Conventional multi-step posterior
sampling can be expensive, while accelerated and distilled variants reduce
that cost. The safe statement is therefore not “diffusion cannot be real
time,” but “latency must be reported for the exact sampler, resolution,
hardware, and pre/post-processing pipeline.” Examples include
[SR3](https://arxiv.org/abs/2104.07636) and
[Come-Closer-Diffuse-Faster](https://openaccess.thecvf.com/content/CVPR2022/html/Chung_Come-Closer-Diffuse-Faster_Accelerating_Conditional_Diffusion_Models_for_Inverse_Problems_Through_Stochastic_CVPR_2022_paper.html).

### 3.2 Performance and computation

**Established:** mature digital methods are indispensable strong baselines and
often dominate conventional image-restoration benchmarks.

**Qualified:** state-of-the-art high-capacity inference may depend on
high-performance computing devices such as GPUs, NPUs, or dedicated AI
accelerators. This is not universal. Classical algorithms, lightweight CNNs,
and optimized mobile pipelines can run on CPUs or edge processors.

Every comparison should report

\[
T_{\mathrm{digital}}
=
T_{\mathrm{transfer}}
+T_{\mathrm{pre}}
+T_{\mathrm{inference}}
+T_{\mathrm{post}},
\]

and should separately report energy, memory, model initialization, and
hardware. Comparing optical propagation time against GPU kernel time while
omitting modulation, detection, conversion, and control is not a valid
end-to-end comparison.

### 3.3 Scientific validity

Digital restoration does not automatically hallucinate, but all inverse
methods use assumptions or priors. The risk rises when the measurement is weak,
the reconstruction target is underdetermined, the model is out of
distribution, or the loss prioritizes perception over fidelity.

The perception–distortion trade-off is formalized by
[Blau and Michaeli](https://openaccess.thecvf.com/content_cvpr_2018/html/Blau_The_Perception-Distortion_Tradeoff_CVPR_2018_paper.html).
Small, task-relevant structures can be unstable in learned reconstruction
([Antun et al.](https://doi.org/10.1073/pnas.1907377117)). In forensic image
enhancement, visually credible hallucinated facial features are a documented
risk
([Norman et al.](https://openaccess.thecvf.com/content/CVPR2024W/WMF/papers/Norman_An_Investigation_into_the_Impact_of_AI-Powered_Image_Enhancement_on_CVPRW_2024_paper.pdf)).

The correct comparison is therefore:

> Can pre-detection adaptation create a better raw measurement under the same
> acquisition budget, not merely a more visually pleasing output?

## 4. Classical Adaptive Optics

AO should be decomposed along four independent axes.

### 4.1 Sensing

- **Direct wavefront sensing:** Shack–Hartmann, pyramid, interferometric, or
  guide-star-based methods measure a wavefront-related observable.
- **Sensorless AO:** known trial aberrations are applied and an image metric is
  optimized.
- **Phase diversity:** known diversity patterns create multiple intensity
  observations from which object and aberration are jointly estimated.
- **Learning-assisted sensing:** a learned estimator maps one or more
  observations to an aberration or control action.

### 4.2 Representation

- Zernike or other smooth modal bases;
- corrector influence functions;
- device-native modes;
- pixel-wise phase;
- multiscale or modal-plus-residual representations.

Zernike decomposition is a representation, not a wavefront sensor. It is
attractive because it is low-dimensional and interpretable, but it is not
universally optimal.

### 4.3 Control

- open-loop correction;
- closed-loop iterative correction;
- fixed phase-diversity protocols;
- active or sequential probe selection;
- prescan-and-hold;
- event-triggered recalibration.

### 4.4 Corrector

| Property | Deformable mirror | LC-SLM |
|---|---|---|
| Typical strength | high optical throughput, faster control, broad polarization/wavelength tolerance | many pixels, flexible high-spatial-frequency phase patterns, large active area |
| Typical limitation | fewer actuators, influence-function coupling, mechanical stroke/packaging | polarization and wavelength dependence, LUT calibration, pixel crosstalk, phase wrapping, slower refresh |
| Best-fit regime | fast closed loops, broadband or high-power systems | programmable, quasi-static, narrowband, high-spatial-degree systems |

This is an application-dependent trade-off, not an absolute ranking. Under
conditions where speed is not limiting, an LC-SLM can be competitive in
dynamic range and sensitivity and offers many more controlled pixels
([Jewel et al.](https://doi.org/10.2971/jeos.2013.13073)). Practical LC-SLM
constraints have been recognized for decades
([Love](https://doi.org/10.1016/S0030-4018(97)00586-5)).

For the proposed project, a quasi-static local microscopy episode is more
compatible with an LC-SLM than atmospheric astronomy is. This is a scope
choice, not evidence that LC-SLMs outperform DMs generally.

## 5. The Modern Microscopy AO Landscape

The weak claims are already occupied:

- pre-detection aberration correction;
- phase-only SLM or DM correction;
- image-based/sensorless AO;
- unknown or extended specimens;
- few phase-diverse images;
- learned wavefront estimation;
- uncertainty-assisted feedback;
- prescan-and-hold correction;
- raw optical image improvement;
- computational joint object–aberration estimation.

Representative peer-reviewed neighbors are:

| Work | Established contribution | Remaining distinction relevant here |
|---|---|---|
| [REALM, 2021](https://doi.org/10.1038/s41467-021-23647-2) | failure-first comparison of sensorless AO metrics; robust SMLM correction | high frame count; no prospective calibrated abstention |
| [MLAO, 2023](https://doi.org/10.1038/s41377-023-01297-x) | physics-structured learned sensorless AO across multiple microscopes | predefined bias images rather than online probe choice |
| [DL-AO, 2023](https://doi.org/10.1038/s41592-023-02029-0) | learned wavefront inference, uncertainty-assisted range selection, physical correction | uncertainty is not calibrated to future harmful correction |
| [Label-free AO-SMLM, 2023](https://doi.org/10.1038/s41467-023-39896-2) | LC-SLM physical correction with calibration separated from long science acquisition | strong prior for SLM and prescan-and-hold; fixed specimens and local isoplanatic scope |
| [Phase-diversity fluorescence microscopy, 2024](https://doi.org/10.1364/OPTICA.518559) | fast object–aberration estimation from phase-diverse fluorescence images | predefined diversity and no correct/abstain risk contract |
| [CoCoA, 2024](https://doi.org/10.1038/s42256-024-00853-3) | self-supervised coordinate-based joint structure and aberration estimation | computational AO and a 3D stack, not the same physical output contract |
| [Uncertainty-driven scanning, 2025](https://doi.org/10.1364/OE.542640) | uncertainty-guided adaptive microscopy acquisition with dose/time benefits | adaptive scanning, not prospective physical-correction harm |
| [NeAT, 2026](https://doi.org/10.1038/s41592-026-03053-6) | neural-field AO from a 3D stack with motion and conjugation handling | high-dimensional acquisition; no calibrated abstention |
| [MeNet-AO, 2026](https://doi.org/10.1038/s41467-026-73389-2) | peer-reviewed early-access work using six wavefront-modulated frames and rapid learned correction in vivo | fixed probe pairs; no online stopping or correction-risk calibration |

An information-guided sensorless AO preprint already optimizes probes with
Fisher information
([Zhang et al., 2025, preprint](https://doi.org/10.48550/arXiv.2506.07482)).
Therefore, “optimized probes” cannot stand alone as novelty. A new active
policy must show that decision utility, hardware constraints, stopping, and
harmful-correction risk produce a material advantage over the best fixed
information-optimal codebook.

## 6. Optical Neural Networks

ONNs and physical neural networks train optical propagation or another
physical substrate to perform a task.

Relevant families include:

- passive diffractive networks;
- programmable Fourier optical processors;
- optical convolution and matrix multiplication;
- hybrid optoelectronic networks;
- physics-aware or in-situ-trained physical networks;
- task-specific all-optical reconstruction and denoising.

Diffractive deep neural networks established free-space optical inference
([Lin et al.](https://doi.org/10.1126/science.aat8084)). Physics-aware training
explicitly uses measured physical forward passes to mitigate model mismatch
([Wright et al.](https://doi.org/10.1038/s41586-021-04223-6)). Diffractive
processors have also been studied for hologram reconstruction
([Rahman and Ozcan](https://doi.org/10.1021/acsphotonics.1c01365)) and
all-optical denoising
([Işıl et al.](https://doi.org/10.1038/s41377-024-01385-6)).

These results establish trainability and physical processing; they do not
establish universal restoration superiority. End-to-end optical-computing
performance must include sources, encoding, modulation, detection, A/D
conversion, control, calibration, and error sensitivity
([McMahon](https://doi.org/10.1038/s42254-023-00645-5)). Even advanced optical
vision hardware reports conversion, nonlinearity, noise, and deployment
constraints
([Qiao et al.](https://doi.org/10.1038/s41586-023-06558-8)).

The defensible criticism is not that ONNs “ignore hardware feasibility.”
Hardware-aware and physics-aware training already exist. The narrower gap is
that many studies demonstrate optimized operating points without mapping:

\[
\mathcal F_{\mathrm{safe}}
=
\left\{
(x,\theta,h):
\Pr[\Delta(a)<-\tau_{\mathrm{harm}}]\leq\alpha
\right\},
\]

where \(\mathcal F_{\mathrm{safe}}\) is the specimen–aberration–hardware region
in which a deployed physical action is predictably non-harmful.

Mapping this region, detecting when the system has left it, and abstaining are
more distinctive than training another phase mask.

## 7. Classical and Programmable 4f Filtering

Under coherent, linear, shift-invariant assumptions, an ideal 4f system
implements

\[
E_{\mathrm{out}}(\mathbf r)
=
\mathcal F^{-1}
\left[
H(\mathbf k)\,
\mathcal F\{E_{\mathrm{in}}\}(\mathbf k)
\right].
\]

This makes the frequency action unusually transparent. Classical applications
include matched filtering, low/high/band-pass filtering, phase contrast,
correlation, optical differentiation, and edge enhancement. Complex spatial
filtering was established by
[Vander Lugt](https://doi.org/10.1109/TIT.1964.1053650), and programmable
Fourier-plane phase filtering has been demonstrated in microscopy
([Fürhapter et al.](https://doi.org/10.1364/OPEX.13.000689)).

For a single ideal phase-only SLM,

\[
H_\Phi(\mathbf k)
=P(\mathbf k)e^{i\Phi(\mathbf k)},
\qquad
|H_\Phi|=P.
\]

It cannot directly realize an arbitrary complex transfer function. Arbitrary
amplitude and phase control generally needs encoding, spatial multiplexing,
multiple modulation planes, or additional filtering
([Zhu and Wang](https://doi.org/10.1038/srep07441);
[Song et al.](https://doi.org/10.1364/OE.20.029844)).

The hardware-feasible phase set is closer to

\[
\Phi_{\mathrm{delivered}}
=
\mathcal W_{2\pi}
\left[
\mathcal C
\left(
\mathcal Q_L[
\operatorname{LUT}_{\lambda,\mathrm{pol},T}
(\Phi_{\mathrm{cmd}})
]
\right)
\right]
+\epsilon_{\mathrm{drift}},
\]

where \(\mathcal Q_L\) is finite-level quantization,
\(\mathcal C\) represents pixel crosstalk or spatial response,
\(\mathcal W_{2\pi}\) wraps phase, and the LUT depends on wavelength,
polarization, temperature, and device state.

Two corrections to simplistic history are necessary:

1. a 4f system is not inherently static; an SLM makes it reconfigurable;
2. a clear transfer function is not automatically a correct inverse.

If the degraded OTF is zero in a band, a passive inverse filter cannot recover
that band without another measurement or prior. Strong gain near an OTF zero
also amplifies noise. Dynamic modulation becomes scientifically interesting
only when the measurements justify a specimen-specific action.

## 8. Synthesis of the Four Routes

| Route | Intervention point | Primary strength | Primary unresolved risk |
|---|---|---|---|
| Digital restoration | after detection | strongest algorithmic flexibility and benchmark performance | cannot change the already formed measurement; prior-driven ambiguity |
| Traditional AO | before detection | physically improves the observation | sensing cost, control bandwidth, isoplanatic and corrector limits |
| ONN / physical network | during propagation | trainable parallel physical transformation | hardware mismatch, system overhead, limited safe-operating map |
| 4f filtering | Fourier plane | explicit frequency-domain mechanism | phase-only feasible set, static assumptions, unknown-degradation adaptation |

The research synthesis is:

> retain the interpretable 4f physical operator; use a phase-only SLM as a
> dynamic corrector; use modern inference and active experimental design to
> choose measurements; and evaluate the correction as a causal, budgeted,
> risk-bearing physical decision rather than only an optimization result.

## 9. Reproduced Local Mechanism Evidence

The following excerpts are reproduced so an external researcher can inspect the
actual local mechanism without accessing a repository.

They are verbatim, non-standalone implementation excerpts. Private identifiers
are intentionally retained so the evidence is not silently rewritten; the
equations and symbol definitions immediately below make the mechanism
self-contained.

### 9.1 Fourier-plane phase modulation

```python
fourier_grid_phase = self._phase_on_fourier_grid((height, width)).to(
    device=input_field.device,
    dtype=real_dtype,
)
transfer = aperture.to(dtype=input_field.dtype) * torch.exp(
    1j * fourier_grid_phase
)

spectrum = torch.fft.fftshift(torch.fft.fft2(input_field), dim=(-2, -1))
modulated_spectrum = spectrum * transfer
return torch.fft.ifft2(torch.fft.ifftshift(modulated_spectrum, dim=(-2, -1)))
```

### 9.2 Coherent arm combination and intensity detection

```python
reference_phase = torch.exp(
    1j * self._reference_phase_offset(input_field.device, input_field.dtype)
)

reference_field = reference_weight * reference_phase * input_field
process_field = process_weight * self._modulation_field(
    input_field,
    is_phase_zero=False,
)

optical_field = reference_field + process_field
return optical_field.abs().square().real
```

These excerpts implement

\[
a_r=\sqrt{\rho_r}g_r,\qquad
a_p=\sqrt{\rho_p}g_p,
\]

\[
E_r(\mathbf r)
=a_r e^{i\delta_{\mathrm{ref}}}E_{\mathrm{in}}(\mathbf r),
\]

\[
E_{p,t}(\mathbf r)
=
a_p\mathcal F^{-1}
\left[
P(\mathbf k)e^{i\Phi_t(\mathbf k)}
\mathcal F\{E_{\mathrm{in}}\}(\mathbf k)
\right],
\]

\[
Y_t
=
|E_r+E_{p,t}|^2
=
|E_r|^2+|E_{p,t}|^2
+2\operatorname{Re}(E_rE_{p,t}^{*}).
\]

The historical input was ordinarily a replayed detected image:

\[
E_{\mathrm{in}}=\sqrt{D}\,e^{i0}.
\]

Therefore, the established mechanism is:

> detected degraded image \(\rightarrow\) coherent amplitude replay
> \(\rightarrow\) compact Fourier filtering \(\rightarrow\) reference-assisted
> interference \(\rightarrow\) a second detected intensity.

It does **not** yet establish:

- a native specimen field;
- a specimen/system aberration propagation model;
- a calibration episode or adaptive probe history;
- an independently acquired science observation;
- compatibility with fluorescence, transmission, or reflection microscopy;
- a full physical V-shaped relay rather than a compact Fourier equivalent.

### 9.3 What Fixed Restoration established

The fixed-measurement program is an author-reported, bounded historical result:

- fixed phase modulation has a reproducible physical and frequency-domain
  effect;
- optical and digital stages do not behave as a trivial additive combination;
- fixed optical transforms did not establish an absolute advantage over strong
  digital neural restoration baselines;
- a single fixed phase mask is therefore insufficient as the active research
  architecture.

This supports a transition to dynamic measurement. It does not prove that the
dynamic route will work. Because the attachment does not reproduce the complete
datasets, budgets, metrics, and uncertainty analysis, GPT Pro must treat the
performance conclusion as historical context rather than independently
verified evidence.

## 10. Frozen Candidate Contract

### 10.1 Hardware and causal invariants

The candidate to be researched uses the following invariants:

1. the commanded reference-arm scalar phase offset is
   \[
   \boxed{\delta_{\mathrm{ref}}^{\mathrm{cmd}}=0\ \mathrm{rad}};
   \]
2. the delivered reference phase may drift,
   \[
   \delta_{\mathrm{ref}}^{\mathrm{delivered}}(t)
   =\epsilon_{\mathrm{ref}}(t),
   \]
   but \(\epsilon_{\mathrm{ref}}\) is a measured or modelled nuisance, never an
   episode action;
3. the delay line is calibrated once and is not trained, searched, or adjusted
   during an episode;
4. the bench uses two independent LCOS devices with separate response models
   and LUTs: a pre-split HDSLM80RA Plus amplitude encoder and an HDSLM80R Plus
   in the V-shaped 4f processing arm;
5. the input-amplitude SLM remains unchanged throughout the episode;
6. the Fourier-plane phase-only SLM is the only adaptive optical actuator;
7. at most eight independently read calibration observations are available
   before a decision; \(T\leq8\) is a ceiling, not a fixed eight-probe
   sequence, and later science exposures remain separate budget items;
8. the reference arm participates only in calibration observations;
9. the science observation is acquired after the correction is loaded and
   settled, with the reference arm absent from the science measurement;
10. no post-detection restoration network belongs to the core method;
11. a calibration observation cannot serve as its own science evidence.

Any design requiring a tunable delay, DM, dynamic amplitude SLM, persistent
science reference arm, or digital restoration output is an out-of-scope
alternative, not a quiet modification of the candidate.

### 10.2 Fixed reference offset is not fixed effective arm phase

In the ideal scalar compact-4f model, and only when the delivered piston acts
as a uniform phase factor over the admitted spectrum, decompose the phase-SLM
action into a spatial component and a global piston:

\[
\Phi_t(\mathbf k)=\widetilde\Phi_t(\mathbf k)+c_t.
\]

Then

\[
E_{p,t}'=e^{ic_t}E_{p,t},
\]

and

\[
Y(\delta_{\mathrm{ref}},\Phi+c)
=
Y(\delta_{\mathrm{ref}}-c,\Phi).
\]

Thus, fixing \(\delta_{\mathrm{ref}}^{\mathrm{cmd}}=0\) fixes the commanded
delay-line/reference-arm parameter, but an SLM global piston can still change
effective arm-relative phase. The design must either gauge-fix \(c_t=0\), or,
if piston is allowed, represent it explicitly as a recorded and budgeted SLM
action. In the latter case it must be counted in switching and settling,
distinguished from delay-line tuning, and modelled explicitly in inference.

For the final held science correction, piston is irrelevant only in the ideal
reference-free, single-arm intensity model. Phase–amplitude coupling,
zero-order leakage, quantization, and polarization mismatch must be tested
rather than hidden inside the ideal identity.

### 10.3 Modality-dependent calibration model

On the reproduced bench, \(A_0\) is the fixed pre-split amplitude-encoding
command that replays a digital target; it is not a native specimen. A native
microscopy design must explicitly determine whether that device carries a
fixed illumination role, is held at an identity state, or makes the present
topology inapplicable. Replayed-field evidence must never be relabelled as
native-specimen evidence.

For a coherent or mutually coherent calibration field, a candidate model is

\[
C_t
\sim
p\!\left(
c\mid
\left|
E_r(O,\psi,h)
+E_p(O,\psi,h,\Phi_t)
\right|^2
\right).
\]

For incoherent fluorescence, the correct observation may instead take the form

\[
C_t
\sim
\operatorname{Poisson}
\left(
\eta\,[O*h_{\psi,\Phi_t}]
+b
\right)
+\epsilon_{\mathrm{read}},
\]

unless a physically justified mutual-coherence/self-interference model is
available. GPT Pro must determine which model is valid for each target
modality. The coherent replay equation must not be copied into fluorescence AO
without this derivation.

### 10.4 Reference-free science model

After selecting correction \(a\), loading it, settling the SLM, and excluding
the calibration reference arm:

\[
Y_{\mathrm{sci}}(a)
\sim
p\!\left(
y\mid O,\psi,h,A_0,u_a,R=0
\right).
\]

The reference-removal step creates a possible calibration-to-science domain
shift. The selected correction must remain optimal or beneficial under this
different observation topology.

## 11. Dynamic Measurement and Decision Theory

Let the episode history be

\[
\mathcal H_t
=
\{(\Phi_1,C_1),\ldots,(\Phi_t,C_t)\}.
\]

A state estimator maintains

\[
q_t(z)
=
p(z\mid\mathcal H_t,h),
\]

where \(z\) may include object nuisance variables, aberration state, delivered
SLM phase, registration, background, and reference-arm uncertainty.

The next probe is selected by decision value, not solely coefficient accuracy:

\[
\Phi_{t+1}
=
\arg\max_{\Phi\in\mathcal A_{\mathrm{SLM}}}
\left\{
\mathbb E[
V(q_{t+1})-V(q_t)
]
-\lambda\,\operatorname{cost}(\Phi)
\right\}.
\]

After each observation:

\[
a_t\in
\{\text{continue},\text{correct},\text{abstain}\}.
\]

### 11.1 Prospective science benefit

Let \(a_{\mathrm{safe}}\) be a preregistered safe action such as system-only
correction, zero sample correction, or the last trusted correction:

\[
\Delta(a)
=
M[Y_{\mathrm{sci}}(a)]
-M[Y_{\mathrm{sci}}(a_{\mathrm{safe}})].
\]

The metric \(M\) is oriented so that larger is better.

Define harmful correction using a separately named margin:

\[
H(a)
=
\mathbb 1[
\Delta(a)<-\tau_{\mathrm{harm}}
].
\]

\(\tau_{\mathrm{harm}}\geq0\), and \(\tau_{\mathrm{harm}}=0\) gives a strict
no-harm definition. If detector
repeatability requires a nonzero practical margin, it must be derived from a
preregistered repeatability study, not tuned on test outcomes.

A candidate risk gate is

\[
\Pr[
H(a)=1
\mid\mathcal H_t
]
\leq\alpha,
\]

or equivalently under a compatible calibrated bound,

\[
\operatorname{LCB}_{1-\alpha}
[
\Delta(a)\mid\mathcal H_t
]
\geq
-\tau_{\mathrm{harm}}.
\]

If the method also claims a minimum positive benefit, define a separate
\(\tau_{\mathrm{gain}}\geq0\) and require

\[
\operatorname{LCB}_{1-\alpha_{\mathrm{gain}}}
[
\Delta(a)\mid\mathcal H_t
]
>
\tau_{\mathrm{gain}}.
\]

If a required risk or benefit gate fails:

- continue only when the expected decision value of another probe exceeds its
  acquisition cost and budget remains;
- otherwise abstain and use \(a_{\mathrm{safe}}\).

Uncertainty in wavefront coefficients is not enough. The target uncertainty is

\[
\Pr[
\Delta(a)<-\tau_{\mathrm{harm}}
\mid\mathcal H_t
].
\]

### 11.2 Complete budget

Fair comparison requires the vector

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

Matching only frame count is insufficient. Incident dose and detected photons,
calibration and science allocation, camera reads, SLM changes, settling,
online computation, end-to-end wall time, reference/process arm energy split,
and amortization over the useful correction lifetime all matter. Offline
training data, compute platform, precision, memory, and energy must also be
reported whenever they support a speed or efficiency claim.

If material coordinates cannot be matched and no preregistered exchange rule
exists, report a resource–performance frontier rather than calling the
comparison matched-budget.

## 12. Feasibility Gates

### 12.1 Modality and coherence

The strongest immediate risk is whether the target science modality supports
the proposed calibration reference.

GPT Pro must separately analyze:

- coherent transmission or phase microscopy;
- reflection microscopy;
- fluorescence detection;
- two-/three-photon excitation AO;
- replayed-field mechanism benches.

For fluorescence, it must determine whether the reference is derived from the
same emission, a reflection channel, excitation light, or another guide-star
mechanism; whether path length is within coherence length; and whether phase
stability is sufficient. If no physically valid reference-assisted calibration
exists, the current candidate is killed or narrowed to a coherent modality.

### 12.2 Object–aberration identifiability

Required questions include:

- Can unknown object structure and aberration be separated from few intensity
  observations?
- Are phase sign, complex conjugation, piston, defocus, or symmetric modes
  ambiguous?
- Do object-spectrum or OTF zeros hide action-relevant modes?
- Can reference amplitude/phase, sample aberration, system aberration, LUT
  error, and pupil registration error be separated?
- If the full state is not identifiable, is the best correction action still
  identifiable as an equivalence class?

### 12.3 Phase-only oracle headroom

Before training any policy, evaluate

\[
\Delta_{\mathrm{oracle}}
=
\max_{\Phi\in\mathcal A_{\mathrm{SLM}}}
M[Y_{\mathrm{sci}}(\Phi)]
-M[Y_{\mathrm{sci}}(a_{\mathrm{safe}})].
\]

If this headroom is small under amplitude scattering, depolarization,
multiple scattering, limited phase stroke, or spatial-frequency mismatch, the
route should stop. No estimator can outperform its actuator’s oracle.

### 12.4 Calibration-to-science transfer

The reference arm is present during calibration and absent during science
acquisition. A correction selected to optimize an interferometric calibration
metric may not optimize the reference-free science image. This must be tested
with:

- known injected aberrations;
- independent wavefront truth where possible;
- sham and opposite-sign corrections;
- matched reference-on/reference-off controls;
- repeated science frames acquired only after the decision.

### 12.5 Hardware-delivered phase

The relevant action is delivered phase, not command phase. Required evidence
includes:

- wavelength- and polarization-specific LUT;
- phase stroke and wrapping;
- quantization;
- pixel crosstalk and fill factor;
- zero-order leakage;
- pupil conjugation and registration;
- SLM settling and flicker;
- temperature and session drift;
- reference/process gain and insertion loss.

### 12.6 Correction lifetime

A held correction is useful only if

\[
N_{\mathrm{usable\ science\ frames}}
\times
G_{\mathrm{per\ frame}}
>
C_{\mathrm{calibration}}.
\]

The spatial field, depth, time, slide, and specimen region over which this holds
must be measured rather than assumed.

## 13. Competitive and Experimental Contract

### 13.1 Required baselines

1. no AO;
2. system-only correction;
3. known-aberration phase-conjugate oracle;
4. classical modal sensorless AO;
5. conventional phase diversity;
6. optimized fixed probe codebook;
7. Fisher-information-optimized probes;
8. learning-assisted AO such as MLAO/MeNet-style estimators;
9. direct wavefront sensing where available;
10. computational AO and strong digital restoration as external comparators.

External digital methods may establish the absolute performance ceiling, but
their processed outputs cannot be relabelled as the proposed raw optical
output.

### 13.2 Primary outcomes

- independent wavefront error or known injected-phase recovery;
- raw science PSF, Strehl, FRC, two-dimensional transfer, contrast, and signal;
- harmful-correction rate;
- risk–coverage curve;
- abstention coverage;
- expected probe count;
- complete budget and amortized cost;
- performance under specimen, aberration, SNR, LUT, registration,
  polarization, and drift shifts;
- biological task metrics only when the modality and statistical unit are
  valid.

### 13.3 Kill tests

Every test must preregister its endpoint and direction, threshold, statistical
unit and repeats, confidence interval or risk bound, independent science
observation, complete budget, and whether failure kills the route or only
narrows a claim. The central candidate is killed or narrowed if any
corresponding claim fails:

- **Exact-prior kill:** a peer-reviewed exact neighbor already implements the
  full causal contract. This kills the corresponding novelty claim, not the
  underlying optical feasibility.
- **Oracle kill:** calibrated hardware-delivered phase-only oracle headroom is
  insufficient after comparison with ideal complex-field and ideal phase-only
  oracle levels.
- **Action-identifiability kill:** the full state may be ambiguous, but no
  correction-action equivalence class is identifiable from the allowed probes.
- **Fixed-codebook kill:** the best fixed codebook matches active probing under
  the full budget.
- **Fisher kill:** information-optimal fixed probes match decision utility and
  failure rate.
- **Calibration-transfer kill:** reference-assisted calibration does not
  improve reference-free science observations.
- **Selective-risk kill:** abstention does not reduce harmful correction at
  matched coverage.
- **Trivial-policy kill:** the method does not beat always-correct,
  never-correct, last-trusted, or a simple image-metric threshold.
- **Circularity kill:** the science frame selects or tunes its own correction.
- **Budget-confound kill:** the advantage disappears after matching photons,
  reads, SLM states, settling, compute, and wall time.
- **Hardware-gap kill:** digital phase estimates are accurate but delivered SLM
  phase does not improve raw science observations.
- **Sham/sign kill:** random, opposite-sign, or equal-RMS non-corrective phase
  produces similar benefit.
- **Goodhart kill:** the optimized calibration metric improves but independent
  optical/science metrics do not.
- **OOD kill:** confidence fails under target specimen or hardware shifts.
- **Isoplanatic kill:** the target ROI improves while adjacent field/depth is
  systematically harmed.
- **Lifetime kill:** held correction expires before calibration cost is
  amortized.
- **Native-specimen kill:** the effect exists only for replayed images.
- **Post-processing kill:** normalization, registration, averaging, denoising,
  or deconvolution supplies the apparent gain.

## 14. Candidate Claim Ladder

### Established now

- Digital restoration is a strong and necessary baseline.
- Pre-detection optical correction and phase-only SLM AO are established fields.
- Fixed 4f phase modulation has an interpretable physical effect.
- The existing local mechanism is a replayed-field compact 4f interferometric
  processor, not native microscopy AO.
- A fixed reference-arm offset of \(0\) rad is compatible with the current
  mechanism, but it does not eliminate SLM-piston phase diversity.

### Supported research inference

- Fixed optical modulation alone is too rigid for unknown, varying degradation.
- A quasi-static microscopy scope is more compatible with LC-SLM control than
  fast atmospheric AO is.
- The most defensible opportunity lies in decision reliability and a mapped
  feasible domain, not in basic AO or trainable Fourier filtering.

### Hypotheses requiring decisive evidence

- Active probes outperform the best fixed codebook under a complete budget.
- A calibration-only reference arm yields a correction that transfers to a
  reference-free science frame.
- The system can calibrate prospective harmful-correction risk.
- Abstention reduces harmful corrections without making coverage useless.
- Held correction remains useful long enough to amortize calibration.

### Prohibited claims

- global first;
- SLM is generally superior to DM;
- digital restoration cannot correct optical degradation;
- ONNs do not consider hardware constraints;
- 4f filtering is inherently static;
- fixed reference phase resolves object–aberration ambiguity;
- a replayed-image bench proves native fluorescence AO;
- few probes, phase-only control, raw output, or uncertainty alone constitute
  novelty.

## 15. Local Research Verdict

The strongest defensible paper question is:

> Under unknown specimens and finite photons, reads, SLM states, settling, and
> compute, can a fixed-reference, phase-only adaptive optical system decide
> what to measure, when to stop, and when not to apply a correction, while
> improving a causally later reference-free raw science observation?

This question is bolder than “dynamic SLM restoration” and more defensible than
“optics restores frequencies that digital methods cannot.”

The route should remain in research mode until GPT Pro resolves:

1. target modality and reference coherence;
2. a valid native forward model;
3. phase-only oracle headroom;
4. reference-on calibration to reference-off science transfer;
5. exact-neighbor and adjacent-prior novelty;
6. a complete matched-budget protocol.

The recommended current verdict is **Continue to decisive external research;
defer implementation**. Here, `Continue` authorizes falsification work, not a
paper claim. The external verdict must aggregate hard gates as follows:

- `Kill` if the frozen contract must be violated, the hardware-delivered
  phase-only oracle has no headroom, the correction action is unidentifiable,
  calibration does not transfer to reference-free science, or causal/budget
  confounding cannot be excluded;
- `Narrow` if the hard gates pass only within an explicit modality, specimen,
  aberration, field/depth, budget, or hardware scope;
- `Continue` only when no hard gate has failed and every critical unresolved
  item has a decisive matched-budget experiment.

A critical `NR` cannot support an unconditional `Continue`.

## 16. Questions the External Audit Must Answer

1. Which microscopy modality can physically support the frozen contract?
2. Does a calibration-only reference arm create a usable and identifiable
   signal when \(\delta_{\mathrm{ref}}^{\mathrm{cmd}}=0\), including realistic
   delivered-phase drift?
3. Should SLM global piston be an explicit probe dimension or a gauge-fixed
   nuisance?
4. What is the minimum probe family required to break sign, conjugation, and
   object–aberration ambiguities?
5. Is the correction action identifiable even when the full aberration is not?
6. What phase-only oracle gain remains under amplitude/multiple scattering?
7. Does an exact or adjacent prior already occupy active stopping, calibrated
   correction-risk estimation, and abstention?
8. Can a fixed information-optimal codebook match the active policy?
9. What safe action is scientifically valid: zero correction, system-only
   correction, or last trusted correction?
10. Which raw science metric can define prospective benefit without circularity?
11. How should risk calibration remain valid after adaptive data acquisition?
12. What native-specimen experiment is the minimum bridge beyond replayed-field
    evidence?

## Selected Web-Accessible Evidence

### Digital restoration and applications

- Richardson, *Bayesian-Based Iterative Method of Image Restoration*,
  [JOSA 1972](https://doi.org/10.1364/JOSA.62.000055).
- Lucy, *An iterative technique for the rectification of observed
  distributions*, [Astronomical Journal 1974](https://doi.org/10.1086/111605).
- Rudin, Osher and Fatemi, *Nonlinear total variation based noise removal
  algorithms*, [Physica D 1992](https://doi.org/10.1016/0167-2789(92)90242-F).
- Aharon, Elad and Bruckstein, *K-SVD*, [IEEE TIP
  2006](https://doi.org/10.1109/TIP.2006.881969).
- Zhang et al., *Beyond a Gaussian denoiser: residual learning of deep CNN for
  image denoising*, [IEEE TIP
  2017](https://doi.org/10.1109/TIP.2017.2662206).
- Weigert et al., *Content-aware image restoration*, [Nature Methods
  2018](https://doi.org/10.1038/s41592-018-0216-7).
- Liang et al., *SwinIR*, [ICCV Workshops
  2021](https://openaccess.thecvf.com/content/ICCV2021W/AIM/html/Liang_SwinIR_Image_Restoration_Using_Swin_Transformer_ICCVW_2021_paper.html).
- Zamir et al., *Restormer*, [CVPR
  2022](https://doi.org/10.1109/CVPR52688.2022.00564).
- Hasinoff et al., *Burst photography for high dynamic range and low-light
  imaging*, [Google Research](https://research.google/pubs/burst-photography-for-high-dynamic-range-and-low-light-imaging-on-mobile-cameras/).
- Yang et al., *PanNet*, [ICCV
  2017](https://openaccess.thecvf.com/content_iccv_2017/html/Yang_PanNet_A_Deep_ICCV_2017_paper.html).

### Adaptive optics and active acquisition

- Booth, *Adaptive optical microscopy: the ongoing quest for a perfect image*,
  [Light: Science & Applications
  2014](https://doi.org/10.1038/lsa.2014.46).
- Mlodzianoski et al., *Robust adaptive optics for localization microscopy
  deep in complex tissue*, [Nature Communications
  2021](https://doi.org/10.1038/s41467-021-23647-2).
- Hu et al., *Universal adaptive optics for microscopy through embedded neural
  network control*, [Light: Science & Applications
  2023](https://doi.org/10.1038/s41377-023-01297-x).
- Zhang et al., *Deep learning-driven adaptive optics for single-molecule
  localization microscopy*, [Nature Methods
  2023](https://doi.org/10.1038/s41592-023-02029-0).
- Park et al., *Label-free adaptive optics single-molecule localization
  microscopy for whole zebrafish*, [Nature Communications
  2023](https://doi.org/10.1038/s41467-023-39896-2).
- Johnson et al., *Phase-diversity-based wavefront sensing for fluorescence
  microscopy*, [Optica
  2024](https://doi.org/10.1364/OPTICA.518559).
- Kang et al., *Coordinate-based neural representations for computational
  adaptive optics in widefield microscopy*, [Nature Machine Intelligence
  2024](https://doi.org/10.1038/s42256-024-00853-3).
- Ye et al., *Learned, uncertainty-driven adaptive acquisition for
  photon-efficient scanning microscopy*, [Optics Express
  2025](https://doi.org/10.1364/OE.542640).
- Zhang et al., *Information-guided optimization of image-based sensorless
  adaptive optics methods*, [arXiv preprint
  2025](https://doi.org/10.48550/arXiv.2506.07482).
- Kang et al., *Adaptive optical correction for in vivo two-photon
  fluorescence microscopy with neural fields*, [Nature Methods
  2026](https://doi.org/10.1038/s41592-026-03053-6).
- Cheng et al., *Physics-informed multi-encoder adaptive optics enables rapid
  aberration correction for intravital microscopy of deep complex tissue*,
  [peer-reviewed early-access, Nature Communications
  2026](https://doi.org/10.1038/s41467-026-73389-2).

### Optical computing, 4f filtering, and SLM constraints

- Vander Lugt, *Signal detection by complex spatial filtering*, [IEEE
  Transactions on Information Theory
  1964](https://doi.org/10.1109/TIT.1964.1053650).
- Fürhapter et al., *Spiral phase contrast imaging in microscopy*, [Optics
  Express 2005](https://doi.org/10.1364/OPEX.13.000689).
- Lin et al., *All-optical machine learning using diffractive deep neural
  networks*, [Science 2018](https://doi.org/10.1126/science.aat8084).
- Wright et al., *Deep physical neural networks trained with
  backpropagation*, [Nature
  2022](https://doi.org/10.1038/s41586-021-04223-6).
- Rahman and Ozcan, *Computer-free, all-optical reconstruction of holograms
  using diffractive networks*, [ACS Photonics
  2021](https://doi.org/10.1021/acsphotonics.1c01365).
- Işıl et al., *All-optical image denoising using a diffractive visual
  processor*, [Light: Science & Applications
  2024](https://doi.org/10.1038/s41377-024-01385-6).
- McMahon, *The physics of optical computing*, [Nature Reviews Physics
  2023](https://doi.org/10.1038/s42254-023-00645-5).
- Zhu and Wang, *Arbitrary manipulation of spatial amplitude and phase using
  phase-only spatial light modulators*, [Scientific Reports
  2014](https://doi.org/10.1038/srep07441).
- Song et al., *Optimal synthesis of double-phase computer generated
  holograms using a phase-only spatial light modulator with grating filter*,
  [Optics Express 2012](https://doi.org/10.1364/OE.20.029844).
- Jewel et al., *A direct comparison between a MEMS deformable mirror and a
  liquid crystal spatial light modulator in signal-based wavefront sensing*,
  [JEOS 2013](https://doi.org/10.2971/jeos.2013.13073).
