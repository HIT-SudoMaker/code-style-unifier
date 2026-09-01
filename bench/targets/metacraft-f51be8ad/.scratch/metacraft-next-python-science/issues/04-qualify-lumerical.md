# 04 — Qualify Lumerical

**What to build:** The shared local workstation can place external engines, and the Lumerical Adapter can establish one exact FDTD binding, its solver-native materials, and a fresh safe capacity before any solver task is exposed as ready.

**Blocked by:** 01 — Cross the authority boundary.

**Status:** wontfix

**Superseded by:** [Four-brief delivery tickets 02 and 04](../../four-brief-metalens-delivery/spec.md).

- [x] Exact executable and Python API paths come from environment configuration and are never searched across the machine.
- [x] Readiness follows configured, found, versioned, licensed, qualified, available in order.
- [x] The binding records exact product/API identities and resolves installed silica and silicon-nitride material names.
- [x] `metacraft_next.workstation` owns topology, four-physical-core/no-SMT lane planning, 16-GiB Job Object containment, and placement read-back without importing a solver product.
- [x] The Lumerical Adapter supplies the fixed four-thread direct-engine command to the workstation Interface, while the product package retains all Lumerical discovery, licensing, native construction, and result parsing.
- [x] Direct-engine capacity is derived from fixed four-physical-core, no-SMT, 16-GiB lanes under fresh topology, node-memory, and license evidence.
- [x] Product dispatch observes capacity automatically, runs remaining candidates in bounded waves, renews stale capacity, and waits when another sweep owns the available permits.
- [x] Fake and opt-in live probes exercise the same public contract.
- [x] Solver-native material identities cannot escape the exact binding.

## Comments

The deterministic probe and authority admission slice are implemented. The
opt-in live probe inspected the configured Ansys Lumerical 2025 R2
installation, verified that the executable and API belong to the same
installation, read its version, CPU resource, license estimate, native
materials, and `grating_s_params` surface, successfully checked out and
released one required solve feature, measured the free feature count through
the configured license utility, and built both periodic templates with exact
object and internal-plane read-back.

The unreliable CAD job-manager path is not used for execution. Qualification
closes its discovery session, saves one propagation project and the two
geometric `x`/`y` projects beneath `runs/`, executes each through the
same-installation `fdtd-engine.exe` Adapter and one workstation lane, then
reopens the completed projects for `grating_s_params` result read-back. A
binding and capacity can be emitted only after all three fixtures return
finite valid observations. License freshness begins when `lmutil` is read,
not when those later fixtures finish, so a long qualification cannot renew an
old capacity observation.

The direct-engine capacity seam must not reuse the CAD Resource Manager's
`capacity=1 / total cores=4` as a host fact. Python enumerates processor
groups, NUMA nodes, LLC domains, physical cores, and SMT siblings at runtime.
One lane always uses four distinct physical cores in one locality cell,
selects one CPU set from each core, excludes its SMT siblings, and is contained
by a 16-GiB Job Object limit. Four physical cores and 16 GiB remain reserved
for the workstation. On the current 12-core host this yields two lanes, one in
each LLC domain.

The workstation package is shared execution infrastructure, not a Lumerical
submodule. CST and COMSOL remain absent from the current implementation. When
a real installation and license contract exists, each product gets its own
solver Adapter and reuses the same workstation Interface; no speculative
common solver abstraction is added now.

The planned public surface is deliberately small:

```text
layout = workstation.plan(demand)
worker = workstation.start(command, layout.lane)
```

The layout retains opaque lanes, a freshness interval, a local capacity limit,
and evidence safe for authority admission. The command carries only generic
process-launch facts. The workstation starts it suspended, applies the lane and
Job Object, verifies effective placement, and resumes it. The Lumerical Adapter
creates the direct-engine command; its package constructs the native project
and parses the native result.

```text
src/metacraft_next/workstation/
  __init__.py
  model.py
  windows.py

src/metacraft_next/solvers/lumerical_fdtd/
  adapter.py
```

Default tests plan from deterministic host facts and launch harmless parent
and child processes to verify four distinct physical cores, excluded SMT
siblings, process-tree affinity, the Job Object limit, exclusive lane use,
cleanup, and read-back. Live FDTD remains an opt-in Adapter test. No CST
package, fake CST semantics, native material, or placeholder command is
created.

The live dispatch test on the configured 2025 R2 workstation admitted two
workers and completed two 1000-fs propagation cells concurrently. Placement
evidence reported `lane-01` on LLC 0 and `lane-02` on LLC 12; each process tree
used four physical cores, excluded SMT siblings, and carried a 16-GiB Job
Object limit.
