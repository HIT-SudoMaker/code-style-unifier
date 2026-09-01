# Adaptive Measurement

Adaptive Measurement owns one measurement-conditioned optical episode. It
shares the frozen interferometer with Fixed Measurement, but it does not share
Fixed's target-visible training protocol or archive.

## Public Interface

```python
run_adaptive_episode(request, bench) -> AdaptiveEpisodeRecord
```

The request contains only an episode identity, the real intensity commanded on
SLM1, and one immutable policy. It cannot carry a clean target, hidden
aberration, complex replay field, pupil truth, optical-bench configuration, or
oracle action. Those facts remain behind the bench Adapter or in evaluator-only
studies.

## Reading order

```text
protocol/       request and policy contracts
inputs/         load -> prepare -> perturb -> intensity replay
reachability/   four-step inference, delivered projection, locked Echo prediction
episode.py      pre -> propose -> abstain/trial -> Echo -> admit/revert -> science
evidence.py     write-once causal record and complete event ledger
adapters/       simulated acquisition and calibration Adapter
validation/     Oracle Ladder and hardware-readiness gates
```

`episode.py` is deliberately small. It never imports the optical propagator or
the modal fitter. The Adapter binds acquisition and calibrated reachability to
one calibration identity, so a future physical Adapter can replace simulation
without changing the episode state machine.

## Causal protocol

```text
4 reference-on pre observations
        -> calibrated correction proposal
        -> abstain, or deliver one trial
        -> 4 reference-on Action Echo observations
        -> admit or revert
        -> 1 later raw reference-on science observation
```

An admitted or reverted episode uses nine camera reads. An abstained episode
uses four pre reads and one safe science read, so policies cannot declare a
budget below five. The canonical record preserves
all raw intensities, commanded and delivered phases, the pre-trial locked Echo
prediction, decisions, thresholds, calibration identity, dose, timing, trial
and Echo exposures, and the prospective science frame. A reverted trial is
never erased. Calibrated utility uncertainty and evaluator-only trial-harm
scoring remain distribution-study gates; the present `should_trial` decision
is a deterministic mechanism threshold, not the final selective policy.

Action Echo audits delivery conformity. It does not see the later science
frame and does not certify recovery against a clean image.

The current simulated delivery keeps the calibrated spatial action invariant
across its four piston states. Quantization, response gain, drift, and local
crosstalk are applied under that separable contract. A physical Adapter must
measure this separability or replace scalar-piston demodulation with the actual
pixel-wise delivered states.

For the same-SLM2 emulator, the hidden phase, policy action, and piston form one
physical command before that delivery model is applied. Policy observations
retain only the commanded action and its delivered differential view; the full
composite command and delivery are stored solely in evaluator evidence. This
prevents simulator truth from entering estimation while preserving an auditable
record of what the simulated SLM actually displayed.

## Active commands

Run the physically distinct O1/O2/O3 truth gate:

```powershell
& 'C:\Users\Administrator\miniforge3\envs\research_env\python.exe' `
  -m experiments.restoration.run_adaptive_measurement `
  oracle-ladder --project-root . --device cpu
```

Run the controlled same-device differential-correction study:

```powershell
& 'C:\Users\Administrator\miniforge3\envs\research_env\python.exe' `
  -m experiments.restoration.run_adaptive_measurement `
  differential-correction --project-root . --device cuda `
  --degradation-profile medium --aberration-mode defocus
```

The study keeps the Fixed-aligned degraded amplitude replay, but labels the
hidden phase as a same-device processing-arm emulator. B2-to-B0 aberration
removal and B2-to-clean restoration remain separate endpoints. It is not
independent-aberrator or native-microscope evidence.

Before a physical episode, fill
`protocol_assets/e0_hardware_readiness.template.json` and run
`check-hardware`. No simulated default may substitute for missing LUT,
registration, timing, coherence, throughput, or correction-lifetime evidence.

The old target-visible observation-sanity and intensity-only recovery runners
were removed. Their useful falsification logic is represented by the Oracle
Ladder and the canonical episode; duplicate nine-frame orchestrators are not
kept as compatibility paths.
