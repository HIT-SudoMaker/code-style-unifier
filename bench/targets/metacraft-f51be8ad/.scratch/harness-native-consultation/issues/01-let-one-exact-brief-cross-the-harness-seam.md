# 01 - Let one exact brief cross the harness seam

**What to build:** Give the local command a strict, deterministic way to read
and validate one canonical metalens brief without asking a model to review
wording. The harness may clarify language and propose a canonical material
family, but only user-confirmed facts enter the immutable brief.

**Blocked by:** None - can start immediately.

**Status:** resolved (2026-08-09)

- [x] Add one strict canonical brief document reader paired with the existing
      brief encoding; every canonical key is present, while unknown, absent,
      mistyped, duplicated, and non-canonical values fail with stable reasons.
- [x] Preserve the user's exact wording and facts. An optional nullable fact is
      an honest omission only when its matching `omissions` entry is present;
      an absent key is malformed, while a missing required scientific fact
      returns InvalidBrief for user clarification.
- [x] Expose deterministic brief validation suitable for structured command
      input without widening the installed Python root beyond `Authority`,
      `compile_study`, and `conduct`.
- [x] Distinguish invalid supplied values from facts that still require user
      confirmation. Neither becomes DesignAdvice, WordingReview, or evidence.
- [x] Prove round-trip identity for the four canonical benchmark briefs while
      exposing no published reference, alignment, comparison rule, or case
      identity.
- [x] Return material questions only from canonical families allowed by the
      material library. The harness may ask “did you mean X?”, but only explicit
      user confirmation changes atom or substrate intent; add no alias table,
      fuzzy matching, or automatic substitution.
- [x] Add no generic schema framework, object mapper, prompt hierarchy, CLI
      framework, or future-aim placeholder.

## Verification boundary

Verify exact bytes, typed outcomes, stable errors, user-fact preservation, and
the existing compiler result. Do not call a harness, network, solver, or
benchmark comparison. The public domain language is `brief`, not request data,
form data, or AI-generated design.

## Comments

Corrective review closed the strict-input gaps: every nullable design fact now
requires its matching omission, and canonical decoding rejects non-finite
decimals. All four benchmark identities were deliberately resealed after this
truth-preserving schema correction. Focused brief/consultation tests, the full
architecture suite, Pyright, and `git diff --check` pass.
