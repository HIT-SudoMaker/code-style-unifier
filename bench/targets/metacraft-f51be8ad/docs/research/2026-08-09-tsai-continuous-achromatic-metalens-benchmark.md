---
record_type: research_record
date: 2026-08-09
status: research_finding
authority_level: none
current_capability: false
---

# Tsai-group continuous-achromatic metalens lineage and benchmark readiness

## Research question

Which Din Ping Tsai-group paper is the intended “continuous achromatic”
metalens method, what did it actually demonstrate, and would it make a sound
fifth `MetalensBenchmarkCase` after MetaCraft's four monochromatic cases?

This record uses only the original publisher articles, an author-hosted copy of
the published 2018 article, the official 2018 supplementary information, and
the repository's own source and decisions. It selects no case and changes no
capability.

## Executive finding

The year ambiguity has a precise two-paper answer:

1. **The continuous-band design principle is the 2017 paper.** Shuming Wang,
   Pin Chieh Wu, Vin-Cent Su, Yi-Chieh Lai, Cheng Hung Chu, Jia-Wern Chen,
   Shen-Hung Lu, Ji Chen, Beibei Xu, Chieh-Hsiung Kuan, Tao Li, Shining Zhu,
   and Din Ping Tsai, “Broadband achromatic optical metasurface devices,”
   *Nature Communications* 8, 187 (2017), DOI
   [10.1038/s41467-017-00166-7](https://doi.org/10.1038/s41467-017-00166-7).
   It formulates the spatial phase as a wavelength-independent geometric-phase
   term plus a resonant phase-compensation term linear in `1 / wavelength`, and
   experimentally demonstrates continuous-band reflective near-infrared
   devices from 1200 to 1680 nm.
2. **The strongest paper-exact reference is the 2018 visible implementation.** Shuming
   Wang, Pin Chieh Wu, Vin-Cent Su, Yi-Chieh Lai, Mu-Ku Chen, Hsin Yu Kuo,
   Bo Han Chen, Yu Han Chen, Tzu-Ting Huang, Jung-Hsi Wang, Ray-Ming Lin,
   Chieh-Hsiung Kuan, Tao Li, Zhenlin Wang, Shining Zhu, and Din Ping Tsai,
   “A broadband achromatic metalens in the visible,” *Nature Nanotechnology*
   13, 227–232 (2018), DOI
   [10.1038/s41565-017-0052-4](https://doi.org/10.1038/s41565-017-0052-4).
   It carries the 2017 principle into a fabricated transmissive GaN platform
   spanning 400–660 nm. The publication date is 29 January 2018; the DOI's
   `2017` segment is not the publication year
   ([publisher record, lines 13–35 and 349–363](https://www.nature.com/articles/s41565-017-0052-4)).

The 2018 device is scientifically strong as a possible fifth benchmark because it adds
an axis the four monochromatic cases do not test: **one spatial layout must
match phase and polarization response over a wavelength band, not merely at
one wavelength**. It is not currently executable as an exact MetaCraft case.
The blocking gaps include materials, but also geometry, response evidence,
solver orchestration, brief semantics, aperture assignment, and spectral
conclusion semantics.

### Current scope disposition

This record preserves the scientific discussion; it does **not** select or
schedule a fifth benchmark. The current programme stops at the four
single-wavelength McClung, Yang, Arbabi, and Khorasaninejad briefs before
periodic-cell evidence. No achromatic brief type, claim, method, capability,
material registration, lattice, template, solver orchestration, or placeholder
test follows from this record.

If achromatic work is reconsidered later, MetaCraft may borrow the continuous
phase-compensation principle while selecting a feasible MetaCraft-owned cell
family. The paper's GaN solid/inverse IRUEs and hexagonal lattice remain
reference facts, not mandatory implementation requirements. Such a future
design is method-inspired and must not claim exact reproduction.

## 1. The 2017 continuous-band design principle

### 1.1 Physical phase contract

For radial coordinate `R` and fixed focal length `f`, the ideal lens phase is

```text
phi(R, wavelength)
  = -2 pi [sqrt(R^2 + f^2) - f] / wavelength.
```

The paper rewrites this relative to the longest wavelength:

```text
phi_lens(R, wavelength)
  = phi(R, wavelength_max) + delta_phi(R, wavelength)

delta_phi(R, wavelength)
  = -2 pi [sqrt(R^2 + f^2) - f]
      (1 / wavelength - 1 / wavelength_max).
```

The first part is independent of the working wavelength and is supplied by
Pancharatnam–Berry geometric phase. The second varies linearly with
`1 / wavelength` and is supplied by the phase dispersion of an
integrated-resonant unit element (IRUE)
([2017 article, equations 1–3 and explanation](https://www.nature.com/articles/s41467-017-00166-7#Sec3)).

An aperture-wide phase offset may be added without changing focusing:

```text
phi_lens_prime(R, wavelength)
  = phi(R, wavelength) + phi_shift(wavelength)

phi_shift(wavelength) = alpha / wavelength + beta.
```

The paper parameterizes `alpha` and `beta` using the band endpoints and a
largest additional phase shift `chi`. This offset changes the attainable
phase-compensation range and therefore constrains device diameter
([2017 article, equation 4 and following paragraph](https://www.nature.com/articles/s41467-017-00166-7#Sec3)).

This is the intended meaning of **continuous achromatic**: the unit response
is designed to follow a smooth, approximately linear phase law against
`1 / wavelength`; it is not an interpolation claim made from a few unrelated
single-wavelength layouts.

### 1.2 2017 implementation and measurements

| Fact | Primary-source result |
| --- | --- |
| band and scheme | 1200–1680 nm, circularly polarized incidence, reflection |
| demonstrated metalens | NA `0.268`, diameter `55.55 um`, focal length `100 um` |
| unit cell | one or several 30-nm-thick gold nanorods; period `550 nm` in x and y |
| stack | `30 nm` Au rods on `3 nm` Cr / `60 nm` SiO2 spacer / `150 nm` Au mirror on `3 nm` Cr / Si |
| degrees of freedom | rod length, width, gap, count, relative placement, and in-plane rotation |
| response | RCP-to-LCP conversion efficiency and phase; resonances positioned so the inter-resonance phase is smooth against `1 / wavelength` |
| simulation | CST Microwave Studio; periodic unit-cell response; the reported lens calculation uses PML in x and periodic boundary in y and therefore models a cylindrical lens |
| fabrication | electron-beam lithography, metal deposition, lift-off; fabricated and optically measured |
| performance | nearly fixed focal plane across the band; operation efficiency on the order of `12%` |

The geometry and device values are reported in Fig. 2 and the characterization
section
([2017 article, unit construction and period](https://www.nature.com/articles/s41467-017-00166-7#Fig2),
[device size](https://www.nature.com/articles/s41467-017-00166-7#Sec5)).
The Methods name CST and the boundary conditions
([2017 article, Numerical simulation](https://www.nature.com/articles/s41467-017-00166-7#Sec9)).
The reported efficiency is the focal-spot intensity divided by the intensity
reflected by a metallic mirror with the same pixel size, not MetaCraft's
present Airy-radius incident-power metric
([2017 article, Fig. 4 caption](https://www.nature.com/articles/s41467-017-00166-7#Fig4)).

The 2017 article is the normative theory source, but it is a poor exact fifth
case for the current transmission-oriented workflow: it adds reflection,
metal loss, a metal–dielectric–metal stack, compound resonators, and a
cylindrical-lens simulation convention before testing the desired visible
achromatic workflow.

## 2. The 2018 visible transmissive realization

### 2.1 Paper-locked device facts

The selected object should be the fabricated metalens with `NA = 0.106` and
designed focal length `235 um`, not an average over the three NA variants and
not the separate chromatic control.

| Fact | Primary-source result |
| --- | --- |
| wavelength band | `400–660 nm`; central wavelength `530 nm`; stated fractional bandwidth about `49%` |
| phase mechanism | wavelength-independent PB phase plus wavelength-dependent integrated-resonance compensation |
| polarization channel | circular input with opposite-helicity converted output (RCP-to-LCP response is plotted) |
| focal length | `235 um` |
| numerical aperture | `0.106` |
| aperture diameter | not quoted in accessible text; about `50.1 um` only if derived from `D = 2 f NA / sqrt(1 - NA^2)` in air |
| atom material | un-doped GaN |
| substrate | Al2O3 / double-polished sapphire |
| atom height | `800 nm` |
| lattice | subwavelength periodic hexagonal lattice, constant `120 nm` |
| atom families | solid GaN nanopillars and inverse/Babinet GaN structures |
| library | 17 IRUEs spanning `660–1140 degrees` phase compensation in `30-degree` intervals |
| varying dimensions | solid features `w_p`, `L_p`; inverse features `w_B`, `L_B`; exact values are tabulated in Supplementary Tables 1–2 |
| fabrication | MOCVD GaN on sapphire; EBL; SiO2/Cr hard masks; RIE and ICP-RIE; fabricated and measured |

The author-hosted published article states the band, GaN platform, solid and
inverse unit families, PB/IRUE split, `f = 235 um`, and `NA = 0.106`
([published PDF, pp. 227–230](https://dsl.nju.edu.cn/litao/res/paper/Wang_SM-nnano_13_227%282018%29.pdf)).
The official supplementary information fixes the `120 nm` hexagonal lattice,
`800 nm` height, 17-member response library, sapphire substrate, and
fabrication sequence
([Supplementary Information, Sections 1–2](https://media.springernature.com/original/springer-static/esm/art%3A10.1038%2Fs41565-017-0052-4/MediaObjects/41565_2017_52_MOESM1_ESM.pdf)).

The `120 nm` value is not a feature width or gap inferred from a diagram.
Supplementary Fig. 1 states, “in a subwavelength periodic hexagonal lattice
(the lattice constant p is 120 nm).” The following sentence separately fixes
the GaN height at `800 nm`, and the next sentence separately names `w_p`,
`L_p`, `w_B`, and `L_B` as the varying feature sizes
([official Supplementary Information, Supplementary Fig. 1 caption, PDF p. 3](https://media.springernature.com/original/springer-static/esm/art%3A10.1038%2Fs41565-017-0052-4/MediaObjects/41565_2017_52_MOESM1_ESM.pdf#page=3)).

The full per-IRUE values in Supplementary Tables 1–2 are image-rendered rather
than machine-readable in the accessible extraction. They remain
**unresolved for a future encoded case** and must not be reconstructed by eye
or filled from a review. The paper says supporting data are available from
the corresponding author on reasonable request
([published PDF, Data availability](https://dsl.nju.edu.cn/litao/res/paper/Wang_SM-nnano_13_227%282018%29.pdf#page=5)).

### 2.2 Design and numerical method

The 2018 phase law is the 2017 law with the global inverse-wavelength offset:

```text
phi_AL(r, wavelength)
  = -2 pi [sqrt(r^2 + f^2) - f] / wavelength
    + phi_shift(wavelength)

phi_shift(wavelength) = a / wavelength + b.
```

It is then separated into:

```text
basic phase at wavelength_max
  -> supplied by PB rotation

wavelength-dependent phase compensation
  -> supplied by the selected solid or inverse GaN IRUE.
```

The atom choice and orientation are therefore coupled outputs at each spatial
site: the IRUE identity realizes the required dispersion; its rotation
realizes the basic phase. The paper attributes the wide compensation range to
multiple waveguide-like cavity resonances in the `800 nm` GaN structures
([published PDF, Fig. 1 and equations 1–2](https://dsl.nju.edu.cn/litao/res/paper/Wang_SM-nnano_13_227%282018%29.pdf#page=2)).

The accessible paper and supplementary information report numerical design
and simulated conversion/phase spectra, but do **not** identify the simulator,
discretization, boundary conditions, mesh, material-dispersion source, or
optimization/search algorithm. Those facts are unresolved. It would be an
unsupported inference to copy the 2017 paper's CST setup into the 2018 case.

### 2.3 Reported performance and measure definitions

| Observation | Paper result | Benchmark disposition |
| --- | --- | --- |
| focal position | brightest spots remain near `235 um` from `400–660 nm`; three NA variants show nearly unchanged focal length | useful spectral target, but no numerical flatness tolerance or raw series is published in accessible text |
| focusing efficiency | maximum up to `67%`; average about `40%` over the full band | definition partially comparable; focal integration boundary remains unspecified |
| efficiency definition | focused circularly polarized beam power divided by incident-beam power with opposite helicity | preserve exact channel wording; do not replace it with total transmitted power or MetaCraft's Airy bucket |
| replication | every Fig. 3b point averages four samples; error bars are their standard deviation | valid experimental context |
| focal width | measured FWHM close to the paper's diffraction value `wavelength / (2 NA)` | qualitative spectral comparison unless plot data are digitized under a separate evidence decision |
| imaging | USAF lines about `2.19 um` resolved; full-colour images shown with explicit colour correction | context only for a focusing benchmark |

These definitions and values appear in the performance section and Fig. 3
caption
([published PDF, pp. 229–230](https://dsl.nju.edu.cn/litao/res/paper/Wang_SM-nnano_13_227%282018%29.pdf#page=3)).

## 3. Do not confuse it with the adjacent Capasso paper

Wei Ting Chen et al., “A broadband achromatic metalens for focusing and
imaging in the visible,” *Nature Nanotechnology* 13, 220–226 (2018), DOI
[10.1038/s41565-017-0034-6](https://doi.org/10.1038/s41565-017-0034-6), is
an adjacent but different work. It is a Federico Capasso-group paper, not a
Din Ping Tsai-group paper. Its design controls phase, group delay, and group
delay dispersion with TiO2 nanofins, covers 470–670 nm, and reports `NA = 0.2`
and about `20%` efficiency at 500 nm
([publisher abstract](https://www.nature.com/articles/s41565-017-0034-6)).

The distinction matters architecturally:

```text
Tsai lineage
  PB basic phase + IRUE phase compensation linear in 1 / wavelength
  solid and inverse GaN units

Capasso lineage
  simultaneous phase + group delay + group-delay-dispersion matching
  TiO2 nanofin library
```

Both are valid achromatic methods. Only the first matches the user's named
team and intended continuous-achromatic lineage.

## 4. MetaCraft readiness audit

### 4.1 Why this is a sound fifth benchmark

The current four cases exercise the monochromatic matrix
`low/high NA x propagation/geometric phase`. Wang 2018 should not be described
as merely a fifth point in that matrix. It adds a new longitudinal axis:

```text
one wavelength
  -> one cell response
  -> one aperture field
  -> one focus

wavelength band
  -> one jointly selected dispersive cell library
  -> one exact field per wavelength
  -> one spectral focus family
  -> one achromatic conclusion
```

It is consequently a strong paper-facing benchmark for whether MetaCraft can
move from monochromatic metalens design to evidence-backed spectral design
without duplicating its lifecycle.

### 4.2 Paper-exact capability gaps, not current requirements

| Gap owner | Minimum capability | Current evidence |
| --- | --- | --- |
| material library | reviewed GaN and Al2O3/sapphire bindings whose native samples cover the entire 400–660 nm band without extrapolation | neither family exists in [`materials/lumerical.toml`](../../materials/lumerical.toml) |
| brief and compiler | wavelength-band intent, reference wavelength, spectral sampling policy, and fixed-focal-length achromatic objective | [`MetalensBrief`](../../src/metacraft/science/metalens/brief.py) carries one integer `wavelength_nm` |
| geometry | positive and inverse/Babinet GaN IRUEs, possibly compound features, rotation, and a 120 nm hexagonal lattice | current aperture geometry admits one circle, square, rectangle, or ellipse; [`lattice_for`](../../src/metacraft/science/metalens/aperture.py) builds an orthogonal mesh |
| response evidence | one exact, phase-unwrapped RCP-to-LCP complex response curve and conversion-efficiency curve for every candidate over the declared band | current [`PeriodicWork`](../../src/metacraft/science/metalens/periodic_request.py) binds one wavelength and one primitive cross-section |
| design workflow | jointly choose IRUE identity for dispersion and orientation for PB phase at every site; include the allowed global spectral phase offset in the contract | current control strategies choose monochromatic propagation states or monochromatic orientation states |
| solver orchestration | qualified broadband material sampling and periodic-response sweeps, with reproducible wavelength grid, phase unwrapping, resonance continuity, and no hidden single-wavelength fallback | current Lumerical periodic request/execution identity is single-wavelength |
| field proof | form, propagate, evaluate, and retain one exact component field per wavelength; permit wavelength-specific grids and qualifications | already anticipated by [ADR 0006](../adr/0006-represent-fields-by-components-not-approximations.md), which explicitly says a future achromatic proof composes multiple exact fields |
| result contract | focal-position flatness over the band, wavelength-resolved efficiency and width, spectral coverage, and missing-wavelength/error provenance | current focus result closes one wavelength at a time |

This classification prevents a false future diagnosis. A failed native
material lookup is a **material-library gap**. Inability to represent an
inverse IRUE or hexagonal lattice is a **geometry gap**. Inability to produce
phase-bearing response across a band is a **solver/evidence gap**. Inability
to jointly select dispersion and orientation, or to conclude over multiple
fields, is a **workflow/domain gap**. Adding GaN alone cannot close the case.

### 4.3 If an exact paper benchmark were selected

This subsection records the minimum honest contract for the paper-exact route
that was investigated. That route is **not selected by the current scope**.
An exact benchmark need not reproduce full-colour imaging or every
fabricated IRUE. Its minimum honest scope is:

1. Paper-locked band `400–660 nm`, `f = 235 um`, `NA = 0.106`, circular
   polarization, GaN on sapphire, `120 nm` hexagonal lattice, and `800 nm`
   height.
2. A source-grounded IRUE table obtained from a machine-readable author source
   or independently regenerated and clearly labeled MetaCraft-owned; never a
   silent transcription of the image tables.
3. One declared spectral grid that includes both endpoints and is dense enough
   to challenge continuity between design samples.
4. Per-wavelength complex converted-channel evidence and one exact propagated
   field per wavelength.
5. A result that reports focal-position variation, wavelength-resolved
   efficiency, and width without comparing unlike efficiency apertures.
6. Separate outcomes for `paper-adapted design` and `exact reproduction`.
   Until the original IRUE table and material dispersion are bound, only the
   former is available.

## Conclusion

The user's remembered method is real, but its origin is **2017**, while its
clearest visible transmissive realization is the **2018** Wang--Tsai paper.
That paper is retained as a method reference, not selected as a fifth current
benchmark, and must not be confused with the adjacent Chen/Capasso 2018 work.

It exposes a credible future architectural seam: a band is not a larger
scalar wavelength, and an achromatic result is not an average of unrelated
monochromatic runs. If that seam is deliberately reopened after the four-case
baseline, a Sonnet-shaped extension would preserve the existing cadence:

```text
band brief
  -> band-qualified materials
  -> dispersive cell responses
  -> joint dispersion-and-orientation assignment
  -> exact field at each wavelength
  -> one spectral conclusion
```

That path is simple in lifecycle, deep in evidence, and faithful to both the
paper and ADR 0006.

## Source-access log

- 2017 Nature Communications publisher article: accessible 2026-08-09.
- 2018 Nature Nanotechnology publisher record: accessible 2026-08-09.
- 2018 author-hosted published PDF at Nanjing University: accessible
  2026-08-09.
- 2018 official Springer Nature supplementary PDF: accessible 2026-08-09;
  Supplementary Tables 1–2 are image-rendered in the available extraction.
- Underlying numerical response tables and raw spectral measurement series:
  not publicly linked by the papers; author-request availability only.
