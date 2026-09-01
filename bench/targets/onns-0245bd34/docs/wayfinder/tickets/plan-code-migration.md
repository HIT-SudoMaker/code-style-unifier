---
title: Plan the restoration code migration
parent: Close restoration around an intelligent optical front end
type: grilling
label: wayfinder:grilling
status: closed
assignee: codex
blocked_by:
  - Separate fixed and adaptive restoration cleanly
  - Write the canonical restoration research prompt
---

# Plan the restoration code migration

## Question

In what order should the shared dual-arm measurement physics be established,
the Fixed-era root Modules be migrated behind an active target-conditioned
Fixed Measurement Interface without changing archived evidence identity, and
the measurement-conditioned Adaptive episode become one deep Module with
simulation and bench Adapters?

## Resolved Fixed boundary

The Fixed scientific design is closed. Its claim-bearing roles are
`trained_phase_frontend_only`, `digital_backend_only`,
`frozen_frontend_serial`, and `joint_frontend_serial`. Its branch controls are
`reference_arm_only`, `zero_phase_processing_arm_only`, and
`trained_phase_processing_arm_only`; zero-phase and trained-phase interference
outputs always refer to reference-on, two-arm acquisition. The implementation
migration must preserve historical evidence identity while writing new runs as
immutable canonical records under this vocabulary. Historical runtime names do
not enter the new public, load, or train Interfaces.

This resolves the Fixed seam. Shared dual-arm physics is now implemented; the
Adaptive episode remains the next deep Module.

## Resolution

Migration proceeds in four sealed stages:

1. expose the shared dual-arm propagation and observation semantics without
   importing either experiment package;
2. place the target-supervised Fixed protocol behind one Fixed Measurement
   Interface and materialize native role identities;
3. verify the four-role Fixed matrix, branch controls, immutable evidence, and
   archived-result identity, then freeze Fixed;
4. design and implement the measurement-conditioned Adaptive episode as a
   separate deep Module using the shared topology only after the Fixed ticket
   closes.

This order preserves one physical apparatus while preventing Fixed replay data
and target-visible optimization from leaking into Adaptive. Stages 1--3 are
complete; the runtime compatibility boundary has been removed.
