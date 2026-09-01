---
title: Define the adaptive restoration scientific contract
parent: Close restoration around an intelligent optical front end
type: grilling
label: wayfinder:grilling
status: closed
assignee: codex
blocked_by:
  - Establish the adaptive-optics competitive gap
---

# Define the adaptive restoration scientific contract

> Historical resolution. ADR-0020 supersedes its reference-free primary
> endpoint with a later raw reference-on science observation and retains
> reference-off acquisition only as a mechanism ablation.

## Question

What exact observations, correction state, causal acquisition order, physical
output, comparison budget, claims, and kill tests define adaptive restoration?

## Resolution

The provisional candidate contract is defined in
[`Restoration Foundations`](../../research/restoration-foundations.md) and
frozen for the external audit in
[`restoration-research-prompt.md`](../../prompts/restoration-research-prompt.md).

The reference offset is fixed at \(\delta_{\mathrm{ref}}=0\); the
input-amplitude SLM is held; the Fourier-plane phase-only SLM is the sole
dynamic optical actuator; the reference arm is calibration-only; and evidence
must come from a later, reference-free raw science observation. Continue,
correct, and abstain are compared under a complete acquisition and compute
budget. A post-detection restoration network is outside the core candidate.

This resolution freezes the object to be researched. It does not accept the
candidate as feasible or novel. The external audit subsequently returned
`Narrow`, authorizing only evidence-preserving cleanup and the bounded
falsification programme consolidated in
[`Restoration Research Design`](../../restoration-research-design.md).
