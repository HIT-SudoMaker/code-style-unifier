# 03 — Let every branch return with its siblings

Type: implementation

Status: resolved (2026-07-29)

Blocked by: ticket 01.

## Outcome

`conduct` owns one complete, ordered scientific frontier. Every transition
returns with its siblings, every checkpoint records the whole delivered
family, and public completion appears only when every delivered branch has a
conclusion.

## Scope

1. Begin with a failing replay test in which several propagation branches are
   formed, a later branch advances, and the remaining siblings disappear.
2. Make branch operations checkpoint-free transformations that return their
   scientific facts to `conduct`.
3. Let `conduct`, which can see the family, replace one advanced branch inside
   the complete frontier and record the whole frontier after every
   transition.
4. Carry the formation report with every later checkpoint, including explicit
   refusals and diagnostics.
5. Order delivered branches deterministically by scientific branch identity
   and phase-set level order where applicable.
6. Advance every currently reachable branch before deciding what the public
   call returns.
7. When completion is not yet possible, return the first canonical honest
   waiting Study while preserving every sibling.
8. Admit completed conclusions idempotently through the existing authority
   verbs. During replay, combine already admitted results with the retained
   frontier and propose only missing conclusions.
9. Return the public Result tuple only when every delivered branch has a
   complete admitted conclusion.
10. Replace the flawed partial checkpoint shape directly. Ignore it rather
    than adding a compatibility decoder; immutable evidence remains available
    to ordinary recompilation.
11. Validate that restored siblings share the capabilities and bindings that
    define their common application context.

## Acceptance

- A propagation formation containing 8-, 12-, and 16-state branches survives
  every later checkpoint as one complete ordered family.
- A family with delivered branches and an explicit formation refusal retains
  both the branches and the refusal report.
- Interruption after any branch transition loses no delivered sibling.
- Interruption during conclusion admission reuses existing admitted Results
  and admits only missing conclusions on replay.
- A waiting call is deterministic and honest; it does not conceal reachable
  sibling work.
- Public completion is family-complete rather than latest-branch complete.
- Geometric phase remains one selected cell with continuous orientations; it
  gains no fabricated 8/12/16 phase-set family.
- Operations no longer persist checkpoints or need sibling knowledge.
- The old partial checkpoint shape is not decoded.
- No new public workflow container, task status, or authority verb appears.

## Focused tests

- three delivered propagation branches across several advances and restarts;
- two delivered branches plus one formation refusal;
- interruption immediately after each branch checkpoint;
- interruption before, during, and after each conclusion admission;
- replay with zero, some, and all conclusions already admitted;
- deterministic waiting selection under reordered input;
- shared capability and binding mismatch on restored siblings;
- one geometric branch with continuous orientation and no quantized fiction.

Tests assert on public Studies, Results, admitted references, and replayed
behavior rather than a private queue representation.

## Verification

- focused compiler, conduct, replay, and result tests;
- Pyright with zero errors;
- CSU on every touched production file with zero hard violations;
- architecture tests for checkpoint ownership and dependency direction;
- an empty Rust production diff;
- `git diff --check`.

## Stop and report

Stop if complete-frontier persistence requires a new Rust verb, mutable public
task status, or a new workflow Interface. The fix belongs inside the existing
application operation and authority evidence model.

## Do not add

Do not add `StudyGroup`, a public frontier type, branch registry, generic
workflow engine, checkpoint version framework, compatibility reader, mutable
status store, background scheduler, or special PB quantization.

## Resolution

Commit `dd5bff7` made conduct retain and record the complete delivered
frontier, preserve siblings across interruption, and replay admitted work
without inventing a public workflow type.
