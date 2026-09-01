# Ideal Thin Lens Focusing

## Physical question

Where does a circularly limited plane wave concentrate after an ideal thin
lens and one focal length of free-space propagation?

## Equation

The lens multiplies the field by the paraxial phase

`exp(-i k ((y-c_y)^2 + (x-c_x)^2) / (2 f))`.

For a circular pupil of diameter `D`, the Fraunhofer first-zero radius is
approximately `r_1 = 1.22 wavelength f / D`.

## Conventions

The direct calculation reads
`PlaneWave -> CircularPupil -> IdealThinLens -> ScalarAngularSpectrum -> IntensityDetection`.
Its hosted root owns the Components and the module-level calculation calls
them in this same physical order.
The source uses explicit `linear_x` transverse polarization. Positive
`focal_length` is also the signed forward `axial_distance`. Public lengths use
SI metres; micrometres and millimetres are display-only local conversions.

## Run

```text
python examples/basic_ideal_lens_focusing/example.py
python examples/basic_ideal_lens_focusing/example.py --sample-counts 128 128 --sample-spacing 2e-6 2e-6 --aperture-diameter 2e-4 --focal-length 2.5e-2 --output focus.json
```

## Scope

This is a paraxial ideal lens followed by scalar radiative angular-spectrum
propagation. It does not claim vector high-NA focusing, aberration, a finite
lens thickness, or a camera model. The Airy radius is reported for
interpretation; scientific tolerances stay in Component tests.

## Sources

- Lens, propagation, and grid contracts: [`CONTEXT.md`](../../CONTEXT.md).
- Reference formulation: J. W. Goodman, *Introduction to Fourier Optics*,
  4th ed., chapters on thin lenses and Fraunhofer diffraction.
- Implemented Components:
  [`ideal_thin_lens.py`](../../src/chromatix_next/optics/element/ideal_thin_lens.py)
  and
  [`scalar_angular_spectrum.py`](../../src/chromatix_next/optics/propagation/scalar_angular_spectrum.py).
