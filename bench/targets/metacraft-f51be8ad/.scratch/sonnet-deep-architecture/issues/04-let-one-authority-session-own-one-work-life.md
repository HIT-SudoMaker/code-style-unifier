# 04 — Let one Authority session own one work life

Type: implementation

Status: resolved (2026-07-31)

Blocked by: ticket 01.

## Outcome

One private `AuthoritySession` owns the Python-side Authority handle, observed
view, revision, admission, and contention recovery. One `WorkExecution` using
that same session owns the complete:

`capacity -> permit -> observation -> receipt`

or:

`capacity -> permit -> close`

life.

Rust source, protocol values, document schemas, references, work identities,
and the four Authority verbs remain unchanged.

## Problem

Revision and work policy are currently repeated across:

- `science/conduct.py::_Admission`;
- `authority/_decision.py::decide_current`;
- `authority/work.py::_WorkAuthority`;
- `runner.py::EvidenceRunner`;
- direct `Authority.view` and `Authority.decide` calls in Lumerical dispatch;
- manual revision refreshes after delegated work in metalens execution;
- replay code that captures a revision and hands it to another owner.

A delegated receipt therefore requires its caller to remember to refresh a
second cursor. Capacity renewal also reconstructs a separate work-authority
object. These are several narrators for one ledger head.

## Scope

1. Add a private `AuthoritySession` beside the Python Authority Adapter.
2. Open it from one Authority view and retain that exact view and revision.
3. Route plain document, structured document, opaque object, current value,
   capacity, permit, receipt, close, and expiry decisions through the session.
4. On `revision_mismatch`, re-observe Authority and retry within one bounded
   policy owned only by the session.
5. Advance the retained revision only from an admitted decision's exact
   `resulting_revision`.
6. Keep structure admission and its structured document admission inside one
   session operation.
7. Verify a delegated admitted reference before re-observing it; callers do
   not assign a revision.
8. Replace `EvidenceRunner` with one route-neutral `WorkExecution`.
9. Make `WorkExecution.execute(...)` recover consumed receipts, close expired
   permits, renew capacity, acquire bounded permits, observe concurrently,
   admit receipts, and close failed work.
10. Make execution restore exact work automatically. Remove separate public
    `has_prior_permit_for`, `replayed_work`, `gather`, and `gather_study`
    lifecycle fragments.
11. Keep `WorkExecution` ignorant of `Study`, metalens, Lumerical, claims,
    methods, and control strategies.
12. Replace all production imports and tests in this ticket. Delete the
    replaced implementation in the same commit.

Primary production files:

- `src/metacraft/authority/session.py`;
- `src/metacraft/work_execution.py`;
- `src/metacraft/authority/_decision.py`;
- `src/metacraft/authority/work.py`;
- `src/metacraft/science/conduct.py`;
- `src/metacraft/runner.py`;
- `src/metacraft/_local/application.py`;
- `src/metacraft/_local/propagation.py`;
- `src/metacraft/_local/geometric.py`;
- `src/metacraft/_local/replay.py`;
- `src/metacraft/solvers/lumerical_fdtd/dispatch.py`;
- `src/metacraft/solvers/lumerical_fdtd/evidence.py`;
- `src/metacraft/solvers/lumerical_fdtd/sweep.py`.

Delete without aliases:

- `_Admission`;
- `_WorkAuthority`;
- `decide_current`;
- `EvidenceRunner`;
- `ReadyWork`;
- `AdmittedWork`;
- `ReplayedWork`;
- every manual assignment to an admission revision.

Use intention-revealing replacements such as `AuthoritySession`,
`WorkExecution`, `WorkRequest`, and `CompletedWork`. Receipt recovery remains
implementation, not another public operation.

## Typed error contract

Expected absence is data:

- fresh positive capacity cannot be established -> typed waiting work;
- a permit is temporarily unavailable -> private retry;
- a product observation reports expected absence -> retain that typed
  observation outcome without interpreting it here.

Direct faults remain faults:

- malformed capacity or changed capacity scope;
- duplicate or conflicting receipts;
- receipt schema mismatch;
- malformed permit documents;
- a non-contention Authority rejection;
- impossible permit transition;
- close failure;
- unexpected observation implementation failure.

No caller parses exception text. `PermitUnavailable`, `CapacityUnavailable`,
`WorkDeferred`, and prefixed rejection strings do not cross the resulting
interface.

## TDD seam

Use real temporary Authority workspaces. `AuthoritySession` is
local-substitutable and does not need a speculative Authority port.

Write focused tests first for:

- plain, structured, and opaque admission advancing one exact revision;
- one forced revision mismatch re-observing and retrying without duplication;
- rejection leaving the session at an exact usable head;
- delegated receipt visibility without caller cursor mutation;
- consumed receipt restoration without invoking the observation callable;
- bounded work admitting every successful observation exactly once;
- one failed observation closing its permit while successful siblings retain
  receipts;
- recovered expired permit closure;
- stale and non-positive capacity returning typed waiting work;
- renewed capacity preserving its scope;
- duplicate receipt, schema drift, malformed permit, and close failure
  remaining direct faults;
- two sessions converging through Rust contention without a Python workspace
  lock.

A clock and wait function may be private injected seams for deterministic
tests. They are not part of the science interface.

## Acceptance

- Exactly one production Python module owns a mutable observed revision.
- All Python Authority decisions use that session.
- `WorkExecution` owns one complete permit life and automatically restores
  consumed work.
- A product Adapter does not maintain another revision cursor.
- No science operation receives raw Authority or mutates a revision.
- Work identity and admitted receipt bytes remain exact.
- No compatibility alias or parallel work lifecycle remains.
- Rust source and protocol fixtures are unchanged.

## Verification

Use the required project interpreter:

```powershell
$projectPython = 'C:\Users\Administrator\miniforge3\envs\research_env\python.exe'

& $projectPython -m pytest `
  tests/authority/test_authority_session.py `
  tests/science/test_work_execution.py `
  tests/solvers/test_ticket07_work_life.py

& $projectPython -m pyright

rg -n "_Admission|_WorkAuthority|decide_current|admission\.revision|authority\.view\(\)\.revision" src tests
git diff --exit-code -- rust
git diff --check
```

The search may mention retired spellings only in explicit absence assertions;
it must return no production use.

## Stop and report

Stop before implementation if the change requires a Rust edit, a protocol or
schema change, a Python workspace lock, a second mutable revision owner, a
change to work identity, or a compatibility layer.

## Do not add

Do not add an Authority port, repository abstraction, dependency container,
background permit watcher, mutable progress store, generic workflow,
exception hierarchy, compatibility alias, record migration, or second work
runner.

## Comments

Resolved with `AuthoritySession` as the sole Python revision and contention
owner and `WorkExecution` as the sole capacity-to-permit-to-receipt-or-close
life. Fresh and restored work now return the same typed `CompletedWork`;
capacity absence is typed waiting; current and capacity compare-and-swap
converge through Rust contention.

The replaced decision helper, work-authority wrapper, runner, Lumerical
evidence recovery module, and their lifecycle-specific tests were deleted
without aliases. Lumerical capacity freshness is bound to an exact admitted
observation reference, same-work concurrent sessions share one stable permit,
restore compares canonical bytes, and every partial acquisition or execution
failure closes its permits, including `BaseException` paths.

The implementing agent passed 196 expanded tests and 51 focused tests.
Independent verification passed 105 affected tests, followed by the final
49-test seam run after the last cancellation-path fix. Pyright reported zero
findings. Production retired-symbol searches were empty, Python decisions
occur only in `AuthoritySession` and the frozen Authority Adapter, Rust had no
diff, and `git diff --check` passed.
