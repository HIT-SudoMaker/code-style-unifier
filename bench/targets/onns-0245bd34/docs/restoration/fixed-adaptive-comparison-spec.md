# Fixed--Adaptive matched comparison specification

- Status: approved for implementation
- Scope: cross-line evaluation, evidence, and timing
- Protected evidence: sealed Fixed Measurement archive

## Decision

Fixed and Adaptive use the same prepared degraded scene, frozen optical bench,
phase-delivery model, detector model, active-support crop, and evaluation
operations. They do not receive the same information and they do not have the
same acquisition protocol.

Fixed remains the target-visible, offline-trained, frozen-action experiment.
Adaptive remains the target-blind, observation-conditioned, selectively
admitted experiment. The comparison measures the consequences of those two
information contracts without rewriting either one.

The sealed Fixed archive is immutable. New results are a matched stress-test
overlay, not a fifth Fixed training role and not a replacement archive.

## Scientific question

For the same degraded SLM1 command and the same delivered optical disturbance,
when is a frozen action preferable, when is an observation-conditioned action
preferable, and when should the optical front end abstain?

The comparison must distinguish three effects:

1. restoration of blur and noise already embedded in the displayed input;
2. correction of a persistent differential pupil aberration in the processing
   arm;
3. performance gained merely by spending more frames, exposure, or wall time.

## Shared case identity

Every matched case binds the following immutable fields:

- source dataset, split, scene identity, and source seed;
- 256 by 256 preparation and centred 512 by 512 padding;
- degradation profile and seed;
- commanded HDSLM80RA Plus amplitude-replay field `D`;
- frozen optical-bench configuration and calibration identity;
- hidden aberration identity and strength, evaluator-only when present;
- phase-delivery and detector-noise configuration;
- active-support crop, historical Fixed-aligned crop, and metric version;
- camera clock, exposure, SLM-state count, and timing-ledger version.

One canonical case identifier is calculated before an actor is selected. A
result is not matched if any field above differs.

## Information views

The evaluator owns clean `X`, degradation truth, hidden aberration truth, `B0`,
and the delivered-space oracle. No acting policy may read them.

The Fixed actor may read only its sealed checkpoint, frozen phase, `D`, and
frozen calibration. It receives no current-scene quadrature history.

The Adaptive actor may read `D`, causal pre-action intensities, delivered
pistons, frozen calibration, action history, and budget state. It may not read
clean `X`, injected coefficients, an oracle command, or episode-later metrics.

The comparison Module enforces these views structurally rather than relying on
call-site discipline.

## Comparison states and actors

The physical states retain the established vocabulary:

- `B0`: the same `D`, with no added differential aberration;
- `B1`: the same `D`, with a persistent hidden aberration and no correction;
- `B2`: the same `D` and aberration, with a truth-blind delivered action;
- `B3`: the same `D` and aberration, with an evaluator-only delivered-space
  oracle action.

`B2` is evaluated with two actors:

- `fixed_frozen_action`: the sealed, specimen-independent Fixed phase;
- `adaptive_observation_conditioned_action`: the current-scene action selected
  from allowed observations.

The existing Fixed restoration table remains separate and unchanged:

- `trained_phase_frontend_only`;
- `digital_backend_only`;
- `frozen_frontend_serial`;
- `joint_frontend_serial`.

Those four roles quantify target-supervised restoration of baked input
degradation. `B0--B3` quantify differential-aberration removal and delivered
control. A paper table may align their endpoints, but it may not merge their
names or claim that their gains have the same denominator.

## Timing and equal-budget controls

"Same speed" means the same camera clock, SLM refresh constraints, exposure
settings, transfer path, and timing accounting. It does not mean pretending
that a one-frame Fixed protocol and a nine-observation Adaptive protocol have
equal latency.

Two timing views are mandatory:

1. `native_protocol`: Fixed acquires its later science frame with its frozen
   action; Adaptive uses `4 pre + 4 echo + 1 science`.
2. `equal_clock_budget`: both occupy the same nine camera slots. Fixed holds
   its action throughout. Its repeated-frame average is reported only as a
   temporal-averaging control; its final raw frame remains the causal endpoint.

At 60 Hz, nine camera slots have an ideal exposure-clock floor of 150 ms.
Measured SLM settling, transfer, computation, and synchronization are added to
that floor. Every result records frames, SLM states, exposure dose,
time-to-decision, time-to-science, and total wall time.

## Metric contract

No single scalar is allowed to define success. Metrics are reported as a
vector with explicit primary endpoints.

### Evaluator-only image fidelity

- active-support PSNR and SSIM;
- normalized mean-square error and mean absolute error;
- historical `fixed_aligned_*` metrics when the full-canvas archive is used.

### Optical mechanism

- `B2` versus `B1` aberration-removal gain;
- `B2` versus `B0` residual loss;
- delivered-space `B3` headroom and recovered-headroom fraction;
- MTF50, MTF10, valid-band MTF area, and passband error;
- cross-term NRMSE, interference visibility, throughput, and saturation rate;
- evaluator-only pupil-phase or Zernike error in simulation.

### Safety and decision quality

- accepted, reverted, and abstained episode counts;
- harmful-correction rate on the later raw science frame;
- Echo false-admit and false-reject rates;
- coverage--risk curve and delivered-oracle regret;
- noise amplification, ringing, overshoot, and background non-uniformity.

### Resource cost

- camera reads, SLM states, exposure dose, settling time, computation time,
  time-to-decision, time-to-science, and correction lifetime.

Edge or spectral energy alone is never a benefit metric: noise and ringing can
increase both. An action is admitted only when physical conformity passes and
the lower confidence bound of predicted utility is positive under declared
safety constraints.

## Module shape

The matched comparison is a leaf Module. Fixed and Adaptive do not import it.
It reads their public records and invokes their public experiment Interfaces;
it does not reach into training, sensing, or decision Implementations.

Its external Interface is one operation:

```python
run_matched_comparison(request) -> MatchedComparisonRecord
```

Case expansion, information-view enforcement, timing normalization, metric
calculation, evidence hashing, and summary generation remain behind that
Interface. Do not add a universal Fixed/Adaptive experiment schema or a family
of pass-through adapters.

## Minimum experiment matrix

The first claim-bearing matrix uses:

- the same held-out scenes at `light`, `medium`, and `heavy` input degradation;
- `B0`, `B1`, both truth-blind `B2` actors, and `B3`;
- the native-protocol and equal-clock-budget timing views;
- a declared low-SNR stress set in which abstention or reversion is expected.

Results are paired by case identifier. Distribution summaries retain
per-scene results and confidence intervals; favourable cases may not be
silently filtered.

## Acceptance

- The sealed Fixed protocol, weights, metrics, and archive hashes are not
  changed.
- All actors consume the same case identity and declared optical configuration.
- Automated tests prove that actor views cannot access forbidden truth.
- Active-support and Fixed-aligned metrics are both reproducible from evidence.
- Native and equal-clock timing ledgers include every read, state, settle,
  transfer, computation, and exposure.
- A low-SNR or deliberately harmful candidate is rejected or reverted rather
  than reported as a successful correction.
- The final record makes gain denominators explicit and never compares the
  current approximately 25 dB aberration-removal gain directly with a clean
  reference PSNR.

## Non-goals

- Retraining or renaming the four sealed Fixed roles.
- Claiming that equal hardware implies equal information or equal latency.
- Reducing the decision to PSNR, SSIM, sharpness, or one learned score.
- Treating an optional post-detection restoration backend as the Adaptive
  optical policy.
