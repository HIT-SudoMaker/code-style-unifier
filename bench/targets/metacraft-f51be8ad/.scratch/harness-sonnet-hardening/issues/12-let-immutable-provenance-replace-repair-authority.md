# Let immutable provenance replace repair authority

**Parent specification:** [Harness-native Sonnet hardening](../spec.md)

**Status:** resolved (2026-08-09)

**Assignee:** Codex

**Blocked by:** none

**Implementation authorization:** Explicit owner approval of the parent
specification is required before any code, test, or canonical-document edit.

## What to build

Snapshot the complete byte identities under retained `acceptance/07`, then
delete both correction flags, both correction writers, correction-only capsule
helpers, dispatch branches, and unused imports from the active runner. Retain
only `--preflight` and `--run --evidence-root <absent-directory>`.

Deepen `tests/acceptance/test_retained_harness_evidence.py` into a read-only
proof of the original, audit-corrected, and retained-evidence-corrected chain:
manifest and correction digests, every old/new run identity, current artifact
bytes, both zero-rerun declarations, redaction/confinement facts, honest
failure positions, and bounded reports. Add a runner Interface test proving
the removed modes are rejected.

Recompute the whole retained-tree snapshot after the change and require exact
equality.

## Acceptance

- No byte under retained `acceptance/07` changes.
- No executable correction, repair, amendment, migration, verify, overwrite,
  or recovered-path writer survives elsewhere.
- The verifier opens no harness and writes no artifact.
- The CLI accepts only the two fresh-run modes.
- Focused retained-evidence/runner tests and `git diff --check` pass.

## Exclusions

Do not implement profiles or partial campaigns, regenerate a retained artifact,
move writers to an archive, add a compatibility flag, run a harness, or edit
production, canonical docs, map, index, or historical correction records.

## Stop condition

Stop when immutable identities alone preserve the correction history and the
active code has exactly one fresh-run writer road.

## Comments

Implemented under explicit owner approval on 2026-08-09. The retained
`acceptance/07` tree was snapshotted before editing as 42 files with whole-tree
identity
`sha256:50145dc009658ce518c52b57fa4ab0c6fbe4628414d8ccaa337f414df67c223b`.
The after snapshot has the same file count and identity.

The active runner now exposes only `--preflight` and an explicit
`--run --evidence-root <absent-directory>`. Both correction flags, dispatch
branches, correction writers, recovered-capsule helpers, and the correction-
only `re` import were deleted. The old retained root is no longer a default
CLI destination.

The read-only retained verifier now proves the original, audit-corrected, and
sanitized manifest chain; both correction-record identities and zero-rerun
declarations; every run's old/new transcript, stderr, audit, and outcome
identity available in the chain; current artifact bytes; post-hoc identities;
confinement and redaction; honest Codex/Claude failure positions; empty advice,
choice, and answer facts; and bounded report claims. Runner Interface tests
prove both retired modes are rejected, the two fresh modes are the only named
modes, and `--run` cannot fall back to a retained root.

Verification used only the required project interpreter and opened no real
harness or Native execution:

```text
C:\Users\Administrator\miniforge3\envs\research_env\python.exe -m pytest tests/acceptance -q
15 passed in 16.55s

before: 42 files, sha256:50145dc009658ce518c52b57fa4ab0c6fbe4628414d8ccaa337f414df67c223b
after:  42 files, sha256:50145dc009658ce518c52b57fa4ab0c6fbe4628414d8ccaa337f414df67c223b

git diff --check
passed
```

No production file, canonical document, retained artifact, map, index, later
ticket, or historical correction record was edited. No commit was created.

Reopened verification on 2026-08-09 after independent review found that the
recorded before/after snapshot was not yet a permanent test assertion. The
read-only verifier now ratchets the complete retained tree at 42 files and
`sha256:50145dc009658ce518c52b57fa4ab0c6fbe4628414d8ccaa337f414df67c223b`.
Its documented canonical framing is sorted POSIX-relative paths, with each line
formed as `path<TAB>byte-size<TAB>lowercase-file-sha256`, UTF-8 without BOM,
LF-joined without a trailing newline, followed by SHA-256 of those canonical
bytes. This closes the unreferenced-addition gap without writing an artifact.
The full acceptance suite passes with `29 passed in 23.97s`; canonical Pyright
reports 0 errors, warnings, or information; `git diff --check` passes; and the
retained `acceptance/07` tree still has zero Git diff. The ticket remains
resolved. No live harness, retained artifact, map, index, or commit was changed.
