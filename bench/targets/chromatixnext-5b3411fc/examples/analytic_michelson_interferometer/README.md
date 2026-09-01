# Analytic Michelson Interferometer

## Physical question

Does one balanced ideal nonpolarizing Cube, encountered once on the outward
path and again on the return path, produce the complementary Michelson
intensity ratios predicted from the differential round-trip phase?

## Equation

For refractive index `n`, wavelength `lambda`, and arm lengths `L_top` and
`L_right`, the relative phase and the two RELATIVE observables are

```text
relative_phase = 4 pi n (L_top - L_right) / wavelength
left_ratio = sin^2(relative_phase / 2)
bottom_ratio = cos^2(relative_phase / 2)
```

Their sum is one. The four frozen phase points `0`, `pi/3`, `2*pi/3`, and
`pi` give unit visibility at both ports.

## Frozen reference card

- Spectrum: one `632.8e-9 m` line with weight `1.0`.
- Medium: vacuum, with constant refractive index `1.0`.
- Grid: `(height, width) = (8, 12)` and spacing
  `(7e-6 m, 11e-6 m)`.
- Input: constant envelope `1 + 0i`, transverse Jones state `(1 + 0i, 0 + 0i)`,
  and RELATIVE normalization.
- Cube: origin `(0, 0, 0) m`, route-right `(1, 0, 0)`, route-top
  `(0, 1, 0)`, rising diagonal, and mixing angle `pi/4`.
- Right Mirror: origin `(1e-3, 0, 0) m`, outward normal `(-1, 0, 0)`, and
  transverse-up `(0, 0, 1)`.
- Top Mirror: origin `(0, L_top, 0) m`, outward normal `(0, -1, 0)`, and
  transverse-up `(0, 0, 1)`.
- At the nondegenerate `pi/3` point, `L_right = 1e-3 m` and
  `L_top = L_right + wavelength/12`.
- Each arm has one explicit positive route-local outbound Propagation and one
  explicit positive route-local return Propagation. Propagation alone advances
  Optical Path Reference, once per action, so an arm accumulates `2 n L`.
- The outward Terminal sequence is `left -> {right, top}`; the return sequence
  is `{top, right} -> {left, bottom}`. Canonical contributor order makes the
  transformed top return the output Optical Path Reference.
- Each ideal Mirror contributes the exact local scalar `-1`. The equal-arm
  gauge labels left dark and bottom bright.
- The only Named Outputs are the two Detection observables
  `left_intensity` and `bottom_intensity`.

The fixed-double acceptance budgets are `5e-13` maximum absolute error for the
independent dense complex operator and `2e-12` absolute error for each port
ratio, complementary sum, and visibility. Every required counterfactual must
separate a port ratio by at least `0.20`.

## One owner and finite topology

The Assembly registers one Cube named `cube`. Its `outward_cube` and
`return_cube` Encounters reference that same exact object. Two Mirrors turn the
arms, four explicit Propagations own distance and phase, and both return
Terminals feed Intensity Detections. Every produced directional output has a
downstream connection; no field is manually added outside the return
Encounter, and no route is flattened into a fake straight-line path.

## Run

From the repository root:

```powershell
$env:PYTHONPATH = "src"
C:\Users\Administrator\miniforge3\envs\research_env\python.exe `
  examples\analytic_michelson_interferometer\example.py
```

## Scope

This is a monochromatic, normal-incidence, ideal, lossless, coherent Wave
model under RELATIVE normalization. It establishes dimensionless port ratios,
complementarity, and visibility for the frozen fixture. It does not describe a
characterized or real coating, infer repeated encounters or cavity recurrence,
provide Ray observational closure, measure performance, or define an optimizer
or experiment runtime. A simultaneous omission of both identical Mirror
scalars is a common global phase and is not observable here; the dedicated
tests challenge a one-arm omission at `pi/3` instead.

## Sources

- The physical values, Optical Path Reference, Assembly, Terminal, Encounter,
  and Detection language is fixed by [`CONTEXT.md`](../../CONTEXT.md).
- Example ownership is fixed by
  [ADR-0004](../../docs/adr/0004-example-owned-research-workflows.md).
- The ideal response implementations are
  [`ideal_cube_beam_splitter.py`](../../src/chromatix_next/optics/element/ideal_cube_beam_splitter.py),
  [`ideal_planar_mirror.py`](../../src/chromatix_next/optics/element/ideal_planar_mirror.py),
  and
  [`scalar_angular_spectrum.py`](../../src/chromatix_next/optics/propagation/scalar_angular_spectrum.py).
- The constants, gauge, phase points, and numerical budgets reproduce the
  frozen analytic Michelson reference card in the direction-aware scientific
  foundation vNext specification, section 12.
