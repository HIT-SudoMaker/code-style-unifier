# 07 — Let dispatch contain one work life

Type: implementation

Status: resolved (2026-07-29)

Blocked by: ticket 06.

## Outcome

Science requests complete evidence gathering through two natural Lumerical
dispatch verbs. Sweep planning and execution details remain inside the
Adapter.

## Interface

- `gather_periodic_transmission`
- `gather_jones_library`

Material sampling remains a qualification-evidence operation, not a sweep
verb.

## Scope

1. Move the science-facing work currently split across
   `_local/propagation.py`, `_local/geometric.py`, `dispatch.py`, and
   `sweep.py` behind the two dispatch verbs.
2. Keep candidate planning, lane allocation, session leasing, permits,
   capacity renewal, artifact paths, native projects, observations, receipts,
   and recovery inside the Lumerical implementation.
3. Retire caller use of `open_sweep` and public caller knowledge of
   `LumericalSweep`.
4. Preserve the workstation as the sole owner of topology, physical cores,
   SMT exclusion, locality, containment, and memory admission.
5. Preserve exact run manifests and replay-safe artifact identities.
6. Replace string-classified expected execution outcomes with narrow typed
   failures at the dispatch seam.

## Acceptance

- `_local/propagation.py` calls one propagation gather verb and interprets only
  admitted scientific evidence.
- `_local/geometric.py` calls one Jones gather verb and interprets only
  admitted scientific evidence.
- Neither science module imports `LumericalSweep`, `SessionPool`, lane,
  artifact, receipt, or recovery implementation types.
- The two gather verbs automatically use fresh qualified capacity and bounded
  workstation lanes.
- Completed candidates are recovered without repetition.
- Sessions are closed and permits are consumed or closed on every expected
  outcome.
- Run manifests retain exact product, capacity, placement, project, and
  observation facts.
- The public Lumerical package exports no sweep implementation.
- Rust is unchanged.

## Focused tests

- propagation gather through fake native session;
- Jones gather through fake native session;
- bounded parallel wave and capacity renewal;
- partial receipt recovery;
- session failure and permit closure;
- manifest identity and safe run paths;
- architecture scan for leaked work-life imports.

## Do not add

Do not add `execute`, a generic sweep base, a solver registry, caller-supplied
worker counts, CST/COMSOL placeholders, or a second workstation policy.
