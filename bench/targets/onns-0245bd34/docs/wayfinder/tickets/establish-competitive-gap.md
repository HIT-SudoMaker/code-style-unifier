---
title: Establish the adaptive-optics competitive gap
parent: Close restoration around an intelligent optical front end
type: research
label: wayfinder:research
status: closed
assignee: codex
blocked_by: []
---

# Establish the adaptive-optics competitive gap

> Historical resolution. ADR-0020 replaces `self-verifying active adaptive
> optics` as the leading name with `correctability-aware intelligent optical
> front end`; the underlying risk and prospective-evidence requirements remain.

## Question

What have conventional, sensorless, computational, and learning-assisted
microscopy adaptive-optics methods already demonstrated, and which
publication-level gap remains defensible under this project's actual optical
and acquisition constraints?

## Resolution

The source-grounded synthesis is
[`Adaptive Restoration: Competitive Gap`](../../research/2026-07-26_adaptive-restoration-competitive-gap.md).

Phase-only correction, few fixed probes, unknown samples, prescan-and-hold,
raw science output, learning-assisted wavefront prediction, uncertainty
estimation, and Fourier-domain evidence all have strong prior art. They cannot
individually carry the paper.

The leading conditional gap is self-verifying active adaptive optics:
sequentially choose calibration probes, stop when evidence is sufficient,
abstain when prospective improvement is unreliable, and judge the decision on
a later independent science observation under matched photon, readout, switch,
and time budgets. This is not yet an accepted project claim; it advances to the
scientific-contract ticket for falsification and scope decisions.
