---
title: Continuous-achromatic experiment branch result
date: 2026-08-14
branch: experiment/continuous-achromatic-metalens
method: Chen-2018-inspired local TiO2/glass single-rectangle feasibility slice
status: promising_reference_screen_not_merge_ready
---

# Continuous-achromatic experiment branch result

## Decision

The local single-rectangle route is physically worth continuing, but the
experiment is **not ready to merge**.  Real local materials can be sampled
across the design and holdout grid, the existing square-cell template produces
real complex Jones observations, and two of four completed reference-wavelength
geometries exceeded the paper-inspired 5% converted-power gate.  The same run
also proved that the eager batch road is too coarse: one non-closing geometry
ended the ten-work request with `periodic_time_budget_exhausted` after 412.9 s.

The branch therefore compiles a reference-wavelength screen before the
non-reference spectral follow-up.  It does not yet turn a per-cell numerical
closure failure into a typed rejected-cell fact, so a complete Native spectral
library, physical aperture, spectral fields, and achromatic focal result remain
unproven.

## What was tested

The target is a local adaptation of Chen et al. 2018, not a reproduction:

- design band `470--590 nm`, reference `530 nm`;
- Siefke TiO2 and Palik glass from the installed Lumerical material registry;
- one `600 nm`-high rectangular fin in the existing square-period template;
- normal-incidence x/y Jones observations, projected to circular converted and
  retained channels;
- positive target `R=10 um`, `F=49 um`, `NA≈0.2`, requiring `3.369 fs` relative
  delay; and a nearby `5.234 fs` refusal stress target.

The exact nine-point material witness is
`tests/fixtures/achromatic/native-material-grid-20260814.json`.  Across it, the
locally order-safe plan selected `p=320 nm`; this is an evidence-derived local
adaptation of the paper's `400 nm` seed.

## Power normalization

Lumerical's grating S-parameter analysis returns complex Fresnel-style
amplitudes.  Its documentation explicitly notes that squared S amplitudes can
exceed one when the incident and output media have different refractive
indices.  Consequently `|J|^2` is not directly the cell power.

For each linear input, the experiment derives the shared normalization from
the admitted reference surface:

```text
q_x = (Ptrans,x / Pincident,x) / (|Jxx|^2 + |Jyx|^2)
q_y = (Ptrans,y / Pincident,y) / (|Jxy|^2 + |Jyy|^2)
```

The two independently derived factors must agree before the Jones observation
is admitted into spectral science.  Circular-channel power is then
`q |t_channel|^2`.  At `530 nm`, `q_x=q_y=0.684548590037827`, the reciprocal of
the observed glass index to numerical precision.

Primary references:

- [Ansys grating S-parameter extraction](https://optics.ansys.com/hc/en-us/articles/360042095873-Metamaterial-S-parameter-extraction)
- [Ansys grating projections](https://optics.ansys.com/hc/en-us/articles/360034394354-Grating-projections)
- [Chen et al. 2018](https://doi.org/10.1038/s41565-017-0034-6)

## Native observations

The first isolated `170 x 220 nm` geometry completed.  Its raw converted
coefficient magnitude squared was `0.0258961`, but the physically normalized
converted power was only `0.0177271`; it is below the 5% gate.  The exact raw
Jones values and derivation are retained in
`tests/fixtures/achromatic/native-periodic-spot-20260814.json`.

The subsequent five-geometry reference screen retained these completed facts:

| rectangle (nm) | converted power | retained power | reference verdict |
|---|---:|---:|---|
| 80 x 130 | 0.0700031 | 0.9140032 | eligible |
| 130 x 170 | 0.1066521 | 0.8520029 | eligible |
| 170 x 220 | 0.0177271 | 0.7503796 | filtered |
| 220 x 260 | 0.0482758 | 0.9031893 | filtered |
| 260 x 310 | incomplete (x only) | incomplete | no verdict |

The exact partial-run record is
`tests/fixtures/achromatic/native-reference-screen-20260814.json`.  It is
reference-wavelength evidence only and cannot establish phase linearity,
holdout behavior, available delay span, aperture feasibility, or achromatic
focus.

## Architectural result

The experiment supports one narrow compiler change and rejects two tempting
shortcuts:

1. `Brief` continues to state user intent only.  The Method chooses the Chen-
   inspired reference wavelength and spectral proof; the Plan chooses the local
   period, height, geometry grid, design points, holdouts, and work count.
2. One existing `periodic_polarization_response` capability remains the common
   external seam.  No spectral solver alias, factory, or caller-side algorithm
   selector is introduced.
3. The Plan now screens reference-wavelength geometries first and projects the
   remaining wavelengths only for survivors.  Full-band qualification filters
   individual cells before evaluating phase coverage and delay span.
4. The square-cell geometry domain reserves at least one minimum feature at the
   cell boundary and samples both rectangle axes, instead of following one
   diagonal chain or allowing a nearly filled `310/320 nm` cell.
5. Holdout phase never participates in design-phase unwrapping or delay fitting;
   it checks the already fitted branch by cyclic residual only.

## Remaining merge boundary

Before this branch can be proposed for integration, the periodic execution seam
must expose a typed per-cell numerical-closure refusal that lets the Method
retain completed screen cells and exclude the failed cell without exception-
text classification or blind retry.  After that, run one bounded full-band
follow-up for the surviving geometries and require an Authority-admitted
qualification result.  Only a candidate qualification justifies implementing
the immutable aperture and per-wavelength focus stages; a typed conversion,
linearity, coverage, or delay refusal is also a valid experiment result.

No current evidence supports a continuous-achromatic lens claim, a Chen-paper
reproduction claim, or a merge into the main branch.
