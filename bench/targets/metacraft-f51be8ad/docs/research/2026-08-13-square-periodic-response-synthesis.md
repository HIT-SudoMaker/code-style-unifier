---
record_type: research_record
date: 2026-08-13
status: research_finding
authority_level: none
current_capability: false
---

# Square-periodic response synthesis without paper-geometry lock-in

## Research question

Can MetaCraft borrow the compensation-phase idea demonstrated by the Din Ping
Tsai team while deliberately standardizing the first implementation on a
square periodic lattice and a bounded geometry family? What is the smallest
complex spectral response fact needed for that route, how can it remain useful
for lenses, deflectors, and holographic reconstruction, and where does
periodic-cell evidence stop being authoritative?

This record uses original papers, publisher-hosted supplementary information,
and author-hosted manuscripts only. It selects no production route and adds no
current capability.

## Executive finding

Yes: **square periodic placement is compatible with PB orientation plus
resonant compensation**. Wang et al. 2017 already used unit elements with
550-nm periods along both `x` and `y`, anisotropic gold nanorods or coupled
nanorods, PB rotation, and an independently designed spectral compensation.
The square lattice was not the source of the PB phase; the anisotropic
cross-section was. The same paper used the building-block idea for both a
fixed-focus lens and an achromatic beam deflector
([Wang et al. 2017](https://doi.org/10.1038/s41467-017-00166-7)).

The terms that matter must therefore remain separate:

- a **square lattice** says where sites repeat;
- a **square unit-cell window** is a computational fundamental domain for that
  lattice;
- a **square aperture footprint** says where the finite device stops; and
- a **square pillar** says that the scatterer's in-plane cross-section has
  fourfold symmetry.

Only the last item conflicts with the ordinary continuously rotated PB
half-wave-plate route. A rectangular or elliptical pillar inside a square
periodic cell is the conservative combination. A perfect square pillar is
well suited to polarization-independent propagation/resonant phase, but its
fourfold symmetry removes the two unequal in-plane eigenchannels that the
usual PB conversion requires. Rotating that square pillar is therefore not a
continuous PB control knob. This conclusion follows from the PB requirement
for a rotated birefringent element and the published use of square posts for
scalar propagation phase; it is not a claim that every possible chiral,
multilayer, or lattice-coupled `C4` structure is incapable of geometric phase
([Mueller et al. 2017](https://doi.org/10.1103/PhysRevLett.118.113901),
[Arbabi et al. 2020](https://doi.org/10.1038/s41598-020-64198-8)).

The most reusable architecture is correspondingly small:

```text
target-specific optics
  -> desired complex aperture transfer T(x, y, lambda)
  -> one target-independent surface assignment
  -> one qualified square-periodic complex-response library
  -> geometry + orientation at each lattice site
```

Fixed-focus achromatization, achromatic deflection, and holographic field
reconstruction should differ in how they synthesize the desired aperture
transfer and how their terminal result is judged. They should not create three
different cell-library abstractions or reproduce three published geometries.

## 1. What the Tsai-team demonstrations actually used

### 1.1 Wang 2017: square lattice, square cell window, anisotropic rods

The reflective near-IR work separates the required phase into a wavelength-
independent base term supplied by geometric phase and a term linear in
`1 / lambda` supplied by the spectral response of an integrated-resonant unit
element. The paper states that those two mechanisms can be combined and then
demonstrates a lens and a constant-angle deflector from the same design
principle ([article, equations 1--5 and Figs. 1--5](https://www.nature.com/articles/s41467-017-00166-7)).

Its physical hierarchy is:

| Concept | Wang 2017 fact |
|---|---|
| Periodic lattice | Equal 550-nm periods along `x` and `y`: a square Bravais lattice. |
| Unit-cell window | A 550 nm by 550 nm periodic computational domain is the natural primitive parallelogram implied by those periods. This is a simulation-domain inference, not a second physical object. |
| Meta-atom cross-section | One or several rectangular gold nanorods; high-compensation members include perpendicular coupled rods. The rods are 30 nm thick over a 60-nm SiO2 spacer and Au reflector. |
| PB control | The anisotropic resonant element is physically oriented; its orientation supplies geometric phase in the converted circular-polarization channel. |
| Resonant compensation | Rod lengths, widths, gaps, and coupled resonances change the smooth phase slope between resonances. |
| Aperture footprint | A finite circular metalens, reported with a 55.55-um diameter for the NA 0.268 example. It is independent of the square microscopic lattice. |

The 550-nm `x/y` periods, rod construction, and 30/60-nm layer thicknesses are
reported with Fig. 2; the unit-cell simulation uses periodic-array conditions
([Wang et al. 2017, Results and Methods](https://www.nature.com/articles/s41467-017-00166-7#Sec9)).
This is direct primary-source evidence that **square lattice + PB orientation +
resonant compensation is not an internally inconsistent platform**.

### 1.2 Wang 2018: not square-periodic and not square pillars

The visible transmissive realization changed the physical implementation. Its
author-supplied supplementary information says that the GaN structures occupy
a subwavelength **hexagonal lattice** with lattice constant 120 nm and fixed
height 800 nm. The illustrated per-site region is hexagonal; an equivalent
numerical primitive cell may be represented by a rhombic parallelogram. Neither
representation is a pillar cross-section
([official Supplementary Section 1 and Fig. S1](https://media.springernature.com/original/springer-static/esm/art%3A10.1038%2Fs41565-017-0052-4/MediaObjects/41565_2017_52_MOESM1_ESM.pdf)).

The scatterers themselves are anisotropic:

- compensation below 1050 degrees uses solid rectangular GaN nanopillars with
  varying length `Lp` and width `wp`;
- compensation above 1050 degrees uses the complementary inverse family, a
  rectangular aperture with length `LB` and width `wB` in a GaN region; and
- the library contains 17 members, sampled in 30-degree compensation steps,
  with complex RCP-to-LCP conversion efficiency and phase spectra.

Those are the shapes drawn and tabulated in the official supplement, not
square pillars. The main paper reports circularly polarized operation over
400--660 nm and attributes the total phase to the combined orientation and
IRUE response ([Wang et al. 2018](https://doi.org/10.1038/s41565-017-0052-4)).

### 1.3 Consequence for MetaCraft

Borrowing the **method** does not require reproducing either physical stack.
The transferable statement is:

```text
one anisotropic local transfer operator
  = geometry-controlled spectral response
  + orientation-controlled geometric phase
```

The gold coupled-rod family, GaN solid/inverse transition, their pitch, and
their exact compensation table are implementations of that statement. They
are not part of its reusable Interface. A MetaCraft first slice may therefore
fix one material stack, one square lattice, one height, and one bounded
rectangular-pillar family, then determine its own spectral response by the
declared solver. Calling that result "Wang 2018 reproduced" would be false;
calling it "compensation-phase method inspired by Wang et al." would be
accurate.

## 2. Square lattice does not mean square pillar

### 2.1 Four independent shapes

| Term | Owns | Does not imply |
|---|---|---|
| **Square lattice** | two orthogonal equal-length translation vectors `(p, 0)` and `(0, p)` | square scatterers or a square finite device |
| **Square unit-cell window** | one `p x p` computational fundamental domain with periodic/Bloch sides | a material boundary at the window edge |
| **Square aperture footprint** | the finite set of active lattice sites | square cells or square scatterers |
| **Square pillar** | a `C4` in-plane material cross-section with equal side lengths | square placement lattice |

This vocabulary matters because the user's intended restriction is most useful
when it constrains the first two rows. It becomes physically incompatible with
ordinary PB rotation if it also constrains the fourth.

### 2.2 Why rectangular-in-square is the minimal PB-capable family

The ordinary PB implementation treats a meta-atom as a rotated birefringent
waveplate. Its two principal axes have different complex responses; rotating
those axes by `theta` gives the cross-helicity term a phase of `+/- 2 theta`.
Published dielectric platforms use elliptical or rectangular posts for this
reason. Mueller et al. arranged elliptical TiO2 pillars on a **square lattice**
and used their shape birefringence plus orientation for independent
polarization holograms
([Mueller et al. 2017](https://doi.org/10.1103/PhysRevLett.118.113901)).
Arbabi et al. likewise use elliptical high-contrast nanoposts for complete
phase and polarization control
([Arbabi et al. 2015](https://doi.org/10.1038/nnano.2015.186)).

By contrast, Arbabi et al. 2020 use square-cross-section posts of varying width
on a square lattice to obtain a scalar complex transmission curve spanning
`2 pi`; that control is propagation/resonant phase, not orientation PB phase
([Fig. 1 and accompanying text](https://www.nature.com/articles/s41598-020-64198-8#Fig1)).
Combining these primary facts with the `C4` symmetry of a perfect square gives
the architectural rule:

- `L != W` rectangular pillars may qualify for PB conversion and spectral
  compensation;
- `L = W` is a degenerate, polarization-isotropic member at normal incidence
  and must not be assigned a continuous PB orientation;
- square pillars may still form a separate propagation/resonant-phase family;
  they should not silently satisfy a PB method profile.

The bounded first geometry family can consequently be just
`(length, width, orientation)` with pitch, height, material stack, corner
model, and fabrication clearances fixed by the study. Bounds must be enforced
after rotation so a long rectangle never violates the minimum gap to the
square cell window or its neighbours.

## 3. Minimum viable complex spectral response

### 3.1 Full scattering object versus first-slice fact

A general periodic structure can scatter between sides, polarizations, and
Floquet orders as a function of frequency and in-plane wavevector. Storing
that whole object from day one would create mostly unused axes.

For the proposed normal-incidence, local, transmissive first slice, the
smallest durable evidence tensor is

```text
J[g, lambda, q_out, q_in] in C

g       = bounded geometry identity at one canonical orientation
lambda  = explicit design or holdout wavelength sample
q_in    = one of two transverse polarization basis states
q_out   = one of two transverse polarization basis states
```

`J[g, lambda]` is therefore one complex `2 x 2` Jones transmission matrix per
geometry and wavelength. Rubin et al. show why a spatially varying `2 x 2`
Jones transfer is the natural common object for polarization-dependent
holographic fields, with its four elements propagated independently
([Rubin et al. 2021](https://doi.org/10.1126/sciadv.abg7488)). The same matrix
contains the converted and retained circular-polarization channels reported by
the Tsai-team papers, instead of retaining phase while discarding leakage.

For an exactly mirror-symmetric rectangular pillar at its canonical
orientation, synthesis may reduce the matrix internally to the two complex
principal-axis coefficients `t_u(lambda)` and `t_v(lambda)`. The evidence
record should still retain the solver-observed `2 x 2` matrix: its nominally
zero cross terms are a check of the assumed symmetry, not data to erase.

### 3.2 Conditions that are required now but are not tensor axes

The response is meaningful only when the following are bound into the
observation identity:

- square lattice vectors and pitch;
- material stack, dispersive material versions, geometry and height;
- incidence side, selected output side, and propagation direction;
- normal incidence (`k_parallel = 0`), including the polarization basis;
- selected zeroth Floquet order `(0, 0)`;
- field normalization, complex phasor convention, and reference planes; and
- solver, mesh/convergence settings, and wavelength grid identity.

These facts must not be implicit. They are fixed coordinates of the first
experiment rather than variable tensor axes.

### 3.3 YAGNI axes for the first slice

Do **not** initially add dense axes for:

- polar and azimuthal incidence angles or arbitrary `k_parallel`;
- both reflection and transmission sides in one universal tensor;
- every propagating and evanescent diffraction order;
- arbitrary input/output media and multilayer cascades;
- neighbouring-cell identities, supercell topology, temperature, or random
  fabrication perturbations; or
- near-field voxels throughout the unit cell.

Before accepting the zero-order fact, the study must demonstrate that unwanted
propagating orders are closed over the declared band and media, or explicitly
measure their power. If the application later introduces oblique incidence,
multi-order metagratings, or reflection/transmission co-design, that creates a
new qualified scattering experiment. It should not retroactively make every
first-slice call learn an enormous optional Interface.

High output NA alone is not a reason to precompute a dense incidence-angle
axis. It is a reason to validate the local approximation with representative
phase-gradient gratings or neighbourhoods. Arbabi et al. show that the usual
local coefficient also assumes an angularly benign element radiation pattern;
the approximation worsens at large deflection angles
([Arbabi et al. 2020](https://doi.org/10.1038/s41598-020-64198-8)).

## 4. Target-independent response, target-specific synthesis

### 4.1 One common aperture fact

The reusable object is a desired complex aperture transfer

```text
T_target(x, y, lambda) in C^(2 x 2)
```

or a scalar/polarization-channel restriction of it. Target generators produce
this fact; the response library does not know why it was requested. One
surface-assignment implementation selects `(geometry, orientation)` at each
square-lattice site to minimize a declared complex residual over wavelength,
amplitude, phase, conversion, leakage, and fabrication constraints.

This is the deeper seam because deleting it would force response matching,
phase gauges, spectral weights, and manufacturing constraints back into every
kind of target. By contrast, a separate `AchromaticLensLibrary`,
`DeflectorLibrary`, and `HologramLibrary` would be three shallow copies of the
same knowledge.

### 4.2 How the three targets differ

- **Fixed-focus achromatization:** the target generator emits the hyperbolic
  aperture phase at every wavelength, plus a common spectral gauge. The
  compensation-phase idea informs the target and matching objective; it does
  not prescribe gold rods or solid/inverse GaN geometries.
- **Achromatic beam deflection:** the target generator emits a wavelength-
  dependent linear phase ramp for a constant output angle. Wang 2017 is direct
  evidence that the same compensation principle and unit-element idea can
  serve lens and deflector targets
  ([Wang et al. 2017, gradient metasurface](https://www.nature.com/articles/s41467-017-00166-7#Fig5)).
- **Holographic field reconstruction:** an inverse propagation method emits a
  complex scalar or Jones aperture transfer whose propagated field matches the
  requested image/vector field. Rubin et al. express the far-field Jones
  response as the Fourier transform of the spatial Jones mask
  ([Rubin et al. 2021](https://doi.org/10.1126/sciadv.abg7488)).

The terminal evaluator remains target-specific: focal shift and PSF are not
deflection efficiency or image fidelity. Reuse belongs below that judgment,
at the aperture-transfer and response-assignment seam.

## 5. Authority limits of local periodic-cell evidence

### 5.1 What a periodic-cell observation actually proves

A local periodic observation proves the complex response of an **infinite
homogeneous array of copies of one cell** under its declared excitation and
normalization. The common library approximation assigns that response to the
same geometry when it is surrounded by different neighbours in an aperiodic
device.

Arbabi et al. identify the two assumptions explicitly: neighbour-induced
coupling changes are ignored, and the meta-atom radiation pattern is treated
as sufficiently angle independent. The conditions are best for gradual
geometry variation, weak coupling, and small deflection angles; they worsen
for high NA and rapid phase gradients
([Arbabi et al. 2020](https://doi.org/10.1038/s41598-020-64198-8)).

Gigli et al. show that lookup-table behaviour can fail for strongly coupled
ultrathin dielectric resonators, and that even square and hexagonal arrays of
the same resonators can exhibit materially different phase and transmission;
high-aspect-ratio waveguide-like elements are the safer local regime
([Gigli et al. 2020](https://doi.org/10.1038/s41524-020-00369-5)).

### 5.2 Neighbour, nonlocal, and supercell evidence are different claims

Three escalation levels must not be conflated:

1. **Local periodic cell:** one geometry repeated indefinitely; appropriate
   for the base spectral library.
2. **Neighbourhood or phase-gradient supercell:** the actual sequence of
   several assigned geometries is solved together; appropriate for checking
   coupling and large local gradients.
3. **Nonlocal/supercell design:** coupling and multiple diffraction orders are
   intentional design degrees of freedom. The supercell, its orders, and its
   inlay are the response-bearing object.

Piccardo et al. show that local subwavelength cells neglect intercell coupling,
whereas supercells redistribute power through coupling and control complex
amplitude and polarization independently in multiple orders. They also state
that supercell size determines the orders that must be considered
([Piccardo et al. 2021](https://doi.org/10.1038/s41467-021-24071-2)).
That is a different scientific method, not an optional flag on a local-cell
record.

### 5.3 Required validation ladder

The square-periodic first slice should fail closed through this ladder:

1. **Cell convergence:** mesh/basis convergence, energy balance, reference-
   plane stability, and design/holdout wavelength agreement for the complex
   `2 x 2` response.
2. **Rotation check:** for a selected subset, simulate physical orientations
   and compare the converted-channel phase/amplitude with the Jones-rotation
   prediction. Do not assume exact `2 theta` behaviour from geometry labels.
3. **Neighbourhood check:** solve representative windows containing the actual
   assigned adjacent geometries, including high spectral-residual and
   high-phase-gradient regions.
4. **Gradient check:** compare representative periodic blazed gratings or
   supercells against the local assignment, especially at the largest target
   deflection angle/NA.
5. **Device check:** compare a tractable reduced or full-device Maxwell solve
   with the synthesized exit field and terminal optical metrics at both design
   and holdout wavelengths.

If neighbourhood or device residuals exceed a declared threshold, the result
is not "a slightly worse local cell." The local response evidence is
inapplicable to that region. The route must narrow its geometry/gradient
bounds or explicitly promote the response-bearing object to a neighbourhood
or supercell.

## 6. Domain vocabulary

- **Lattice** — the infinite set of allowed site positions generated by two
  in-plane translation vectors.
- **Cell window** — a chosen computational fundamental domain of the lattice;
  its drawn shape is not a material cross-section.
- **Aperture footprint** — the finite set or spatial support over which lattice
  sites are populated in one device.
- **Scatterer cross-section** — the in-plane material shape at a site, before
  orientation is applied.
- **Bounded geometry family** — the finite, constraint-qualified parameter
  domain from which scatterer identities may be selected.
- **Orientation** — a physical in-plane rotation of an anisotropic scatterer;
  it is not a synonym for phase.
- **Periodic-cell observation** — one solver-derived response for a homogeneous
  infinite periodic array under a fully declared excitation.
- **Complex spectral response** — the wavelength-indexed complex Jones matrix
  for a selected side, order, and reference plane.
- **Response library** — qualified geometry identities and their periodic-cell
  observations; it is target-independent.
- **Aperture target** — the desired spatial and spectral complex transfer
  before assignment to fabricable geometries.
- **Surface assignment** — the evidence-bearing mapping from an aperture target
  to a geometry and orientation at every populated lattice site.
- **Neighbourhood evidence** — a multi-cell solve used to test whether a local
  periodic observation transfers to its actual neighbours.
- **Supercell response** — a coupled, multi-order response whose supercell is
  itself the design object; it is not a local-cell response with more samples.

## 7. Architecture facts

1. Square placement, square computational window, square finite aperture, and
   square pillar are four independent decisions.
2. Square lattice is already compatible with the Tsai-team compensation-phase
   principle; Wang 2017 is the direct precedent.
3. Ordinary continuous PB control requires an anisotropic scatterer. The
   conservative first family is rectangular-in-square, not square-in-square.
4. The published geometry is not part of the reusable method. MetaCraft should
   establish its own bounded family and solver evidence.
5. One target-independent complex response library should serve all aperture
   targets that share its physical experiment.
6. The minimum durable response tensor is
   `geometry x wavelength x 2 output polarizations x 2 input polarizations`
   for one selected side and zeroth order at normal incidence.
7. Angle, arbitrary ports, all Floquet orders, neighbourhoods, and near fields
   are not first-slice tensor axes. Their fixed conditions or exclusions must
   nevertheless be explicit.
8. A local periodic observation is an approximation when transferred into an
   aperiodic device. Its applicability is a qualified claim, not a default.
9. Nonlocal or multi-order supercell design is a separate future method and
   must not complicate the local first route in advance.

## 8. Recommended first slice

1. Fix one transmissive material stack, height, square pitch, normal incidence,
   circular-polarization convention, and subwavelength zero-order band.
2. Use one bounded rectangular pillar family `(L, W)` inside the square cell;
   keep orientation separate and enforce rotated minimum-gap constraints.
3. Record the full complex `2 x 2` zeroth-order Jones transmission matrix for
   every geometry on design wavelengths and independent holdout wavelengths.
4. Qualify spectral smoothness, amplitude, leakage, PB rotation, interpolation,
   and periodic-solver convergence before creating a response library.
5. Let one aperture-target synthesizer express the Wang-inspired fixed-focus
   compensation phase, then let one surface assignment choose geometry and
   orientation jointly across the band.
6. Validate representative neighbour windows, the steepest phase-gradient
   regions, and a tractable full/reduced device before claiming achromaticity.
7. Reuse the same library and assignment for a constant-angle deflector as the
   first architectural generality check. Defer holographic reconstruction until
   the two deterministic targets have closed the shared seam.

This slice is deliberately narrower than a paper reproduction and deeper than
a lens-specific workflow. It tests exactly the reusable claim: **one qualified
square-periodic response family can compile more than one spectral aperture
target without changing its Interface**.

## 9. Open human decisions

1. Does "square periodic structure" mean the recommended square lattice and
   square cell window, or does it also require a square pillar? If it requires
   the latter, the ordinary PB-orientation route must be removed and the method
   reframed as propagation/resonant dispersion engineering.
2. What material stack and wavelength band define the first physical
   experiment? Pitch and order closure cannot be decided independently of
   these facts.
3. Is the first route transmissive or reflective? The response library should
   bind one, not expose a universal optional port Interface.
4. Is circular-polarization conversion an explicit requirement? The answer
   fixes the basis, efficiency definition, leakage limits, and orientation
   qualification.
5. What numerical thresholds close the five-step validation ladder, especially
   neighbourhood transfer and holdout-wavelength residuals?
6. After the fixed-focus proof, should the second proof be the Wang-like
   constant-angle deflector (recommended) or should holographic reconstruction
   enter immediately with its larger inverse-design and evaluation surface?

## Primary-source register

- Shuming Wang et al., "Broadband achromatic optical metasurface devices,"
  *Nature Communications* 8, 187 (2017),
  [DOI 10.1038/s41467-017-00166-7](https://doi.org/10.1038/s41467-017-00166-7).
- Shuming Wang et al., "A broadband achromatic metalens in the visible,"
  *Nature Nanotechnology* 13, 227--232 (2018),
  [DOI 10.1038/s41565-017-0052-4](https://doi.org/10.1038/s41565-017-0052-4),
  [official supplementary information](https://media.springernature.com/original/springer-static/esm/art%3A10.1038%2Fs41565-017-0052-4/MediaObjects/41565_2017_52_MOESM1_ESM.pdf).
- J. P. Balthasar Mueller et al., "Metasurface Polarization Optics:
  Independent Phase Control of Arbitrary Orthogonal States of Polarization,"
  *Physical Review Letters* 118, 113901 (2017),
  [DOI 10.1103/PhysRevLett.118.113901](https://doi.org/10.1103/PhysRevLett.118.113901).
- Amir Arbabi et al., "Dielectric metasurfaces for complete control of phase
  and polarization with subwavelength spatial resolution and high
  transmission," *Nature Nanotechnology* 10, 937--943 (2015),
  [DOI 10.1038/nnano.2015.186](https://doi.org/10.1038/nnano.2015.186),
  [author record](https://authors.library.caltech.edu/records/kv58m-mcb25).
- Ehsan Arbabi et al., "Increasing efficiency of high numerical aperture
  metasurfaces using the grating averaging technique," *Scientific Reports*
  10, 7124 (2020),
  [DOI 10.1038/s41598-020-64198-8](https://doi.org/10.1038/s41598-020-64198-8).
- G. Gigli et al., "Inverse design of metasurfaces with non-local
  interactions," *npj Computational Materials* 6, 55 (2020),
  [DOI 10.1038/s41524-020-00369-5](https://doi.org/10.1038/s41524-020-00369-5).
- Giuseppe Piccardo et al., "Multifunctional wide-angle optics and lasing based
  on supercell metasurfaces," *Nature Communications* 12, 3670 (2021),
  [DOI 10.1038/s41467-021-24071-2](https://doi.org/10.1038/s41467-021-24071-2).
- Noah A. Rubin et al., "Jones matrix holography with metasurfaces,"
  *Science Advances* 7, eabg7488 (2021),
  [DOI 10.1126/sciadv.abg7488](https://doi.org/10.1126/sciadv.abg7488),
  [author-hosted paper](https://projects.iq.harvard.edu/files/capasso/files/eabg7488.full_.pdf).
