# Closure report — Sonnet terminal convergence

Baseline: local `main` at `ca90c27`.

Ticket 07 implementation base: `1e178a2`.

Python:
`C:\Users\Administrator\miniforge3\envs\research_env\python.exe`.

This report closes the non-live implementation road. It records no adviser
call, native Lumerical run, delivery attempt, or canonical-brief result.

## What closed

- SCIENCE assigns 8/12/16 quantization only to propagation phase. Geometric
  phase remains one selected anisotropic cell with continuous orientation.
- Production comments state lasting wire and product-dialect invariants rather
  than ticket history, test provenance, or implementation syntax.
- ADR 0012 and ADR 0014 remain the single accepted records for verified-state
  concurrency and one-way runtime dependencies; neither is duplicated.
- The previous performance-and-reliability road and this terminal road now
  agree with their integrated Git history.
- The canonical live ticket remains `ready-for-human`, blocked by explicit
  approval, with no preparation or execution performed.

## Commit ledger

| Work | Integrated commit |
| --- | --- |
| Plan the terminal convergence | `9e8e043` |
| Ticket 01 — one audit, one generation | `0c64fce` |
| Ticket 02 — exact Python authority decoding | `428af0b`, `1dd10f9`, `18e4fcd` |
| Ticket 03 — runtime dependencies flow one way | `a93d8bc`, `44c493d` |
| Ticket 04 — field evidence hides storage | `9f31996` |
| Ticket 05 — one frontier returns one science | `aa01ee0`, `e6ff0cc`, `2e6430c` |
| Ticket 06 — periodic responses fail honestly | `1baf82e`, `1e178a2`, `2c84e93` |
| Ticket 07 — code and record close together | this closure commit |

Production Rust changed only in Ticket 01 at `0c64fce`. The complete `rust/`
tree remains byte-identical to that commit and matches
`rust/SOURCE_MANIFEST.json`.

## Authority release diagnostics

| Events | Seed | Open audit | Explicit check | Stable view | 16 stable views |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 304 | 5.588 s | 8.695 s | 8.654 s | 1.724 ms | 28.976 ms |
| 1,504 | 80.447 s | 221.562 s | 212.145 s | 5.378 ms | 98.112 ms |
| 3,004 | 308.761 s | 868.099 s | 820.545 s | 10.963 ms | 196.750 ms |

Every stable view must perform zero complete audits and scan zero historical
rows. Stable view was approximately 5,020, 39,450, and 74,848 times faster
than explicit check at the three scales. Timings are diagnostic observations
rather than pass/fail thresholds.

## Final gates

- Complete non-live Python: **776 passed, 15 deselected, 0 failed, 0
  unexpected skips** in 45.00 s.
- Pyright: **0 errors, 0 warnings, 0 informations**.
- Architecture: **71 passed**; the runtime DAG and exact typed-outcome importer
  gates also passed directly.
- Rust: format clean; Clippy clean with warnings denied; all targets passed
  (**18 library + 3 architecture + 17 Interface tests**, with only the three
  separately executed release diagnostics ignored by the ordinary run).
- Rust source manifest: **2 passed**, 18 deselected.
- Touched-production CSU: **0 blocking findings** across `protocol.py`,
  `lane.py`, `probe.py`, and `session.py`.
- Production Rust diff from `0c64fce`: **empty**.
- Fixed-range `git diff --check ca90c27..HEAD`: **clean**.

The fixed implementation range is `ca90c27..HEAD`. Touched-production CSU is
limited to production Python changed by Ticket 07.

## Preserved surfaces

- `.scratch/metacraft-cityu-pre-reorg-hashes.csv` remains untracked and
  untouched.
- `docs/presentations/` remains untracked and untouched.
- Environment files, `runs/`, solver artifacts, and user presentation files
  remain untouched.
- Unrelated `.claude/worktrees/agent-*` worktrees remain registered and
  untouched.
- The clean, patch-equivalent `sonnet-ticket04` and `sonnet-ticket05`
  worktrees are removed only after every final gate passes, without force,
  pruning, or branch deletion.
