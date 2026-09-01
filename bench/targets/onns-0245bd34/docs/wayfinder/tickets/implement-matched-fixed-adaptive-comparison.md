---
title: Implement the matched Fixed--Adaptive comparison
parent: Close restoration around an intelligent optical front end
type: task
label: wayfinder:task
status: claimed
assignee: codex
blocked_by: []
---

# Implement the matched Fixed--Adaptive comparison

## Outcome

Produce one auditable comparison Module that evaluates sealed Fixed and
truth-blind Adaptive actions on identical degraded scenes, optical states,
active-support crops, detector conditions, and timing clocks without rewriting
the Fixed archive.

The governing specification is
[`fixed-adaptive-comparison-spec.md`](../../restoration/fixed-adaptive-comparison-spec.md).

## Work

1. Define one canonical matched-case identity and separate evaluator, Fixed,
   and Adaptive information views.
2. Load the sealed Fixed checkpoints through their public Interface; do not
   introduce role aliases, compatibility layers, or retraining.
3. Evaluate `B0`, `B1`, `B2/fixed`, `B2/adaptive`, and `B3` on paired cases.
4. Implement the metric vector for image fidelity, optical mechanism, safety,
   decision quality, and resource cost.
5. Record both native-protocol timing and the equal-clock-budget control at the
   same camera/SLM operating constraints.
6. Write immutable per-case evidence before producing summaries or figures.

## Module target

Expose one operation:

```python
run_matched_comparison(request) -> MatchedComparisonRecord
```

The comparison is a leaf Module. Fixed and Adaptive must not depend on it. It
may use only their public experiment and evidence Interfaces.

## Acceptance

- Fixed formal artifact identities and hashes remain unchanged.
- A test proves all actor views reject evaluator-only truth.
- Every method in a paired comparison has the same canonical case identity.
- The final record distinguishes clean-reference PSNR from aberration-removal
  gain and refuses dimensionally invalid comparisons.
- Native and equal-clock ledgers count every frame, SLM state, exposure,
  settling interval, transfer, and computation interval.
- PSNR/SSIM are accompanied by mechanism, safety, decision, and cost metrics.
- Low-SNR harmful candidates are represented as abstentions or reversions, not
  silently excluded failures.
- Focused tests, the Restoration test suite, compile checks, and
  `git diff --check` pass under the project Python interpreter.

## Parallel contract

This ticket can run in parallel with
[`Implement the same-device Adaptive aberration bench`](implement-same-device-adaptive-aberration-bench.md).
It owns comparison orchestration, metric semantics, and cross-line evidence.
It does not own phase-SLM calibration, acquisition, or the Adaptive episode
Implementation.

## Non-goals

- Changing the four Fixed roles or their archived training protocol.
- Training a new restoration teacher for Adaptive.
- Building the physical bench Adapter.
- Selecting manuscript figures before the evidence gate passes.

## Implementation progress — 2026-08-16

The specification and case vocabulary are frozen, but the claim-facing Module
is intentionally not implemented yet. A first callback-based harness was
rejected during architecture review because an in-process closure could read
evaluator truth, its timing ledger was synthetic, and its derived JSON did not
retain enough raw evidence to reproduce metrics.

Implementation resumes only when it can consume the sealed Fixed public record
and the canonical `AdaptiveEpisodeRecord` directly, validate their shared case
and calibration identities, and derive both native and equal-clock ledgers from
actual events. The ticket therefore remains claimed; no partial comparison API
is archived as if it were trustworthy evidence.
