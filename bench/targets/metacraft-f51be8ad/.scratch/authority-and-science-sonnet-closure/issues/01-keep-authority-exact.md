# 01 — Keep authority exact

Type: implementation

Status: resolved (2026-07-29)

Blocked by: nothing.

## Outcome

The Rust authority has a distribution-safe freeze gate and a recorded
integrity/scale audit. Its public interface remains one `Authority` with
`check`, `view`, `fetch`, and `decide`.

## Scope

1. Audit `rust/src/authority`, `rust/src/workspace`, and
   `rust/src/python_binding` against ADR 0001.
2. Exercise valid replay at hundreds, thousands, and several thousand ledger
   events. Record timings as diagnostics, not pass/fail thresholds.
3. Audit which failures are stable authority findings and which are internal
   faults. Do not expose science or a new exception framework.
4. Replace `test_rust_tree_is_the_frozen_git_baseline` with a committed source
   manifest verified without `.git`.
5. Include `Cargo.toml`, `Cargo.lock`, Rust source, Rust tests, and the protocol
   fixture in the manifest. Keep build output outside it.
6. Change production Rust only if the audit exposes a reproducible authority,
   integrity, protocol, security, or measured scaling defect.

## Acceptance

- A source archive without `.git` can verify the exact Rust baseline.
- The manifest fails when a governed Rust file changes or a governed file is
  added without an intentional manifest update.
- Valid replay preserves revision, current values, decisions, permits, and
  object integrity at every exercised scale.
- Canonical protocol fixtures remain byte-stable.
- Rust source names no scientific concern.
- The Python extension surface remains exactly one class and four verbs.
- If production Rust is unchanged, the ticket records that as the correct
  result rather than inventing a cleanup.

## Verification

- `cargo fmt --check`;
- Clippy on all targets with warnings denied;
- all Rust tests;
- release build;
- Python import smoke with
  `C:\Users\Administrator\miniforge3\envs\research_env\python.exe`;
- focused architecture tests for the Rust seam;
- CSU on touched non-Rust production files, if any;
- `git diff --check`.

## Stop and report

Stop before implementation if the fix would change the four verbs, wire
schema, authority lifecycle, or generic finding meanings.

## Do not add

Do not add science, a version number in source, a benchmark framework, a
mutable cache, a second authority class, or a Git command in the new freeze
gate.
