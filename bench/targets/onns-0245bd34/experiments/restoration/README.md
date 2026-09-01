# Restoration architecture

Restoration shares one optical bench, not one experiment protocol. The root
contains only physical and evidence concepts that are meaningful to both
research lines; Fixed and Adaptive keep their different inputs, state
transitions, optimization rules, and result contracts inside their own
packages.

## Shared root

- `optical_bench/` is the single physical source of truth. Its public
  Interface freezes the sampled geometry and propagates the reference and
  Fourier-processing arms through the same coherent bench for both protocols.
  Internally it separates configuration, Fourier-plane mapping, propagation,
  and the low-level dual-arm kernel.
- `phase_control.py` defines requested phase commands, delivered phase states,
  and phase-delivery adapters.
- `input_protocol.py` and `degradation.py` freeze the source, 256-to-512
  preparation, encoding, and light/medium/heavy degradation contracts consumed
  by both Fixed and Adaptive.
- `pupil_aberrations.py` defines normalized pupil-phase states.
- `observations.py` defines causally identified detector observations.
- `metrics.py`, `targets.py`, `value_contracts.py`, and `evidence.py` provide
  experiment-neutral measurement and evidence contracts.

The root does not own training, probe scheduling, archive migration, or a
universal scene object. A shared module must serve both protocols without
importing either one.

## Fixed Measurement

`fixed_measurement/` owns the target-supervised route. Clean targets may guide
offline training, but the deployed Fourier phase is specimen-independent. Its
public surface contains only:

```python
run_fixed_measurement(request) -> FixedMeasurementRecord
record_fixed_optical_states(frontend, input_field) -> FixedOpticalRecord
```

Its implementation follows the scientific reading order:

```text
fixed_measurement/
  experiment.py       public orchestration
  protocol/           inputs, frozen plan, roles, records, settings
  optics/             trained-phase frontend and physical control records
  learning/           data contract, model assembly, training, checkpoints
  evidence/           native archive, integrity gate, study artifacts
  protocol_assets/    frozen split and operating-point inputs
```

The primary matrix has four roles and 36 runs:

- `trained_phase_frontend_only`;
- `digital_backend_only` with NAFNet-S;
- `frozen_frontend_serial` with the seed-matched trained phase;
- `joint_frontend_serial` with the same initialization.

A further nine `digital_backend_only` runs use NAFNet-M as a capacity
challenge. They test the large-digital-backend alternative without inventing a
fifth scientific role. The sealed native archive therefore contains 45 runs.
Normal loading performs no historical role translation, and training is an
explicit opt-in.

## Adaptive Measurement

`adaptive_measurement/` owns measurement-conditioned episodes: calibration
observations, delivered-feasibility prediction, `trial / abstain`, Action Echo,
`admit / revert`, later science observations, and canonical episode evidence.
Simulated aberration truth is evaluator-only. Its target deep interface is:

```python
run_adaptive_episode(request, bench) -> AdaptiveEpisodeRecord
```

The Adaptive package follows `protocol / inputs / reachability / adapters /
validation`, with the causal state machine in `episode.py` and write-once
evidence in `evidence.py`. Claim-facing studies live in the leaf `studies/`
package. The physical bench Adapter is added only when measured hardware gives
it a second real implementation. See
`docs/restoration/adaptive-architecture.md` for the active contract.

The coherent reference remains present in primary science observations.
Reference-off acquisition is a named mechanism ablation, not the default
endpoint.

## Dependency direction

```text
data pipeline      flat layers
       \             /
        shared restoration
          /         \
fixed_measurement  adaptive_measurement
```

Both experiments may depend on the frozen `data` pipeline, flat physical
`layers`, and shared Restoration contracts. Shared Restoration imports neither
experiment, and Fixed and Adaptive never import one another. The shared
`optical_bench` unifies 638 nm wavelength, 100 mm focal length, sampled
geometry, aperture, splitter, arm gains, reference phase, and coherent
detection. The separated protocols preserve the distinction between
target-supervised training and measurement-conditioned control.

The frozen simulator is the calibrated
`compact_fourier_4f_equivalent`: an ideal thin-lens Fourier relay represented
by centered FFT, Fourier-plane transfer, and inverse FFT. It does not claim a
calibrated element-by-element model of the physical V-shaped relay. Replacing
it with such a model requires an explicit equivalence and bench-calibration
gate; it cannot silently change the sealed Fixed evidence.
