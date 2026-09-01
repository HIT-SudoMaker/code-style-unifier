# 23 — Session reuse and run legibility

**Type:** implementation (spec phase 4, independent)

**Status:** wontfix

**Superseded by:** [Metalens Sonnet convergence ticket 07](../../metalens-sonnet-convergence/issues/07-let-lumerical-contain-one-work-life.md).

**Blocked by:** none; the run-manifest slice may proceed beside ticket 18.
The open-once slice remains conditional on ticket 24's workstation proof.

**What to build:** The run **manifest** carries the physical period and the
order regime as the factual record; the directory name may echo them for
readability only (ticket 11). The old run directories and the ledger are not
touched.

Session reuse is conditional on
[The hidden session's workstation contract](24-hidden-session-workstation-contract.md).
`DirectEngine.solve` may keep one hidden product session across build, engine
solve, and result load only when the workstation owns that process tree's
placement, containment, and memory accounting for its complete lifetime. No
GUI Module or GUI-specific Interface is introduced. If the current
workstation Interface cannot provide that ownership, retain the established
two-session lifecycle; an RSS measurement alone is not admission. The three
project files, their bytes, per-candidate recovery, and evidence seams remain
unchanged in either case.

**Acceptance:**

- Public-seam test
  `test_admitted_receipt_survives_replay_without_redispatch` visibly opens a
  permit through typed `Authority`, admits one fake-solver observation as its
  receipt, reopens and checks the workspace, then recovers the exact receipt
  reference and bytes from `view()` without invoking the Adapter again.
- A workstation-seam test proves placement, containment, and memory accounting
  before the open-once path is enabled. Without that proof, tests pin the
  two-session lifecycle.
- When enabled, Adapter tests with a fake session cover the open-once lifecycle
  and failure at each stage; session death mid-candidate closes the permit path
  exactly once. A separately marked live timing check may record the saved
  round-trip, but performance never weakens admission.
- The manifest test shows period and order regime as facts; voided runs
  remain untouched.
- Touched files leave `csu check` with zero hard violations.

Decisions: tickets 09, 11;
[The hidden session's workstation contract](24-hidden-session-workstation-contract.md);
[public-seam acceptance](29-public-seam-acceptance.md).
