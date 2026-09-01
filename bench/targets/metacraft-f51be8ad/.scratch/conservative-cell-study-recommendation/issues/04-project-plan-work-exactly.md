# Project CellStudyPlan work exactly

Status: resolved (2026-08-10)
Labels: `ready-for-agent`
Depends on: 03

Make periodic request construction consume `CellStudyPlan.work` verbatim.
Remove the downstream complete-grid and Cartesian reconstruction paths from
the new lifecycle. Preserve a clearly named legacy adapter only when an old
serialized root is explicitly selected. Assert candidate identity, basis,
height, period, material, and work count against the plan before creating
solver-neutral work. Add tests proving PB has two basis tasks per geometry and
zero orientation tasks.
