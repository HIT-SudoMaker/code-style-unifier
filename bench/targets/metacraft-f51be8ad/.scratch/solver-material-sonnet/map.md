# Let materials choose and solvers verify

Label: `wayfinder:map`

## Destination

Reach one implementation-ready specification in which the project material
library selects solver-native materials, each run admits only the selections
it uses, and the Lumerical Adapter verifies rather than interprets them before
Ticket 10 enters its live smoke gate.

## Notes

- Use the canonical language in `CONTEXT.md` and the decision in ADR 0016.
- Preserve the traceability chain from
  [solver-native material ownership](../../docs/research/2026-07-12-solver-native-materials-fdtd-cst.md)
  and
  [Lumerical index-read semantics](../../docs/research/2026-07-26-lumerical-index-read-semantics.md)
  through ADR 0016, this specification, its tickets, and their verification.
- Preserve the frozen Rust authority and the current brief → study → result
  lifecycle.
- Prefer deep Modules with small Interfaces; add no generic solver framework,
  plugin registry, compatibility reader, or automatic material substitution.
- Sonnet rule: materials choose, solvers verify; samples observe, bindings
  apply.
- Planning only. Live Adviser, Lumerical, solver sweeps, and canonical delivery
  remain outside this map.

## Decisions so far

- [Let the material library own reusable selection](decisions/01-let-the-material-library-own-reusable-selection.md) — MetaCraft holds portable records and solver materials; the external database remains an observed source.
- [Let the project reuse and each run remember](decisions/02-let-the-project-reuse-and-each-run-remember.md) — Git-reviewed registrations are reusable, while each run admits only its exact selected snapshots.
- [Let names remain exact and choices remain explicit](decisions/03-let-names-remain-exact-and-choices-remain-explicit.md) — One current choice exists per solver and canonical family, with no aliases, fuzzy matching, or silent substitution.
- [Let one narrow seam carry material truth](decisions/04-let-one-narrow-seam-carry-material-truth.md) — Materials own registration, local composition owns admission, the Adapter owns verification, and science owns task roles.
- [Let evidence close before live work opens](decisions/05-let-evidence-close-before-live-work-opens.md) — Samples cite registrations, bindings cite samples, replay stays offline, and Ticket 10 opens in bounded stages.

## Not yet specified

None. The way to the canonical specification and bounded implementation
tickets is clear.

## Out of scope

- Automatic import, `addmaterial`, approximate substitution, or fuzzy search
  in an external material database.
- A universal solver registry, plugin system, common solver Interface, or CST
  implementation.
- Refactoring portable local-table or refractiveindex.info parsing, sampling,
  or interpolation beyond the one canonical `MaterialSource` type migration.
- Rust changes, live solver execution, Adviser calls, or four-case delivery.
