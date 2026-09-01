# 01 — Bind and qualify one Torch Field realization

**Type:** implementation

**Status:** wontfix

**Superseded by:** `../../metalens-sonnet-convergence/spec.md`

**Blocked by:** none.

## Outcome

One qualified Torch realization propagates every current component-based
Field. Composition binds one exact device and numerical configuration;
execution restores that binding without a hidden fallback.

## What to build

- Migrate production propagation, its dependency, qualification, binding,
  provenance, and directly conflicting tests atomically to Torch.
- Select CUDA when available and Torch CPU only when CUDA is absent.
- Bind the exact device, complex128/float64 dtypes, two-times padding,
  transform convention, evanescent treatment, and safe working-memory budget.
- Qualify that exact configuration with zero-distance reconstruction and an
  apodized Gaussian propagation/refinement case.
- Prepare one spectrum for each nonzero component and skip transforms for an
  identically zero component.
- Retain only the axial intensity curve, complex best-focus plane, incident
  reference power, transmitted aperture power, binding, and provenance.
- Derive the actual axial batch from the admitted memory budget and real
  padded grid; return a waiting Study when one plane cannot fit.
- Retire `source_power`, NumPy FFT production paths, four-times padding,
  private batch constants in tests, and implementation-spelling assertions.

## TDD seam

Begin at the public Field propagation and evaluation interface. Prove one
reviewed numerical fixture on the bound realization before adding device,
qualification, and insufficient-memory cases.

## Acceptance

- Focused Field tests collect and pass.
- The same tensor program runs on CUDA or CPU according to the admitted
  binding; execution never re-observes availability.
- Qualification and execution share device, dtype, padding, and convention.
- Numerical provenance is provider-neutral and exact.
- No public device selector, batch size, CPU/CUDA type split, or alternate
  propagation implementation is introduced.
- Architecture tests, Pyright, and CSU on touched files pass.
- Rust has no diff.

## Verification

Implemented on 2026-07-28 without a commit.

- Public Field and composition checks: 23 passed; 3 explicit integration
  checks deselected.
- Propagation Result checks: 12 passed.
- Geometric Result checks: 6 passed.
- Independent focused Field and architecture review: 40 passed.
- Pyright: zero errors.
- CSU on touched files: zero hard violations.
- Rust diff: empty.

The remaining legacy material spelling and standard-study hash failures enter
ticket 02 and ticket 03 respectively; neither is hidden by this closure.
