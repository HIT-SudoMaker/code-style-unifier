---
name: csu-review
description: Run and interpret CSU semantic source reviews for Python, Rust, C, and C++. Use when checking coding standards, documentation carriers, identifier semantics, dependency declarations, or CSU Clean, Findings, and Incomplete results.
license: MIT
metadata:
  author: HIT-SudoMaker
---

# CSU Review

Run one sealed semantic source review and return its evidence. CSU observes
source; it does not execute target code or edit it during the review.

## Resolve the review contract

Identify these three inputs before running CSU:

1. **Workspace**: use the scope named by the user. Otherwise choose the smallest
   source root that completely covers the requested judgment. Keep an existing
   `.csu-inventory.json` as the frozen file owner.
2. **Authority**: prefer the user-supplied path, then
   `.csu/authority/authority.json`. Use
   `docs/authority/csu-self/authority.json` only when reviewing the CSU
   repository itself.
3. **Executable**: prefer `csu` on `PATH`. Inside the CSU repository, a current
   `target/release/csu` or `target/release/csu.exe` is also valid.

An external project without its own Authority is blocked. Return
`BLOCKED_MISSING_AUTHORITY` with the expected path and stop. Never substitute
CSU's self Authority, infer public callables, or expand vocabulary to obtain a
verdict.

If no executable exists, return `BLOCKED_MISSING_EXECUTABLE` with the cheapest
applicable installation command and stop. Do not install software implicitly.

The contract is resolved when the exact executable, Authority directory, and
workspace path are known and the Authority belongs to that workspace.

## Capture one terminal

Create a UTC run identifier in `YYYYMMDDTHHMMSSZ` form and use:

```text
.csu/runs/<UTC-run-id>/
```

Run exactly one semantic review:

```text
csu review --authority <authority-directory> --workspace <workspace> --format json
```

Capture stdout, stderr, and the exit code independently. Parse stdout before
writing it:

- Valid schema-versioned JSON becomes `CSU-REVIEW.json`.
- Non-empty stderr becomes `CSU-STDERR.txt`.
- Invalid or absent JSON becomes `CSU-STDOUT.txt`; report
  `BLOCKED_INVALID_PROJECTION` and preserve the exit code.

Do not run a second human-format review. The JSON projection is the single
evidence owner for this run.

The capture is complete when the exit code and either a valid terminal
projection or a typed blocked setup result are preserved.

## Read the terminal

Interpret the projection on independent axes:

| Terminal evidence | Conclusion |
|---|---|
| `sealed + complete + clean` | Clean |
| `sealed + complete + findings` | Complete with Findings |
| `sealed + incomplete` | Incomplete, regardless of Finding count |
| `rejected` | Authority or request rejected before a valid review |
| `failed` | Review execution failed |

For a sealed result, read the scope, Completion, Finding summary, blocked
families, ordered Findings, metrics, presentation, and Seal. For a rejected or
failed result, read its error code and message. Exit codes are transport
signals; they never replace the terminal.

Use the projection to prepare the chat response. `CSU-REVIEW.json` remains the
only persisted interpretation of the terminal. Do not write a parallel
Markdown report or call a result Clean unless all three Clean conditions are
present.

## Repair only when requested

Review leaves target source read-only. If the user explicitly requests repair,
record the original Seal and Finding identity, make the smallest semantic
source change, and run CSU again into a new run directory.

A valid repair keeps the governed declaration visible and uses the language's
real carrier. Replacing documentation with an ordinary comment, renaming or
deleting a declaration to hide it, changing Authority or grade, adding an
exclusion, or accepting Incomplete as Clean is an evasion, not a repair.

The repair is complete only when the new terminal is interpreted independently
and every changed Finding or blocked family is accounted for.

## Return to the user

Return a compact result containing:

1. Terminal, Disposition, Completion, and exit code.
2. Finding counts by grade and blocked family count.
3. Seal or typed blocked reason.
4. The absolute run directory and the authoritative JSON path when present.
5. One next action grounded in the terminal evidence.

Keep unknowns visible. A missing input ends in a typed blocked result, not a
fabricated review.
