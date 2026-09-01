---
title: Implement and seal Fixed Measurement
parent: Close restoration around an intelligent optical front end
type: task
label: wayfinder:task
status: closed
assignee: codex
blocked_by:
  - Plan the restoration code migration
---

# Implement and seal Fixed Measurement

## Outcome

Expose one deep Fixed Measurement Interface that runs and records the frozen
target-supervised protocol without requiring callers to understand historical
root-level training, frontend, benchmark, or artifact Modules.

## Scientific matrix

The four claim-bearing roles are:

- `trained_phase_frontend_only`;
- `digital_backend_only`;
- `frozen_frontend_serial`;
- `joint_frontend_serial`.

The physical branch controls are:

- `reference_arm_only`;
- `zero_phase_processing_arm_only`;
- `trained_phase_processing_arm_only`.

The reference-on two-arm outputs are:

- `zero_phase_interference_output`;
- `trained_phase_interference_output`.

## Interface target

Callers provide one validated Fixed protocol request and receive one canonical
study record. Protocol expansion, seed-matched frontend initialization,
trainable-parameter selection, physical-control acquisition, evidence writing,
and native evidence loading remain inside the Module. Historical role
translation is absent from the public, load, and train paths.

## Acceptance

- Public Fixed names match the frozen vocabulary exactly.
- All digital-bearing roles use one declared backend contract; both serial
  roles share the seed-matched trained-frontend checkpoint.
- An `*_arm_only` record proves the other arm was blocked; an
  `*_interference_output` record proves both arms were enabled.
- Canonical records bind data identity, split, seed, configuration, optical and
  phase state, initialization lineage, trajectory, checkpoint, per-sample
  measurements, aggregate metrics, failure status, and provenance.
- Existing weights are preserved as native four-role artifacts without a
  runtime compatibility layer.
- The eleven-parameter backend and open-ended capacity ladder are absent. A
  bounded nine-run NAFNet-M digital-only capacity challenge is retained.
- Adaptive imports no Fixed implementation Module.
- Fixed Interface, architecture, archive, and focused regression tests pass
  under the project Python interpreter.

## Non-goals

- Adaptive episode logic or policy design.
- Re-running formal experiments during code migration.
- Deleting historical results.
- Redesigning the frozen `data` pipeline or flat `layers` package.

## Implementation record

- The public package exposes one experiment operation and one optical-record
  operation rather than the historical execution and artifact internals.
- The active compiler emits the four scientific roles directly under one
  native protocol identity.
- NAFNet-S is the common backend in the 36-run primary matrix; NAFNet-M appears
  only in the nine-run `digital_backend_only` capacity challenge.
- Physical records distinguish three arm-isolated intensities from two
  reference-on interference outputs and retain input, reference-phase, and
  trained-phase tensors.
- Run provenance and results retain role, profile, seed, configuration,
  upstream lineage, and metrics. Execution exceptions append immutable failure
  records while leaving the run resumable.
- The public experiment defaults to `load`; `train` is an explicit opt-in.
  The native gate covers 45 studies and all 495 declared study artifacts.
- The CLI exposes only `describe`, `load`, and `train`; `load` reads only the
  native four-role archive.

## Verification

- `python -m compileall` passes for the Fixed package and CLI.
- `python -m pytest tests/restoration -q` passes.
- `git diff --check` passes.
- No formal training was launched and no archived result was rewritten.
- A real native archive load passes for all 45 studies and verifies 495
  content-hashed study artifacts.

## Resolution

Fixed Measurement is sealed behind its five-name public surface. The active
four-role matrix and physical controls use the frozen vocabulary. The native
archive contains the 36-run primary comparison and the nine-run NAFNet-M
digital capacity challenge. Runtime code loads it directly, without an alias
manifest, migration command, or historical-role compatibility layer. Data and
weights are reused without retraining; only evaluation-derived optical records
and presentation artifacts need regeneration. Training remains available
solely through explicit opt-in.
