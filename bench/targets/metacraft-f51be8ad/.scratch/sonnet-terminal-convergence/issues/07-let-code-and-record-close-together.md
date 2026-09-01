# Let code and record close together

Type: implementation

Status: resolved (2026-07-29)

Blocked by:
[Let each periodic response fail honestly](06-let-each-periodic-response-fail-honestly.md).

## Outcome

Production code, architecture ratchets, canonical science prose, ADRs, tracker
lifecycle, performance evidence, and Git verification describe one completed
non-live baseline.

## Scope

1. Run focused closure audits before editing documentation.
2. Correct SCIENCE prose that implies geometric phase returns 8-, 12-, and
   16-state quantized results.
3. Remove commit ids, ticket language, and syntax narration from production
   comments; retain only invariant explanation.
4. Make Lumerical typed-outcome and runtime-DAG architecture ratchets reflect
   their stated contracts.
5. Confirm that accepted ADR 0012 and ADR 0014 describe the implemented
   authority and dependency decisions; do not duplicate either record.
6. Record durable 304-, 1,504-, and 3,004-event release diagnostics and the
   stable-view speedup.
7. Repair committed EOF whitespace and run `git diff --check` over the fixed
   implementation range, not only the clean worktree.
8. Reconcile the previous performance-and-reliability map, spec, Ticket 01–05,
   closure report, this map, this spec, and all seven tickets with actual Git
   state.
9. Write one durable closure report for this effort.
10. Keep the canonical live delivery ticket `ready-for-human` and explicitly
    blocked; do no live preparation or execution.

## Acceptance

- Complete non-live Python suite passes with zero failures and zero unexpected
  skips.
- Pyright reports zero errors, warnings, and information.
- Runtime import DAG test passes with no allowlist.
- Rust format, Clippy, and all Rust tests pass; production Rust is unchanged
  since Ticket 01.
- Touched production files have zero CSU hard violations.
- Fixed-range `git diff --check` passes.
- SCIENCE states that 8/12/16 quantization belongs to propagation phase;
  geometric phase remains one selected cell plus continuous orientation.
- Old and new planning lifecycle states agree with Git.
- Live adviser, Lumerical, delivery, and canonical-brief tests remain
  deselected.
- User PPTX, `docs/presentations/`, environment files, solver artifacts, and
  unrelated worktrees remain untouched.

## Verification

Use:

`C:\Users\Administrator\miniforge3\envs\research_env\python.exe`

for every project Python command.

Run:

- complete non-live Pytest;
- Pyright;
- architecture tests;
- Rust format, Clippy, and tests;
- source-manifest verification;
- touched-file CSU;
- fixed-range `git diff --check`;
- clean-worktree inspection that preserves unrelated untracked files.

## Stop and report

Stop if closure requires live execution, changing scientific thresholds,
editing user presentation files, removing unrelated worktrees, altering
environment secrets, or modifying Rust after Ticket 01.

## Do not add

Do not add new features, future-aim placeholders, compatibility code, broad
renames, more implementation tickets, live preparation, or a second closure
framework.

## Resolution

Science prose, production comments, both planning roads, and the durable
closure record now describe one integrated non-live baseline.

- Complete non-live Python: 776 passed, 15 deselected, 0 failed, and no
  unexpected skips.
- Pyright: 0 errors, 0 warnings, and 0 informations.
- Architecture: 71 passed; the runtime DAG and exact typed-outcome importer
  gates also passed directly.
- Rust format, Clippy, tests, source manifest, and the freeze diff all passed.
- Touched production files reported zero blocking CSU findings.
- The 304-, 1,504-, and 3,004-event diagnostics preserve constant-time stable
  views without audits or historical-row scans.
- No live adviser, Lumerical, delivery, or canonical-brief work ran.
