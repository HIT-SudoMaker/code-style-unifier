---
record_type: research_record
date: 2026-08-13
status: research_finding
authority_level: none
current_capability: false
---

# Achromatic compensation-phase roadmap after the monochromatic metalens closure

## Research question

What is the exact Din Ping Tsai-group compensation-phase lineage, what physical
contract must MetaCraft add to move from a single-wavelength metalens to a
continuous-band achromatic metalens, how does that programme compare with
MetaChat, and are the monochromatic and achromatic demonstrations sufficient
for a publishable paper?

This record extends the earlier
[Tsai-group continuous-achromatic benchmark study](2026-08-09-tsai-continuous-achromatic-metalens-benchmark.md).
It uses only original articles, publisher or author-hosted papers and
supplements, and the authors' official code repository. It selects no route,
adds no capability, and changes no current single-wavelength claim.

## Executive finding

The user's intended method is identifiable without ambiguity. Its theoretical
source is Wang et al. 2017 and its visible transmissive demonstration is Wang
et al. 2018, both with Din Ping Tsai. The method is not merely "run the same
lens at several wavelengths." It jointly assigns:

1. a wavelength-independent PB orientation phase;
2. a wavelength-dependent, phase-unwrapped complex response from an
   integrated-resonant unit element; and
3. one aperture-wide spectral phase offset that changes library coverage but
   not focusing.

For an air-side fixed-focus lens, the required relative phase is linear in
optical frequency. Consequently, Tsai's compensation-phase condition and the
usual relative-group-delay condition are the same first-order physical
condition expressed in different variables. A continuous-band claim still
requires interior spectral validation: matching two endpoints is insufficient
unless the unit response is independently shown to be linear between them.

Architecturally, MetaCraft should not turn `Field` into a spectral tensor and
should not add an achromatic workflow beside `conduct`. One achromatic proof
should compose exact single-wavelength `Field` facts, while one deep spectral
response Module owns phase unwrapping, common polarization channels,
interpolation, phase-slope diagnostics, and design/holdout grids. The current
singular `control strategy` framing also needs deliberate treatment because
the Tsai method composes geometric phase and resonant phase dispersion; it is
not honestly reducible to either existing strategy alone.

Two demonstrations can support a strong computational-science paper if they
are framed as orthogonal tests of one evidence-native architecture:

- the current monochromatic `low/high NA x propagation/PB` matrix establishes
  breadth and numerical qualification;
- one genuine continuous-band compensation-phase case establishes that the
  same proof language extends without weakening evidence semantics.

They are not yet a paper result. A publication claim needs real broadband cell
responses, a separately held-out wavelength grid, an achromatic Result,
baselines and ablations, and measured runtime/reuse/provenance outcomes. The
current recorded journeys alone cannot establish optical accuracy, continuous
achromaticity, experimental validity, or superiority to MetaChat.

## 1. Primary-source lineage

### 1.1 Normative theory: Wang et al. 2017

Shuming Wang et al., "Broadband achromatic optical metasurface devices,"
*Nature Communications* 8, 187 (2017), DOI
[10.1038/s41467-017-00166-7](https://doi.org/10.1038/s41467-017-00166-7),
is the primary design-rule paper. The publisher's
[full article](https://www.nature.com/articles/s41467-017-00166-7)
derives the fixed-focus phase, splits it into a PB base phase and resonant
compensation phase, and demonstrates reflective devices from 1200 to 1680 nm.

For radius `r`, focal length `f`, and vacuum wavelength `lambda`, it requires

```text
DeltaL(r) = sqrt(r^2 + f^2) - f

phi_required(r, lambda)
  = -2 pi DeltaL(r) / lambda + phi_shift(lambda).
```

The paper chooses

```text
phi_shift(lambda) = alpha / lambda + beta,
```

so the offset remains linear in `1 / lambda`. It changes the attainable
compensation range and therefore the feasible aperture diameter, while its
spatial uniformity means that it does not change the focus. The paper's
[equations 1--4 and accompanying explanation](https://www.nature.com/articles/s41467-017-00166-7#Sec3)
are the source of this contract.

The integrated-resonant unit element (IRUE) is not just "a resonator." The
paper deliberately uses the smooth phase region between resonances. Its phase
compensation is approximated as

```text
delta(lambda)
  = S (1 / lambda - 1 / lambda_max),
```

and the slope `S` is tuned by moving the bounding resonances. One, two, or
three resonances are used as more compensation range is needed. The
[IRUE construction and slope equations](https://www.nature.com/articles/s41467-017-00166-7#Fig2)
also retain RCP-to-LCP conversion efficiency; phase without channel amplitude
is not the reported response. The paper used CST unit-cell simulations and a
cylindrical-lens simplification for the device simulation
([Methods](https://www.nature.com/articles/s41467-017-00166-7#Sec9)).

### 1.2 Visible transmissive realization: Wang et al. 2018

Shuming Wang et al., "A broadband achromatic metalens in the visible,"
*Nature Nanotechnology* 13, 227--232 (2018), DOI
[10.1038/s41565-017-0052-4](https://doi.org/10.1038/s41565-017-0052-4),
is the strongest paper-exact reference for the intended visible device. The
[author-hosted version of record](https://dsl.nju.edu.cn/litao/res/paper/Wang_SM-nnano_13_227%282018%29.pdf)
reports a transmissive GaN-on-sapphire device over 400--660 nm, with
`f = 235 um` and a selected `NA = 0.106` lens. Its solid and inverse GaN IRUE
identity supplies spectral compensation, while physical orientation supplies
the PB base phase.

The official
[supplementary information](https://media.springernature.com/original/springer-static/esm/art%3A10.1038%2Fs41565-017-0052-4/MediaObjects/41565_2017_52_MOESM1_ESM.pdf)
fixes a 120-nm hexagonal lattice, 800-nm GaN height, and a 17-member IRUE
library spanning reported compensation values in 30-degree intervals. It also
contains the exact solid/inverse geometry tables, although those tables are
image-rendered in the accessible PDF. They must be obtained from a reliable
machine-readable source or independently regenerated; they must not be
silently transcribed and called paper-exact.

The reported maximum focusing efficiency is up to 67% and the band average is
about 40%, but the paper defines efficiency for the focused opposite-helicity
beam relative to incident power. That definition is not interchangeable with
MetaCraft's current through-plane transmission or Airy-bucket concentration.

### 1.3 Later Tsai-group clarification and extension

Two later papers are useful, but they play different roles:

- Maoxiong Zhao et al., "Phase characterisation of metalenses," *Light:
  Science & Applications* 10, 52 (2021), DOI
  [10.1038/s41377-021-00492-y](https://doi.org/10.1038/s41377-021-00492-y),
  directly measures the phase distribution of PB and propagation-phase
  metalenses and derives focal length, PSF, MTF, Strehl ratio and depth from
  the measured pupil. Its
  [full article](https://www.nature.com/articles/s41377-021-00492-y)
  shows why aperture phase residual is a useful validation fact in addition
  to focal intensity.
- Jin Yao et al., "Integrated-Resonant Units for Phase Compensation and
  Efficiency Enhancements in Achromatic Meta-lenses," *ACS Photonics* 10,
  4273--4281 (2023), DOI
  [10.1021/acsphotonics.3c01073](https://doi.org/10.1021/acsphotonics.3c01073),
  extends the IRU programme with local/nonlocal plasmonic resonances and
  reports an effective group-delay range of 42.5 fs over 400--660 nm. It is a
  relevant follow-up, but its nonlocal coupled response requires a different
  qualification than today's isolated periodic-cell evidence. It should not
  be smuggled into the first achromatic route as if it were another local cell.

### 1.4 Adjacent group-delay formulation, not the Tsai paper

Wei Ting Chen et al., "A broadband achromatic metalens for focusing and
imaging in the visible," *Nature Nanotechnology* 13, 220--226 (2018), DOI
[10.1038/s41565-017-0034-6](https://doi.org/10.1038/s41565-017-0034-6),
is the adjacent Capasso-group paper. Its
[author-group record and paper](https://capasso.seas.harvard.edu/publications/broadband-achromatic-metalens-focusing-and-imaging-visible)
state the simultaneous phase, group-delay, and group-delay-dispersion design
language. It is a useful formal cross-check, but it is not the user's named
team and it uses a different TiO2 nanofin library.

Federico Presutti and Francesco Monticone, "Focusing on bandwidth:
achromatic metalens limits," *Optica* 7, 624--631 (2020), DOI
[10.1364/OPTICA.389404](https://doi.org/10.1364/OPTICA.389404), formalizes the
required phase as a frequency expansion and shows that fixed-focus operation
requires the reference phase, relative delay, and vanishing spatially varying
higher-order terms. It also supplies the delay-bandwidth feasibility warning:
large aperture, NA and bandwidth cannot be selected independently of the
available device delay.

## 2. Compensation phase, group delay, and dispersion are one contract

For an output medium with wavenumber `k_m(omega)`, the general fixed-focus
target is

```text
phi_required(r, omega)
  = -k_m(omega) DeltaL(r) + phi_0(omega).
```

`phi_0` is common to the whole aperture. It is a focusing gauge, not a local
degree of freedom for every cell. The spatially relative phase is

```text
phi_required(r, omega) - phi_required(0, omega)
  = -k_m(omega) DeltaL(r).
```

For nondispersive air, `k_m = omega / c`; therefore the required relative phase
is exactly linear in `omega`, and equivalently in `1 / lambda`. Its relative
phase slope is

```text
partial phi / partial omega = -DeltaL(r) / c,
```

and its spatially relative second and higher derivatives vanish. Depending on
the declared phasor time convention, optical group delay may be defined with
the same or opposite sign. MetaCraft must bind that convention before naming
the derivative `group delay`; the convention-free stored fact is the phase
slope.

In a dispersive output medium,

```text
partial phi / partial omega
  = -n_group(omega) DeltaL(r) / c + phi_0'(omega),
```

and higher derivatives need not vanish. Thus `air` cannot be silently
generalized to an arbitrary medium. Each wavelength-specific `Field` already
owns its medium; an achromatic target must use those exact medium samples.

Tsai's restricted `phi_shift = alpha / lambda + beta` is also linear in
frequency. It changes the common phase and common phase slope but introduces
no spatially varying group-delay dispersion. The scientific equivalence is:

```text
Tsai phase compensation linear in 1/lambda
  == constant relative phase slope across the band
  == required relative group-delay pattern for fixed f in air.
```

This equivalence does **not** permit three common shortcuts:

1. Endpoint agreement cannot establish an interior linear law unless the
   response has been qualified between endpoints.
2. Wrapped phase samples cannot be differentiated before one coherent branch
   is established across the band.
3. A separate global phase may be removed at each wavelength for focal-shape
   comparison, but a paper-exact Tsai design must retain its restricted
   `alpha / lambda + beta` gauge; arbitrary per-wavelength offsets would hide
   a dispersion error.

## 3. Minimum achromatic scientific facts

### 3.1 Brief and design facts

One achromatic brief must state, or honestly leave unresolved:

- vacuum wavelength band and units;
- one design grid and one independently held-out verification grid;
- focal length, aperture footprint, NA and output medium;
- reference wavelength or frequency and phase/time convention;
- incident polarization and evaluated output channels;
- whether the claim is continuous-band, discrete multiwavelength, or merely
  broadband-efficient;
- allowed spectral phase gauge;
- focal-flatness, phase-residual, efficiency, leakage, and spot-shape
  objectives with explicit aggregation (`worst`, `mean`, percentile);
- fabrication constraints and whether the case is paper-exact,
  paper-adapted, or MetaCraft-owned.

A wavelength list is not a band contract. Conversely, a band without a
sampling and interpolation policy is not executable.

### 3.2 Material and response evidence

The minimum reusable cell evidence is one exact complex spectral response, not
a list of independent phase scalars. For every candidate it must retain:

- exact geometry, height, lattice/supercell and material references;
- material `n,k` samples covering the whole band without extrapolation;
- solver realization, mesh/time convergence and response-plane convention;
- wavelength grid and the complete complex Jones response needed for the
  declared incident and output channels;
- transmission/conversion and leakage amplitudes, not phase alone;
- one qualified phase-unwrapping result and its failure modes;
- phase-slope and higher-order residual diagnostics derived from the
  unwrapped response;
- locality applicability: isolated periodic cell, coupled supercell, or
  nonlocal array evidence.

The full spectral sweep should be one atomic scientific observation for one
geometry and binding. Repeating the current single-wavelength request N times
and later guessing that the phases belong to one branch would destroy
locality and make interruption recovery scientifically ambiguous.

### 3.3 Target and assignment

For the Tsai route, cell identity and orientation are coupled outputs at every
occupied aperture site:

- IRUE identity supplies the required spectral compensation;
- orientation supplies the wavelength-independent PB base phase;
- the exact converted and retained channel responses determine usable power.

The most stable primary matching quantity is the complex channel response over
the complete design grid. A gauge-aware loss may compare

```text
t_candidate(i, omega_k) exp(i * PB(theta))
```

with the required complex phase at the site, while one aperture-wide spectral
offset is optimized under the selected gauge contract. Phase-slope and
higher-order errors remain independently reported diagnostics. This avoids
differentiating wrapped/noisy phases as the only optimizer input.

The assignment objective should also retain conversion/transmission, leakage,
fabrication loss and a deterministic tie-break. A mean-only spectral loss is
unsafe: it can hide a failed band edge. A bounded first realization should
report both worst-wavelength and weighted-mean residuals before introducing a
generic optimizer Module.

### 3.4 Field and Result evidence

ADR 0006 is already the correct base: one `Field` remains single-wavelength.
The achromatic proof composes one exact `Field` and one exact focal region per
verification wavelength. Its spectral conclusion must retain at least:

- found focal position and `f(lambda) - f_target`;
- x/y half-maximum widths and depth of focus;
- through-plane transmission and concentration with their existing separate
  meanings;
- converted and retained power where PB channels apply;
- pupil or aperture phase residual after the declared global gauge removal;
- all missing/failed wavelengths rather than averages that omit them;
- worst, mean and band-edge summaries over the complete verification grid.

A continuous-band conclusion additionally needs either a qualified response
interpolant with an error bound or a sufficiently dense independent spectral
survey. It cannot be inferred from the design wavelengths alone.

## 4. The MetaChat comparison

### 4.1 Exact identification

The most likely and now precise referent is Robert Lupoiu et al., "A
multi-agentic framework for real-time, autonomous freeform metasurface
design," *Science Advances* 11, eadx8006 (2025), DOI
[10.1126/sciadv.adx8006](https://doi.org/10.1126/sciadv.adx8006). The
[author-hosted paper](https://robertlupoiu.com/publications/pdfs/lupoiu2025metachat.pdf)
and [official Jon Fan Lab repository](https://github.com/jonfanlab/metachat)
both call the system **MetaChat**. No other photonics project found under that
exact name is a comparably plausible referent.

MetaChat combines an Agentic Iterative Monologue design agent, a materials
agent, tool calls, a FiLM-conditioned WaveY-Net surrogate, gradient-based
freeform optimization, and near-to-far evaluation. The paper demonstrates a
dual-wavelength metalens and an RGB multiobjective metalens. These are
multiwavelength spatial-function demonstrations; they are not a Tsai-style
continuous-band fixed-focus phase-compensation proof.

The reported dual-wavelength example uses 100 aperiodic superpixels and
300,000 surrogate simulations on eight GPUs, completing the design process in
about 11 minutes. The surrogate is trained from Ceviche FDFD data over
400--700 nm; the paper reports held-out normalized field MAE varying from
0.098 to 0.043 over the band. MetaChat also evaluates agent reasoning on 101
problems in five categories using pass@3 and a GPT-4o grader. These are the
correct primary-source comparators, not a generic claim that "an LLM designed
a lens."

### 4.2 Evidence-based comparison

| Question | MetaChat paper | Current / proposed MetaCraft |
| --- | --- | --- |
| Primary contribution | agentic interaction plus an ultrafast differentiable Maxwell surrogate and freeform optimization | evidence-native scientific compilation, immutable Authority, qualified realizations, and resumable proof closure |
| Demonstrated optical domain | two-dimensional freeform dielectric superpixels; discrete multiobjective/multiwavelength lenses and deflectors | current recorded monochromatic propagation/PB and low/high-NA matrix; proposed continuous-band compensation proof |
| Scientific Interface | prompt-driven AIM agents call task-specific design functions | `conduct` remains the sole harness-facing Interface; route and binding select methods |
| Numerical acceleration | trained FiLM WaveY-Net, GPU batching and differentiable optimization | no surrogate claim; qualified component/electromagnetic propagation plus joint FFT/CZT reference formation |
| Evidence identity | paper benchmark, held-out surrogate set, code/data release and example outputs | content-addressed observations, exact references, claim/method proof, admitted evidence, terminal Result replay |
| Agent evaluation | 101-question benchmark, several model/agent variants, pass@3 LLM grading | no comparable published agent benchmark today; agent callability is an application fact, not a model-brand proof |
| Achromaticity | discrete wavelengths and different requested focal offsets/functions | proposed one physical layout with a continuous-band fixed focal objective and compensation-phase evidence |

The strongest defensible contrast is therefore **surrogate-accelerated agentic
design versus evidence-governed agentic scientific closure**. The systems
optimize different things. MetaCraft may reasonably claim stricter provenance,
typed failure and resumability after those properties are empirically
demonstrated. It may not claim to be faster, more autonomous, more accurate or
"better than MetaChat" without a common task, hardware, metric and independent
reference.

An informative head-to-head experiment would give both systems the same
fully specified discrete two-wavelength lens request and separately give
MetaCraft the continuous-band Tsai request that MetaChat's published metalens
function does not express. Report human interventions, wall time, solver calls,
failed/reused work, final full-wave error and provenance completeness. Do not
rank the systems by one incomparable scalar.

## 5. Proposed research programme

### Stage A -- decision and feasibility, no production code

1. Decide whether the first case is paper-exact Wang 2018 or a clearly named
   method-inspired local-cell case. The latter is substantially smaller.
2. Fix the band, medium, polarization, phase gauge, design/holdout grids and
   metric definitions.
3. Apply the delay-bandwidth feasibility screen before opening solver work.
4. Decide whether composite PB plus resonant compensation is represented as a
   new method over existing mechanisms or as a redesigned plural control
   language. Do not add one misleading enum value by default.

### Stage B -- spectral response qualification

1. Bind band-covered materials.
2. Create one bounded spectral cell study with atomic complex-response
   observations.
3. Qualify channel convention, phase unwrapping, interpolation/holdout error
   and phase-slope residuals.
4. Establish a chromatic baseline library and a compensation-capable library
   under the same binding.

### Stage C -- compensated aperture and spectral field family

1. Form the ideal target including the declared global gauge.
2. Jointly assign one cell identity and orientation per site.
3. Materialize one physical aperture identity and exact wavelength-specific
   response references.
4. Form and propagate one existing component `Field` per verification
   wavelength. Batch wavelength internally where valid, but retain separate
   evidence.

### Stage D -- conclusion and publication evidence

1. Compare compensation against a no-compensation chromatic baseline and a
   discrete phase-only baseline.
2. Report focal shift, shape, phase residual, efficiency/leakage and failures
   at every verification wavelength.
3. Ablate the spectral gauge, response qualification and holdout grid; show
   which unsupported conclusions the proof compiler refuses.
4. Measure wall time, solver work, interruption/reuse and Authority replay.
5. Independently validate selected cells and the final aperture using Native
   full-wave evidence or a second qualified realization.

## Architecture consequences

1. **Keep the external seam.** `conduct` remains the sole harness-facing
   Interface. Achromaticity enters through new claims, methods, realizations,
   bindings and evidence, not a parallel workflow.
2. **Keep `Field` single-wavelength.** Add a small manifest-like spectral
   family that retains exact `Field`, focal-region and wavelength references;
   do not add a wavelength dimension to every current field operation.
3. **Deepen response qualification.** One spectral-response Module should own
   complex-channel restoration, phase unwrapping, interpolation, phase slope,
   holdout validation and provenance. Its Interface should return qualified
   response facts or typed refusal, not expose each numerical step.
4. **Do not repeat single-wavelength work N times.** A spectral cell sweep is
   one atomic observation for one geometry and binding. Internal solver
   batching is an implementation detail.
5. **Resolve composite control honestly.** PB orientation and IRUE dispersion
   are simultaneously necessary. The current singular control-strategy value
   must not force the achromatic method to pretend that one mechanism owns the
   whole design.
6. **Make the gauge explicit.** A global spectral phase is legal, but its
   allowed function and pulse consequences belong to the method's Interface.
   Per-cell or silently independent per-wavelength offsets are invalid.
7. **Keep optimization as a realization.** Start with deterministic bounded
   assignment and explicit loss/tie-break. Add a qualified optimizer only when
   a concrete proof need requires it; do not create a public optimization
   workflow layer.
8. **Separate local and nonlocal evidence.** Wang 2018 method-inspired local
   cells can be a first slice. The 2023 nonlocal IRU extension requires a real
   supercell/array seam and its own qualification.
9. **Preserve current numerical decisions.** Each wavelength-specific plane
   `Field` still uses its applicable component or electromagnetic propagation;
   an independently authored aplanatic reference still meets it only in
   comparison under ADR 0026. Achromatic synthesis does not merge these
   physical methods.

## Publishability verdict

### Claims that can become defensible with the proposed work

- one evidence-native agentic architecture supports both a mature
  monochromatic matrix and a physically different continuous-band proof
  without adding a second lifecycle;
- the achromatic extension composes exact single-wavelength `Field` facts and
  preserves method, solver, material and response provenance;
- a compensation-phase method reproduces the required relative phase-slope
  law and reduces spectral focal shift against declared baselines;
- interruption and replay reuse already admitted spectral evidence without
  duplicating solver work;
- numerical realizations agree within separately qualified tolerances.

Those claims could support a strong computational photonics / scientific
software paper. The optical novelty would be the trustworthy, resumable,
evidence-governed design method, not the rediscovery of Tsai's 2017 phase law.

### Claims that are not currently defensible

- exact reproduction of Wang 2018;
- continuous achromatic performance from two or three design wavelengths;
- experimental validation, fabrication tolerance or imaging performance;
- state-of-the-art efficiency, bandwidth, NA or aperture size;
- faster, more accurate, more autonomous, or categorically better performance
  than MetaChat;
- Native solver closure from recorded-response journeys alone.

### What is required for a paper comparable in ambition to MetaChat

Two deep cases are enough in count, but not enough in evidence. At minimum the
paper needs:

1. real band-covered cell response data and one completed achromatic Result;
2. independent spectral holdout and full-wave validation;
3. chromatic, phase-only and compensation-phase baselines;
4. architecture ablations showing why typed proof/evidence changes outcomes;
5. measured wall time, solver count, interruption/reuse and human-intervention
   data;
6. a common-task comparison if MetaChat is named as a performance comparator;
7. public briefs, response/result manifests and replay instructions.

Physical fabrication is not mandatory for a computational-methods paper if
all claims are explicitly simulation-only and independently validated. It is
mandatory for claims about experimental achromatic imaging, fabrication yield
or device efficiency. A higher-impact optics claim would benefit strongly from
fabrication or a laboratory collaborator.

The recommended paper story is therefore not "we wrote two examples." It is:

```text
one immutable scientific proof language
  -> closes four orthogonal monochromatic journeys
  -> extends to a composite, continuous-band compensation method
  -> preserves exact evidence, resumability, numerical qualification,
     and honest failure across both.
```

That is differentiated from MetaChat and potentially publishable. It becomes
convincing only when the achromatic branch produces real spectral evidence
rather than architecture placeholders.

## Primary sources

1. Wang et al. 2017, DOI
   [10.1038/s41467-017-00166-7](https://doi.org/10.1038/s41467-017-00166-7).
2. Wang et al. 2018, DOI
   [10.1038/s41565-017-0052-4](https://doi.org/10.1038/s41565-017-0052-4),
   [author-hosted paper](https://dsl.nju.edu.cn/litao/res/paper/Wang_SM-nnano_13_227%282018%29.pdf),
   [official supplement](https://media.springernature.com/original/springer-static/esm/art%3A10.1038%2Fs41565-017-0052-4/MediaObjects/41565_2017_52_MOESM1_ESM.pdf).
3. Zhao et al. 2021, DOI
   [10.1038/s41377-021-00492-y](https://doi.org/10.1038/s41377-021-00492-y).
4. Yao et al. 2023, DOI
   [10.1021/acsphotonics.3c01073](https://doi.org/10.1021/acsphotonics.3c01073).
5. Chen et al. 2018, DOI
   [10.1038/s41565-017-0034-6](https://doi.org/10.1038/s41565-017-0034-6).
6. Presutti and Monticone 2020, DOI
   [10.1364/OPTICA.389404](https://doi.org/10.1364/OPTICA.389404).
7. Lupoiu et al. 2025, DOI
   [10.1126/sciadv.adx8006](https://doi.org/10.1126/sciadv.adx8006),
   [author-hosted paper](https://robertlupoiu.com/publications/pdfs/lupoiu2025metachat.pdf),
   [official code](https://github.com/jonfanlab/metachat), and
   [archived code/data](https://doi.org/10.5281/zenodo.15802727).

