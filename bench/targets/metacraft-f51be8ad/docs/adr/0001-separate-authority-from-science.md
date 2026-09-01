# 0001 — Separate authority from science

Status: accepted

## Context

Earlier designs placed scientific workflow, solver, and campaign meanings inside Rust. That made every scientific change a core change and obscured the durable state machine.

## Decision

Rust owns generic workspace authority only: immutable objects, exact references, revisions, relations, decisions, capacity, permits, atomic commit, integrity, and replay.

Python owns briefs, AI advice, scientific compilation, materials, solvers, sweeps, numerical methods, evidence interpretation, and results. Python proposes; Rust admits or rejects. AI only advises.

The stable Python extension surface is one `Authority` class with `check`, `view`, `fetch`, and `decide`.

## Consequences

Scientific capability can grow without recompiling Rust. Python cannot bypass authority by maintaining a second lifecycle. Rust cannot acquire science-specific relations or fields.
