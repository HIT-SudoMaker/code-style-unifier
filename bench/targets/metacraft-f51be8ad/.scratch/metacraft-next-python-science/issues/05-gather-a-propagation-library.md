# 05 — Gather a propagation library

**What to build:** The standard propagation study can gather a traceable periodic circular-post response library beneath `runs/`, using bounded independent workers and one Rust permit for each active solver engine.

**Blocked by:** 02 — Compile the standard studies; 04 — Qualify Lumerical.

**Status:** wontfix

**Superseded by:** [Four-brief delivery ticket 05](../../four-brief-metalens-delivery/issues/05-let-circle-and-square-share-one-propagation-proof.md).

- [x] The template constructs one FDTD region, substrate, post, and `grating_s_params` group from the compiled contract; source and reference planes remain group-owned, with no standalone source or monitor.
- [x] Geometry and monitor placement follow the accepted period, height, feature, span, and offset rules and are verified by read-back.
- [x] Only the Lumerical session boundary imports `lumapi` or creates `lumapi.FDTD`.
- [x] Each candidate saves before/after projects, construction evidence, observation evidence, and logs beneath one run root.
- [x] One permit maps to one worker and at most one active engine; worker count never exceeds fresh admitted capacity.
- [x] The Lumerical Adapter launches each solver worker through the shared workstation Interface; the sweep never handles CPU sets or Job Objects directly.
- [x] Each engine is pinned to four distinct physical cores in one locality cell, excludes SMT siblings, and reads back its placement before solving.
- [x] Each engine process tree has a fixed 16-GiB Job Object limit and is admitted only against fresh node-local memory.
- [x] Capacity freshness is checked before every wave; stale capacity launches no further engine and preserves all admitted observations.
- [x] Valid partial observations remain reusable and only missing evidence is recompiled.
- [x] The library retains complex transmission, power, phase reference, solver status, warnings, and provenance.

## Comments

The admitted aggregate record retains every full response beside its exact
observation reference, then exposes the narrow matching projection. The fake
suite proves the contract but does not claim a live Lumerical qualification.

On 2026-07-23, a live 2025 R2 experiment fixed periodic mesh accuracy at `4`.
Moving the source/reflection frame from `-200/-100 nm` to `-300/-200 nm`
changed phase by `0.191 deg` and transmitted power by `0.00280`; accuracy `4`
cost only `1.17x` to `1.24x` the elapsed time of accuracy `2`.

The same fixture measured direct-engine capacity on the current 12-core host.
Pinning two four-core engines to separate LLC domains improved throughput from
`4.18` to `4.54 candidates/min`. A narrower four-worker layout reached `7.22`,
but the accepted execution invariant is intentionally fixed at four physical
cores and 16 GiB per engine. This is a Python placement policy, not a Rust
science or scheduling rule: one candidate worker still consumes one Rust
permit, and geometric-phase `x/y` inputs remain sequential within that worker.

`LumericalSweep` now requires an explicit execution object. `DirectEngine`
closes construction, launches the saved project through the Adapter and shared
workstation, then reopens the completed result. `before.fsp` remains an
immutable construction snapshot; the engine receives its own `engine.fsp`,
and the reopened result is saved as `after.fsp`. Deterministic execution
exists only in tests and writes `native = false` into the admitted
observation. The generic runner rechecks capacity before every bounded wave;
once freshness expires it starts no later wave and keeps already admitted
observations intact.
