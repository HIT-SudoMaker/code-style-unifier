# Let cleanup follow the four-brief baseline

Label: `wayfinder:grilling`

Status: resolved (2026-08-09)

## Question

What may leave the project workspace now, and what must wait until the four
briefs establish a traceable baseline?

## Resolution

The user explicitly abandoned the sibling `report` repository and the
`sonnet-ticket09-20260804-01` application root. On 2026-08-09 both exact
directories were verified beneath `E:\Year2026_Project_MetaCraft` and sent to
the Windows Recycle Bin. The report repository had no configured remote and
contained tracked and untracked presentation changes, including a group-
meeting PowerPoint; its recovery now depends on the Recycle Bin or an external
backup. This resolution supersedes only the earlier active-retention
disposition for those two exact paths in
`Let cleanup remove only abandoned work`.

The code repository's current harness-hardening movement, `.scratch` history,
accepted and superseded ADRs, Research Records, canonical skills, and requested
reference repositories remain. The four-brief baseline precedes deletion of
reproducible `.venv`, Rust build output, Python caches, test caches, and local
analysis reports. Existing `runs/` evidence and other ignored references are
reviewed separately after McClung replaces Yun and all four brief capsules are
retained.

## Consequences

- Explicitly abandoned sibling work leaves without turning cleanup into a
  broad repository purge.
- Historical issue identity and decision links remain stable.
- Reproducible cache deletion cannot hide an unfinished four-brief change.
- Old Yun run artifacts become cleanup candidates only after the replacement
  baseline exists.
