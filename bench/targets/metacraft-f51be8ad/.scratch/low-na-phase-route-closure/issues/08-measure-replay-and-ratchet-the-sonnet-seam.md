# 08 — Measure replay and ratchet the Sonnet seam

**Type:** implementation

**Status:** wontfix

**Superseded by:** [Four-brief delivery tickets 03 and 07](../../four-brief-metalens-delivery/spec.md).

**Blocked by:** ticket 07.

## Outcome

The completed route is measured before it is polished. Any performance change
answers observed Python-side replay cost, while the final public vocabulary
stays small, natural, and stable.

## What to build

- Measure Authority view, document fetch, and decode counts during the
  four-example fake matrix with an instrumented Adapter. Keep wall-clock
  timing descriptive, never an acceptance threshold.
- Add immutable, conduct-call-scoped memoization only if the measurement shows
  repeated material work. Record the before/after evidence in the ticket
  comments or a focused research note.
- Audit the existing propagation and geometric application caches. Remove
  them if replay is already cheap; otherwise make their lifetime provably one
  conduct call so a configured application cannot leak stale values into a
  later call.
- Review touched public names for one concept per noun and paired word order.
- Remove leaked product strings, underscore-shaped public shape values,
  optional propagation conventions, and sampling-ceiling substitutions from
  the completed seam.
- Split an internal Module only when propagation and geometric behavior have
  different reasons to change. Keep the compiler, science, Field, conduct,
  and Lumerical Adapter interfaces deep.
- Clear hard CSU violations in every touched file and remove stale local
  tracker references made obsolete by this feature. Close overlapping
  historical tickets 31–33 under `order-regime-and-phase-envelope` as
  `wontfix` with a dated comment pointing to this accepted replacement; do
  not delete their history.

## TDD seam

Capture a repeatable baseline around the four-example fake matrix before
changing replay behavior. If there is no material repeated fetch or decode
work, preserve the simpler implementation and turn the measurement into a
regression bound.

## Acceptance

- The measurement distinguishes Authority calls, fetches, and decodes.
- The baseline is structural and repeatable; no test fails because a machine
  was temporarily slower.
- Any memoization is immutable, local to one conduct call, and invisible to
  Rust and persisted documents.
- The four-example matrix and exact replay remain unchanged.
- Architecture tests forbid hard-coded material families, physical-period
  substitution, public propagation conventions, and lossy public shape
  values.
- Touched files have zero CSU hard violations and zero Pyright errors.
- The affected full test suite passes.
- Rust is unchanged from the ticket's recorded starting revision.
- Legacy tickets 31–33 no longer advertise active implementation ownership.

## Do not add

- Persistent or process-global caches.
- An application-lifetime cache presented as conduct-local.
- Rust changes or Authority protocol extensions.
- A repository-wide rename or style rewrite.
- File splitting justified only by line count.
