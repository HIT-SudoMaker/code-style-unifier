# Plane Wave Intensity

## Physical question

What intensity does a normalized, monochromatic, linearly polarized plane
wave produce on a transverse observation plane?

## Equation

The source envelope is

`E(y, x) = A exp(i (k_y y + k_x x)) e_x`.

For the on-axis unit-amplitude case, `k_y = k_x = 0` and the relative
intensity is `I = sum_p |E_p|^2 = 1` everywhere.

## Conventions

The source uses `Polarization.linear_x()`: the transverse Jones order is
`(Ex, Ey)` and its state is `(1, 0)`. Fields use the negative time exponent
`exp(-i omega t)`. For propagation along `+z`, left-circular is
`(1, -i)/sqrt(2)` and right-circular is `(1, +i)/sqrt(2)`; the explicit vector
always takes precedence over handedness words. Field axes are
`[batch..., spectrum, polarization, height, width]`. Public lengths are SI
metres.

The direct physical reading order is `PlaneWave -> IntensityDetection`.
The root owns the two Components; the module-level calculation calls them one
line at a time, then Workstation performs the sole checked replay.

## Run

```text
python examples/basic_plane_wave_intensity/example.py
python examples/basic_plane_wave_intensity/example.py --sample-counts 64 64 --sample-spacing 5e-7 5e-7 --wavelength 5e-7 --output plane-wave.json
```

The command line always creates `Workstation.cpu(...)`. Importers instead pass
an already-created `workstation` to `run(...)`.

## Scope

This case teaches source metadata, transverse polarization, direct Component
composition, hosting, and intensity observation. It does not model
propagation, a sensor, noise, or polarization-changing matter. Component tests
own analytic, gradient, and CUDA evidence.

## Sources

- Polarization and field conventions: [`CONTEXT.md`](../../CONTEXT.md).
- Component definitions:
  [`plane_wave.py`](../../src/chromatix_next/optics/source/plane_wave.py) and
  [`intensity_detection.py`](../../src/chromatix_next/optics/detection/intensity_detection.py).
- Reference formulation: J. W. Goodman, *Introduction to Fourier Optics*,
  4th ed., sections on plane waves and scalar diffraction.
