# 04 — Let direct Debye establish one vector truth

**What to build:** Establish one direct Richards--Wolf/Debye reference
realization for the complex high-na focal field of an ideal aplanatic pupil or
reference sphere.

**Blocked by:** None — can start immediately.

**Status:** resolved (2026-07-30)

- [ ] Direct Debye is a distinct physical method for an aplanatic pupil or
      reference sphere and does not accept an arbitrary sampled exit plane.
- [ ] The public contract declares pupil surface, coordinate frame, medium,
      polarization, apodization convention, wavelength, and focal coordinates.
- [ ] Angular quadrature, vector-component construction, batching, and
      reductions are implemented entirely in Torch.
- [ ] No production Direct Debye module imports or calls NumPy or SciPy.
- [ ] The same Torch implementation runs on CUDA when available and Torch CPU
      only when CUDA is absent.
- [ ] Complex128 is preserved from pupil construction through Ex, Ey, and Ez.
- [ ] On-axis, symmetry, parity, handedness, and component-sign fixtures
      establish the Richards--Wolf convention.
- [ ] Bounded batching changes resource use without changing the complex
      result or realization identity.
- [ ] Qualification records quadrature, sampling, device, dtype, convention,
      and exact reference fixtures.
- [ ] A failed selected-device qualification produces no binding and never
      falls back to a NumPy, SciPy, or alternate Torch implementation.
- [ ] Direct Debye focused tests pass without FFT, CZT, Lumerical, or the four
      canonical cases.
