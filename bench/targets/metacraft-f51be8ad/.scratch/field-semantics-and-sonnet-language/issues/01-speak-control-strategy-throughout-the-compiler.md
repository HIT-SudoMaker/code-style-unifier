# 01 — Speak control strategy throughout the compiler

**Type:** implementation (spec foundation)

**Status:** wontfix

**Superseded by:** `../../metalens-sonnet-convergence/spec.md`

## What to build

Atomically migrate `PhaseMethod` / `phase_method` to `ControlStrategy` /
`control_strategy`, with the canonical values `propagation phase` and
`geometric phase`. Rename the brief condition to `incident_polarization`.
Introduce the independent `ApertureRegime` design fact. Use the stable route
identities `metalens.low_na.propagation_phase`,
`metalens.low_na.geometric_phase`, and
`metalens.large_na.propagation_phase`. Repair the large-na relationship
fixture so it first respects control strategy and then changes applicable
methods. Large-na geometric phase remains an explicit unsupported
combination.

Remove `CellPolicy`. Put `sampling_ceiling_nm` on the resolved metalens design;
derive height candidates and fabrication ranges inside `HeightDomain`; move
substrate thickness, mesh accuracy, simulation time, and grating-plane offsets
behind the Lumerical template seam. `HeightDomain.route` and
`HeightChoice.route` must equal the compiled route, while an explicit
`control_strategy` owns strategy-specific rules.

Separate `science/model.py` into `brief.py` and `study.py` without changing the
public `Brief -> compile_study -> Study` language. Delete `Finding.as_legacy_text`,
`Study.unresolved`, and all compatibility exports after callers migrate.

## TDD seam

Through `compile_study`, compile the two standard low-na briefs and one
large-na propagation-phase brief. Assert the exact control strategy, aperture
regime, compound route identity, sampling ceiling, proof methods, and typed
findings. Recompile from the same values and require identical canonical
bytes. A large-na geometric brief must fail explicitly rather than enter
either neighboring route.

## Acceptance

- No production identifier or canonical schema contains `PhaseMethod`,
  `phase_method`, or `CellPolicy`.
- Propagation phase and geometric phase remain distinct compiled proofs.
- Large na changes applicable methods without erasing control strategy.
- Height and material evidence distinguish route from control strategy.
- Lumerical construction reads no compiler-owned mesh or monitor policy.
- Standard compilation, height-domain, phase-envelope, solver-template, and
  result-closure tests pass.
- No compatibility alias remains.
- Rust diff is empty and touched files pass CSU.

## Do not add

Do not add a strategy registry, aperture-regime route class, fixed workflow,
large-na implementation, or fallback strategy.
