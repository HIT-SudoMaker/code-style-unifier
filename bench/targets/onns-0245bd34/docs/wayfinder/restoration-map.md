---
title: Close restoration around an intelligent optical front end
label: wayfinder:map
status: open
---

# Close restoration around an intelligent optical front end

## Destination

A reproducible, evidence-preserving Restoration architecture in which a
fixed-reference interferometer predicts a hardware-feasible action, audits a
physically delivered trial through a coherent Action Echo, and selectively
admits or reverts that action before a causally later raw optical observation.
The implementation must remain simple enough to freeze after the bounded
simulation endgame and to transfer to the bench through the same episode
Interface.

## Frozen decisions

- The project and package remain named `restoration`; no version suffix is
  introduced.
- `data` remains an ordered pipeline; `layers` remains a flat collection of
  optical primitives. Both are frozen.
- Shared Restoration owns stable physical/evidence Interfaces; Fixed and
  Adaptive own separate protocols and claims.
- Fixed Measurement remains reproducible historical evidence, a static optical
  baseline, and the capability--limitation bridge. Its protocol and evidence
  identity are not rewritten.
- The Fixed scientific design is closed at ADR-0023. Its four training roles
  and branch controls are stored as distinct canonical records; failed and
  unfavourable outcomes remain part of the evidence, and presentation
  artifacts are regenerated from that evidence.
- The active Fixed matrix is `trained_phase_frontend_only`,
  `digital_backend_only`, `frozen_frontend_serial`, and
  `joint_frontend_serial`. All digital-bearing conditions use the same backend;
  both serial conditions share the seed-matched trained-frontend warm start.
  `reference_arm_only`, `zero_phase_processing_arm_only`, and
  `trained_phase_processing_arm_only` are branch controls, not extra training
  roles. Zero-phase and trained-phase interference outputs always denote the
  coherent, reference-on, two-arm acquisition. The capacity ladder and retired
  eleven-parameter backend are not part of the claim-bearing matrix.
- The active route is a correctability-aware intelligent optical front end,
  not a post-detection restoration network.
- The mechanical delay arm is fixed during an episode. Effective phase and
  drift are calibrated nuisance state; SLM global piston supplies phase-shifting
  diversity.
- The primary science endpoint is a later raw reference-on observation.
  Reference-off acquisition is a mechanism ablation.
- The initial aberration scope is processing-arm differential aberration unless
  broader identifiability is independently established.
- The robust protocol is `4 pre + 4 echo + 1 science`; one optional probe raises
  the bounded protocol to ten observations. `4 + 1` remains a non-audited
  baseline, and the five-observation mode awaits a sideband-separation proof.
- The pre-echo decision is `probe / trial / abstain`; the post-echo decision is
  `admit / revert`. Every trial contributes to Episode Harm even when reverted.
- Simulated aberration truth is evaluator-only.
- Adaptive actions remain full 512 by 512 Fourier-grid phases. Their native SLM
  commands use physical-coordinate projection rather than integer two-times
  pixel replication.
- Bounded simulation uses a 512 by 512 observation grid; the ASI585MM Adapter
  archives native intensity frames before a separately calibrated analysis
  projection.
- Use `correctability estimate` until prospective calibration justifies a
  stronger term.

## Workspace constraints

- `data/raw`, Fixed results, protocol assets, dirty worktrees, `.agents`, and
  `.claude` are outside automatic cleanup.
- `refresh_workspace.py` remains unchanged as an ignored local archival tool.
  It is not run during routine cleanup.
- Only verified reproducible cache state may be removed without a separate
  evidence review.
- Research notes live under `docs/research`; current decisions live in ADRs,
  `project-baseline.md`, and the active Restoration design.

## Closed decisions

- [`Clean the workspace without erasing evidence`](tickets/clean-workspace.md)
- [`Establish the adaptive-optics competitive gap`](tickets/establish-competitive-gap.md)
- [`Reassess the adaptive-optics publication claim against current evidence`](tickets/reassess-adaptive-optics-publication-claim.md)
- [`Define the adaptive restoration scientific contract`](tickets/define-scientific-contract.md)
- [`Separate fixed and adaptive restoration cleanly`](tickets/separate-fixed-and-adaptive.md)
- [`Write the canonical restoration research prompt`](tickets/write-research-prompt.md)
- [`ADR-0020: adopt the intelligent front end`](../adr/0020-adopt-a-fixed-reference-correctability-aware-intelligent-front-end.md)
- [`ADR-0021: adopt action-echo admission control`](../adr/0021-adopt-action-echo-admission-control.md)
- [`ADR-0022: use a full Fourier-grid action and physical SLM projection`](../adr/0022-use-a-full-fourier-grid-action-and-physical-slm-projection.md)
- [`ADR-0023: use a four-role Fixed comparison`](../adr/0023-use-a-four-role-fixed-comparison.md)
- [`Implement and seal Fixed Measurement`](tickets/implement-fixed-measurement.md) — seal 36 primary studies plus nine NAFNet-M digital-capacity studies as native four-role artifacts and keep runtime loading free of historical-name translation.
- [`Plan the restoration code migration`](tickets/plan-code-migration.md) — establish shared physics, seal Fixed, then build Adaptive.

## Active execution

- [`Four-day Restoration design endgame`](../restoration/four-day-endgame.md)
- [`Choose the first native coherent-microscopy demonstration`](tickets/choose-first-native-demonstration.md)
- [`Prove delivered phase-only oracle headroom`](tickets/prove-delivered-phase-only-oracle-headroom.md)
- [`Test correction-action identifiability`](tickets/test-action-identifiability.md)
- [`Test calibration-to-science causal transfer`](tickets/test-calibration-science-transfer.md)

## Remaining decisions

- Whether the physics-only estimator is sufficient or a learned amortized
  estimator materially improves the matched decision frontier.
- Whether one optional uncertainty-resolving probe earns its complete cost
  before the Action Trial.
- The first native coherent specimen and task-facing quality endpoint.

## Out of scope

- Redesigning `data` or `layers`.
- Treating a post-detection neural restoration backend as part of Adaptive.
- Claiming general AO superiority, fluorescence transfer, or fast live control
  from the current coherent quasi-static design.
- Deleting or rewriting protected evidence or worktrees.
