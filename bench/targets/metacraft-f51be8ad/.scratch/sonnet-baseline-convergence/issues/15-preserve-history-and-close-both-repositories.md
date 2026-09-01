# 15 — Preserve history and close both repositories

**What to build:** A recoverable, immutable phase archive followed by exact
local Git cleanup, leaving code and report ready for brief validation.

**Blocked by:** 14 — Prove the pre-brief-validation baseline.

**Status:** resolved (2026-07-30)

- [x] The closure record and all intentional code and report changes are
      committed before any ref or worktree removal.
- [x] Matching immutable annotated stage tags identify the verified heads of
      both repositories; the existing code tag remains at its original object.
- [x] Complete bundles containing all then-current refs and tags are created
      for both repositories and independently verified before cleanup.
- [x] Every Git LFS object reachable from the tagged report commit is collected
      into a separately hashed, restorable payload archive because Git bundles
      do not contain LFS object bytes.
- [x] The ignored archive manifest records both tagged commits, both bundle
      hashes, the LFS payload archive hash, all four brief identities, and the
      exact disposition of branches, worktrees, and deleted duplicates.
- [x] Every worktree target is resolved and confirmed to be an intended stale
      code worktree before removal.
- [x] Only merged or patch-equivalent obsolete branches are deleted; unique
      commits, current branches, intentional tags, and the main history remain
      reachable.
- [x] The code repository is not reinitialized, squashed, or reset.
- [x] Ordinary Git maintenance packs reachable history and prunes only
      unreachable loose objects after the verified bundles exist.
- [x] Both repositories finish on their tagged intended heads with clean
      statuses, functioning LFS checkout, and verified recovery artifacts.
- [x] The final handoff states that the next authorized work is the separate
      four-brief validation phase, not further baseline refactoring.

## Closure record

The immutable recovery set is stored in the report repository's ignored
`archive/phase-archives/pre-brief-validation-2026-07-30/` directory. Its phase
manifest records the tagged code and report commits, complete pre-cleanup Git
bundles, the report's reachable LFS payload, four-brief identities, and exact
SHA-256 identities for the dirty stale-worktree patches and untracked files.

An independent read-only audit found no production behavior in either stale
agent worktree that is absent from the verified main line. Both worktree heads
are merged; the two ticket branches are patch-equivalent to main. Cleanup is
therefore limited to those four obsolete branches and the two exact stale
worktrees named in the ignored manifest. `main`, the matching stage tags, the
existing `next-v0.0.0` tag, and all repository histories are retained.

The next authorized work is the separate four-brief validation phase. Further
baseline refactoring is outside this closure.
