# Scalar Angular Spectrum Propagation

## Physical question

How does a pupil-limited field propagate between parallel planes when the
observation window is translated without changing its sampling?

## Equation

For wavelength `λ` in a medium with refractive index `n(λ)`, define

`k = 2π n(λ) / λ`

and, on radiative spatial-frequency support,

`k_z = sqrt(k^2 - k_y^2 - k_x^2)`.

For signed axial distance `d` and destination first-sample translation
`(Δy, Δx)`, the envelope transfer is

`H_envelope = exp(i[(k_z - k)d + k_y Δy + k_x Δx])`.

The residual axial phase `(k_z - k)d` remains in the envelope, while the
uniform carrier is recorded per spectral component as
`OpticalPathReference += n(λ)d`. Translation contributes only the
`k_y Δy + k_x Δx` phase and does not change the Optical Path Reference.
Non-radiative components and components outside the angular-spectrum
alias-safe band are set to zero.

## Conventions

The direct calculation reads
`PlaneWave -> CircularPupil -> ScalarAngularSpectrum -> IntensityDetection`.
Its hosted root owns the Components and the module-level calculation calls
them in this same physical order. The source uses `linear_x` transverse
polarization. `axial_distance` is signed: positive is forward.
`destination_shift` changes only the destination
`SpatialGrid.first_sample_position`; it is not an off-axis propagation
direction. A destination grid must have the same sample counts, signed sample
spacing, and orientation as the input grid; only its first-sample position may
be translated. Periodic exterior meaning is used. Public lengths use SI metres.

## Run

```text
python examples/propagation_scalar_angular_spectrum/example.py
python examples/propagation_scalar_angular_spectrum/example.py --sample-counts 64 64 --sample-spacing 1.5e-6 1.5e-6 --aperture-diameter 4.5e-5 --axial-distance 5e-4 --destination-shift 6e-6 -3e-6 --output propagation.json
```

## Scope

The current method supports first-sample translations between parallel planes
whose sample counts, signed spacing, and orientation match. It rejects other
geometry instead of selecting another propagator. Evanescent continuation,
scaled transforms, vector propagation, and nonuniform sampling are outside
this case.

## Sources

- Propagation, Destination Grid, Exterior, and Optical Path Reference:
  [`CONTEXT.md`](../../CONTEXT.md).
- Reference formulation: J. W. Goodman, *Introduction to Fourier Optics*,
  4th ed., angular-spectrum chapter.
- Implementation:
  [`scalar_angular_spectrum.py`](../../src/chromatix_next/optics/propagation/scalar_angular_spectrum.py).
