# Let one frontier return one science

Type: implementation

Status: resolved (2026-07-29)

Blocked by:
[Let dependencies flow without return](03-let-dependencies-flow-without-return.md).

## Outcome

Conduct advances one private, ordered, fail-closed frontier; replay restores
that science from one authority snapshot; propagation and geometric routes
share one declared and executed metalens proof tail.

## Scope

1. Add failing tests for missing-leaf replace and remove, mixed replay
   snapshots, repeated result scans, and duplicated common relationship tail.
2. Give conduct one private `_Frontier` owner for ordered branches, exact
   replace, exact remove, snapshots, and invariants.
3. Keep scientific sibling ordering in scientific operations. Conduct
   preserves it and knows no metalens phase levels.
4. Make an absent replacement or removal target raise immediately.
5. Observe Authority once per replay, build one private index, and restore
   branches, admitted results, and formation from that exact view.
6. Eliminate per-result full scans and repeated checkpoint reads.
7. Concentrate the identical
   `aperture -> field -> focal region -> focus` relationship tail in one
   private declaration owner.
8. Preserve the existing common execution owner in `_local/proof_tail.py`.
9. Keep propagation quantization deterministic and cyclic; keep geometric
   placement one selected cell plus continuous orientations.

## Acceptance

- A transition replaces or removes exactly one live leaf or raises.
- One checkpoint contains the complete delivered sibling family.
- Replay calls `Authority.view` once and cannot mix revisions.
- Replay lookup is indexed rather than `results x decisions`.
- Propagation operation order remains deterministic for 8, 12, and 16 phase
  states.
- Geometric phase does not acquire phase levels or an orientation sweep.
- The common relationship tail and common execution tail each have one owner.
- No public Frontier or workflow type appears.

## Focused tests

- missing, duplicate, replace, remove, converge, and sibling frontier cases;
- interrupted and idempotent checkpoint/replay;
- changing fake Authority views prove snapshot coherence;
- view-call and decision-scan counts;
- propagation 8/12/16 order and 0/2π seam;
- geometric continuous orientation;
- relationship-tail architecture test.

## Verification

- focused conduct, replay, propagation, geometric, and architecture tests;
- Pyright;
- touched-file CSU;
- production Rust diff is empty;
- fixed-range `git diff --check`.

## Stop and report

Stop before adding scientific ordering to conduct, changing matching physics,
altering checkpoint bytes, implementing large-NA assignment, or touching Rust.

## Do not add

Do not add a public Frontier, workflow engine, task status, queue framework,
registry, optimizer, orientation sweep, or compatibility alias.

## Resolution

Conduct now advances one private, identity-exact `_Frontier`. Scientific
operations choose sibling order; the frontier preserves it, records complete
snapshots, and raises on a missing or repeated live leaf.

`recall_science` observes Authority once, indexes admitted decisions by body
reference, caches immutable fetches, and restores the latest branch family,
formation report, admitted conclusions, and completed results from that same
revision. The local composition root consumes this one private value and
continues admission from its observed revision.

Propagation and geometric relationships retain strategy-local aperture
assignment, then share one private field-to-focus declaration. Their existing
execution tail remains owned by `_local/proof_tail.py`; propagation keeps
deterministic 8/12/16 quantization and geometric phase keeps one selected cell
with continuous orientation.

Verification completed with 121 focused conduct, replay, propagation,
geometric, delivery, and architecture tests; project Pyright at zero errors
and warnings; touched production CSU at zero hard violations; an empty
production Rust diff; and a clean fixed-range diff check.

A post-integration review found one missing persistence edge: converged
siblings contracted the in-memory frontier without recording that removal.
Conduct now records the contracted snapshot immediately, and a focused replay
regression proves the durable frontier contains one leaf.
