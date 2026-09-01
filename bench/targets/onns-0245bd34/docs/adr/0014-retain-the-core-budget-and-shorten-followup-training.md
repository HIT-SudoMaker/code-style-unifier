---
status: accepted
---

# Retain the Core Budget and Shorten Follow-up Training

The completed 36-run core matrix remains archived under its original 6,000
optimizer-update budget. Capacity and mechanism experiments use 3,000 updates,
with micro-batch 2, effective batch 8, the fixed learning policy, and
`search=None` unchanged.

This revision follows the complete core trajectories rather than a new
hyperparameter search. The nine optical-only runs reached their best validation
PSNR between updates 2,975 and 5,950, but restricting trajectory comparisons to
the first 3,000 updates loses only 0.015 dB on average and at most 0.035 dB. All
27 digital, frozen, and joint NAFNet-S runs reached their best validation PSNR
between updates 297 and 743. Continuing those runs to 6,000 added no best-model
value and introduced substantial late-training degradation in one frozen run.

Consequences:

- The existing core checkpoints, trajectories, report, and gate are preserved;
  they are not renamed or represented as 3,000-update training runs.
- All 54 capacity runs and all 54 mechanism runs stop after 3,000 optimizer
  updates and retain `best.pt` as the evaluation checkpoint.
- Cross-stage trajectory tables use update 3,000 as the declared comparison
  cutoff. Any checkpoint-based result continues to disclose the checkpoint's
  actual training budget and selection update.
- Core optical warm starts remain the seed- and profile-matched `best.pt`
  checkpoints produced by the completed 6,000-update core runs.
- The core gate binds only the core matrix. A change to a downstream capacity
  or mechanism budget cannot invalidate completed core evidence. The verifier
  continues to accept the already frozen version-one gate after validating its
  original full-matrix identity and all 396 artifact hashes.
- This is a preregistered protocol revision grounded in completed convergence
  evidence, not Optuna calibration or architecture-specific model shopping.
