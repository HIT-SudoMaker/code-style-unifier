# Let two concrete profiles own two dialects

**Parent specification:** [Harness-native Sonnet hardening](../spec.md)

**Status:** resolved (2026-08-09)

**Assignee:** Codex

**Blocked by:** [Let immutable provenance replace repair authority](12-let-immutable-provenance-replace-repair-authority.md)

**Implementation authorization:** Explicit owner approval of the parent
specification is required before any code, test, or canonical-document edit.

## What to build

Replace harness-string dispatch in acceptance support with the closed
`CodexAcceptanceProfile | ClaudeAcceptanceProfile` union and the fixed
`ACCEPTANCE_PROFILES` tuple. Implement only the frozen preflight, prepare, and
observe behaviors and their four shared immutable values. Keep common capsule
facts, canonical command parsing, confinement, redaction, inspection, sealing,
and reporting in shared support/runner ownership.

Use small recordings from both real native JSONL dialects. Test exact native
layout, byte-identical canonical skill materialization, environment, argv,
cwd, prompt channel, normalized access/explanation facts, and fail-closed
missing/unknown/case-changed/malformed/forbidden/path/write mutations.

Delete string parameters and superseded argument/environment/event/access/
explanation switches without compatibility wrappers. Update the concrete-
profile ownership clauses in `DESIGN.md` and `DEVELOPMENT.md` in this slice.

## Acceptance

- The tuple is literally Codex then Claude and the runner passes each same
  object through preflight, preparation, execution, and observation.
- Each profile owns its complete external convention; shared policy is not
  copied into profiles.
- Valid live and recorded bytes would cross the same `observe` path.
- Production imports/defines no profile and the canonical skill remains the
  sole behavior source.
- Focused profile/audit/capsule tests and `git diff --check` pass.

## Exclusions

Do not add a Protocol, registry, discovery, plugin, callback recipe, third
harness, production Adapter, live execution, campaign partial-availability
logic, retained-artifact rewrite, `CONTEXT.md`, ADR 0021, map, or index.

## Stop condition

Stop when every real CLI dialect decision has one concrete acceptance-only
owner and the shared lifecycle contains no harness-name redispatch.

## Comments

Implemented under explicit owner approval on 2026-08-09 after Ticket 12
removed historical repair authority. Acceptance support now contains exactly
the frozen `CodexAcceptanceProfile | ClaudeAcceptanceProfile` union and the
fixed Codex-then-Claude `ACCEPTANCE_PROFILES` tuple. The runner passes each
same profile object through preflight, preparation, private execution, and raw
and redacted observation while retaining the existing fixed 2x4 lifecycle.

Each profile owns its executable/help/flag contract, native skill destination,
authentication environment names, capsule overlay, argv/stdin, strict event
dialect, outer command grammar, normalized accesses, and final explanation.
The common capsule facts, reviewed runtime filtering, canonical
`metacraft conduct` primitive, confinement and answer-name policy, redaction,
inspection, classification, hashing, sealing, and post-hoc reports remain
shared. The superseded harness-string parameters, argument/environment
helpers, mixed event walker, dialect switch, and runner explanation switch
were deleted without compatibility wrappers. A private execution callable was
retained for the existing runner; no `RecordedHarnessExecution`, partial
campaign, or Ticket 14 artifact/counting behavior was added.

Profile tests use stable outer-event fixtures from the already retained real
Codex and Claude streams. The Codex fixture is an exact selection of real
lines, and the Claude fixture is byte-identical to its three-line retained
authentication stream. The retained Claude sessions contain no real
`tool_use` event, so Read, Write, and Bash cases are explicitly documented and
tested as derived content-block mutations of the real assistant outer
envelope. They are not claimed as a real Claude tool-use recording. No live
harness was opened to fill that evidence gap.

Verification used the required project interpreter:

```text
C:\Users\Administrator\miniforge3\envs\research_env\python.exe -m pytest tests/acceptance -q
20 passed in 17.40s

C:\Users\Administrator\miniforge3\envs\research_env\python.exe -m pyright tests/harness_acceptance.py tests/harness_acceptance_runner.py
0 errors, 0 warnings, 0 informations

C:\Users\Administrator\miniforge3\envs\research_env\python.exe -m pyright
0 errors, 0 warnings, 0 informations

git diff --check
passed
```

The retained `acceptance/07` root remains 42 files with whole-tree identity
`sha256:50145dc009658ce518c52b57fa4ab0c6fbe4628414d8ccaa337f414df67c223b`.
No production file, retained artifact, `CONTEXT.md`, ADR, map, index, Ticket 14
campaign behavior, live harness, Native execution, or commit was included.

An independent review reopened Ticket 13 for one Medium contract drift: the
private execution callable received only `HarnessInvocation`, so the recorded
campaign inferred its fixture dialect from `argv[0]` instead of receiving the
same concrete profile object used by the lifecycle. The callable now receives
`(profile, invocation)`, the runner passes the exact tuple singleton through
execution, and `RecordedHarnessExecution` selects recordings only from
`profile.name`. A lifecycle test proves object identity through preflight,
prepare, execution, and both raw and redacted observation calls; a focused
search found no harness-name redispatch in shared acceptance support.

Final verification after the Medium fix used the repository interpreter and
opened no live harness: all 28 acceptance tests passed in 25.38 seconds;
targeted and project Pyright each reported 0 errors, 0 warnings, and 0
informations; `git diff --check` passed. Ticket 14 counting, terminal,
artifact, report, and sealing semantics were unchanged.
