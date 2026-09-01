---
record_type: research_record
date: 2026-08-14
status: research_finding
authority_level: none
current_capability: false
---

# Continuous-achromatic metalens: intent-to-proof traceability

## Research question

For a Chen et al. 2018-inspired transmissive continuous-achromatic metalens,
what exact chain connects user intent to physical necessities, Method
applicability or typed refusal, bounded solver work, admitted evidence, one
fixed physical aperture, and a spectral conclusion? Can MetaCraft begin with
its existing square-period, single-rectangle Lumerical template, and precisely
when must that first slice refuse rather than silently enlarge the template or
weaken the request?

This record uses the original Chen article, its official publisher record and
supplement, the original works used to cross-check phase/dispersion control,
and the current repository source. It records design facts only; it changes no
production capability.

## Decision

Yes: the current square-lattice, single-rectangle, transmissive Jones template
is a scientifically legitimate **first feasibility slice**, provided it is
compiled as a proof with typed failure, not advertised in advance as an
achromatic solution.

The slice is applicable only when all of these claims can be established:

1. the user asks for one fixed physical transmissive device over a continuous
   band and accepts the circular-input/opposite-helicity PB channel;
2. one local material binding covers the entire band without extrapolation;
3. one fixed square period and height are valid over the entire band;
4. the primitive rectangular-fin library supplies enough qualified relative
   phase-slope range for the requested radius, NA and focal length;
5. after one legal aperture-wide spectral gauge, the same library jointly
   covers reference phase and slope at every site;
6. its complex converted response stays continuous, efficient enough and close
   enough to the required spectral law on both design and held-out wavelengths;
7. one immutable `(geometry, orientation)` pair is assigned to each site and
   reused at every wavelength;
8. independently propagated held-out fields satisfy the declared fixed-focus
   criteria.

If a complete primitive-cell survey fails items 4--6, the proper result is a
typed refusal such as `single_rectangle_spectral_coverage_insufficient`. It is
not permission to add a second fin, narrow the band, lower NA, shrink the
aperture or switch polarization without a new user decision or a separately
applicable Method. Chen's published library used one **or two** TiO2 nanofins;
the paper's success is therefore evidence for the physical method, not evidence
that one primitive rectangle must suffice
([Chen et al. 2018, Fig. 2 and Methods](https://capasso.seas.harvard.edu/sites/g/files/omnuum6306/files/capasso/files/s41565-017-0034-6.pdf)).

## 1. The physical necessity chain

### 1.1 User objective to target phase

For a nondispersive output medium, a radius `r`, fixed focal length `F`, and
angular frequency `omega` require the relative phase

```text
DeltaL(r) = sqrt(r^2 + F^2) - F

phi_required(r, omega)
  = -omega * DeltaL(r) / c + C(omega).
```

`C(omega)` is common to the whole aperture, so it changes no transverse phase
gradient and no focal position. Chen writes the center-referenced case with
`C(omega)=0`; Shrestha et al. make the same aperture-wide spectral freedom
explicit and show that choosing it to fit the available library changes
feasibility without changing focusing
([Chen et al. 2018, Eqs. 1--2](https://capasso.seas.harvard.edu/sites/g/files/omnuum6306/files/capasso/files/s41565-017-0034-6.pdf),
[Shrestha et al. 2018, Eqs. 1--3](https://www.nature.com/articles/s41377-018-0078-x)).

The important consequence is that "fixed focus across a band" is not a list
of unrelated monochromatic target phases. It is one spectral law whose
spatially relative phase is linear in `omega` for air:

```text
phase intercept at omega_ref:
  phi_0(r) = phi_required(r, omega_ref)

relative phase slope:
  d phi_required / d omega = -DeltaL(r) / c + C'(omega)

spatially varying higher derivatives:
  d^m phi_required / d omega^m = 0,  m >= 2
```

The sign called "group delay" depends on the declared phasor/time convention.
MetaCraft should therefore preserve the signed phase slope together with that
convention and only derive a named group delay from it. The gauge adds the
same slope or higher derivative to every site; it cannot erase spatially
relative dispersion error.

For an aperture of radius `R`, the exact required relative delay span is

```text
Delta_tau_required
  = [sqrt(R^2 + F^2) - F] / c.
```

At low NA this becomes approximately `R * NA / (2c)`, the scaling stated in
Chen's Methods. Chen reports about `5 fs` of available delay range from its
`600 nm`-high library and explicitly says that larger radius and NA require a
larger library delay range
([Chen et al. 2018, pp. 222, 225 and Methods](https://capasso.seas.harvard.edu/sites/g/files/omnuum6306/files/capasso/files/s41565-017-0034-6.pdf)).

This comparison is the first necessary feasibility test:

```text
available qualified slope span >= required relative slope span.
```

It is not sufficient by itself because the same cells must also cover the
reference phases, amplitudes and interior spectral law.

### 1.2 Geometry supplies dispersion; PB supplies the reference-phase offset

For an unrotated anisotropic fin, let `t_long(omega)` and `t_short(omega)` be
the complex principal-axis transmission coefficients. In the converted
circular-polarization channel, Chen's Jones expression is proportional to

```text
t_cross(g, alpha, omega)
  = [t_long(g, omega) - t_short(g, omega)] / 2
    * exp(i * 2 * s * alpha),
```

where `g` is the fixed geometry and `s` is fixed by the declared helicity and
phase convention. Consequently,

```text
arg t_cross
  = arg[t_long - t_short] + 2 * s * alpha.
```

Rotation adds a frequency-independent PB phase and therefore changes the phase
intercept without changing the phase slope or higher-order residual. Geometry
and material determine the complete complex spectral factor
`t_long-t_short`, including group delay, nonlinear phase and conversion
efficiency. Chen uses this separation explicitly
([Chen et al. 2018, Eq. 4 and Fig. 2c](https://capasso.seas.harvard.edu/sites/g/files/omnuum6306/files/capasso/files/s41565-017-0034-6.pdf)).

The orientation at one site therefore is not generally
`phi_required/2`. Once a geometry has been selected, it is

```text
alpha(r)
  = [phi_required(r, omega_ref)
     - arg t_cross(g(r), 0, omega_ref)] / (2s)
    modulo pi.
```

This equation makes geometry and orientation coupled assignment outputs. It
also makes the reference frequency a Method coordinate: Chen chose
`lambda_ref=530 nm` for its `120 nm` design band, but a general user requesting
a band has not thereby selected `530 nm` or any other reference wavelength
([Chen et al. 2018, design and Methods](https://capasso.seas.harvard.edu/sites/g/files/omnuum6306/files/capasso/files/s41565-017-0034-6.pdf)).

### 1.3 Higher-order residual is evidence, not an optional refinement

Chen Taylor-expands the target around the design frequency and states that
phase, group delay and higher derivatives must be considered for broadband
diffraction-limited focusing. For the achromatic `n=0` lens in air, the ideal
relative phase is linear in frequency; a real cell's curvature, resonances and
higher modes create residual error. Chen fitted each cell across a `120 nm`
band centered at `530 nm` and discarded cells with fit `R^2 < 0.99` or
polarization conversion below `5%`. It also distinguishes the designed
`120 nm` band from the experimentally observed extension to `470--670 nm`
([Chen et al. 2018, pp. 220--223 and Methods](https://capasso.seas.harvard.edu/sites/g/files/omnuum6306/files/capasso/files/s41565-017-0034-6.pdf),
[official supplement, Supplementary Figs. 1--11](https://media.springernature.com/original/springer-static/esm/art%3A10.1038%2Fs41565-017-0034-6/MediaObjects/41565_2017_34_MOESM1_ESM.pdf)).

The paper's `R^2` and `5%` thresholds are paper-specific method facts, not
universal user acceptance criteria. A MetaCraft Method may use them as a named
paper-informed profile, but its proof should retain stronger direct evidence:

- the complex response at every design and holdout wavelength;
- a coherent phase branch and its ambiguity diagnostics;
- maximum and RMS phase residual after the allowed global gauge;
- slope and higher-order residual under the declared convention;
- converted, retained and total transmitted power;
- band-edge results and every failed/missing wavelength.

Shrestha et al. provide the useful complementary design rule: minimize the
complex-phasor error over many closely spaced wavelengths, which directly
includes amplitude and deviations from a linear phase model, rather than
selecting cells from endpoint phase or slope alone
([Shrestha et al. 2018, Error minimization](https://www.nature.com/articles/s41377-018-0078-x)).

### 1.4 One device means one immutable layout across the band

Chen selects a nanofin element and one rotation at each coordinate, fabricates
one single-layer device, and illuminates that same device from `470` to
`670 nm`. Wavelength is an observation coordinate, not a design actuator
([publisher record](https://www.nature.com/articles/s41565-017-0034-6),
[Chen et al. 2018, Figs. 2--4](https://capasso.seas.harvard.edu/sites/g/files/omnuum6306/files/capasso/files/s41565-017-0034-6.pdf)).

Accordingly, MetaCraft must form exactly one layout identity:

```text
layout = {(site_i, geometry_i, orientation_i)}
```

and derive wavelength-specific complex aperture responses from it. Independent
per-wavelength geometry assignment would prove several monochromatic lenses,
not one continuous-achromatic metalens.

## 2. Fact ownership

### 2.1 Ownership table

| ID | Fact | Owner | Why |
| --- | --- | --- | --- |
| `U1` | Aim is one transmissive metalens with one fixed focus over a continuous vacuum-wavelength interval | Aim-owned continuous-band Brief | This is user outcome and operating condition |
| `U2` | Band endpoints, focal length, aperture/NA, output medium and incidence | Brief | These determine the physical target; they are not solver decisions |
| `U3` | Incident polarization/output-channel requirement, material/fabrication bounds, and any explicitly required or forbidden mechanism | Brief | User constraints determine Method applicability |
| `U4` | User-owned focal-flatness, efficiency, leakage or spot criteria, if explicitly stated | Brief | A Method may supply named defaults, but may not rewrite user acceptance |
| `M1` | Applicable physical Method: transmissive anisotropic dielectric cell, converted PB channel, geometry-controlled spectral phase | Method | It is one way to satisfy the aim, not user language |
| `M2` | `phi_required(r,omega)`, signed slope law, exact required delay span, and allowed aperture-wide spectral gauge | Method derivation | Deterministically derived from `U1--U3` plus a declared phase convention |
| `M3` | Reference frequency/wavelength and PB sign convention | Method | Chen's `530 nm` is paper-specific; a general band does not imply it |
| `M4` | Applicability and refusal rules, fit/residual/power qualifications, assignment loss and tie-break | Versioned Method contract | These make success/failure reproducible |
| `B1` | Actual material binding with band coverage, square period, height, substrate and phase-reference surface | Realization binding | These are resolved physical implementation facts, not Brief fields by default |
| `P1` | Geometry candidates, dimension step/minimum feature, exact x/y response channels | Spectral `CellStudyPlan` | They bound solver work |
| `P2` | Design wavelengths, independently held-out wavelengths and any convergence refinement schedule | Spectral `CellStudyPlan` / validation plan | Sampling is compiled work, not user intent |
| `P3` | Exact `PeriodicWork` identities, batching/chunking and expected receipt set | Plan/execution layer | Execution organization may vary without changing the scientific intent |
| `E1` | Raw complex x/y Jones values, transmitted powers, warnings, reference planes, solver/material provenance | Periodic-response evidence | Observed facts must remain below derived fits |
| `E2` | Coherent phase branch, converted spectrum, slope, higher-order residual, design/holdout qualification and convergence | Qualified spectral-cell evidence | Derived only from complete `E1` under `M4` |
| `A1` | One geometry and one orientation per site, shared by all wavelengths | Achromatic assignment output | This is the physical device |
| `E3` | One complex aperture field, propagated field and focal survey per holdout wavelength | Field/focus evidence | Wavelength-resolved proof; no averaging away failures |
| `R1` | Spectral focal flatness, spot/power/leakage summaries, worst wavelength and all omissions | Continuous-band Result | Terminal conclusion traceable to `E3`, `A1`, `E2`, `P1--P3`, `M1--M4`, and `U1--U4` |

Square lattice does not belong in the Brief merely because this first Method
uses it. The present template has one scalar period and equal x/y spans, so
square placement is a fixed realization property. Likewise, a single
rectangle is the first candidate family, not a user fact
([current periodic template](../../src/metacraft/solvers/lumerical_fdtd/template/periodic.py#L521-L577),
[`RectangularCrossSection`](../../src/metacraft/science/periodic_response.py#L498)).

### 2.2 Design and holdout bands

The user owns the **claimed operating band**, not the numerical samples. The
compiler must preserve three distinct sets:

```text
claim band
  continuous interval requested by the user

design grid
  wavelengths used for cell fitting and aperture assignment

holdout grid
  independently selected wavelengths used only for qualification/proof
```

Chen's paper proves why these names must not collapse: it designed over
`120 nm` around `530 nm`, then simulated and measured more broadly. Its outer
wavelengths are experimental validation, not evidence that two endpoints
prove every interior wavelength. MetaCraft's explicit holdout split is a proof
policy derived from that distinction; it is not claimed as a data structure
used in the paper.

## 3. Forward and reverse traceability

### 3.1 Forward compilation

```text
U1 continuous fixed-focus intent
 + U2 band/focus/aperture/medium
 + U3 polarization/material/fabrication constraints
      |
      v
M1 choose or refuse transmissive PB-dispersion Method
      |
      +--> M2 derive target phase and required delay span
      +--> M3 select reference frequency and legal global gauge
      +--> M4 freeze qualifications and typed refusal rules
      |
      v
B1 resolve square period, height and band-covered material stack
      |
      v
P1/P2/P3 bound rectangle candidates, design/holdout grids and work
      |
      v
E1 observe raw complex x/y Jones spectra
      |
      v
E2 qualify phase branch, converted response, slope, residual and coverage
      |
      +--> typed refusal if complete evidence proves insufficiency
      |
      v
A1 choose one fixed geometry + orientation per site
      |
      v
E3 form and propagate the same layout at every holdout wavelength
      |
      v
R1 conclude fixed-focus performance or honest spectral failure
```

### 3.2 Reverse audit

Every terminal claim must be traversable in the opposite direction:

```text
"fixed focus over band" R1
  <- every wavelength-specific focal survey E3
  <- one immutable aperture layout A1
  <- admitted qualified spectral cells E2
  <- raw Jones receipts and solver/material provenance E1
  <- exact candidate/grid/work plan P1/P2/P3 and binding B1
  <- target, gauge, convention and applicability Method M1--M4
  <- preserved user facts U1--U4.
```

This reverse chain detects four invalid shortcuts:

1. a result with different layouts per wavelength cannot reach one `A1`;
2. a fitted slope without raw complex spectra cannot reach `E1`;
3. an untested continuous-band claim cannot reach an independent `P2` holdout;
4. an alleged user requirement for square lattice or `530 nm` reference cannot
   reach `U1--U4` unless the user actually stated it.

## 4. Method applicability and typed refusal

### 4.1 Refuse before solver work

The primitive-square PB Method is inapplicable, and should issue a deterministic
typed refusal, when the preserved intent already contradicts it:

- the user requires reflection, polarization-independent operation, same-
  helicity output, or a non-PB mechanism while this Method promises a
  converted circular channel;
- the user fixes a material/stack outside the template or a period/height that
  cannot be made subwavelength and fabricable across the complete band;
- the requested band is not covered by exact material data without forbidden
  extrapolation;
- the user explicitly requires a compound, inverse or non-rectangular cell
  that the selected realization cannot represent;
- the requested output medium or polarization convention is incompatible with
  the Method's target derivation.

Missing information is not automatically a physical refusal. An unspecified
material choice, budget or acceptance threshold should remain a typed need,
advice or incomplete state according to the existing compiler vocabulary.

### 4.2 Refuse only after complete cell evidence

The following are evidence-backed refusals, not preflight guesses:

- `single_rectangle_no_qualified_converted_cells`: no candidate passes complex
  response completeness, power and phase-continuity gates;
- `single_rectangle_delay_span_insufficient`: qualified spectral slope span is
  smaller than `Delta_tau_required` under every allowed aperture-wide gauge;
- `single_rectangle_joint_phase_dispersion_coverage_insufficient`: the scalar
  delay span passes, but no deterministic geometry/orientation assignment
  covers required phase and slope at all sites;
- `single_rectangle_spectral_residual_exceeded`: design or holdout complex-
  phasor/phase residual exceeds the Method contract, including a failed band
  edge;
- `pb_rotation_relation_unqualified_over_band`: physical rotated-cell checks
  do not preserve the predicted `2s alpha` offset and spectral response;
- `local_periodic_model_inapplicable`: neighbor/supercell validation shows the
  isolated periodic library is not predictive for the selected layout.

Chen reports that periodic-cell modeling ignores unlike-neighbor coupling and
attributes part of the measured-versus-predicted efficiency gap to this
approximation. A periodic-cell library therefore cannot by itself close the
final physical proof
([Chen et al. 2018, efficiency discussion](https://capasso.seas.harvard.edu/sites/g/files/omnuum6306/files/capasso/files/s41565-017-0034-6.pdf)).

### 4.3 Incomplete evidence is not a negative physical result

If wavelengths, receipts, material samples, reference-plane facts or
convergence runs are missing, the correct outcome is incomplete/unavailable,
not `coverage_insufficient`. A refusal asserts that complete admitted evidence
proved the Method cannot satisfy this request under this realization. This
distinction keeps interruption recovery from being misreported as physics.

## 5. Exact delta from current MetaCraft

The existing code already provides the structural base:

- `PeriodicWork` binds one exact wavelength, geometry, period, height and
  material stack
  ([`periodic_response.py`](../../src/metacraft/science/periodic_response.py#L651));
- the native template uses equal x/y periodic spans, normal incidence and a
  single start/stop wavelength
  ([`template/periodic.py`](../../src/metacraft/solvers/lumerical_fdtd/template/periodic.py#L521-L577));
- `JonesResponse` retains the four complex linear-basis coefficients
  ([`geometric_phase.py`](../../src/metacraft/science/metalens/geometric_phase.py#L205));
- `OrientationRelation` already represents converted phase plus signed twice-
  orientation PB phase
  ([`geometric_phase.py`](../../src/metacraft/science/metalens/geometric_phase.py#L887-L935));
- `JonesEvidenceBatch` already groups paired polarization evidence
  ([`periodic_cell_evidence.py`](../../src/metacraft/science/metalens/periodic_cell_evidence.py#L214)).

The first slice therefore should not change the solver template. It needs deep
scientific composition above it:

1. a sibling continuous-band metalens Brief rather than changing the existing
   scalar `MetalensBrief`;
2. one achromatic Method with explicit applicability/refusal and phase
   convention;
3. one bounded spectral cell-study plan that composes existing single-
   wavelength work identities into a complete response family;
4. qualified spectral Jones evidence owning coherent phase, slope, residual,
   design/holdout and provenance;
5. one gauge-aware joint geometry/orientation assignment;
6. one immutable aperture layout with wavelength-specific response views;
7. one continuous-band Result composed from existing single-wavelength fields
   and focal surveys.

The existing `MetalensBrief` requires one scalar `wavelength_nm`, and the
existing `CellStudyPlan` is also single-wavelength. Retrofitting tuple
wavelengths into either would blur the fact ownership established above
([`brief.py`](../../src/metacraft/science/metalens/brief.py#L96-L113),
[`cell_study.py`](../../src/metacraft/science/metalens/cell_study.py#L654)).

## 6. Acceptance of the first slice

The primitive single-rectangle slice is successful only if it produces both a
positive case and an honest nearby negative case:

### Positive closure

- a modest compiled band/NA/aperture whose required delay is within the
  observed library;
- complete design and holdout spectral Jones evidence;
- one fixed layout with deterministic geometry/orientation assignment;
- holdout focal position, spot, converted power and leakage within declared
  thresholds;
- a chromatic PB-only baseline showing materially larger focal drift under the
  same propagation and metrics.

### Negative closure

- a deliberately larger-band, larger-radius or higher-NA request whose
  required delay/joint coverage exceeds the same primitive library;
- a typed, evidence-backed refusal naming the failed bound;
- no automatic geometry expansion and no partial-wavelength average reported
  as success.

Only after that negative closure should a compound two-fin template be
considered. Chen establishes that coupled fins add dispersion degrees of
freedom; it does not establish that such a template is universally necessary.
This staged boundary lets measured evidence, rather than paper imitation,
decide the architecture.

## Final conclusion

The correct dual trace is:

```text
user intent
  -> fixed-focus spectral phase law
  -> required phase intercept + relative slope + higher-order residual
  -> PB/geometry Method applicability
  -> bounded square primitive-cell evidence
  -> joint fixed geometry/orientation layout
  -> independent spectral field/focus proof

and back:

spectral conclusion
  -> exact fields
  -> one layout
  -> qualified spectral cells
  -> raw receipts
  -> plan and Method
  -> original user facts.
```

Chen 2018 is especially suitable because its physical factorization already
matches MetaCraft's x/y Jones plus analytical PB vocabulary, its unit cell is
square, and its simulations used Lumerical. The scientific risk is not the
template syntax; it is whether a primitive rectangular library spans the
needed joint phase--dispersion space with adequate converted power and low
interior residual. That question must be answered by evidence, with typed
refusal as a first-class successful outcome of the compiler.

## Primary sources

1. W. T. Chen et al., "A broadband achromatic metalens for focusing and
   imaging in the visible," *Nature Nanotechnology* 13, 220--226 (2018),
   [DOI](https://doi.org/10.1038/s41565-017-0034-6),
   [publisher record](https://www.nature.com/articles/s41565-017-0034-6),
   [author-group published PDF](https://capasso.seas.harvard.edu/sites/g/files/omnuum6306/files/capasso/files/s41565-017-0034-6.pdf),
   [official supplementary information](https://media.springernature.com/original/springer-static/esm/art%3A10.1038%2Fs41565-017-0034-6/MediaObjects/41565_2017_34_MOESM1_ESM.pdf).
2. E. Arbabi et al., "Controlling the sign of chromatic dispersion in
   diffractive optics with dielectric metasurfaces," *Optica* 4, 625--632
   (2017), [DOI and primary article](https://doi.org/10.1364/OPTICA.4.000625),
   [Caltech author repository](https://authors.library.caltech.edu/records/nnf8v-92988/latest).
3. S. Wang et al., "Broadband achromatic optical metasurface devices,"
   *Nature Communications* 8, 187 (2017),
   [DOI and open primary article](https://doi.org/10.1038/s41467-017-00166-7).
4. S. Shrestha et al., "Broadband achromatic dielectric metalenses,"
   *Light: Science & Applications* 7, 85 (2018),
   [DOI and open primary article](https://doi.org/10.1038/s41377-018-0078-x).
