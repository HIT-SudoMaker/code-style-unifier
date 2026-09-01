---
record_type: research_record
date: 2026-08-13
status: research_finding
authority_level: none
current_capability: false
---

# Low-cost transmissive continuous-achromatic metalens routes for MetaCraft

## Research question

Which experimentally grounded transmissive continuous-achromatic metalens
route can migrate into MetaCraft with the smallest honest change to its current
square-period Lumerical template, primitive dielectric rectangle/ellipse cell,
linear-basis Jones observation, and analytical PB-orientation path?

This record uses original articles, official supplementary material, and the
repository source. It recommends a research route; it does not select a method,
change production code, or claim that MetaCraft can presently design an
achromat.

## Executive finding

The 2017 Wang--Tsai paper did **not** demonstrate or specify a transmissive
implementation. It only says that its principle could be used in transmission
*if* transparent integrated-resonant unit elements (IRUEs) can be introduced.
That conditional sentence supplies no transmissive stack, geometry library,
solver qualification, or efficiency evidence
([Wang et al. 2017, Discussion](https://www.nature.com/articles/s41467-017-00166-7)).

The best low-cost scientific starting point is therefore not a literal port of
Wang 2017 or Wang 2018. It is a **Chen et al. 2018-inspired, local-material,
square-cell PB plus spectral-phase-slope feasibility slice**:

1. retain one dielectric layer, one substrate, one square period, a primitive
   rectangular fin, x/y complex Jones response, and analytical PB orientation;
2. add a coherent spectral response observation, phase-branch qualification,
   phase-slope/residual diagnostics, and gauge-aware assignment;
3. deliberately choose a modest band, aperture and NA only after the measured
   single-fin library passes the required delay-range screen;
4. add a two-fin compound cell only if the primitive library demonstrably lacks
   coverage.

This is a method-inspired first slice, not a reproduction of Chen 2018. The
published achromatic lens used a library containing **one or two** coupled TiO2
nanofins, so a single-fin library is a falsifiable feasibility gate rather than
an assumption of success
([Chen et al. 2018, Fig. 2 and Methods](https://capasso.seas.harvard.edu/sites/g/files/omnuum6306/files/capasso/files/s41565-017-0034-6.pdf)).

## What MetaCraft already has

The current periodic template is unusually close to the numerical skeleton of
the Chen route:

- one scalar period sets equal x/y solver spans and periodic boundaries;
- primitive rectangular and elliptical dielectric cross-sections are admitted;
- x- and y-polarized runs recover the complete complex linear Jones response;
- the source is normal-incidence and the response is referenced to transmitted
  zeroth order;
- each `PeriodicWork` is intentionally single-wavelength;
- the geometric-phase domain already derives orientation from an admitted
  Jones response rather than physically rotating every library cell.

The relevant implementation is
[`template/periodic.py`](../../src/metacraft/solvers/lumerical_fdtd/template/periodic.py),
especially its equal `span_x_nm`/`span_y_nm`, single start/stop wavelength, x/y
input basis, and `RectangularCrossSection` construction. The missing capability
is primarily **spectral evidence and assignment**, not a new solver family.

## Route comparison

| Rank by first-slice migration cost | Primary route | Lattice and stack | Cell degrees of freedom | Phase mechanism and reported result | Exact delta from current MetaCraft | Scientific disposition |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | **Chen et al. 2018, restricted primitive-fin feasibility slice** | Square `400 x 400 nm` element; one `600 nm` TiO2 layer on glass; transmission | Published library: one or two rectangular fins, each with length/width, `60 nm` inter-fin gap, common rotation | Cross-polarized phase is `arg(t_L-t_S)+2 alpha`; geometry controls phase slope/group delay and PB rotation controls the reference phase. Design band `120 nm` around `530 nm`; measured diffraction-limited behavior `470–670 nm`, NA `0.2`, `f=63 um`; about `20%` efficiency near `500 nm` | **No template delta** for a one-fin feasibility library. Add atomic spectral Jones evidence, unwrapping/linearity qualification, delay-range screen and band assignment. Compound two-fin geometry is the first optional template delta | **Recommended first slice.** Closest solver, lattice, primitive and PB semantics; failure of primitive coverage is informative and must be allowed |
| 2 | **Chen et al. 2018, paper-mechanism compound-fin route** | Same square cell and single transmissive TiO2 layer | One or two independently sized/arranged fins plus gap, then common rotation | Same phase/GD/GDD framework; Lumerical FDTD and Eigenmode Solutions were used; library entries below `R^2=0.99` linearity or `5%` conversion were discarded | Add one compound-cross-section/supercell primitive and its canonical identity/building rules; existing x/y response and PB algebra remain useful | **Best expansion if rank 1 fails.** A small but real template extension, not a new lattice or multilayer solver |
| 3 | **Wang et al. 2018 visible transmissive IRUE** | Hexagonal `120 nm` lattice; `800 nm` GaN on sapphire; transmission | Solid and inverse/Babinet GaN IRUEs with length/width, family and rotation; 17 reported compensation states | PB base phase plus multiple waveguide/cavity-resonance compensation; `400–660 nm`, NA `0.106`, average efficiency about `40%`, maximum up to `67%` | New hex lattice, positive and inverse compound geometry, much finer features, GaN/sapphire band bindings, broadband converted-channel qualification, and paper-specific IRUE library recovery | **Reliable experiment, poor low-cost migration.** This is the 2017 principle's demonstrated transmissive realization, but it removes almost every template advantage |
| 4 | **Shrestha et al. 2018 dielectric phase-dispersion-space route** | Single transmissive amorphous-Si layer on fused quartz; `800` or `1400 nm` tall | Circular pillar, annulus, concentric rings; later crosses and inscribed crosses | No PB is required: geometry directly fills reference-phase/dispersion space and dense-wavelength complex-phasor matching selects cells. Polarization independent; up to `50%` efficiency; `1200–1650 nm`; M1B NA about `0.24`, high-NA M3 about `0.88` over `1200–1400 nm` | Add annular/concentric/cross/inscribed-cross compound shapes, scalar/polarization-independent spectral library, `C(omega)` gauge search, and dense complex-phasor assignment. The existing primitive circle alone supplies only one dispersion per phase and is explicitly called insufficient by the paper | **Excellent framework and validation oracle, not a cheap first realization.** Its spectral gauge and complex-phasor loss should influence MetaCraft even if its geometry library is deferred |
| 5 | **Wang et al. 2017 exact device** | Square `550 nm` grid; Au/SiO2/Au reflection stack | One or several coupled Au rods, gaps, relative placement and rotation | PB plus integrated plasmonic resonance; `1200–1680 nm`, NA `0.268`, efficiency order `12%` | Reflection port, metal mirror/spacer multilayer, lossy materials, compound rods and reflected-channel propagation | **Reject for current migration.** It is a theory/reference case, not a low-cost transmissive case |
| 6 | **Khorasaninejad et al. 2017** | TiO2 nanopillars on dielectric spacer above a metallic mirror; reflection | Pillar dispersion and multiple phase branches | Dispersion-engineered reflective phase shifters; `490–550 nm`, NA `0.2`; the paper reports about `15%` focusing efficiency | Reflection and mirror/spacer multilayer before spectral assignment can even be tested | **Do not treat as a transmissive alternative.** It shares TiO2 with later work but not MetaCraft's present stack |

## Primary-source details

### 1. Wang 2017: a conditional transmission claim, not a route specification

Wang et al. demonstrated only the reflective Au/SiO2/Au devices. Their exact
transmission statement is conditional: the principle is applicable if
transparent IRUEs can be successfully introduced. Accordingly, citing Wang
2017 alone cannot justify any particular transparent material, cross-section,
lattice, phase library or performance target. The 2018 Wang--Tsai paper is a
new physical realization that supplies those missing facts, not a hidden
transmission example inside the 2017 work
([2017 article](https://doi.org/10.1038/s41467-017-00166-7)).

### 2. Wang 2018: transmissive, but structurally expensive

Wang et al. 2018 realized the same PB-plus-compensation logic in a transmissive
visible device. The primary paper and official supplement report undoped GaN
on double-polished sapphire, `800 nm` height, a `120 nm` hexagonal lattice, and
solid plus inverse IRUE families. A fixed geometry determines the
wavelength-dependent compensation and a fixed rotation supplies the PB base
phase. The `400–660 nm` device with NA `0.106` reports average efficiency about
`40%`
([article](https://doi.org/10.1038/s41565-017-0052-4),
[official supplement](https://media.springernature.com/original/springer-static/esm/art%3A10.1038%2Fs41565-017-0052-4/MediaObjects/41565_2017_52_MOESM1_ESM.pdf)).

For MetaCraft, "adapt it to a square lattice" is not a harmless parameter
change. Its very small hexagonal pitch and its mixture of solid and inverse
resonant cells define the demonstrated library. A square, primitive-rectangle
adaptation would have to regenerate and re-qualify the entire spectral library
and should be named Wang--Tsai-inspired, not a reproduction.

### 3. Chen 2018: closest to the current template

Chen et al. use the same Jones/PB factorization already represented in
MetaCraft. For a circular input, the cross-polarized term is proportional to

```text
(t_long - t_short) exp(i 2 alpha).
```

The rotation `alpha` shifts the reference phase without changing the spectral
slope, while the complex difference of the long- and short-axis transmission
coefficients controls conversion and dispersion. Each TiO2 fin is treated as
a truncated waveguide; its dimensions tune effective/group index. The
published cell is a square `400 x 400 nm` region with `600 nm` height. The
library contains one- and two-fin elements, and the paper explicitly used
Lumerical FDTD and Eigenmode Solutions with transverse periodic and
longitudinal PML boundaries
([article PDF, Fig. 2 and Methods](https://capasso.seas.harvard.edu/sites/g/files/omnuum6306/files/capasso/files/s41565-017-0034-6.pdf)).

The paper's achromatic design first linearly fitted every candidate's phase
spectrum over a `120 nm` band centered on `530 nm`; candidates below
`R^2=0.99` or `5%` polarization conversion were excluded. Geometry supplied a
group-delay range around `5 fs`, then the chosen element was rotated to meet
the reference phase. Measured near-achromatic behavior extended from
`470–670 nm`, but the authors clearly distinguish this observed extension from
the narrower design band. MetaCraft must preserve that distinction rather
than labelling a 200-nm band proven from a 120-nm fit.

The direct architectural fit is strong:

```text
paper                         MetaCraft today
square 400-nm cell            one equal x/y period
single dielectric layer       atom on substrate
x/y principal transmissions   full linear Jones response
PB rotation                   analytical OrientationRelation
Lumerical FDTD                native periodic Lumerical route
```

The cheapest honest experiment scans only primitive rectangles already
supported by the template. It asks whether the local material/height/period
domain produces enough qualified phase-slope range for a deliberately bounded
lens. Only an evidence-backed "insufficient coverage" authorizes the compound
two-fin extension.

### 4. Shrestha 2018: best general matching framework, costly shape space

Shrestha et al. formulate the lens target with an aperture-wide spectral gauge
`C(omega)` and describe each cell in phase--dispersion space. Their practical
assignment is stronger than endpoint or derivative matching alone: it compares
the simulated complex phasor against the target at many wavelengths and
jointly searches the gauge parameters. This naturally includes amplitude and
interior nonlinear phase error
([article, equations and error minimization](https://www.nature.com/articles/s41377-018-0078-x)).

However, the demonstrated coverage does not come from a primitive pillar
library. Generation 1 uses singular, annular and concentric-ring pillars;
Generation 2 adds crosses and inscribed crosses. The authors state that singular
pillars provide essentially one dispersion value per phase and are a poor
library by themselves. Raising height from `800` to `1400 nm` nearly doubles
dispersion coverage, with an explicit fabrication and neighbor-coupling cost.
Thus this route is highly reliable as a phase-gauge, feasibility-limit and
complex-loss reference, but adopting its demonstrated cell family would
expand the current template more than the Chen compound-fin route.

Reported transmissive results include polarization-independent focusing up to
`50%` efficiency and continuous near-constant focus over `1200–1650 nm`.
M1B has diameter `100 um`, NA about `0.24`; M2 has diameter `200 um`, NA about
`0.13`; M3 reaches NA about `0.88` only over the reduced `1200–1400 nm` band.
The paper also states the fundamental tradeoff: required dispersion coverage
grows with aperture, NA and bandwidth
([article, Eqs. 4--5 and Figs. 3--5](https://www.nature.com/articles/s41377-018-0078-x)).

### 5. Khorasaninejad 2017 is not the requested escape hatch

The earlier Capasso-group 60-nm visible achromat used TiO2 pillars, but those
pillars sit above a dielectric spacer and metallic mirror and operate in
reflection from `490–550 nm`. Its material name can make it appear close to a
transmissive TiO2 template; its optical boundary and stack are not close
([primary article record and PDF](https://capasso.seas.harvard.edu/publications/achromatic-metalens-over-60-nm-bandwidth-visible-and-metalens-reverse-chromatic)).

## Recommended first slice

The first implementation should be named something like **square-cell
transmissive PB dispersion feasibility**, not "Wang 2018 reproduction" or
"Chen 2018 reproduction".

Its minimum scientific contract is:

1. One user achromatic metalens intent: a continuous band, one focus, aperture,
   NA, circular input/output channel, and local materials/fabrication bounds.
2. One fixed realization selected by the method: square period, one height,
   primitive rectangular dielectric fin on one substrate, normal incidence.
3. One bounded `CellStudyPlan` crossing geometry candidates with a declared
   design wavelength grid and an independent holdout grid.
4. One complete complex x/y Jones spectrum per geometry. The spectral family
   must be admitted atomically even if native work remains resumable per
   wavelength.
5. One qualification that owns coherent phase branching, converted/retained
   power, spectral-linearity residual, holdout error and solver/material
   provenance.
6. One delay-bandwidth feasibility decision **before** aperture assignment.
   If the qualified primitive library cannot cover the required range, return
   a typed insufficiency; do not silently narrow the lens or fabricate
   responses.
7. One gauge-aware assignment that jointly chooses the fixed geometry and
   fixed orientation at every site. Use dense complex-phasor error over the
   band as the primary loss; report phase slope/GDD and worst wavelength as
   diagnostics.
8. Existing single-wavelength field formation, propagation and focus
   evaluation composed into one spectral conclusion with no missing wavelength
   hidden by averaging.

The only mandatory production deltas should therefore be spectral orchestration
and evidence/domain logic. The current primitive geometry and native Lumerical
template stay unchanged. A compound two-fin cross-section becomes a separate,
small second ticket only after the feasibility result requires it.

## Caveats that prevent a premature success claim

- A primitive rectangular fin may not span independently enough reference
  phase and group delay for the requested band/NA/aperture. That is the central
  experiment, not an implementation nuisance.
- Analytical `2 alpha` PB rotation assumes the canonical-cell response remains
  valid after physical rotation and among unlike neighbors. Selected physical
  rotations and local supercells need held-out validation.
- Phase must be branched coherently across frequency before slope/GDD is
  computed. Independent wrapped phases cannot be differentiated.
- A global spectral phase gauge is legal only aperture-wide. Independent
  per-cell or unconstrained per-wavelength offsets can hide dispersion error.
- Delay range scales against aperture, NA and bandwidth. MetaCraft must compile
  a feasible first device from the measured library rather than pre-lock a
  spectacular paper geometry.
- Chen 2018 reported about `20%` measured efficiency near `500 nm` versus about
  `50%` predicted, attributing the gap in part to fabrication and neighbor
  coupling ignored by periodic cells. Periodic-cell success is not full-lens
  Maxwell validation.
- Shrestha's dense complex-phasor assignment is preferable to treating fitted
  group delay as the only optimizer input; the derivative quantities remain
  valuable qualification diagnostics.

## Final recommendation

Use **Chen 2018 as the nearest physical method**, **Shrestha 2018 as the nearest
assignment/feasibility framework**, and **Wang 2017/2018 as historical
mechanism and comparison references**.

The resulting MetaCraft method should be intentionally local-material and
paper-inspired:

```text
existing square primitive transmission template
  + coherent spectral Jones evidence
  + Shrestha-style gauge-aware complex matching
  + Chen-style PB/reference-phase decoupling
  + delay-range refusal before design
```

This route has the lowest migration cost without weakening the claim. It also
has a clear escalation path: primitive rectangle first; compound two-fin cell
second; richer symmetric phase-dispersion cells only if the desired
polarization or coverage later demands them. Wang 2018's hexagonal solid/inverse
IRUE library should not be on the first implementation path.

## Primary sources

1. S. Wang et al., "Broadband achromatic optical metasurface devices,"
   *Nature Communications* 8, 187 (2017),
   [DOI 10.1038/s41467-017-00166-7](https://doi.org/10.1038/s41467-017-00166-7).
2. S. Wang et al., "A broadband achromatic metalens in the visible,"
   *Nature Nanotechnology* 13, 227--232 (2018),
   [DOI 10.1038/s41565-017-0052-4](https://doi.org/10.1038/s41565-017-0052-4),
   [official supplementary information](https://media.springernature.com/original/springer-static/esm/art%3A10.1038%2Fs41565-017-0052-4/MediaObjects/41565_2017_52_MOESM1_ESM.pdf).
3. W. T. Chen et al., "A broadband achromatic metalens for focusing and
   imaging in the visible," *Nature Nanotechnology* 13, 220--226 (2018),
   [DOI 10.1038/s41565-017-0034-6](https://doi.org/10.1038/s41565-017-0034-6),
   [author-group published PDF](https://capasso.seas.harvard.edu/sites/g/files/omnuum6306/files/capasso/files/s41565-017-0034-6.pdf).
4. S. Shrestha et al., "Broadband achromatic dielectric metalenses,"
   *Light: Science & Applications* 7, 85 (2018),
   [DOI 10.1038/s41377-018-0078-x](https://doi.org/10.1038/s41377-018-0078-x).
5. M. Khorasaninejad et al., "Achromatic Metalens over 60 nm Bandwidth in
   the Visible and Metalens with Reverse Chromatic Dispersion," *Nano
   Letters* 17, 1819--1824 (2017),
   [DOI 10.1021/acs.nanolett.6b05137](https://doi.org/10.1021/acs.nanolett.6b05137),
   [author-group record/PDF](https://capasso.seas.harvard.edu/publications/achromatic-metalens-over-60-nm-bandwidth-visible-and-metalens-reverse-chromatic).
