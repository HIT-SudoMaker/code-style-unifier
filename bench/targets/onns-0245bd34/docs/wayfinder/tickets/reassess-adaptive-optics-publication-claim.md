---
title: Reassess the adaptive-optics publication claim against current evidence
parent: Close restoration around an intelligent optical front end
type: research
label: wayfinder:research
status: closed
assignee: codex
blocked_by: []
---

# Reassess the adaptive-optics publication claim against current evidence

> Historical resolution. ADR-0020 replaces the `self-verifying` name,
> `continue` action, and reference-free endpoint with `intelligent optical front
> end`, `probe`, and prospective reference-on science, respectively.

## Question

After reading the local DONN research collection, the 2025 *Laser & Photonics
Reviews* perspective on metasurfaces in adaptive optics, and current primary
literature, which physical and algorithmic claim remains defensible for a
PhotoniX- or *Light: Science & Applications*-quality restoration programme,
and what minimum falsification experiment should decide whether to proceed?

## Resolution

The source-grounded synthesis is recorded in
[`Restoration 转向自适应光学：文献竞争面、可证伪主张与快速实验路线`](../../research/restoration-adaptive-optics-literature.md).

The decision is **Narrow and proceed by gates**. Speed, single-shot sensing,
few-probe estimation, compact neural inference, and nominal SLM pixel count do
not constitute a defensible novelty claim by themselves. The remaining
conditional claim is a self-verifying active-AO episode that selects bounded
calibration probes, decides whether to correct, continue, or abstain, holds the
chosen pre-detection correction, and is judged on a later independent raw
science observation under a complete matched budget.

Before estimator or policy development, the programme must pass three hard
gates: delivered phase-only oracle headroom, action identifiability under the
allowed observation budget, and causal transfer from calibration measurements
to a separately acquired science frame. Failure at any gate narrows or kills
the corresponding claim.
