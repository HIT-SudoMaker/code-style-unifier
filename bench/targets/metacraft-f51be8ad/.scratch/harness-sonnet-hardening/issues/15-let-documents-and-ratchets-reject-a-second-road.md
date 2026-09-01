# Let documents and ratchets reject a second road

**Parent specification:** [Harness-native Sonnet hardening](../spec.md)

**Status:** resolved (2026-08-09)

**Assignee:** Codex

**Blocked by:** [Let recompile prove advice before compilation](11-let-recompile-prove-advice-before-compilation.md), [Let recorded campaigns prove nonblocking exact once](14-let-recorded-campaigns-prove-nonblocking-exact-once.md)

**Implementation authorization:** Explicit owner approval of the parent
specification is required before any code, test, or canonical-document edit.

## What to build

Reconcile the slice-owned edits in `DESIGN.md`, `SCIENCE.md`, and
`DEVELOPMENT.md` so they state one current architecture: private structural
advice sharing, typed caller-fault ownership, Authority-backed current-rule
replay, two concrete acceptance-only profiles, one shared exact-once partial
campaign, immutable historical provenance, and nonblocking live status.

Add only the three architecture guards frozen by the specification:
`_closed_advice.py` in consultation contract paths plus its inward/private
dependency; exact Codex-then-Claude composition with no production profile or
harness dispatch; and continued absence of a production harness Adapter.

Repair the existing local-Markdown-link ratchet to send `git check-ignore`
candidates in bounded batches on Windows while preserving its exact link
scope and ignored-path semantics. The canonical pytest test itself must pass;
do not substitute a one-off proxy script.

Run existing architecture guards unchanged for installed exports, Authority,
runtime DAG, science ownership, provider absence, schemas, no string
classification, single frontier, and canonical skill/router identity. Verify
behavior through prior ticket tests rather than source-shape assertions.

## Acceptance

- Canonical prose and implementation use one vocabulary and owner at every
  changed seam.
- `CONTEXT.md` and ADR 0021 have no diff.
- The new private Module is unexported, inward-only, and provider-free.
- Acceptance profiles exist only under tests and form no registry or future-
  harness promise.
- No source-text test pins replay order, catch width, private helper bodies,
  event parsers, or campaign counts.
- Focused architecture and domain naming gates, the canonical Markdown-link
  pytest entry, and `git diff --check` pass.

## Exclusions

Do not repair semantic behavior, alter frozen schemas/Interfaces, amend ADR
0021, add glossary terms, update retained-run claims without an actual new
record, run a harness, or edit map/index.

## Stop condition

Stop when prose, dependency direction, names, and architecture guards make a
second production or acceptance road impossible without reopening an explicit
contract.

## Resolution

Reconciled `DESIGN.md`, `SCIENCE.md`, and `DEVELOPMENT.md` around one ownership
story for private structural advice, typed caller faults, Authority-backed
replay, the two acceptance-only profiles, exact-once partial campaigns,
immutable historical provenance, and nonblocking live status. `CONTEXT.md` and
ADR 0021 remain unchanged.

Added exactly three architecture guards: the private inward-only
`_closed_advice.py` consultation contract, the exact Codex-then-Claude profile
tuple, and the absence of production profile/harness Adapter dispatch. Updated
the existing runtime-DAG expectation for the typed fault's direct owner import;
the guard's dependency rule is unchanged.

The canonical local-Markdown-link ratchet now partitions `git check-ignore --`
candidates by bounded rendered command length while preserving candidate order,
link scope, and ignored-path semantics. A focused helper test covers batching.

## Comments

- `87 passed` across the focused Sonnet ratchets, architecture, runtime DAG,
  scientific boundary, and domain naming suites.
- The canonical Markdown-link pytest entry and its batching helper pass.
- Canonical `python -m pyright` reports 0 errors, warnings, or information.
- `git diff --check` passes; `CONTEXT.md` and ADR 0021 have zero diff.
- No business behavior, live/native harness, retained-run, map/index, or commit
  work was performed for this ticket.
