# 08 — Let Result close and replay exact evidence

Type: implementation

Status: resolved (2026-07-28)

Blocked by: tickets 05A, 06, and 07.

## Outcome

Result records one exact scientific closure. Replay restores it without
repeating consultation, solver execution, or numerical propagation.

## What to build

- Keep generic `ResultClosure` in shared science and move metalens conclusion
  values under `science/metalens/`.
- Retain distinct `PropagationResult` and `GeometricResult` types.
- Encode both through the single stable document schema
  `metacraft.science.metalens.result`.
- Store only the scientific conclusion, exact fabrication output, evaluation
  references, closure reference, origin, and replay provenance.
- Read aim, objectives, control strategy, aperture regime, route, and proof
  meaning from the exact cited closure instead of duplicating those facts in
  the Result document.
- Make conclusion accept only complete admitted proof evidence. It may
  validate references and assemble immutable output; it may perform no
  aperture reconstruction, propagation, focus evaluation, power integration,
  or leakage calculation.
- Restore strategy-specific Result values by following the closure and typed
  fabrication references, not a duplicated route label.
- Replay completed Results and waiting Studies from authority objects without
  invoking Adviser, Lumerical, Torch, device observation, or FFT work.
- Persist admitted scientific values and solver artifacts; exclude CUDA
  workspaces, spectra, padded tensors, and other temporary numerical buffers.
- Retire the remaining `science/routes/` package, `interpret` operations, and
  `*_operation` suffixes. Use the common metalens verbs:
  `assign_aperture`, `form_field`, `propagate_field`, `evaluate_focus`, and
  `conclude`.
- Delete old Result schema readers and route-shaped replay caches.

## TDD seam

Using compact recorded evidence:

1. conclude and replay one propagation Result for each 8/12/16 phase set;
2. conclude and replay one geometric Result with continuous orientations;
3. replay one waiting Study carrying an incomplete FocusSurvey;
4. disable Adviser, solver, Torch, and device observation during replay;
5. reject a Result whose task, proof, evaluation, or fabrication reference
   belongs to another closure.

## Acceptance

- One metalens Result schema supports two distinct typed scientific outputs.
- Result contains no second copy of design or proof authority.
- `conclude` is pure closure validation and immutable assembly.
- Replay produces byte-identical conclusion documents and no repeated work.
- No `science/routes/`, `interpret`, route cache, or compatibility decoder
  remains.
- Conduct returns independent propagation quantizations and one geometric
  result when their proofs are complete; otherwise it returns honest waiting
  studies.
- Focused Result, conduct, replay, evidence, and architecture tests pass.
- Pyright reports zero errors; touched files have zero CSU hard violations.
- `git diff -- rust` is empty.

## Do not add

Do not add a universal Result payload, workflow serializer, replay engine
registry, mutable result builder, or fabricated completion path.

## Verification

- Baseline: `25b68da` (`Let Lumerical contain one work life (ticket 07)`).
- Focused Result, replay, conduct, closure, evidence, standard-study, and
  architecture tests passed.
- Independent main-agent replay and architecture check:
  `20 passed in 24.76s`.
- Pyright reported `0 errors, 0 warnings`.
- CSU reported `0 hard_violation` across all 16 touched production files.
- Independent Spec review: PASS, `0 blocker/high`.
- Independent Standards review: PASS, `0 blocker/hard`.
- `git diff --check` passed and `git diff --name-only -- rust` was empty.
- The complete non-live suite is intentionally deferred to ticket 09, where
  the final architecture ratchet is verified once.
