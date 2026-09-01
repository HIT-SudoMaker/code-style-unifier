# Minimal optical path

This example is the shortest complete scientific path in ChromatixNext. It
constructs a spatial grid, spectrum, and polarization state; samples a plane
wave; applies a circular pupil and ideal thin lens; propagates to the focal
plane; and detects intensity.

## Physical question

Does a normally incident plane wave, clipped by a centered circular pupil and
focused by an ideal thin lens, produce its maximum focal-plane intensity on
axis?

## Equation

The path follows the scalar paraxial Fourier-optics result: at one focal length
behind an ideal thin lens, a uniformly illuminated circular pupil produces the
Airy intensity `I(u) ∝ [2 J₁(u) / u]²`, whose central value is the maximum.
The final assertion is the independently inspectable observable: the
grid-centre intensity equals the global maximum.

## Conventions

All lengths use SI metres, the source is monochromatic and x-polarized, and
the retarded-time convention is `exp(-iωt)`. The propagation distance equals
the ideal thin-lens focal length.

## Run

From the repository root:

```powershell
$env:PYTHONPATH = "src"
C:\Users\Administrator\miniforge3\envs\research_env\python.exe `
  examples\minimal_optical_path\example.py
```

## Scope

This is scalar, monochromatic, paraxial, ideal-element evidence. It does not
model sensor sampling, noise, aberration, or vector high-NA focusing.

## Sources

The scientific source is Joseph W. Goodman, *Introduction to Fourier Optics*,
3rd edition (Roberts & Company, 2005): §4.4.2 for Fraunhofer diffraction by a
circular aperture and §5.2 for the Fourier-transforming property of a thin
lens. The same circular-pupil, Goodman thin-lens phase, and single-transform
Fresnel equations are independently exercised by
`tests/element/test_pupil.py`, `tests/element/test_ideal_thin_lens.py`, and
`tests/propagation/test_fresnel_transform.py`.

The file contains eleven top-level logical statements: two imports, eight
named calculation statements in physical reading order, and one scientific
assertion. This count is independent of the expanded formatting used for
readable named arguments. There is no Assembly or Workstation because neither
is required for direct calculation.
