# 05 — Let fast Debye answer to the direct field

**What to build:** Add FFT-Debye and CZT-Debye as Torch accelerations of the
already qualified direct Debye method, preserving the same physical contract
and complex vector field.

**Blocked by:** 04 — Let direct Debye establish one vector truth.

**Status:** resolved (2026-07-30)

- [ ] FFT-Debye and CZT-Debye are realizations of the existing Debye method,
      not new physical methods or compiler routes.
- [ ] Transform, chirp, coordinate, batching, interpolation, and reduction
      operations are implemented entirely in Torch.
- [ ] No production FFT-Debye or CZT-Debye module imports or calls NumPy or
      SciPy.
- [ ] Both realizations preserve Torch complex128 and remain on the selected
      CUDA or CPU device.
- [ ] FFT-Debye agrees with direct Debye in complex Ex, Ey, and Ez on matched
      coordinates across representative low and high numerical apertures.
- [ ] CZT-Debye agrees with direct Debye in complex Ex, Ey, and Ez on matched
      off-axis and focal-region coordinates.
- [ ] Phase, amplitude, coordinate, normalization, and handedness differences
      are tested separately so intensity agreement cannot hide an error.
- [ ] Each binding records sampling, window, coordinate convention, device,
      dtype, source method, and realization identity.
- [ ] An architecture ratchet rejects NumPy or SciPy imports from every
      production Debye realization.
- [ ] Performance measurements occur only after complex-field parity and do
      not become scientific acceptance thresholds.
- [ ] Focused accelerated-Debye tests pass without Lumerical or a four-case
      delivery.
