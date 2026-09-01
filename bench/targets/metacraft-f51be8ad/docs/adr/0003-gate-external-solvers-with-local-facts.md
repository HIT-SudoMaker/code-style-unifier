# 0003 — Gate external solvers with local facts

Status: accepted

## Context

Solver sweeps are limited by installed software, API compatibility, license features, local compute, and memory. Guessing these facts produces invalid plans and license contention.

## Decision

External solver readiness follows:

`configured → found → versioned → licensed → qualified → available`

Users provide exact product paths in a product-owned environment file such as
`.env.lumerical`; `.env` is reserved for LLM/API credentials. Each solver
Adapter owns its product discovery, version, license, native model, command,
and result parsing.

A shared Python workstation Module owns local topology, physical-core
placement, NUMA/LLC locality, process containment, and memory admission. Its
fixed lane is four distinct physical cores with SMT siblings excluded and a
16-GiB process-tree limit. Solver Adapters request lanes; they do not implement
their own affinity or memory policy.

The solver Adapter supplies a product-owned worker command. The workstation
Implementation starts that worker suspended, places it in one lane, contains
its complete child process tree, verifies the effective placement, and only
then resumes it. The Adapter retains the entrypoint, product API, and all
scientific meaning. Lumerical currently uses its direct `fdtd-engine.exe`
entrypoint; another product may instead use a small Adapter-owned worker that
opens its API inside the contained tree.

Python combines the workstation layout with the product's fresh license facts
to form capacity evidence. Rust reserves that capacity with generic permits;
Python schedules the independent workers.

Worker count is not a client parameter. A product-owned dispatch observes the
license and workstation, chooses their tightest bound, admits that capacity,
and opens a sweep. The runner executes remaining candidates in bounded waves
and renews stale capacity before starting another wave. Completed candidates
are not repeated merely because the bound changed.

Independent sweeps in one workspace share the same Rust capacity scope. A
runner waits when every permit is occupied and retries optimistic revision
contention; it neither overbooks the solver nor treats temporary contention as
a scientific failure.

Solver-native materials remain valid only inside their qualified solver binding.

Qualification is immutable evidence for one exact implementation, not a mutable solver status. Binding states what that implementation can do, capacity states how many workers its scope currently admits, and a permit reserves one worker. Availability is derived from a matching binding and fresh positive capacity rather than stored as another state object.

Loading the API, checking out a license, and constructing native objects do
not prove that the simulation engine can accept work. Engine execution must be
verified before qualification emits a binding or capacity.

## Consequences

One MetaCraft workspace may supervise several independent sweeps without
moving process scheduling into Rust. Missing software or license blocks
execution honestly but does not corrupt scientific compilation.

Lumerical is the first solver Adapter. A future CST or COMSOL Adapter must use
the same workstation Interface while retaining its own product-specific
qualification, construction, license, and observation semantics. No common
solver Interface is introduced until a second real Adapter proves which
product behavior actually varies.
