---
record_type: research_record
date: 2026-08-13
status: research_finding
authority_level: none
current_capability: false
---

# Square-template PB and spectral-compensation seams

## Research question

What square-lattice and geometry capabilities does MetaCraft's current
Lumerical periodic template actually establish? What does the original
Wang--Tsai achromatic method require when a wavelength-independent PB phase is
combined with geometry-controlled spectral compensation? Which facts belong
to the Method, template/binding, bounded plan, and evidence rather than the
Brief?

This record uses only repository source and tests, the original 2017 and 2018
Wang--Tsai papers, and the 2018 paper's official supplementary information. It
changes no capability or architecture.

## Executive finding

The user's simplification is correct: **square lattice should not become a
required Brief field while MetaCraft exposes no competing lattice family.**
The current Lumerical periodic realization already constructs a square
computational cell from one scalar `period_nm`: the FDTD region, substrate, and
response group all use equal `span_x_nm` and `span_y_nm`, with periodic x/y
boundaries. That is an implementation fact verified by construction read-back,
not a choice the user must repeat
([periodic template, lines 521--580](../../src/metacraft/solvers/lumerical_fdtd/template/periodic.py),
[expected read-back, lines 674--729](../../src/metacraft/solvers/lumerical_fdtd/template/periodic.py)).

The current template is nevertheless **not yet a broadband PB-compensation
template**. It observes one wavelength at normal incidence, targets zeroth
transmission order, and builds an unrotated primitive circle, square,
rectangle, or ellipse. For anisotropic rectangle/ellipse cells it obtains the
full linear-basis Jones response through separate x- and y-input work, while
orientation is deliberately absent from the `CellStudyPlan`
([periodic template, lines 288--317 and 555--580](../../src/metacraft/solvers/lumerical_fdtd/template/periodic.py),
[native atoms, lines 624--671](../../src/metacraft/solvers/lumerical_fdtd/template/periodic.py),
[cell-study source, lines 84--93 and 293--352](../../src/metacraft/science/metalens/cell_study.py),
[cell-study test, lines 100--123](../../tests/science/test_cell_study.py)).

Wang--Tsai supplies a **Method principle**, not a paper-locked template:

```text
required phase
  = wavelength-independent PB base phase
  + geometry-controlled resonant phase compensation versus wavelength.
```

The 2017 paper implements this on a square `550 nm x 550 nm` reflective cell;
the 2018 visible paper implements the same decomposition with solid/inverse
GaN IRUEs on a `120 nm` hexagonal lattice. Thus the phase decomposition does
not require a hexagonal lattice, and adapting it to MetaCraft's square
periodic realization is scientifically legitimate. It is **method
adaptation**, not exact reproduction
([Wang et al. 2017, equations 1--4 and Fig. 2](https://www.nature.com/articles/s41467-017-00166-7#Sec3),
[Wang et al. 2018, pp. 227--230](https://dsl.nju.edu.cn/litao/res/paper/Wang_SM-nnano_13_227%282018%29.pdf),
[official 2018 supplementary information, Supplementary Fig. 1](https://media.springernature.com/original/springer-static/esm/art%3A10.1038%2Fs41565-017-0052-4/MediaObjects/41565_2017_52_MOESM1_ESM.pdf)).

The Sonnet-shaped first slice should therefore add no public `lattice_kind`
enum. It should retain one scalar pitch in the bounded plan, let the qualified
Lumerical realization own square construction, and require evidence to prove
the spectral Jones response and the PB-rotation approximation for the selected
local material stack.

## 1. What the current MetaCraft template actually promises

### 1.1 Fixed square-periodic experiment

For every `PeriodicConstruction`, one scalar `period_nm` is projected into:

- equal FDTD `span_x_nm` and `span_y_nm`;
- periodic lower/upper x and y boundaries;
- equal substrate x/y spans; and
- equal response-group x/y spans.

The expected construction record repeats those equal spans, so native
read-back can reject a construction that differs from the declared square
cell
([construction, lines 521--580](../../src/metacraft/solvers/lumerical_fdtd/template/periodic.py),
[manifest comparison, lines 583--620](../../src/metacraft/solvers/lumerical_fdtd/template/periodic.py),
[expected response, lines 674--693](../../src/metacraft/solvers/lumerical_fdtd/template/periodic.py)).

There is no `period_x`, `period_y`, lattice-angle, Bravais-lattice, or
hexagonal-cell parameter in `PeriodicWork`; it contains one `period_nm`
([PeriodicWork, lines 649--674](../../src/metacraft/science/periodic_response.py)).
Consequently the current interface cannot represent rectangular or hexagonal
lattices. A `square lattice` Brief field would currently have only one legal
value and would duplicate the realization's fixed fact.

### 1.2 Geometry varies; lattice topology does not

The route-neutral periodic seam accepts exactly four primitive cross-sections:
circle, square, rectangle, and ellipse
([cross-section types, lines 464--537](../../src/metacraft/science/periodic_response.py)).
The Lumerical template maps them to native circle, rectangle, or ellipse
objects. Rectangles and ellipses use unequal principal dimensions and are
therefore the current PB-capable anisotropic families; circle and literal
square are routed to scalar/transverse-linear transmission rather than the
cartesian Jones profile
([construction routing, lines 288--317](../../src/metacraft/solvers/lumerical_fdtd/template/periodic.py),
[native mapping, lines 624--671](../../src/metacraft/solvers/lumerical_fdtd/template/periodic.py)).

The metalens planner currently derives the geometry family from the aim-owned
atom shape. Circular/square candidates produce one scalar transmission task;
rectangular/elliptical candidates produce two tasks, one for each x/y linear
input, and request all four Jones coefficients
([bounded options, lines 945--1010](../../src/metacraft/science/metalens/cell_study.py),
[Jones work, lines 1143--1164](../../src/metacraft/science/metalens/cell_study.py)).
Geometry family is therefore a real design/planning fact. Square lattice is
not currently a peer choice.

### 1.3 Present limits that matter for achromatization

The native response group currently fixes:

- normal incidence (`polar_angle_degrees = azimuth_degrees = 0`);
- positive-z plane-wave propagation;
- one wavelength (`start_wavelength_nm == stop_wavelength_nm`);
- zeroth transmitted order; and
- an x- or y-linear incident basis

([response construction, lines 555--580](../../src/metacraft/solvers/lumerical_fdtd/template/periodic.py)).

The template has no physical meta-atom rotation parameter, and the planner's
canonical PB plan explicitly contains no `orientation`. Current monochromatic
PB science instead qualifies one unrotated x/y Jones anchor and derives the
continuous orientation relation analytically without further solver work
([orientation derivation, lines 1288--1313](../../src/metacraft/science/metalens/geometric_phase.py),
[cell-study test, lines 100--123](../../tests/science/test_cell_study.py)).

This is an efficient and intentional current seam. It must not be mistaken for
evidence that the analytic rotation law remains exact for every geometry,
orientation, and wavelength in a dispersive square array.

## 2. Exact PB plus compensation decomposition

For optical path difference

```text
OPD(r) = sqrt(r^2 + f^2) - f,
```

the ideal fixed-focus phase is

```text
phi_lens(r, lambda) = -2 pi OPD(r) / lambda.
```

Wang et al. split it at the longest wavelength:

```text
phi_lens(r, lambda)
  = phi_lens(r, lambda_max)
  + Delta_phi(r, lambda)

Delta_phi(r, lambda)
  = -2 pi OPD(r) (1/lambda - 1/lambda_max).
```

The first term is independent of the working wavelength and is supplied by PB
rotation. The second term must be supplied by a unit response whose phase is
smooth and approximately linear in `1/lambda`. A spatially uniform gauge
`phi_shift(lambda) = alpha/lambda + beta` may be added without changing focus;
the paper uses it to place the required compensation inside the attainable
library range
([Wang et al. 2017, equations 1--4](https://www.nature.com/articles/s41467-017-00166-7#Sec3),
[Wang et al. 2018, equations 1--2, PDF p. 229](https://dsl.nju.edu.cn/litao/res/paper/Wang_SM-nnano_13_227%282018%29.pdf#page=3)).

For a selected anisotropic geometry `g`, the separable PB model in the
converted circular channel is

```text
t_cross(g, lambda, theta)
  ~= t_cross(g, lambda, 0) exp(i s 2 theta),

s in {-1, +1}, fixed by handedness and phasor convention.
```

Accordingly, geometry identity selects the wavelength-dependent complex
response, while orientation supplies a wavelength-independent phase offset.
The robust site assignment is not simply `theta = phi_basic/2`; it must account
for the selected geometry's complex phase at the reference wavelength:

```text
theta(r)
  = wrap_pi(
      [phi_basic(r) - arg t_cross(g(r), lambda_max)] / (2 s)
    ).
```

This exposes the desired duality:

| Spatial role | Physical control | Evidence obligation |
| --- | --- | --- |
| wavelength-independent phase intercept | orientation `theta` | converted-channel `+/-2 theta` law with stable amplitude/leakage |
| wavelength-dependent phase difference | geometry `g` and its resonances | continuous complex phase response versus `1/lambda`, including efficiency |

The paper states that the base phase is obtained by PB and the compensation by
IRUEs, and that IRUE identity and rotation are jointly placed on the surface
([Wang et al. 2017, lines accompanying equations 2--3](https://www.nature.com/articles/s41467-017-00166-7#Sec3),
[Wang et al. 2018, PDF pp. 227--229](https://dsl.nju.edu.cn/litao/res/paper/Wang_SM-nnano_13_227%282018%29.pdf#page=2)).
The equations above merely make the phase-origin correction explicit for a
local-material library; they do not assume that every adapted geometry has
the paper's zero intercept.

## 3. What may be inherited and what must be re-established

### 3.1 Method invariants inherited from Wang--Tsai

MetaCraft can faithfully inherit:

1. one physical layout over the whole band;
2. the fixed-focus phase law and its split at `lambda_max`;
3. PB orientation as the wavelength-independent base-phase control;
4. geometry-dependent integrated resonances as the spectral-compensation
   control;
5. an optional global inverse-wavelength phase gauge; and
6. cross-helicity conversion efficiency and leakage as part of the response,
   not phase alone.

These are stated by the original 2017 principle and retained by the 2018
transmissive realization
([Wang et al. 2017, Results and Fig. 2](https://www.nature.com/articles/s41467-017-00166-7),
[Wang et al. 2018, PDF pp. 227--230](https://dsl.nju.edu.cn/litao/res/paper/Wang_SM-nnano_13_227%282018%29.pdf)).

### 3.2 Paper-specific facts that do not transfer automatically

The following do not become requirements merely by adopting the Method:

- the 2017 reflective Au/SiO2/Au stack, coupled metallic nanorods, `550 nm`
  pitch, CST realization, or `1200--1680 nm` band;
- the 2018 GaN/sapphire stack, solid/inverse shapes, `800 nm` height, `120 nm`
  hexagonal lattice, 17-element table, or `400--660 nm` band; and
- either paper's fabrication-specific efficiency values.

The 2017 square cell already proves that the Method is not inherently
hexagonal: it uses equal `550 nm` periods along x and y. Conversely, the 2018
hexagonal device proves that lattice topology is not the Method's defining
coordinate
([Wang et al. 2017, Fig. 2 caption](https://www.nature.com/articles/s41467-017-00166-7#Fig2),
[official 2018 supplementary information, Supplementary Fig. 1](https://media.springernature.com/original/springer-static/esm/art%3A10.1038%2Fs41565-017-0052-4/MediaObjects/41565_2017_52_MOESM1_ESM.pdf)).

MetaCraft's present material catalogue registers silica-family records,
silicon, silicon nitride, and amorphous titanium dioxide for Lumerical; it does
not currently register GaN or sapphire
([local Lumerical material catalogue](../../materials/lumerical.toml)).
Whichever local stack is selected must therefore establish its own band
coverage, resonance family, conversion efficiency, phase-compensation range,
fabrication constraints, and qualification thresholds. It must be reported as
a Wang--Tsai-inspired square-template adaptation, not as a reproduction of the
2018 visible device.

## 4. Architecture ownership

| Fact or decision | Correct owner | Reason |
| --- | --- | --- |
| continuous operating band, fixed focus, NA, incident polarization, material/fabrication intent, explicit mechanism requirement/prohibition | aim-owned metalens Brief | these are user facts |
| PB base phase plus resonant spectral compensation and its applicability | metalens Method | this is the scientific way to establish the achromatic-focus claim |
| square x/y periodic boundaries, equal x/y span, supported primitive native shapes, normal-incidence/zeroth-order construction | Lumerical realization and its qualification | these are exact template abilities, not user intent |
| selection of that qualified square realization for a ready proof need | binding | late binding connects Method capability to the installed implementation |
| exact pitch, fixed height, bounded `(L,W)` geometries, design and holdout wavelength samples, Jones channels, exact work count | spectral CellStudyPlan | these are bounded planning facts |
| material samples over the full band, complex Jones coefficients, reference planes, convergence, phase unwrapping, conversion/leakage, physical rotation checks | admitted evidence | these are observed facts; forecasts and template names cannot substitute |
| one geometry and one orientation at every aperture site, unchanged with wavelength | spectral aperture-assignment Method output | this is the one physical device synthesized from the evidence |

This distribution preserves the established cadence:

```text
aim-owned Brief
  -> resolved Design and compiled Method
  -> bounded spectral CellStudyPlan
  -> late-bound square periodic realization
  -> observed spectral evidence
  -> one physical aperture assignment
  -> one exact Field per wavelength
  -> continuous-band Result.
```

No `lattice_kind = square` field is needed in the first Brief, Design, or
public template interface. The exact pitch remains a real physical design fact
and stays in the plan. Equal x/y periodicity must remain visible in realization
qualification and construction/evidence provenance so the square assumption
is audited rather than merely undocumented.

If a rectangular or hexagonal implementation is later added, that second real
adapter would justify a lattice capability/profile or a new Method
applicability decision. Adding an enum before that event would be speculative.

## 5. Minimum qualification evidence for the local-material adaptation

### 5.1 Spectral response qualification

For every bounded geometry, the evidence must retain:

1. exact square pitch, height, dimensions, material identities and dispersive
   samples covering the complete band without silent extrapolation;
2. ordered design and holdout wavelengths and one consistent complex phasor,
   normalization, output order, and reference-plane convention;
3. the full complex `2 x 2` linear-basis Jones transmission response from both
   input bases, not phase-only samples;
4. converted and retained circular-channel complex amplitudes, total power,
   cross-coupling/leakage, and energy-balance/convergence diagnostics;
5. a branch-coherent unwrapped converted phase versus `1/lambda`, with design
   residual and independent holdout residual against the compensation model;
6. the attainable compensation interval and gaps under the declared efficiency
   and leakage gates; and
7. the same physical pitch, height, geometry identity, and reference planes at
   every wavelength.

The original papers report phase and circular-conversion efficiency together,
and locate useful compensation between/among resonances rather than accepting
an arbitrary wrapped endpoint difference
([Wang et al. 2017, Fig. 2 and integrated-resonance discussion](https://www.nature.com/articles/s41467-017-00166-7#Fig2),
[Wang et al. 2018, Fig. 1](https://dsl.nju.edu.cn/litao/res/paper/Wang_SM-nnano_13_227%282018%29.pdf#page=2)).

### 5.2 PB-rotation qualification

The unrotated Jones matrix algebra predicts `+/-2 theta`, but the current
square periodic environment is only discretely, not continuously,
rotation-symmetric. The adapted binding should therefore add a **small
qualification set**, not a third production sweep axis:

- physically simulate representative anisotropic geometries at several
  orientations including neither 0 nor 90 degrees;
- include band endpoints, the reference wavelength, resonance-sensitive
  wavelengths, and independent holdout wavelengths;
- compare actual converted complex amplitude with
  `t_cross(g,lambda,0) exp(i s 2 theta)`;
- gate phase error, amplitude change, retained-channel change, and
  cross-coupling under an explicit response qualification profile; and
- refuse analytic orientation for geometry/band regions outside the qualified
  residual envelope.

This leaves production planning efficient: geometry x wavelength x two input
bases is planned once, while a bounded template/binding qualification proves
that continuous analytic rotations may be derived without solving every site
orientation. The repository already distinguishes caller-owned PB thresholds
for converted power, retained power, cross-coupling, and half-wave retardance
([PB qualification profile, lines 32--157](../../src/metacraft/science/metalens/geometric_phase.py)).

### 5.3 Device-transfer qualification

Periodic-cell evidence describes a homogeneous infinite array, while an
aperture places different resonant geometries and orientations next to each
other. Wang 2018 argues that high-index dielectric nanopillar fields are
strongly confined and neighbour interaction is weak, but that claim belongs
to its GaN geometry; it cannot be copied into a different local material stack
([Wang et al. 2018, PDF p. 228](https://dsl.nju.edu.cn/litao/res/paper/Wang_SM-nnano_13_227%282018%29.pdf#page=2)).

The minimal local-material adaptation should consequently validate
representative neighbour windows or phase-gradient supercells and one
tractable reduced device at design and holdout wavelengths. Failure narrows
the local Method's applicability or requires a future coupled/supercell
Method; it does not authorize the compiler to conceal the discrepancy.

## 6. Recommended first slice

1. Keep `square lattice` out of the Brief and do not add a lattice enum.
2. Keep one scalar exact pitch, one fixed height, and one physical device
   identity over the whole band.
3. Reuse the current rectangle-in-square or ellipse-in-square Jones route;
   choose one family only after the local material domain is formed.
4. Extend the bounded plan from one wavelength to explicit design/holdout
   spectral samples while retaining full x/y Jones channels.
5. Qualify physical rotations on a bounded subset before allowing the existing
   analytic orientation relation over the band.
6. Jointly choose geometry for inverse-wavelength compensation and orientation
   for the reference-wavelength PB phase, correcting for each geometry's
   observed phase intercept.
7. Form one immutable aperture and derive one exact single-wavelength Field at
   each evaluation wavelength; conclude only from the full spectral family.

The result is smaller than a configurable lattice framework and more honest
than treating the current single-wavelength template as already broadband:

```text
Method owns the PB + compensation physics.
Plan owns the bounded spectral investigation.
Template/binding owns the one square realization.
Evidence proves that this local material stack actually obeys both parts.
Brief owns none of those implementation answers.
```

## Primary-source register

- Shuming Wang et al., "Broadband achromatic optical metasurface devices,"
  *Nature Communications* 8, 187 (2017),
  [DOI 10.1038/s41467-017-00166-7](https://doi.org/10.1038/s41467-017-00166-7).
- Shuming Wang et al., "A broadband achromatic metalens in the visible,"
  *Nature Nanotechnology* 13, 227--232 (2018),
  [DOI 10.1038/s41565-017-0052-4](https://doi.org/10.1038/s41565-017-0052-4),
  [author-hosted article](https://dsl.nju.edu.cn/litao/res/paper/Wang_SM-nnano_13_227%282018%29.pdf),
  [official supplementary information](https://media.springernature.com/original/springer-static/esm/art%3A10.1038%2Fs41565-017-0052-4/MediaObjects/41565_2017_52_MOESM1_ESM.pdf).
- MetaCraft periodic template,
  [`src/metacraft/solvers/lumerical_fdtd/template/periodic.py`](../../src/metacraft/solvers/lumerical_fdtd/template/periodic.py).
- MetaCraft periodic science contract,
  [`src/metacraft/science/periodic_response.py`](../../src/metacraft/science/periodic_response.py).
- MetaCraft metalens bounded cell-study planner,
  [`src/metacraft/science/metalens/cell_study.py`](../../src/metacraft/science/metalens/cell_study.py).
- MetaCraft PB science,
  [`src/metacraft/science/metalens/geometric_phase.py`](../../src/metacraft/science/metalens/geometric_phase.py).
