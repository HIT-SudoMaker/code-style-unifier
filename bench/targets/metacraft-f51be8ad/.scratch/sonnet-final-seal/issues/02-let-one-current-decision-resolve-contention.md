# Let one current decision resolve contention

Type: implementation

Status: resolved (2026-07-29)

Blocked by:
[Let one native record speak once](01-let-one-native-record-speak-once.md).

## Outcome

One private Python authority operation resolves optimistic revision contention
for both bounded work and Lumerical capacity admission.

## Scope

1. Add private Module `authority/_decision.py`.
2. Add `decide_current(authority, proposal)`.
3. Preserve the existing policy exactly:
   - at most 32 attempts;
   - observe a fresh Authority revision for every attempt;
   - retry only a Decision containing `revision_mismatch`;
   - wait one millisecond after every mismatch, including the final mismatch;
   - return the first non-mismatch Decision;
   - raise `authority_contention` after exhaustion.
4. Replace `_WorkAuthority._decide` with the shared operation.
5. Replace `LumericalDispatch._decide` with the shared operation.
6. Delete both duplicated retry implementations and their now-unused imports.
7. Keep the helper private and absent from `authority.__all__`.

## Acceptance

- One production implementation owns current-revision retry.
- `_WorkAuthority` and `LumericalDispatch` call that implementation.
- First-attempt success returns unchanged.
- A mismatch followed by success observes the new revision and returns.
- Thirty-two mismatches raise exactly `authority_contention`.
- Thirty-two mismatches preserve the existing thirty-two one-millisecond
  waits before exhaustion.
- A non-mismatch rejection is returned and never retried.
- The public Python `Authority` still exposes only the existing four verbs.
- No retry setting enters environment or configuration.
- Rust is untouched.

## Focused verification

Run only focused tests or exact nodes covering:

- immediate current decision;
- one and several revision mismatches;
- exhaustion;
- non-mismatch rejection;
- bounded work use;
- Lumerical capacity-admission use;
- private export shape.

Also run:

- local Pyright for touched Python scope;
- CSU for touched production files;
- `git diff --check`;
- `git diff -- rust`.

Do not run Rust tests, scale diagnostics, a native solver, or a complete
Python suite.

## Stop and report

Stop if the two callers require different retry semantics, if a caller must
hold a fixed revision rather than observe current truth, or if the operation
would need to become public.

## Do not add

Do not add an Authority method, public export, retry class, configurable retry
policy, background worker, database state, compatibility wrapper, or Rust
change.
