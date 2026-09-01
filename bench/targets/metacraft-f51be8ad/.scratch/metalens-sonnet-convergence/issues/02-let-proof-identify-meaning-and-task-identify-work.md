# 02 — Let proof identify meaning and task identify work

Type: implementation

Status: resolved (2026-07-28)

Blocked by: ticket 01.

## Outcome

Proof identity states scientific meaning. Task identity binds that meaning to
one exact operation. Evidence can close only the task it actually answered.

## What to build

- Replace hand-written dotted route names with one canonical
  content-addressed `Route` value.
- Keep Route and Proof distinct: Route records selected claims and methods;
  Proof records their complete prerequisite and evidence topology.
- Derive `proof_identity` from the exact canonical proof meaning.
- Derive `task_identity` from proof identity, target claim and method, exact
  brief/design inputs, prerequisite evidence, consultations, choices,
  and the binding and capacity scope when the method requires them.
- Derive solver `work_identity` from task identity plus exact candidate and
  basis input.
- Make `EvidenceFact` cite `task_identity`; reject evidence prepared for
  another task even when its schema happens to match.
- Remove persisted `route_identity`, route strings on scientific values, and
  route-derived artifact paths.
- Let each scientific value Module own its stable schema identifier. Methods
  declare that identifier; compilation copies and validates it.
- Remove formulas of the form
  `metacraft.science.{route}.{obligation}` and every compatibility reader for
  the old schema spellings.
- Update canonical encoders, decoders, authority references, replay fixtures,
  and architecture tests atomically.

## TDD seam

Use pure Route, Proof, Task, and evidence values:

1. identical inputs produce identical route, proof, and task identities;
2. a changed method changes proof and task identity;
3. a changed brief, prerequisite reference, consultation, choice, or binding
   changes task identity without inventing a new route label;
4. same-schema evidence from the neighboring brief cannot close the task;
5. one exact admitted fact closes the intended task and survives replay.

## Acceptance

- No production constant such as `LOW_NA_PROPAGATION_ROUTE` or
  `LOW_NA_GEOMETRIC_ROUTE` remains.
- No domain value persists a route name or separate route identity.
- `EvidenceFact` and work manifests preserve exact task/work identity.
- Schema identifiers are constants owned beside their decoders, not compiler
  string interpolation.
- Route identity is canonical content, not a user-facing strategy label.
- Old evidence and run layouts are not migrated or silently accepted.
- Focused identity, compiler, evidence, replay, and architecture tests pass.
- Pyright reports zero errors; touched files have zero CSU hard violations.
- `git diff -- rust` is empty.

## Do not add

Do not add an identity manager, schema registry, universal codec, versioned
module, compatibility alias, or route class per control strategy.
