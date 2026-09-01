# Close PB response before choosing a cell

Status: resolved (2026-08-10)
Labels: `ready-for-agent`
Depends on: 04

Require complete x/y Jones evidence for every unrotated candidate, calculate
total transmission, converted power, retained leakage, and the adopted
retardance/cross-coupling profile, then filter qualified candidates before a
deterministic ranking. If all candidates fail, return `NoQualifiedPbCell` (or
an equivalent typed finding), never a least-bad CellChoice. Only one qualified
cell may produce the analytical rotation relation and 8/12/16 orientation
sets; no orientation solver work is created.
