---
record_type: research_record
date: 2026-08-06
status: research_finding
authority_level: none
current_capability: false
---

# Published measure definitions for the four metalens benchmark cases

## Research question

What do the quantitative values and named qualitative measures currently
carried by the four `MetalensBenchmarkCase` values mean in their primary
papers? In particular, which paper observations can be compared with
MetaCraft's present `Focus` semantics, and which can only provide context?

This record audits evidence. It does not change a case, an ADR, a threshold,
or a scientific method. A paper value remains encoded until a separately
approved change replaces it.

## Disposition vocabulary

- **comparable**: the paper and MetaCraft name the same physical quantity,
  scope, normalization, and measurement region. A numerical delta is
  meaningful once both observations exist.
- **context only**: the source is valid, but its device, illumination,
  normalization, channel, or measurement region differs from the benchmark
  result. It may explain a result but cannot score agreement.
- **cannot yet classify**: a required definition is absent from the accessible
  primary source or the relevant official source is inaccessible. No numerical
  delta is allowed.
- **not reported**: the paper does not publish the named observation.

MetaCraft currently defines `focus_efficiency` as focused power inside a
circle of radius `0.61 * wavelength / NA`, divided by incident power. It
reports separate interpolated `x_half_maximum` and `y_half_maximum` widths.
Those definitions are the comparison side used below; they are not assertions
about any paper's convention.

## Executive finding

None of the six encoded paper metrics is presently eligible for a direct
numerical delta:

| Case and encoded metric | Source status | Disposition | Reason |
| --- | --- | --- | --- |
| Yun simulated focus efficiency `0.828` | value verified; denominator and focal bucket absent | cannot yet classify | The paper states the simulated value but not the integration region or normalization used for Fig. 3. |
| Yang measured focus efficiency `0.26` | value and denominator verified; focal bucket absent | cannot yet classify | The source defines focal-spot power divided by power impinging on the metalens, but does not define the spot boundary. |
| Yang theoretical focus efficiency `0.60` | value and denominator verified; focal bucket absent | cannot yet classify | Same definition and missing boundary as the measured value. |
| Arbabi measured family maximum `0.82` | value, device, denominator, and bucket verified | context only | It belongs to the fabricated `d = 500 um` fibre-illuminated lens and uses a radius of three measured FWHM; the benchmark is a compact plane-wave standard and MetaCraft uses an Airy-radius bucket. |
| Khorasaninejad measured focus efficiency `0.73` | value verified; denominator and focal bucket inaccessible | cannot yet classify | The accessible article reports the measurement but delegates setup details to the inaccessible supplementary bundle. |
| Khorasaninejad focal width `375 nm` encoded as a mean width | value verified, encoded meaning conflicts | context only | The paper reports the FWHM of one vertical focal-spot cut, not a mean of independent x and y widths. |

The Khorasaninejad Science supplementary bundle returned HTTP 403 from both
publisher supplement paths on 2026-08-06. Claims that require it are marked
**inaccessible**, rather than **absent**. The author-hosted published article
itself was accessible.

## 1. Yun 2025: conventional full-turn comparator

Primary sources:

1. Jeong-Geun Yun et al., “Compact eye camera with two-third wavelength
   phase-delay metalens,” *Nature Communications* 16, 7299 (2025),
   [article and Fig. 3](https://doi.org/10.1038/s41467-025-62577-1).
2. [Official supporting information](https://static-content.springer.com/esm/art%3A10.1038%2Fs41467-025-62577-1/MediaObjects/41467_2025_62577_MOESM1_ESM.pdf),
   especially Supplementary Note 3 and Supplementary Fig. 2.

### Device and platform facts

The selected source object is the **numerical conventional `2 pi` comparator**
in the article's “Comparison between `2 pi` and `4 pi / 3` phase-delay
metalens” section and Fig. 3, not the fabricated wide-field camera metalens.

| Encoded fact | Primary-source result |
| --- | --- |
| wavelength `850 nm` | Verified in the Fig. 3 comparison and the design discussion. |
| NA `0.35` | Verified for the `0.5 mm`-diameter numerical metalenses. |
| circular aperture `500 um` by `500 um` | Verified as a `0.5 mm` diameter. |
| focal length `669.1 um` | **Derived, not quoted.** It follows from the encoded diameter and NA using `f = R * sqrt(1 - NA^2) / NA`, giving about `669.1 um`. The source does not state this precision for the Fig. 3 comparator. |
| square period `400 nm` | Verified for the meta-atom platform. |
| comparator height `800 nm` | Verified in the Fig. 3 comparison; the article says the proposed design reduces height from `800 nm` to `500 nm`. |
| cylindrical a-Si:H on fused silica | Verified for the platform. |
| exclusion: `4 pi / 3` optimized device | Correct: it is the proposed device, not the selected conventional comparator. |
| exclusion: `900 nm` supporting-analysis library | Correct and important: Supplementary Note 3/Fig. 2 uses `H = 900 nm`, `P = 400 nm`, meta-atom index `2.58`, and substrate index `1.472`; it is not the article's `800 nm` Fig. 3 comparator. |

The blind brief's `10 nm` fabrication increment and the MetaCraft `8/12/16`
phase sets are MetaCraft-owned test choices, not paper measurements.

### Encoded `0.828` focus efficiency

The article's Fig. 3 comparison states that the `4 pi / 3` and conventional
`2 pi` metalenses have numerically calculated focusing efficiencies of
`87.2%` and `82.8%`, respectively. Thus the encoded value, numerical status,
wavelength, device, and comparator scope are correct.

The accessible article and official supporting information do **not** state
for this calculation:

- the numerator's focal integration radius or region;
- whether the numerator uses scalar intensity, Poynting flux, or another
  normalization;
- the denominator surface or whether it is incident or transmitted power;
- a polarization-channel restriction; or
- a numerical uncertainty.

This is an **absent definition**, not an access failure. The value is
**cannot yet classify** and must not be differenced against MetaCraft's
Airy-radius `Focus.focus_efficiency`.

### Named qualitative measures

| Measure | Primary-source definition and locator | Disposition |
| --- | --- | --- |
| phase coverage | Article Fig. 3a describes the conventional library as full `2 pi`; Fig. 3b is the separate `4 pi / 3` library. | comparable as a qualitative span; no paper response table exists for pointwise numerical equality |
| transmitted magnitude | Fig. 3a plots “Transmission,” while Supplementary Note 3 discusses complex amplitude and near-constant transmission for a different `900 nm` library. The source does not identify Fig. 3 transmission as complex-field magnitude rather than power transmission. | context only; do not equate transmission with field magnitude |
| complex focal field | The article reports focusing efficiency and MTF, not a reusable complex focal-field observation or array. | not reported |

## 2. Yang 2018: one circular-polarization sublens

Primary sources:

1. Zhenyu Yang et al., “Generalized Hartmann-Shack array of dielectric
   metalens sub-arrays for polarimetric beam profiling,” *Nature
   Communications* 9, 4607 (2018),
   [publisher article](https://doi.org/10.1038/s41467-018-07056-6) and
   [PMC full text](https://pmc.ncbi.nlm.nih.gov/articles/PMC6214988/).
2. [Official supporting information](https://static-content.springer.com/esm/art%3A10.1038%2Fs41467-018-07056-6/MediaObjects/41467_2018_7056_MOESM1_ESM.pdf).

### Device and platform facts

| Encoded fact | Primary-source result |
| --- | --- |
| wavelength `1550 nm`, focal length `30 um`, NA `0.32` | Verified in “Principle of metalens array design.” |
| square footprint `22.5 um` by `22.5 um` | Verified; it contains `15 x 15` lattice sites at the reported period. |
| square period `1500 nm`, height `340 nm` | Verified in the main text and Fig. 2. |
| ellipse axes `1350 nm` and `480 nm` | Verified by the white-circle selection in Fig. 2b,c. |
| silicon ellipse on silicon dioxide | Verified. |
| one circular-polarization sublens | Verified: one `l` or `r` lens is selected, not the complete six-lens sub-array or Hartmann-Shack array. |

The brief's `100 nm` fabrication increment and MetaCraft's `8/12/16`
orientation sets are MetaCraft-owned choices. The paper varies orientation
continuously over `[0, pi)` and does not publish those three quantizations.

### Encoded `0.26` and `0.60` focus efficiencies

The last paragraph of the article's circular-lens design discussion reports
a theoretical (measured) focusing efficiency of `60%` (`26%`) for circular
incident polarization. The preceding definition applies to these lenses:
focusing efficiency is the ratio of optical power in the focal spot to optical
power impinging on the metalens. The values, numerical/experimental status,
device scope, denominator, and lack of a transmitted-power normalization are
therefore verified.

Neither the main article nor official supporting information defines the
focal spot's integration boundary. They also provide no uncertainty for these
two values. Both values are **cannot yet classify** against MetaCraft's fixed
Airy-radius bucket.

The abstract's `28%` is the **mean measured efficiency of the complete array**;
it does not conflict with the selected circular sublens's `26%`.

### Named qualitative measures

| Measure | Primary-source definition and locator | Disposition |
| --- | --- | --- |
| orientation relation | Main-text Eqs. 2 and 3 split same- and opposite-handed transmission; the opposite-handed terms carry handedness-dependent geometric phases of opposite sign. Varying ellipse orientation from `0` to `pi` covers `0` to `2 pi`. | comparable only after MetaCraft's propagation direction, handedness basis, viewing direction, and angle sign are explicitly aligned |
| polarization conversion | The paper chooses the fixed ellipse so the same-handed term ideally vanishes and the incident circular field is converted to the opposite handedness. This is a Jones-channel statement, not a claim that a fabricated cell converts with unit power. | comparable at the Jones-channel level; efficiency remains evidence-dependent |
| complex focal field | The paper publishes focal intensities used for Stokes reconstruction, not a reusable complex focal-field array. Supplementary Note 4 discusses measured background from direct substrate transmission and other polarization components. | not reported |

## 3. Arbabi 2015: HCTA family and compact derived standard

Primary source:

1. Amir Arbabi et al., “Subwavelength-thick lenses with high numerical
   apertures and large efficiency based on high-contrast transmitarrays,”
   *Nature Communications* 6, 7069 (2015),
   [publisher article](https://doi.org/10.1038/ncomms8069) and
   [author manuscript with Methods and Supplementary Information](https://arxiv.org/abs/1410.8261).

### Device and platform facts

| Encoded fact | Primary-source result |
| --- | --- |
| wavelength `1550 nm` | Verified throughout Fig. 1 and the device study. |
| hexagonal period `800 nm`, post height `940 nm`, diameter `200-550 nm` | Verified in Fig. 1d; that library has transmission above `92%` over the selected diameter range and covers the full transmission phase range. |
| circular amorphous/hydrogenated-amorphous silicon posts on fused silica | Verified; the fabrication section identifies hydrogenated amorphous silicon. |
| compact diameter `100 um`, focusing distance `25 um`, NA about `0.89` | Verified as the factor-of-four numerical counterpart of the fabricated `400 um` family; `0.89` is the geometric NA derived from radius `50 um` and distance `25 um`. |
| x-linear plane-wave benchmark illumination | **Adaptation, not the paper simulation.** The paper obtains the incident electric and magnetic fields from the scaled single-mode-fibre geometry and uses those fields as FDTD excitation. The case correctly excludes reproduction of the fibre field, so it is an HCTA-derived standard rather than an exact paper device. |

The `10 nm` fabrication increment is a MetaCraft-owned test choice.

### Encoded family maximum `0.82`

The abstract reports measured focusing efficiency “up to `82%`.” The main
text and Fig. 4d locate that maximum at the **fabricated `400 um`-diameter
lens with focusing distance `d = 500 um`**, illuminated by a cleaved
single-mode fibre `600 um` behind the substrate. It is not the compact
`100 um`, `d = 25 um` numerical lens.

The Methods define focusing efficiency as incident-light fraction passing
through a circular aperture in the focal plane whose **radius is three times
the measured FWHM spot size**. Experimentally, an iris is set to that radius;
incident power is measured by removing the microlens and bringing the fibre
tip into the microscope focus. Opening the iris completely gives total
transmitted power. No uncertainty for the `82%` family maximum is stated.

The value is therefore valid but **context only**. Its device, incident field,
and focal bucket differ from the compact plane-wave benchmark and MetaCraft's
Airy-radius bucket.

### Named qualitative measures

| Measure | Primary-source definition and locator | Disposition |
| --- | --- | --- |
| focusing-efficiency trend | Fig. 2d (simulation) and Fig. 4d (measurement) show efficiency decreasing as NA rises / focusing distance falls. | context only for the adapted compact case; the family trend is a valid diagnostic |
| spatial phase sampling | Supplementary Section S.2 attributes high-angle loss to under-sampling: a `2 pi` ramp is sampled by `n = wavelength / (a sin(theta))` cells; smaller lattice constant improves sampling. | comparable as a qualitative mechanism, not as a paper-layout equality |
| transmitted power | Methods distinguish total transmitted power (iris fully open) from focused power and incident power. Fig. 4d reports transmission for the fibre-illuminated family. | context only because illumination and device differ |
| complex focal field | Fig. 2 shows simulated electric-field and Poynting-vector distributions, but no reusable complex field data are published. | not reported as comparison data |

## 4. Khorasaninejad 2016: 532 nm PB metalens

Primary sources:

1. Mohammadreza Khorasaninejad et al., “Metalenses at visible wavelengths:
   Diffraction-limited focusing and subwavelength resolution imaging,”
   *Science* 352, 1190-1194 (2016),
   [author-hosted published article](https://capasso.seas.harvard.edu/resource/2016khorasaninejadetal3pdf),
   DOI [10.1126/science.aaf6644](https://doi.org/10.1126/science.aaf6644).
2. The official Science supplementary bundle linked from the article was
   **inaccessible** (HTTP 403) during this audit.

### Device and platform facts

| Encoded fact | Primary-source result |
| --- | --- |
| selected wavelength `532 nm`, focal length `90 um`, diameter `240 um`, NA `0.8` | Verified in the design section and Fig. 1. |
| square period `325 nm`, height `600 nm`, long side `250 nm`, short side `95 nm` | Verified in the Fig. 1F caption for the 532 nm device. |
| amorphous-TiO2 rectangular nanofin on glass | Verified. |
| right-circular incidence | Verified for all reported efficiency measurements; the converted transmitted channel is left-circular. |
| exclusions `405 nm` and `660 nm` | Correct: they are separate fabricated devices with different cells. |

The brief's `10 nm` fabrication increment is MetaCraft-owned, not a source
measurement.

### Encoded focus efficiency `0.73`

The “Characterizing metalens performance” section and Fig. 3A report a
**measured `73%` focusing efficiency** at the 532 nm design wavelength. All
efficiency measurements use right-circular incident light.

The accessible article does not define the efficiency numerator, denominator,
normalization surface, or focal collection aperture. It directs measurement
details to its supplementary materials, which were inaccessible during this
audit. These definitions are therefore **inaccessible**, not proven absent.
No uncertainty is stated in the article.

The value is **cannot yet classify** against MetaCraft's Airy-radius bucket.

### Encoded focal width `375 nm`

Figure 2B/H and the Fig. 2 caption report `375 nm` as the measured FWHM of
the **vertical cut** through the 532 nm focal-spot intensity profile. The
article describes the two-dimensional spot as highly symmetric, but it does
not report independent x and y FWHMs or their arithmetic mean.

This conflicts with the current encoded measure name
`MEAN_HALF_MAXIMUM_WIDTH`. The number and unit are correct; the statistical
and directional meaning is not. Until a separately approved correction, the
value is **context only** and cannot be compared to a mean of MetaCraft's
`x_half_maximum` and `y_half_maximum`.

### Named qualitative measures

| Measure | Primary-source definition and locator | Disposition |
| --- | --- | --- |
| orientation relation | Design Eqs. 1-2 state that for right-circular incidence the nanofin rotation gives geometric phase `+2 * orientation` with conversion to left-circular light. | comparable only after coordinate and handedness conventions align |
| polarization conversion | Fig. 1F defines conversion efficiency as opposite-helicity transmitted power divided by total incident power; simulated conversion reaches as high as `95%` for the wavelength-specific cell families. | comparable for the cell-level channel and normalization, not a substitute for whole-lens focusing efficiency |
| x/y half-maximum widths | One vertical-cut FWHM is reported; independent x and y widths are not. | context only |
| longitudinal field fraction | No longitudinal-component power fraction is reported in the accessible article. | not reported; supplementary status inaccessible |
| complex focal field | The paper reports intensity profiles and cuts, not a reusable phase-bearing complex focal field. | not reported; supplementary status inaccessible |

## Cross-case comparison contract

The source audit supports the following safe sequence for Ticket 02:

1. Preserve a paper metric's **device**, **illumination/polarization channel**,
   **numerator**, **denominator**, **focal bucket**, and **width convention** as
   separate facts.
2. Refuse a numerical delta when any required fact is absent or inaccessible.
3. Treat Arbabi's `0.82` as family context, not as the compact case's target.
4. Treat Khorasaninejad's `375 nm` as a vertical-cut FWHM unless a later,
   primary-source-backed decision changes the encoded measure.
5. Never translate “transmission” into field magnitude, or intensity into a
   complex field, without an explicit source definition.

This leaves useful qualitative comparisons—phase coverage, PB orientation,
polarization conversion, sampling trend—while preventing unlike efficiency
buckets from appearing to agree numerically.

## Source-access log

- Yun article and official supplementary PDF: accessible 2026-08-06.
- Yang publisher/PMC article, author-deposited article PDF, and official
  supplementary PDF: accessible 2026-08-06.
- Arbabi publisher article and author manuscript containing Methods and
  Supplementary Information: accessible 2026-08-06.
- Khorasaninejad author-hosted published article: accessible 2026-08-06.
- Khorasaninejad official Science supplementary bundle: publisher endpoints
  returned HTTP 403 on 2026-08-06; no secondary source was used to fill its
  missing definitions.
