# Let one typed fault cross the answer seam

**Parent specification:** [Harness-native Sonnet hardening](../spec.md)

**Status:** resolved (2026-08-09)

**Assignee:** Codex

**Blocked by:** [Let two advice shells close through one core](09-let-two-advice-shells-close-through-one-core.md)

**Implementation authorization:** Explicit owner approval of the parent
specification is required before any code, test, or canonical-document edit.

## What to build

Move `InvalidMetalensConsultationAnswer` beside the period and height rules in
`science/metalens/consultation.py`, carry `QuestionKind` as data, and narrow
both acceptance functions to the ordered formation -> typed caller validation
-> direct construction flow. Remove broad `ValueError` translation from
`accept_metalens_consultation`; generic conduct catches exactly the typed fault
and remains the sole producer of public `invalid`.

Drive the change through period, height, metalens-conduct, generic-conduct, and
command tests. Inject non-typed sentinel failures at formation, candidate
conversion/advice construction, Authority admission, and frontier replacement
to prove direct propagation. Assert types and structured reasons, never
exception text.

Update the fault-ownership clauses in `SCIENCE.md` and `DEVELOPMENT.md` in this
same slice.

## Acceptance

- All four public rejection reasons and duplicate-before-stale precedence
  remain exact.
- Only caller-controlled answer closure and explicit question rules produce
  `InvalidMetalensConsultationAnswer` and public `invalid`.
- Stale internal requests, every envelope integrity fault, construction faults,
  `consultation_frontier_conflict`, Authority/storage faults, and wrong runtime
  types stay direct.
- Malformed command documents remain `answer_document_invalid`.
- Focused consultation/conduct/command tests and `git diff --check` pass.

## Exclusions

Do not alter public exception ancestry/reasons, schemas, scientific rules,
Authority, replay, acceptance support, `CONTEXT.md`, ADR 0021, map, or index.

## Stop condition

Stop when one typed internal value is the only path to public `invalid`, every
other owner keeps its fault, and no broad catch or message classifier survives.

## Resolution

`InvalidMetalensConsultationAnswer` now belongs to
`science.metalens.consultation`, retains the exact closed `QuestionKind`, and
crosses metalens composition unchanged. Period and height both re-form and
compare the current request before entering the sole caller-fault scope.
Shared answer closure and the explicit height forecast/ruled-out rules raise
the typed fault; candidate conversion, public recommendation/advice
construction, envelope integrity, Authority admission, frontier replacement,
wrong runtime types, and other implementation faults remain direct.

`accept_metalens_consultation` no longer catches `ValueError`. Generic conduct
catches exactly the typed metalens fault and remains the sole producer of
`ConsultationAnswerRejected("invalid")`; duplicate-before-stale and all four
public reasons remain unchanged. Command decoding still rejects malformed or
noncanonical answer documents as `answer_document_invalid` before the typed
science seam.

Interface tests now inject non-typed `ValueError` sentinels at request
formation, candidate conversion, advice construction, Authority admission,
and frontier replacement. They also prove direct stale internal requests,
propagation-envelope integrity faults, geometric envelope prohibition,
Authority reference mismatch, wrong runtime types, typed period/height caller
fault data, public translation, and command translation without inspecting
exception text.

## Comments

- 2026-08-09: Implemented only the typed-fault slice after Ticket 09 resolved.
  Preserved the concurrent Ticket 09 closed-advice work, Ticket 12 acceptance
  work, and user planning changes; no replay, harness, map/index, `CONTEXT.md`,
  ADR, Rust, retained-artifact, live, or Native change was made.
- Focused verification:
  `86 passed` across period consultation, height consultation, generic conduct,
  and command tests; `45 passed` across the scientific-boundary and Sonnet
  architecture checks; Pyright reported
  `0 errors, 0 warnings, 0 informations`; `git diff --check` passed.
