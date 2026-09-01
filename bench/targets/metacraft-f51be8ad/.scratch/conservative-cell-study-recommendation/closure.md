# Conservative cell-study seam closure

Date: 2026-08-10

The eight implementation tickets are closed in dependency order:

`01 → 02 → 03 → 04 → [05, 06] → 07 → 08`.

## Acceptance evidence

- `tests/acceptance/test_four_case_cell_study.py`: 4 passed. McClung and
  Arbabi use propagation work; Yang and Khorasaninejad use PB x/y work. Each
  card replays byte-for-byte, preserves the admitted brief/domain facts, and
  closes a bounded plan without importing a solver module.
- Cell-study, projection, run-projection, PB, propagation, and periodic
  response tests: 53 passed.
- Architecture suite: 118 passed; the runtime import graph remains acyclic,
  naming/provider ratchets remain closed, and all exported contracts have
  documentation.
- Authority: 230 passed. Solver response suites: 306 passed, 4 deliberately
  deselected. Field/material/workstation suites: 148 passed. Examples and
  command suites: 124 passed.
- Full project type check: `pyright` reports 0 errors, 0 warnings, and 0
  informations. `git diff --check` passes.

The historical `tests/science/test_delivery_matrix.py` is a long fake-solver
conduct stress test. It exceeded the ten-minute local command window without
an assertion failure; it is outside the brief-to-cell-study acceptance gate
and no new cell-study path is invoked by that test. No live solver, field, or
focus claim is made by this closure.

## Boundary sealed

The deep `cell_study` Module owns the decision card and exact work. Periodic
request construction projects that work verbatim; propagation and PB response
qualification remain later evidence gates. Authority remains the truth owner;
`run_projection` is read-only, deterministic presentation. Legacy period,
height, grid, and unqualified PB routes are explicit compatibility paths, not
silent alternatives.
