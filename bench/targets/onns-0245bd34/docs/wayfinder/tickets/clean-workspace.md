---
title: Clean the workspace without erasing evidence
parent: Close restoration around an intelligent optical front end
type: task
label: wayfinder:task
status: closed
assignee: codex
blocked_by: []
---

# Clean the workspace without erasing evidence

> Current-state note (2026-08-12): project Nature skills were intentionally
> reinstalled after the earlier cleanup. `.agents`, the `.claude` skill
> junctions, and `skills-lock.json` are now protected project tooling. The
> ignored `refresh_workspace.py` is also protected as an unchanged archival
> tool and is not part of routine cleanup.

## Question

Which approved cleanup can be applied now while preserving raw data, formal
fixed-measurement evidence, protocol integrity, and uncommitted worktree state?

## Resolution

The workspace reset uses a delete-first boundary for obsolete local state and
documentation:

- Recycled `.mypy_cache`, `.pytest_cache`, project `__pycache__` directories,
  validation previews, `.superpowers`, `.spec-workflow`, `.codex_tmp`, `.csu`,
  and `.claude`.
- Removed the clean `.claude` Git worktree through Git before recycling its
  parent directory; the branch remains available.
- Preserved formal validation results, the fixed-measurement result tree,
  protocol assets, and all worktrees outside `.claude`.
- Moved two useful fixed-measurement serial runners from `.codex_tmp` into
  `scripts/restoration/` and corrected their project-root resolution.
- Deleted superseded plans, audits, prompts, narrative archives, fixed-era
  ADRs, and transitional research reports.
- Condensed Fixed Restoration into `docs/project-baseline.md`; its code,
  protocol assets, results, and formal entry points remain canonical evidence.
- Reduced the active documentation to the baseline, one competitive research
  synthesis, the frozen data/layers architecture, four ADRs, the active
  Wayfinder map, and the future prompt entry.

No file under `data/raw`, `results/restoration/fixed_measurement`, or any
protocol asset directory was moved, edited, or deleted. Existing user changes
in the primary worktree remain intact.

The 2026-08-12 maintenance pass removed only reproducible `.mypy_cache`,
`.pytest_cache`, `.spec-workflow`, and project-source `__pycache__` state. It
added `.mypy_cache/` to `.gitignore` and did not run or modify
`refresh_workspace.py`.
