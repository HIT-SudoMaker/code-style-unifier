# 02 — Let present angular spectrum prove only what it does

**What to build:** Strengthen the existing componentwise angular-spectrum
realization so that its current low-na field claim is established by an
independent numerical reference without pretending it is a Maxwell-vector
method.

**Blocked by:** None — can start immediately.

**Status:** resolved (2026-07-30)

- [ ] The existing public angular-spectrum meaning remains componentwise and
      gains neither a `scalar` prefix nor a vector claim.
- [ ] One bounded direct scalar diffraction reference establishes Fourier
      sign, propagation direction, coordinate scaling, and complex-field
      normalization.
- [ ] A low-na circular-pupil fixture agrees with the Airy focus limit within
      an explicit numerical tolerance.
- [ ] Qualification compares complex fields rather than intensity alone.
- [ ] Production propagation remains Torch-native with complex128 arithmetic.
- [ ] CUDA is selected when available and Torch CPU only when CUDA is absent;
      a failed selected-device qualification never falls back silently.
- [ ] Angular-spectrum padding remains exactly two times and no four-times
      configuration survives.
- [ ] Chunking changes memory use but not complex field, focal metrics, or
      evidence identity.
- [ ] The qualified binding records device, dtype, padding, Fourier
      convention, sampling, and realization identity.
- [ ] Existing low-na propagation, focus, result, and replay behavior remains
      unchanged.
- [ ] Focused angular-spectrum and focus tests pass without Lumerical or a
      four-case run.
