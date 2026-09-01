# Four-brief grounded baseline closure

Closed: 2026-08-12

This record seals the four-brief baseline after the owner-approved direct
caller evaluation. It records identities and reproducibility facts; scientific
authority remains in each capsule's canonical brief, material receipts, and
answer documents.

## Retained outcomes

| Slot | Case | Period | Height | Terminal state | Next study | Capsule digest |
| --- | --- | ---: | ---: | --- | --- | --- |
| 01 | McClung 2024, low-NA propagation | 430 nm | 650 nm | `WaitingStudies` | periodic transmission | `a6691bb45acd0a7e0f6b749352d8e1b9c537aaeb7e780f0d7bfce4e654f29957` |
| 02 | Yang 2018, low-NA PB | 1500 nm | 800 nm | `WaitingStudies` | Jones library | `96bdc19c0fe21c1788dbd99fa236859771977003bdb6918cc46802b287d3fae9` |
| 03 | Arbabi 2015, high-NA propagation | 800 nm | 900 nm | `WaitingStudies` | periodic transmission | `8607d67b723fb274fc0fee8bba9b6d762d01732bd73a9f2623f3a74bf484419a` |
| 04 | Khorasaninejad 2016, high-NA PB | 320 nm | 600 nm | `WaitingStudies` | Jones library | `8bc8a882d09d69a801348267b2dd6dcc88d24fece7398d6c0574a4257f35046e` |

Each digest is SHA-256 over the ordered lines
`<file-sha256><two spaces><capsule-relative-path>\n` for the 13 retained,
versionable capsule files. Prepared application databases, locks, and the
bundled executable are excluded as reproducible local runtime material.

All four choices are on the 10 nm fabrication grid and strictly below their
sampling ceilings. Their multi-order classifications and cautions remain
visible. Yang's 800 nm height intentionally records the lowest emitted legal
choice; the 340 nm paper value was outside the emitted 800/850/900 nm domain.
Paper proximity is diagnostic and was never an acceptance threshold.

## Harness history

The sealed nested-process campaign under `acceptance/03/` contains four honest
failures: Codex policy rejected execution of the capsule-local Windows PE
before the first consultation. A later single-variable smoke reproduced that
boundary. These artifacts are retained as historical usability evidence.

The accepted baseline is `acceptance/03-direct-codex/`. The active Codex agent,
acting as an ordinary harness caller, invoked the installed `metacraft` command
directly. It supplied exactly one canonical period answer and one canonical
height answer per fresh material-grounded root, then restored every root in a
fresh process with no current consultation. It did not use a nested provider,
network search, Lumerical, a parameter sweep, or a field calculation.

## Cleanup classification

The active catalogue contains McClung, Yang, Arbabi, and Khorasaninejad; the
live Yun example and contract test are removed. The exact historical run
`runs/brief-stage-yun-20260808-130913-ddc0e3c6` and seven large two-case Native
work directories were moved, not destroyed, to the recoverable external
archive `E:\Year2026_Project_MetaCraft\local-archive\metacraft-code-cleanup-20260812`.
No unknown path was removed. Local `authority/`, `runs/`, diagnostics, FSP,
SQLite, lock, and executable products are ignored while tracker records and
small reproducibility evidence remain versionable. Previously owner-authorized
deletion of sibling `report` and `sonnet-ticket09-20260804-01` directories is
historical and was not repeated by this seal.

## Qualification

The terminal repository qualification passed with:

- deterministic non-live pytest: `1519 passed, 5 deselected`;
- architecture pytest: `118 passed`;
- Pyright: `0 errors, 0 warnings`;
- Rust Authority: `39 passed, 3 ignored` across unit and contract suites;
- CSU over `src/metacraft`: `0 hard`, `5021 under_review`;
- `git diff --check`: passed apart from Git's existing line-ending notices.

Default isort is not a repository gate: its import grouping conflicts with the
CSU dependency-order contract and also reports historical files outside this
initiative. The terminal source ordering follows the repository-owned CSU
contract, not an incompatible formatter rewrite.

Integration, Lumerical live/canary/delivery, Native, paid, field-performance,
and achromatic runs are explicitly outside this seal.

## Boundary

This closure proves a material-grounded, replayable brief-to-`WaitingStudies`
baseline and one coherent implementation road. It does not claim periodic-cell
accuracy, full-aperture focusing accuracy, paper-efficiency reproduction, or
support for every material record. Those belong to a new bounded full-flow
evaluation, not another brief-stage refactor.
