# 06 — Share the coverage predicate between forecast and judgement

**Type:** `wayfinder:grilling`

**Blocked by:** None — on the frontier.

**Status:** resolved (2026-07-26)

## Question

How much of `_form_phase_set` becomes a shared pure predicate, so the envelope
tests exactly what production tests?

- The real rule in `propagation_phase.py:564-638` is not "span at least one
  turn". It is: every one of `levels` uniform targets has a candidate within
  `pi/levels`, *and* a distinct candidate can be assigned to each target — the
  existence check at `:588` is necessary but not sufficient, which is why the
  post-assignment recheck at `:612` exists. A forecast that only checks
  existence is more optimistic than production.
- Proposed extraction into `science/phase.py`, which already owns `FULL_TURN`
  and `cyclic_distance`:
  `uniform_targets(levels)`, `level_tolerance(levels)`,
  `covers_uniform_levels(phases, levels) -> bool`.
  Is that the right split, and does `_assign` move with them or stay?
- `_form_phase_set` weights loss by useful power and leakage; the forecast has
  neither. Does the shared predicate stay phase-only, with loss weighting
  remaining in the route module?
- `science.__all__` is asserted exactly by
  `tests/architecture/test_scientific_boundary.py:31-52`. Do the new names go
  public, or stay module-internal and imported directly?
- Does extracting this change any admitted document bytes? It should not — it is
  a refactor of a predicate, not of a value — confirm before relying on it.

## Comments

### 2026-07-26 — Claude Code, verification pass (position, not resolution)

- Verified the ticket's premise: the production rule is three-staged —
  candidate count at `propagation_phase.py:572`, per-target existence at
  `:588`, and distinct assignment via `_assign` with the post-assignment
  recheck at `:612`. An existence-only forecast is strictly more optimistic
  than production.
- Proposed split: `covers_uniform_levels` in `science/phase.py` does
  *feasibility matching* — existence plus distinctness, no costs. The
  loss-weighted `_assign` and `_loss` stay in the route;
  `_form_phase_set` calls the shared predicate first, after which the `:612`
  recheck can only be an assertion. The envelope calls the same predicate on
  forecast phases. One rule, two callers — that is the whole point.
- Public-surface cost is zero: the architecture test asserts the *package*
  `science.__all__` exactly (`test_scientific_boundary.py:32-52`), but
  `phase.py`'s own module `__all__` is not part of that assertion. The new
  names can join `phase.__all__` and be imported directly.
- Byte-neutrality: keep `cyclic_distance` and its Decimal working-precision
  context as the only comparison primitive so no admitted boundary case can
  flip during the refactor.

## Resolution (2026-07-26)

**Full three-stage extraction into `science/phase.py`.**

- `phase.py` gains `uniform_targets(levels)`, `level_tolerance(levels)`, and
  `covers_uniform_levels(phases, levels)` — feasibility means per-target
  existence AND a distinct-candidate assignment (private bipartite matcher):
  the exact production rule, not the optimistic existence-only check.
- `_form_phase_set` calls the shared predicate first and keeps its
  loss-weighted `_assign`/`_loss` selection; the `:612` post-assignment
  recheck degrades to an assertion that cannot fire. Loss and power
  weighting stay route-owned — the forecast has neither.
- The envelope calls the same predicate on forecast phases: forecast and
  judgement share one law.
- The new names join `phase.__all__` and are imported directly;
  `science.__all__`, asserted exactly by the architecture test, is untouched.
- Byte-neutrality holds by keeping `cyclic_distance` and its Decimal
  working-precision context as the sole comparison primitive; the refactor
  changes no admitted document bytes.
