# 03 — Let each test prove one scientific fact

**Type:** implementation

**Status:** wontfix

**Superseded by:** `../../metalens-sonnet-convergence/spec.md`

**Blocked by:** ticket 02.

## Outcome

The test suite observes stable scientific interfaces without repeatedly
running unrelated compiler, solver, matching, propagation, Result, and replay
work in one giant fixture.

## What to build

- Replace cross-test imports with small dedicated test-support Modules.
- Keep two compact `conduct` tracers: one propagation route and one geometric
  route.
- Test the four public brief factories for exact intent, compilation, and
  ready-task formation without repeating numerical propagation.
- Make negative Result, refusal, and replay tests consume compact recorded
  evidence; retain one focused expensive Field numerical test.
- Remove tests that import private constants, monkeypatch implementation
  spelling, or require named private caches and NumPy/Torch calls.
- Preserve architecture tests that enforce public interfaces, dependency
  direction, canonical language, and Rust immutability.

## TDD seam

Use the public operation or the smallest truthful scientific interface for
each fact. Before deleting a broad fixture, add one focused behavior test that
retains its independent scientific assertion.

## Acceptance

- Test collection is green.
- No test case imports helpers from another test case file.
- No single test owns compiler interpretation, fake solver generation, three
  quantizations, propagation, Result formation, and replay.
- Expensive propagation runs once in the focused numerical suite.
- Existing meaningful scientific and architecture coverage remains.
- Focused and architecture tests, Pyright, and CSU pass.
- Rust has no diff.

## Verification

Implemented on 2026-07-28 without a commit.

- Cross-test-case imports: eight reduced to zero.
- Collection: 289 of 300 non-live tests selected; 11 explicit markers
  deselected; 1.9 seconds.
- Architecture, Field, and daily conduct tracers: 34 passed in 3.5 seconds on
  independent review.
- Solver, science, Result, and remaining non-live tests passed in bounded
  groups.
- Exactly one Field test performs real Torch propagation.
- Pyright: zero errors.
- New test-support Modules: zero CSU hard violations.
- Rust diff: empty.

The two Result Modules now spend roughly 27 and 17 seconds constructing
authority closure rather than recomputing ASM. That remaining cost is honest
integration evidence, not duplicated numerical work.
