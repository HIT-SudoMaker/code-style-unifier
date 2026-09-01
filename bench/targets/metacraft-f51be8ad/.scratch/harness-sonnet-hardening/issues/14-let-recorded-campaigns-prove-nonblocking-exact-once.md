# Let recorded campaigns prove nonblocking exact once

**Parent specification:** [Harness-native Sonnet hardening](../spec.md)

**Status:** resolved

**Assignee:** Codex

**Blocked by:** [Let two concrete profiles own two dialects](13-let-two-concrete-profiles-own-two-dialects.md)

**Implementation authorization:** Explicit owner approval of the parent
specification is required before any code, test, canonical-document, or real
external-session action.

## What to build

Implement the fixed 2x4 nonblocking campaign over `ACCEPTANCE_PROFILES`.
Collect both mandatory preflights before root creation; represent profile
availability explicitly; claim one absent root; start eligible cells once; and
retain eight plan entries without synthetic artifacts for unavailable cells.

Separate planned, eligible, and started counts. Implement the frozen
availability, attempt, audit, inspection, and consultation axes. Write the
specified preflight record, started-cell artifacts, blind manifest, four slot
reports, matrix report, and final sealed manifest with exact hashes and zero
reruns. Keep unavailable profiles and partial outcomes explicit and bounded.

Add a test-only `RecordedHarnessExecution` and use native recorded events to
prove both-available, Codex-only, Claude-only, and neither-available campaigns;
all process terminal classes; raw/redacted parity; no retries; absent-root and
mode rejection; truthful partial reports; and complete hash closure.

Update the fresh-run/nonblocking campaign clause in `DEVELOPMENT.md` in this
slice.

## Acceptance

- Eligibility is exactly 0, 4, or 8; started count reflects actual process
  crossings and is never inferred from the plan.
- An unavailable profile consumes its one profile-level campaign opportunity
  but creates no fictitious session.
- Every started cell is attempted at most once and every terminal class is
  final.
- Confinement rejection suppresses consultation claims without erasing process
  facts; inspection failure remains distinct.
- Both manifests close exactly the prescribed blind/post-hoc boundaries.
- Focused recorded campaign tests and `git diff --check` pass without invoking
  a real harness.

## Exclusions

Do not run Codex or Claude Code, default to/reuse/amend retained evidence,
create an overall pass/winner/threshold, claim support/parity/scientific
success, add retry/resume/repair, change production, `CONTEXT.md`, ADR 0021,
map, or index.

## Stop condition

Stop when deterministic recordings prove every availability and terminal path
through one exact-once sealing lifecycle; live usability remains optional
evidence outside this ticket.

## Comments

- Implemented the fixed 2x4 campaign with both preflights preceding root
  creation, explicit per-profile availability, eight retained plan entries,
  started-only artifacts, and zero retry behavior.
- Split availability, attempt, audit, inspection, and consultation into
  orthogonal states; rejected audits suppress consultation claims while
  retaining process facts.
- Added the blind manifest, four slot reports plus matrix report, and final
  sealed manifest with full hash closure.
- Added a test-only `RecordedHarnessExecution` covering both, one, or neither
  profile available, every process terminal class, audit rejection, inspection
  failure, exact-once crossings, bounded reports, and the frozen consultation
  vocabulary without invoking a live harness.
