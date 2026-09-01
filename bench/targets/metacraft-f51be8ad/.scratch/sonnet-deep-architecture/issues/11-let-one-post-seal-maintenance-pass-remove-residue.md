# 11 — Let one post-seal maintenance pass remove residue

Type: implementation

Status: resolved (2026-08-05)

## Context

The sealed architecture exposed three concrete maintenance contradictions:
the same `Study` crossed execution under two names, periodic-response callers
imported underscore-prefixed codec implementation as a de facto Interface,
and one-caller `periodic_work_protocol.py` separated frozen identity policy
from its request owner. Planning history also lacked one current navigation
entry. These are concrete naming, Interface, and locality concerns under ADR
0018, not a general request to deepen the architecture again.

## Requirements

- Pass one `study` value through metalens execution and ratchet the vocabulary.
- Let `science.periodic_response` expose one explicit owner-facing internal
  codec/admission Interface; do not widen the installed root or add a Module.
- Move the frozen Authority work-method projection into `periodic_request.py`,
  delete the pass-through Module, and preserve exact work and receipt bytes.
- Add non-normative planning and ADR indexes, correct only status drift proved
  by existing resolved issues, and retain every historical record.
- Do not alter scientific behavior, schemas, Rust, Native evidence, root or
  Field exports, or public conduct composition.

## Verification

- Focused Interface and golden-byte tests.
- Complete non-live suite and architecture suite.
- Pyright and blocking CSU.
- Frozen Rust diff from `40f2127` and `git diff --check`.

## Stop condition

Stop when these exact contradictions are removed and the gates agree. Do not
use this ticket to split deep execution Modules, add a registry, or redesign
periodic response.

## Resolution

- Metalens execution now advances one `study` value; its vocabulary ratchet
  passes.
- Periodic-response callers use the explicit owner-facing internal codec and
  admission Interface; no production caller imports its retired underscore
  implementation names.
- `periodic_work_protocol.py` is deleted. Its frozen projection lives with
  `periodic_request.py`, and the exact work-identity, permitted-work, and
  receipt golden bytes remain unchanged.
- Planning and ADR navigation are non-normative, all new Markdown links
  resolve, and only status drift proved by existing records was corrected.
- Verification passed: 93 focused tests, 1,248 non-live tests with 6
  deselected, 109 architecture tests, the explicit 53-test architecture gate,
  Pyright with zero diagnostics, CSU with 4,467 findings and zero blocking,
  an empty Rust diff from `40f2127`, and `git diff --check`.
- About 1.07 GiB of verified generated or stale artifacts left the workspace
  through the Windows Recycle Bin; the active Python 3.12 extension, virtual
  environment, run records, reference data, and environment files remain.
- No live Adviser, Lumerical, Native, or canary execution occurred.
