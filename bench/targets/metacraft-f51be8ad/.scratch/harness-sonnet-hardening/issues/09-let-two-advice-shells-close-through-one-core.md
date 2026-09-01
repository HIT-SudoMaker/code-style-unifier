# Let two advice shells close through one core

**Parent specification:** [Harness-native Sonnet hardening](../spec.md)

**Status:** resolved (2026-08-09)

**Assignee:** Codex

**Blocked by:** none

**Implementation authorization:** Explicit owner approval of the parent
specification is required before any code, test, or canonical-document edit.

## What to build

Add private `science/metalens/_closed_advice.py` with exactly the structural
validation, strict restoration, and exact-byte responsibilities frozen by the
specification. Route the unchanged `PeriodAdvice` and `HeightAdvice` public
Interfaces through it while keeping schema checks, outer keys, names,
constructors, envelope ownership, and stable domain-specific reasons in their
shells.

Replace the asymmetric period-only closure tests with one parameterized public
period/height matrix. Include frozen recommendation and `EvidenceRequired`
bytes/references for both schemas and height round trips with and without an
envelope reference. Delete superseded duplicate tests; do not test or export
the private helpers directly.

Update only the private-sharing clause owned by this slice in `DESIGN.md`.

## Acceptance

- Public signatures, schemas, canonical bytes, document references, and stable
  period/height reasons are unchanged.
- The shared Module imports neither shell and owns no scientific question or
  envelope policy.
- Period and height consultation-specific candidate and envelope tests remain
  in their existing suites.
- Removing the private Module would force the full closed-record invariant back
  into both shells; no compatibility wrapper remains.
- Focused period/height consultation tests and `git diff --check` pass.

## Exclusions

Do not move the typed consultation fault, change answer acceptance, implement
replay, alter package exports, add generics/registries/base classes, or edit
`CONTEXT.md`, ADR 0021, the harness runner, retained evidence, map, or index.

## Stop condition

Stop when both public shells prove the same private structural invariant with
unchanged visible meaning and the former duplicate invariant/test road is gone.

## Comments

- 2026-08-09: Implemented the approved private
  `science/metalens/_closed_advice.py` Module. Period and height retain their
  public values, schema identifiers, exact document bytes, stable reasons, and
  separate physical names; height alone still restores its optional envelope
  reference. The shared implementation now owns recommendation/advice closure,
  strict common-field and indexed restoration, and exact-byte proof.
- Replaced the four asymmetric period-only closure tests with one public
  period/height behavioral matrix. It freezes recommendation and
  `EvidenceRequired` document references for both schemas, covers height with
  absent and admitted envelope references, exercises valid external-claim
  closure and malformed mutations, and never imports the private Module.
- Updated only the private-sharing clause in `DESIGN.md`. No Ticket 10+ fault
  work, replay, harness, retained evidence, map, index, glossary, ADR, Rust,
  Native, or live execution change belongs to this ticket.
- Verification: 204 focused science and architecture tests passed; Pyright
  reported 0 errors, 0 warnings, and 0 informations; `git diff --check`
  passed. All Python commands used the repository `research_env` interpreter.
- 2026-08-09 seal reopen: Reflowed the eight private-core docstrings so their
  delimiters occupy separate lines and documented the shared recommendation
  validation contract. This was documentation-only: behavior and signatures
  are unchanged. The reopened Ticket 09 focused suite passed 163 tests,
  Pyright remained at 0 errors and 0 warnings, and a fresh CSU report contained
  zero blocking findings for `science/metalens/_closed_advice.py`.
