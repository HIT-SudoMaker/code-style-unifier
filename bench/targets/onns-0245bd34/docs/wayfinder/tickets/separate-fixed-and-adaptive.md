---
title: Separate fixed and adaptive restoration cleanly
parent: Close restoration around an intelligent optical front end
type: grilling
label: wayfinder:grilling
status: closed
assignee: codex
blocked_by:
  - Define the adaptive restoration scientific contract
---

# Separate fixed and adaptive restoration cleanly

## Question

Which Fixed interfaces remain reproducible, which physics is genuinely shared,
and which new concepts belong exclusively to Adaptive Restoration?

## Research boundary

[`Restoration Research Design`](../../restoration-research-design.md) keeps
Fixed Restoration as reproducible historical evidence and limits Adaptive
Restoration to bounded feasibility experiments until the hard gates pass.

## Resolution

ADR-0019 establishes the accepted hierarchy. Stable phase-control,
pupil-aberration, and observation semantics live in the restoration root.
`fixed_measurement` owns target-supervised training and native archive loading;
`adaptive_measurement` owns oracle, episode, and hardware-readiness evidence.
The two protocols do not import one another, and shared restoration Modules do
not depend on either experiment.

Fixed and Adaptive now compose the same dual-arm propagation kernel, but Fixed
retains its target-supervised input and Adaptive retains its causal observation
history. The Adaptive line starts with O1/O2/O3 oracle headroom and E0 hardware
readiness, not with a shared training engine or a universal optical-scene
abstraction.

The ownership decision and physical relocation are complete. Root
compatibility exports and the former Fixed bridge have been removed.
