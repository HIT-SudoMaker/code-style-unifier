---
title: Local TiO2/glass feasibility for a Chen-2018 continuous-achromatic first slice
date: 2026-08-14
status: research record
scope: paper requirements, repository evidence, and a no-solve experiment envelope
primary_paper_doi: https://doi.org/10.1038/s41565-017-0034-6
---

# Local TiO2/glass achromatic feasibility

## Decision

MetaCraft has enough local structure to **ask** the right first feasibility
question, but it does not yet have evidence to answer it. A square-lattice,
single-rectangle, local TiO2-on-glass slice is scientifically legitimate because
Chen et al.'s library itself included single nanofins. It is an adaptation and a
deliberately restricted subfamily, not a reproduction: the published successful
library also contained pairs of coupled fins and arrangement/gap degrees of
freedom. The single-rectangle outcome is therefore **unknown** until native
spectral Jones observations close the joint phase, group-delay, residual, and
power requirements.

The useful first experiment is not a full metalens solve. It is a bounded native
periodic campaign over the paper's **design band**, followed by an independently
sampled holdout check and an algebraic capacity test. Only after that evidence
exists may MetaCraft return either a positive candidate or a typed refusal of the
single-rectangle realization. A missing spectrum is `unknown`, never a physical
refusal.

This conclusion is based on Chen et al.'s published article and Methods
([DOI record](https://doi.org/10.1038/s41565-017-0034-6),
[author-hosted published PDF](https://capasso.seas.harvard.edu/sites/g/files/omnuum6306/files/capasso/files/s41565-017-0034-6.pdf),
[Harvard DASH author record](https://dash.harvard.edu/entities/publication/73120379-336e-6bd4-e053-0100007fdf3b))
and the repository sources and retained records cited below. No native solve was
run for this audit.

## The paper-owned contract

Chen et al. require the relative phase of a fixed-focus metalens to follow

\[
\phi(r,\omega)=-\frac{\omega}{c}
\left(\sqrt{r^2+F^2}-F\right).
\]

Expanding around a declared design frequency \(\omega_d\) separates the
reference-frequency phase, group delay (GD), group-delay dispersion (GDD), and
higher-order residual. For an ideal achromat with frequency-independent \(F\),
the relative phase is linear in \(\omega\): the required relative GD is
\(-[\sqrt{r^2+F^2}-F]/c\), while relative GDD and all higher derivatives are
zero. This is the paper's physical requirement, not a regression convenience
([Chen et al., equations 1--3 and discussion](https://capasso.seas.harvard.edu/sites/g/files/omnuum6306/files/capasso/files/s41565-017-0034-6.pdf)).

For a left-circular input, the paper writes the transmitted field of a rotated
anisotropic fin as the sum of retained- and converted-handedness terms. The
converted term is proportional to
\((\tilde t_L-\tilde t_S)e^{i2\alpha}\). Consequently, geometry determines the
complex spectral factor and its GD/GDD, whereas rotation adds a
frequency-independent PB phase \(2\alpha\). Rotation can close the phase
intercept at \(\omega_d\); it cannot manufacture a missing phase slope or hide
spectral curvature
([Chen et al., equation 4 and Fig. 2c](https://capasso.seas.harvard.edu/sites/g/files/omnuum6306/files/capasso/files/s41565-017-0034-6.pdf)).

### Requirement inventory

| Paper-owned fact | Chen et al. 2018 | What it means for a local adaptation |
|---|---|---|
| Optical mode | Transmission through one metasurface layer; no spatial multiplexing or cascade | One immutable patterned layer and one substrate must be used at every wavelength, not one layout per wavelength. [Nature article abstract](https://www.nature.com/articles/s41565-017-0034-6) |
| Material/stack | TiO2 nanofins on a transparent substrate; the response is normalized to a substrate-only simulation. The cited Capasso-group ALD platform fabricates amorphous TiO2 structures on fused silica | Local `Siefke` TiO2 and `Palik` glass are a plausible adaptation pair, but material-family similarity is not equality of film dispersion. [Chen Methods](https://capasso.seas.harvard.edu/sites/g/files/omnuum6306/files/capasso/files/s41565-017-0034-6.pdf); [the cited TiO2 platform, DOI 10.1073/pnas.1611740113](https://doi.org/10.1073/pnas.1611740113) |
| Cell/lattice | A `400 x 400 nm` square element, spacing `p = 400 nm`, and common fin height `h = 600 nm` | `p=400 nm` and `h=600 nm` are paper seeds only. Local material dispersion, diffraction-order regime, and fabrication bounds must requalify them. [Chen Fig. 2a caption](https://capasso.seas.harvard.edu/sites/g/files/omnuum6306/files/capasso/files/s41565-017-0034-6.pdf) |
| Geometry degrees of freedom | One or two fins with varied lengths, widths, and arrangements; paired fins use `g = 60 nm` and a common rotation | One rectangle covers only the single-fin subset. Two fins, a controlled gap, and their relative placement are absent from the current primitive. [Chen Fig. 2a and Methods](https://capasso.seas.harvard.edu/sites/g/files/omnuum6306/files/capasso/files/s41565-017-0034-6.pdf) |
| Polarization channel | Circularly polarized illumination; phase and conversion are read in the cross-polarized circular component | Local x/y complex Jones observations are sufficient only if coherently paired and projected into converted and retained circular channels under one declared convention. [Chen equation 4 and Methods](https://capasso.seas.harvard.edu/sites/g/files/omnuum6306/files/capasso/files/s41565-017-0034-6.pdf) |
| Reference wavelength | `lambda_d = 530 nm` | It owns the phase intercept and Taylor expansion for this benchmark. It is not a default for every future user band. [Chen Methods](https://capasso.seas.harvard.edu/sites/g/files/omnuum6306/files/capasso/files/s41565-017-0034-6.pdf) |
| Design band | `120 nm` centered at `530 nm`, hence `470--590 nm` | Fit/selection evidence must cover this entire interval coherently. Two endpoints or the 532-nm local receipt cannot prove it. [Chen Fig. 2e and Methods](https://capasso.seas.harvard.edu/sites/g/files/omnuum6306/files/capasso/files/s41565-017-0034-6.pdf) |
| Demonstrated band | Simulated and measured focal behavior was reported from `470--670 nm`, extending beyond the fitted design band | `590--670 nm` is validation/extrapolative performance, not part of the paper's 120-nm fitting interval. MetaCraft must name design and validation bands separately. [Chen main results and article abstract](https://www.nature.com/articles/s41565-017-0034-6) |
| Phase/GD qualification | Unwrapped phase spectrum is linearly fit versus angular frequency over the design band; its slope is GD | A complex spectral response and one coherent phase branch are mandatory. Pointwise wrapped phases cannot supply GD. [Chen Fig. 2e and Methods](https://capasso.seas.harvard.edu/sites/g/files/omnuum6306/files/capasso/files/s41565-017-0034-6.pdf) |
| GDD/higher-order qualification | The achromatic library is selected for nearly zero GDD; high linear-fit quality is the paper's proxy. The paper uses a quadratic fit and explicit GDD for its separate `n=2` dispersive lens | For the `n=0` first slice, GDD is a residual/error term, not an extra requested focal law. Preserve residual spectra; do not report only a fitted slope. [Chen discussion around Figs. 1c and 2e, and Methods](https://capasso.seas.harvard.edu/sites/g/files/omnuum6306/files/capasso/files/s41565-017-0034-6.pdf) |
| Library gates | Elements below `R^2 = 0.99` linearity or `5%` polarization conversion were dropped | These are paper gates, not evidence that the local library passes. The paper text does not define a reusable across-band aggregation rule for the 5% gate, so a MetaCraft adaptation must declare its rule explicitly. [Chen Methods](https://capasso.seas.harvard.edu/sites/g/files/omnuum6306/files/capasso/files/s41565-017-0034-6.pdf) |
| Device-scale result | The demonstrated achromat had `NA=0.2`; its initial focusing efficiency was about `20%` at `500 nm`. Efficiency was focal-spot power divided by incident circularly polarized power through an equal-diameter aperture | Cell conversion and whole-lens focusing efficiency are different measures and must not substitute for one another. [Nature article abstract](https://www.nature.com/articles/s41565-017-0034-6); [Chen measurement Methods](https://capasso.seas.harvard.edu/sites/g/files/omnuum6306/files/capasso/files/s41565-017-0034-6.pdf) |
| Model limitations | Library elements used transverse periodic boundaries; full-lens phase propagation neglected actual coupling between unlike neighboring elements, and a smaller full-wave lens was simulated separately | Passing a periodic-cell library is necessary but not sufficient evidence for an aperiodic lens. [Chen Methods and achromatic-focusing section](https://capasso.seas.harvard.edu/sites/g/files/omnuum6306/files/capasso/files/s41565-017-0034-6.pdf) |

The paper reports that its implemented library supplied about `5 fs` of GD
range. That is an observed capability of its own compound library and material
model, not a lower bound for the local single-rectangle/Siefke library
([Chen Fig. 2 discussion](https://capasso.seas.harvard.edu/sites/g/files/omnuum6306/files/capasso/files/s41565-017-0034-6.pdf)).

## Repository fact map

### Materials: names exist; continuous-band evidence does not

The reviewed Lumerical registry contains the exact local names
`TiO2 (Titanium Dioxide) - Siefke` for `amorphous titanium dioxide` and
`SiO2 (Glass) - Palik` for `glass`
([`materials/lumerical.toml`](../../materials/lumerical.toml#L13),
[`materials/lumerical.toml`](../../materials/lumerical.toml#L33)). This is enough
to resolve native names. It does not prove equivalence to Chen's fabricated film
or any band response.

A retained Lumerical observation does exist for this exact pair at `532 nm`.
It reports

- TiO2: `n = 2.449972396051889`,
  `k = 0.00000012524968996802398`;
- glass: `n = 1.4607226165310925`, `k = 0`.

The receipt is replay-protected by the acceptance contract
([retained-receipt test](../../tests/acceptance/test_retained_material_receipt.py#L45))
and its exported product sample explicitly says `grid_wavelengths_nm: [532]`
with equal minimum and maximum fit frequencies
([retained product sample](../../.scratch/four-brief-baseline/acceptance/03/receipts/slot-04/reviewed-material-product-sample.json#L1)).
Therefore it proves one native material sample, not `470--590 nm` dispersion,
not `470--670 nm` coverage, and not a spectral Jones response. The broad
`tabulated_band` metadata in that product sample says where the native model
has data; it is not a set of observed in-band `n,k` values and is not a pass for
the device library.

The portable-material module can retain immutable source bytes, compute a
closed covered band, linearly interpolate, and reject extrapolation
([`MaterialRecord`](../../src/metacraft/materials/portable.py#L127),
[`sample`](../../src/metacraft/materials/portable.py#L167)). It accepts local
tables and refractiveindex.info datasets
([portable parsers](../../src/metacraft/materials/portable.py#L283)). A read-only
inventory found no MetaCraft-owned, admitted portable TiO2 or glass record in
the repository. The TiO2 CSV under `reference/teamate's code` is neither a
tracked MetaCraft material asset nor an Authority-admitted `MaterialRecord`, has
no paired glass record, and must not be promoted to evidence by proximity.

The native material request is itself one-wavelength-at-a-time
([`MaterialObservationRequest`](../../src/metacraft/materials/verification.py#L40)).
The least architectural change is therefore either a coherent spectral request
or a set of point requests whose complete expected wavelength set is sealed and
whose material identity is unchanged. In both cases, Native observations are
needed at every design and holdout wavelength before band claims are possible.

### Periodic template: close in shape, monochromatic in evidence

The existing template already supplies important matching invariants:

- equal solver `span_x_nm` and `span_y_nm` from one period, hence a square
  cell, with transverse periodic boundaries
  ([template construction](../../src/metacraft/solvers/lumerical_fdtd/template/periodic.py#L521));
- a primitive unrotated rectangular fin with independent long and short sides
  ([native rectangle](../../src/metacraft/solvers/lumerical_fdtd/template/periodic.py#L651));
- independent x- and y-linear input work whose complex Cartesian outputs are
  paired and projected to converted/retained circular channels
  ([`JonesEvidenceBatch`](../../src/metacraft/science/metalens/periodic_cell_evidence.py#L214),
  [circular projection](../../src/metacraft/science/metalens/periodic_cell_evidence.py#L636));
- an explicit local PB power qualification seam and a complete linear Jones
  value
  ([`PbCellQualification`](../../src/metacraft/science/metalens/geometric_phase.py#L32),
  [`JonesResponse`](../../src/metacraft/science/metalens/geometric_phase.py#L205));
- an analytic orientation relation downstream of the unrotated cell response
  ([`OrientationRelation`](../../src/metacraft/science/metalens/geometric_phase.py#L887)).

The same sources expose the blockers:

- `CellStudyPlan` owns one bounded geometry/basis work set but no spectral
  design grid or holdout grid
  ([`CellStudyPlan`](../../src/metacraft/science/metalens/cell_study.py#L654));
- `PeriodicWork` owns exactly one integer `wavelength_nm`, and wavelength is
  part of the batch context, so one request cannot contain multiple wavelengths
  ([`PeriodicWork`](../../src/metacraft/science/periodic_response.py#L651),
  [`_batch_context`](../../src/metacraft/science/periodic_response.py#L746));
- the projector requires the material binding and design wavelength to match
  and always writes `design.wavelength_nm`
  ([periodic request projection](../../src/metacraft/science/metalens/periodic_request.py#L399));
- the native source has equal start/stop wavelengths
  ([template source](../../src/metacraft/solvers/lumerical_fdtd/template/periodic.py#L571));
- the only compound geometry types are not two-fin supercells: the current PB
  route accepts one rectangle or one ellipse
  ([`CellResponseWork`](../../src/metacraft/science/metalens/cell_study.py#L123),
  [`RectangularCrossSection`](../../src/metacraft/science/periodic_response.py#L498));
- the present Jones library stores single-frequency converted/retained phase
  and power but no wavelength-indexed complex family, phase unwrap, GD, GDD,
  fit residual, or design/holdout result
  ([`JonesCell`](../../src/metacraft/science/metalens/geometric_phase.py#L296)).

The present zero-order target also deserves explicit attention. `p=400 nm` is
the paper's geometry, but local glass dispersion determines whether additional
substrate orders propagate near the blue band edge. The current template asks
for transmission order zero
([grating-response request](../../src/metacraft/solvers/lumerical_fdtd/template/periodic.py#L555)).
No decision about the local order regime is legal from the 532-nm sample alone.
The experiment must either select a period proven to remain in the intended
order regime or retain and qualify every relevant order rather than silently
discarding it.

## Requirement-to-evidence matrix

| Requirement | Already available | Still required | Current status |
|---|---|---|---|
| Resolve local TiO2/glass native names | Reviewed `Siefke`/`Palik` registrations | None for naming | **available** |
| Local `n,k` at 532 nm | Retained native TiO2/glass receipt | None for that exact point | **available at one point** |
| Local material band | Native models expose table-domain metadata | Coherent observations over every design/holdout wavelength, with no extrapolation and one stable material identity | **unknown** |
| Square cell | Equal x/y period and periodic boundaries | Band-aware order-regime qualification | **structure available; physics unknown** |
| `h=600 nm` | Template supports an arbitrary positive height; prior local work can name 600 nm | A local height choice and spectral response at that height | **constructible, not passed** |
| One fin | Primitive rectangle with two size degrees of freedom | Spectral response family | **constructible, not passed** |
| Two coupled fins | No compound primitive | New geometry only if single-fin evidence fails | **unavailable** |
| Circular converted channel | Complete x/y Jones pairing and circular projection | Coherent spectral pairing and convention continuity | **single-frequency path available** |
| Reference phase at 530 nm | Analytic PB orientation relation | Spectral geometry selected first; orientation must be bound once and reused | **algebra available; spectral selection unknown** |
| GD | No spectral phase evidence | Complex spectrum, unwrap convention, linear slope vs `omega`, source/reference-plane continuity | **unknown** |
| GDD/higher residual | No spectral residual evidence | Quadratic diagnostic and full residual on design plus holdout wavelengths | **unknown** |
| `R^2` and conversion gates | User-owned single-point PB power thresholds exist | Explicit band aggregation, `R^2`, worst-wavelength converted/retained/total power | **unknown** |
| Same device across wavelengths | Current monochromatic aperture can bind one cell/orientation | One immutable site layout evaluated without per-wavelength reselection | **not represented spectrally** |
| Full-lens efficiency/focal stability | Monochromatic field/focus path exists | Per-wavelength fields and focal surveys using the same layout, with omissions retained | **unknown** |

## Minimal no-claim experiment envelope

The first native campaign should be small enough to fail cheaply and complete
enough that failure has scientific meaning.

### Fixed realization candidates

1. Bind the existing local native pair: amorphous TiO2 `Siefke` on glass
   `Palik`. Call it a **local adaptation**, not Chen's material.
2. Start with one square period and one `600 nm` height. Admit `p=400 nm` only
   as the paper-seeded candidate; include at least one locally order-qualified
   smaller-period alternative if fabrication bounds permit. Do not infer the
   order regime before observing the material band.
3. Scan only the existing single unrotated rectangle, with short/long sides
   taken from an explicitly admitted fabrication grid. Do not add a two-fin
   primitive in this slice.
4. Observe the complete x/y complex Jones matrix and substrate-only reference
   at each wavelength. Derive circular converted and retained channels from
   those same receipts.

### Spectral sampling

Use `470, 500, 530, 560, 590 nm` as a minimal design grid and
`485, 515, 545, 575 nm` as an interleaved holdout grid. Fit phase versus angular
frequency, not wavelength. This grid is an economical MetaCraft proof policy,
not a sampling rule claimed by Chen et al. It covers their declared 120-nm
design interval and exposes interpolation error. Only after this closes should
an extension grid over `600--670 nm` test the paper's wider demonstrated band.

For every geometry retain:

- raw complex x/y Jones coefficients and reference planes at every wavelength;
- converted, retained, and total transmitted power;
- one deterministic phase unwrap with branch provenance;
- phase at `530 nm`, GD, GDD diagnostic, `R^2`, maximum design residual,
  maximum holdout residual, and worst-wavelength power;
- warnings, diffraction-order content, solver/material identity, and all
  missing wavelengths.

The paper gates (`R^2 >= 0.99` and conversion not below `5%`) may be reported as
a benchmark qualification. A local product claim should use a separately named,
explicit acceptance policy, preferably worst-wavelength converted power plus
retained/total-power limits. The paper's `20%` device efficiency is neither of
those cell gates.

### Capacity check before aperture assignment

For aperture radius `R` and focal length `F`, require the exact relative delay
span

\[
\Delta\tau_{required}=
\frac{\sqrt{R^2+F^2}-F}{c}.
\]

After spectral qualification, compute `Delta tau_library` from the extreme
qualified slopes. If `Delta tau_library < Delta tau_required`, return
`single_rectangle_delay_span_insufficient`. If the scalar range passes but no
fixed geometry plus analytic orientation jointly closes phase, GD, residual,
and power at all lens radii, return
`single_rectangle_joint_spectral_coverage_insufficient`. Do not select geometry
independently at each wavelength.

## Positive and nearby refusal candidates

These are pre-registered **test candidates**, not predicted outcomes:

| Candidate | Fixed facts | Exact required relative GD span | Prior status |
|---|---|---:|---|
| Positive candidate `P` | One 20-um-diameter lens (`R=10 um`), `F=49 um`, `NA=0.19996`, design band `470--590 nm`, same local stack/library/layout | `3.369 fs` | **unknown**. It is close to the paper's `NA=0.2` demonstration but uses a restricted local library and different material record. |
| Nearby refusal candidate `N` | Change only diameter to `25 um` (`R=12.5 um`), keep `F=49 um`, giving `NA=0.24719` | `5.234 fs` | **unknown**. It is a stress candidate, not a refusal until local evidence proves insufficient capacity or joint coverage. |

The numbers follow the exact formula above with
`c = 0.299792458 um/fs`. The paper's reported approximately `5 fs` library
range must not be used to label `P` passed or `N` refused: it belonged to a
one-or-two-fin published library. If both local candidates pass, increase only
`R` by a preregistered bisection until the first evidence-backed refusal; if
both fail, decrease only `R` to find whether any nontrivial positive closure
exists.

### Typed outcomes

Return one of these outcomes without ambiguity:

- `positive_single_rectangle_candidate`: complete material, spectral Jones,
  design/holdout, capacity, fixed-layout, and focal evidence all pass the
  declared local policy;
- `single_rectangle_delay_span_insufficient`: qualified slope span is too
  small for the exact aperture requirement;
- `single_rectangle_joint_spectral_coverage_insufficient`: enough scalar GD
  range exists but no cells jointly satisfy phase/GD/residual/power;
- `single_rectangle_spectral_linearity_insufficient`: design or holdout
  residual fails the declared policy;
- `single_rectangle_conversion_insufficient`: converted/retained/total power
  fails the declared policy;
- `period_order_regime_unqualified`: the period/order accounting cannot support
  the intended transmitted channel;
- `local_periodic_approximation_unqualified`: rotated-cell or neighboring-cell
  validation invalidates the local-library model;
- `spectral_evidence_incomplete`: any material wavelength, x/y pair, reference
  surface, or holdout receipt is absent.

Only the first six evidence-backed failures can refuse a realization. The last
outcome is incomplete work. A single-rectangle refusal does not refute Chen's
method; it is the evidence trigger for a new, separately reviewed two-fin
geometry ticket.

## Final recommendation

Proceed with the single-rectangle periodic campaign as the first slice, but
gate it in this order:

1. native TiO2/glass material observations over the sealed design and holdout
   grids;
2. order-regime decision for the candidate square periods;
3. spectral x/y Jones observations for the bounded single-fin grid;
4. phase unwrap, GD/GDD/residual, and power qualification;
5. exact capacity and joint-coverage tests for `P` and `N`;
6. one immutable aperture assignment and held-out wavelength focal evaluation.

Do not implement two coupled fins, do not claim `470--670 nm`, and do not run a
full-lens native solve before steps 1--5 close. The current repository is close
to the required experimental harness, but its retained evidence is still
monochromatic. The correct present scientific verdict is therefore:

> **Local TiO2/glass, square-cell, single-rectangle continuous-achromatic
> feasibility: unknown but cheaply testable.**

