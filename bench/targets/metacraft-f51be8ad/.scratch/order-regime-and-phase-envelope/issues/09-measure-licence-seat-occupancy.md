# 09 — Measure licence seat occupancy before changing session lifetime

**Type:** `wayfinder:task`

**Blocked by:** None — on the frontier.

**Status:** resolved (2026-07-26)

## Question

Does holding a hidden CAD session open across the engine solve consume a licence
seat that `bounded_capacity` is not accounting for?

Session reuse saves roughly 22 s per candidate by keeping the construction
session alive instead of closing it at `adapter.py:225` and reopening at
`adapter.py:228`. But `qualification.py:403` sets concurrency to
`min(license_limit, layout.limit)` on the assumption that one unit of work holds
one seat. If an idle CAD session and its engine each hold a seat, concurrency
must halve — and halved concurrency can cost more than 22 s per candidate buys.

Work to do:

- Read the existing licence query path (`probe.py:226`, timeout 15 s) and record
  what it reports and at what granularity.
- Record the actual `license_limit` and `layout.limit` on this workstation.
- Measure seat occupancy in three states: idle hidden session only; engine only;
  hidden session held open while an engine runs.
- Record peak memory of an idle hidden session — it sits outside the lane's job
  object, so the 16 GiB guard does not cover it.

Record the numbers in the resolution. They decide whether session reuse ships,
ships with a halved capacity rule, or does not ship.

## Comments

### 2026-07-26 — Claude Code, read-only preparation

- Verified: capacity observes exactly one licence feature. The probe binds
  `binding.license_feature` and queries it with
  `lmutil lmstat -f <feature> -c <server>` (`probe.py:214-237`);
  `bounded_capacity` never sees any other feature. A hidden CAD session may
  well draw a *different* feature the model never observes.
- Protocol addition: in each of the three states, also run `lmstat` without
  `-f` (full feature table) and diff the per-feature in-use counts, so the
  measurement reveals which feature the CAD session checks out versus
  `fdtd-engine.exe` — not just the bound feature's count.
- Verified: today CAD and engine never overlap inside one lane —
  `DirectEngine.solve` closes the session at `adapter.py:225` before
  `execute` at `:227`. Reuse makes them overlap for the full ~57 s solve, so
  the same-pool worst case is 2 seats per lane; the split-pool case instead
  requires the untracked CAD pool to hold at least `lanes` seats.
- The held-open session lives outside the lane's job object, so the 16 GiB
  guard does not cover it — record its RSS while the engine runs.

## Resolution (2026-07-26)

Measured on this workstation in four states (baseline / idle hidden session /
engine only / both), full `lmstat -a` table each time, checkout lines matched
to process PIDs. Raw tables in the session scratchpad
(`lmstat_state0_baseline.txt` … `lmstat_state3_both.txt`).

- **Different pools.** The hidden CAD session checks out `lumerical_gui`;
  `fdtd-engine.exe` checks out `lumerical_solve`. They never cross. Both
  pools hold **500 seats** (server `1055@localhost`, vendor `ansyslmd`
  v11.19.5, expiry 2035-12-31).
- **Capacity conclusion:** holding a hidden CAD session open across the
  solve consumes no `lumerical_solve` seat, so session reuse does **not**
  halve `bounded_capacity` concurrency — with 500-seat pools the licence is
  not a bottleneck at all. Session reuse ships with no capacity-rule
  change.
- **Memory:** idle hidden session RSS 237.5 MB (stable); engine (-t 4)
  ~108 MB, observed peak ~131 MB. The held session sits outside the lane
  job object but at 0.24 GB is no threat to the 16 GiB budget.
- **Defect found (must fix in the spec):** `probe.py:231`'s regex
  `Total of (\d+) licenses issued;\s+Total of (\d+) licenses in use` fails
  on FlexNet's singular form `Total of 1 license in use` — with exactly one
  seat in use, `_license_capacity` raises `license_capacity_unreadable`.
  Fix: `licenses? in use` (and the plural on "issued" likewise guarded).
