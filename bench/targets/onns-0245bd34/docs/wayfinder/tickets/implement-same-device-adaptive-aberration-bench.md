---
title: Implement the same-device Adaptive aberration bench
parent: Close restoration around an intelligent optical front end
type: task
label: wayfinder:task
status: claimed
assignee: codex
blocked_by: []
---

# Implement the same-device Adaptive aberration bench

## Outcome

Complete the minimum simulation and physical-transfer path in which the present
processing-arm phase SLM emulates a hidden differential Zernike aberration,
delivers a truth-blind corrective action, audits it through Action Echo, and
admits or reverts it before a later raw camera observation.

The governing specification is
[`same-device-aberration-emulator-spec.md`](../../restoration/same-device-aberration-emulator-spec.md).

## Work

1. Finish the existing `run_adaptive_episode(request, bench)` deep Module with
   explicit observation, estimate, projection, decision, trial, Echo,
   admission/reversion, science, and evidence states.
2. Keep amplitude blur/noise in the shared pre-SLM1 data pipeline, hidden
   Zernike phase on the processing SLM, and detector noise per exposure.
3. Extend the simulation Adapter without exposing complex fields or injected
   coefficients to the policy.
4. Implement calibrated same-device composition of hidden aberration, spatial
   corrective action, and four-step global piston.
5. Calibrate LUT, pupil support, relative reference phase, scale, parity,
   centre, registration, native physical-coordinate projection, and timing.
6. Run the bounded Zernike suite, low-SNR rejection controls, and the minimum
   bench subset before expanding the experiment.

## Interface discipline

Do not add another runner or a tunable-reference Interface. Simulation and
physical acquisition remain Adapters at the existing bench seam. Phase
delivery and hardware-specific composition stay inside those Adapters.

## Acceptance

- The policy receives raw intensities, delivered pistons, `D`, calibration,
  history, and budget only; evaluator truth is inaccessible by construction.
- The phase SLM receives the calibrated sum of hidden emulator phase,
  corrective action, and measurement piston without integer 2-by-2 mapping.
- The simulation gate reaches at least 6 dB median held-out `B2` versus `B1`
  aberration-removal gain across light, medium, and heavy replay profiles.
- Unsafe low-SNR or drift cases abstain or revert; a reverted trial is retained
  as an executed exposure and never erased from evidence. The distribution
  study later assigns evaluator-only harm outcomes.
- Accepted corrections improve a separately acquired later raw science frame
  and outperform sham, opposite-phase, and equal-RMS controls.
- Every raw intensity, command, delivered phase, calibration identity, and
  timing event is retained in canonical evidence.
- Claims and result labels say `same-device differential-aberration emulator`,
  never independent incoming aberration or native microscope AO.
- Focused tests, the Restoration test suite, compile checks, and
  `git diff --check` pass under the project Python interpreter.

## Parallel contract

This ticket can run in parallel with
[`Implement the matched Fixed--Adaptive comparison`](implement-matched-fixed-adaptive-comparison.md).
It owns Adaptive episode behaviour, simulated/physical bench Adapters, and
calibration evidence. It does not own Fixed replay, cross-line summaries, or
publication metric aggregation.

## Non-goals

- Adding a phase plate, moving delay, third SLM, or native specimen.
- Treating Gaussian/disk blur as a pupil-phase aberration.
- Using a teacher restoration network to generate the Adaptive action.
- Claiming that four-step sensing reconstructs information lost before SLM1.

## Implementation progress — 2026-08-16

The deep `run_adaptive_episode(request, bench)` Module is implemented and is
now the only B2 orchestration path used by differential-aberration validation.
It owns four pre observations, replay-conditioned fitting, calibrated delivered
projection, can/should gates, trial/abstention, four-frame Echo,
admission/reversion, later raw science, and complete trial exposure history.
The simulated bench privately owns hidden aberration and one phase-delivery
Implementation used for projection, prediction, and acquisition.

The canonical record retains every trial and Echo exposure, including reverted
actions. It does not yet claim calibrated utility uncertainty or a formal harm
score; those require the held-out distribution and remain part of this open
ticket. The simulated four-step delivery now also freezes one calibrated
spatial state across the four global-piston steps. Hardware must validate that
separability before scalar-piston demodulation is accepted.

The same-device Adapter now composes injected hidden phase, policy action, and
global piston before one nonideal delivery operation. Policy observations keep
only the action and delivered differential view; `evaluation.pt` retains the
full composite command and delivery as evaluator-only evidence. The policy
also rejects budgets below the five-read safe episode before acquisition.

The earlier 10,000-photon gains of 21.7377--24.6431 dB and the 1,000-photon
reversion diagnostic are withdrawn as claim evidence. They were generated
before B1, B2, and B3 shared the same nonideal composite-delivery path: B2
delivered hidden phase and action together, while B1 and B3 applied the hidden
phase outside the SLM delivery model. They remain historical debugging values
only and must not be cited as current Adaptive performance.

The v5 study now acquires B1, B2, and B3 through one same-device Adapter and
records each full composite command and delivered state in evaluator-only
evidence. Its B3 artifact also retains the quiet B0 target, every raw candidate
observation, every complete composite delivery, the evaluator error, and the
selected candidate identity. Fresh light, medium, and heavy results must be
generated before the 6 dB gate or any end-to-end clean-gain statement is
accepted.

A non-archival light-profile smoke run verified that all three claim states are
present. Its aberration-removal and clean-endpoint metrics moved in opposite
directions, so it is a plumbing diagnostic, not restoration evidence; this
reinforces why calibrated utility and harm remain open gates.

The complete Restoration suite passes with 640 tests. This ticket remains
claimed because the bounded five-family/two-strength distribution study,
formal sham/opposite/equal-RMS controls, native physical-coordinate projector,
measured LUT/registration/timing, and physical bench Adapter are not complete.
