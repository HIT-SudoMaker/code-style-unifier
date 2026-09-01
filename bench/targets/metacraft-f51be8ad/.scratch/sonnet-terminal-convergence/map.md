# Map — Close MetaCraft in one Sonnet

**Label:** `wayfinder:map`

**Status:** road completed (2026-07-29)

## Destination

One implemented, reviewed, non-live-verified MetaCraft baseline whose authority
proof is atomic, whose Python adapters are exact, whose runtime dependency
graph is acyclic, and whose scientific evidence path is deep without becoming
generic machinery.

This effort explicitly carries execution through non-live closure. Canonical
live delivery remains a separate human gate.

## Notes

- Canonical language comes from `CONTEXT.md`; system constraints come from
  `DESIGN.md`, `AUTHORITY.md`, `SCIENCE.md`, `DEVELOPMENT.md`, and the ADRs.
- Sonnet means balanced ownership, paired language, one-way dependencies,
  natural names, deep Modules, and the smallest truthful Interface. It does
  not name a model.
- Rust closes first. After Ticket 01, production Rust remains frozen.
- The public authority Interface remains exactly
  `check -> view -> fetch -> decide`.
- `compile_study` and package-level `workstation.plan` retain their public
  meaning.
- Focused tests run per ticket. The complete non-live suite runs at closure.
- No ticket enables live adviser, Lumerical, delivery, or canonical-brief
  flags.

## Decisions so far

- [Let one audit remember one generation](issues/01-let-one-audit-remember-one-generation.md)
  — one writer lifetime binds audit, generation, revision, and view; failures
  forget proof rather than serve stale truth.
- [Let Python accept only what Rust can say](issues/02-let-python-accept-only-what-rust-can-say.md)
  — every authority value is decoded by exact shape, order, uniqueness, and
  relation without coercion.
- [Let dependencies flow without return](issues/03-let-dependencies-flow-without-return.md)
  — the production runtime import graph becomes a DAG; composition knows aims
  while generic science does not.
- [Let field evidence hide its storage](issues/04-let-field-evidence-hide-its-storage.md)
  — field evidence owns binary component mechanics while metalens owns focal
  meaning.
- [Let one frontier return one science](issues/05-let-one-frontier-return-one-science.md)
  — a private frontier fails closed, replay observes once, and the shared
  metalens proof tail has one owner.
- [Let each periodic response fail honestly](issues/06-let-each-periodic-response-fail-honestly.md)
  — independent response fixtures prove only what they observe; expected
  absence is typed and implementation drift raises.
- [Let code and record close together](issues/07-let-code-and-record-close-together.md)
  — tests, architecture ratchets, canonical documents, tracker state, and Git
  evidence finish in one voice.

## Not yet specified

Nothing. The design tree is closed and the implementation road is fully
specified by [the canonical specification](spec.md).

## Out of scope

- The human-only canonical live delivery ticket, adviser calls, native
  Lumerical qualification, solver sweeps, or four-brief execution.
- A public Frontier, workflow framework, aim registry, plugin discovery,
  compatibility shim, second decoder, new exception hierarchy, or storage
  registry.
- A field-storage type tree or public field-internals Interface.
- New aims, large-NA methods, optimization, achromatic synthesis, CST, COMSOL,
  RCWA, GUI work, or changed physical thresholds.
- A full-database hash on every stable authority view, adversarial
  metadata-preserving raw-byte tamper detection, or a storage migration.
- Broad renaming outside files already changed for a semantic reason.
