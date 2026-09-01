# Close propagation response with global phase offset

Status: resolved (2026-08-10)
Labels: `ready-for-agent`
Depends on: 04

Assess admitted complex transmission against the exact plan work. For each of
8, 12, and 16 levels, search and record a deterministic global phase offset,
apply cyclic half-step tolerance and distinct-cell identity, and check useful
power/leakage. A complete shifted library is valid; fixed zero offset is not a
contract. The 8-level 3pi/2 span remains a diagnostic necessary-condition
heuristic only. Insufficient or poor evidence returns a typed finding and
cannot form a PhaseSet.
