# 04 - Let one application root resume one conduct life

**What to build:** Replace the active MetalensConsultation callback with an
explicit consultation-required outcome and exact answer input, allowing one
application root to pause across a harness process and resume through the same
conduct lifecycle.

**Blocked by:** 01 - Let one exact brief cross the harness seam; 03 - Let height
answer only after period.

**Status:** resolved (2026-08-09; review corrected)

- [x] The first conduct call still requires and claims a fresh application
      root. A later call resumes only a structurally complete MetaCraft root
      bound to byte-identical brief content.
- [x] Derive the current ConsultationRequest from the admitted StudyFrontier.
      Do not persist a mutable pending request, cursor, workflow status, or
      second application state.
- [x] Return one typed consultation-required outcome before unrelated waiting
      outcomes. Repeating without an answer returns identical request bytes.
- [x] Change the one public operation to
      `conduct(brief, *, application_root, evidence_adapter=None,
      consultation_answer=None)` and add `ConsultationRequired` to its closed
      outcomes. Add no fourth installed Python entry.
- [x] Accept at most the answer for the exact current request, validate it,
      admit the resulting advice with exact sources, recompile, checkpoint, and
      advance until the next request, honest waiting, or completed Results.
- [x] Reject a foreign directory, partial root, brief mismatch, stale answer,
      duplicate answer, impossible question order, and losing Authority
      revision without partial advancement.
- [x] Reorder restoration so merely repeating a pending request does not reopen
      a solver or repeat scientific work. Open the evidence Adapter only when a
      genuinely ready evidence step requires it.
- [x] Treat `evidence_adapter=None` as explicit absence of executable capability.
      It creates no fake or state; after pre-admitted prerequisites and
      consultations, the first ready evidence boundary returns honest
      WaitingStudies without opening a product.
- [x] Preserve one `conduct`, one Study, one StudyFrontier, one AuthoritySession
      policy, one WorkExecution life, and the three installed Python exports.
- [x] Delete MetalensConsultation and RecordedMetalensConsultation after all
      tests consume the new value seam; do not keep a fake-only Protocol.
- [x] Update the application-root and conduct contracts in `CONTEXT.md`,
      `DESIGN.md`, `SCIENCE.md`, and `DEVELOPMENT.md` in the same change as code
      and tests; ADR 0021 remains the destination, not a substitute for current
      documentation.

## Verification boundary

Exercise fresh start, period pause, height pause, exact resume, repeat prepare,
completed results, unrelated waiting, faults, concurrency, and no repeated
evidence work. Tests and callers cross the same conduct Interface. No command,
skill, harness, HTTP, or Native execution is introduced in this ticket.

## Comments

Implemented the resumable public cadence with one frontier-derived request,
one exact answer input, strict root restoration, a per-root non-scientific
execution lock, lazy optional evidence, and completed-Result replay. Caller
answer faults cross the narrow `ConsultationAnswerRejected` type; Authority,
storage, and implementation faults remain direct. Removed the active and
recorded consultation callback classes. Verification: 141 scoped lifecycle and
consultation tests, 25 advice tests, and 110 architecture tests pass; Pyright
reports zero errors and warnings, and `git diff --check` passes.

Review correction: caller-supplied advice now reopens only an existing exact
root, so an absent root is rejected before any claim or Authority mutation.
Authority exposes no multi-Proposal transaction; a forced post-advice frontier
CAS loss therefore raises the direct `consultation_frontier_conflict` storage
fault instead of a typed caller rejection. The current projection, frontier
reference, and frontier bytes remain unchanged. The already admitted immutable
non-current advice record is the explicit, unavoidable residue of that missing
atomic primitive and makes an exact retry safe rather than partially advancing
science.

Correction verification: 56 scoped application-root and consultation tests and
54 architecture tests pass. Pyright reports zero errors and warnings across
the corrected production seams, and `git diff --check` passes.
