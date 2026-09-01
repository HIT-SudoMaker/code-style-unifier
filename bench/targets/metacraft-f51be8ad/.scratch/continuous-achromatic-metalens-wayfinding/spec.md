# Continuous compensation phase in the Sonnet architecture

Status: accepted (2026-08-15)

## Objective

Close one Wang--Tsai-inspired, locally adapted continuous-achromatic metalens through the existing public `brief -> study -> result` lifecycle without changing the meaning or evidence of the monochromatic propagation-phase and PB-phase proofs.

## Scientific contract

The first Method accepts one circularly illuminated, transmissive, low-NA metalens over one continuous band. It uses one square period, one fixed height, and a bounded primitive rectangular-fin library. For every occupied aperture site it selects exactly one geometry and one physical orientation; both remain unchanged at every design and holdout wavelength.

The target phase under the admitted time and polarization convention is

```text
Delta L(r) = sqrt(r^2 + F^2) - F
phi_required(r, omega) = -omega Delta L(r) / c + C(omega)
t_converted(g, theta, omega) = t_converted(g, 0, omega) exp(i 2 s theta)
```

where `C(omega)` is one aperture-wide spectral gauge and `s` is derived from the admitted circular-polarization convention. Geometry is selected against the required relative phase slope and qualified complex spectral response; orientation closes the reference-frequency phase after accounting for the selected geometry's own phase.

## Proof

```text
achromatic focus
  <- spectral field family
  <- achromatic aperture
  <- qualified spectral library
  <- spectral Jones library
  <- reference-wavelength screen
  <- spectral cell-study plan
  <- full-band material binding
  <- continuous-band target
```

The spectral field family indexes exact single-wavelength Fields and focal regions. Achromatic focus evaluates those admitted regions without propagating again and fails closed if any design or holdout wavelength is absent or incomplete.

## Acceptance

- A positive qualified library produces one immutable geometry/orientation aperture and exact replayable document.
- Changing wavelength never changes geometry or orientation assignment.
- Left/right circular incidence derives the PB sign from `PolarizationConvention`; no new Method document writes a universal `+2 theta` law.
- Every design and holdout wavelength forms converted and retained circular fields and one bracketed focus over `0.8F-1.2F`.
- Achromatic focus retains every per-wavelength metric and complete-band worst/mean summaries.
- A PB-only chromatic baseline is formed from one fixed reference geometry and the same aperture, wavelengths, propagator, focus evaluator, and normalization.
- A complete but physically insufficient library yields a typed refusal; missing or numerically incomplete evidence never becomes a physical refusal.
- Existing propagation-phase and PB-phase result bytes and Interface tests remain unchanged.
- Result replay restores the continuous conclusion without rerunning selection, propagation, or focus evaluation.

## Publication boundary

This implementation establishes a local square-template adaptation, not a paper-exact reproduction. Publication still requires Native completion of the bounded spectral library, positive device closure or typed refusal, PB-only and chromatic comparisons, an independent transfer/full-device check, and release of exact evidence and failed work.
