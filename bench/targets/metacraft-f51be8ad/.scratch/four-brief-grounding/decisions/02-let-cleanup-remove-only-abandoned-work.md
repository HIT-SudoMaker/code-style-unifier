# Let cleanup remove only abandoned work

Label: `wayfinder:grilling`

Status: resolved (2026-07-30)

## Question

Which untracked presentation, figure-audit, section-QA, cleanup-trash, and
pre-reorganization hash artifacts are abandoned and may be deleted, which
belong outside the code repository, and which remain active user work that
must be preserved?

## Decision

Active presentation sources now belong to the independent `report` repository.
Historical cleanup material, section-QA snapshots, the audited figure working
copy, the pre-reorganization inventory, and the non-unique editor backup were
removed from the code workspace only after exact byte-count and SHA-256
verification against their retained report destinations.

The ignored recovery record is
`report/archive/presentation-archive-v1/decision-trace-v1.md`; its
`manifest-v1.csv` contains 229 source dispositions totaling 190,027,459 bytes
and has SHA-256
`5a9442d449823dc51b7817976de64466109b1418e3bf82ddd97b9a5fb6b73488`.
The tracked report head recording the migration is
`4c7340206eb139a909a254296988d8beda11f5e5`.

The separate four-brief grounding decisions and the active convergence tracker
remain in the code repository. No Git ref, worktree, tag, or unique history was
removed by this decision.
