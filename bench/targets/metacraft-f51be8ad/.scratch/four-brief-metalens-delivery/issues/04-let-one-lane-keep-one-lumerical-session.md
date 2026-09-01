# 04 — Let one lane keep one Lumerical session

**Type:** implementation

**Status:** wontfix

**Superseded by:** `../../metalens-sonnet-convergence/spec.md`

**Blocked by:** ticket 03.

## Outcome

Each automatically admitted workstation lane owns one hidden Lumerical
session across its candidate wave, including its direct-engine descendants.

## What to build

- Record native `lumerical_gui` and `lumerical_solve` limits independently
  and admit the minimum of both and available workstation lanes.
- Keep one hidden session per admitted lane instead of opening a session for
  each candidate or basis.
- Apply four distinct physical cores without SMT siblings, one locality cell,
  and the shared 16 GiB process-tree limit for the lane's whole lifetime.
- Give each geometric x/y basis solve its own work identity, permit, receipt,
  artifact, and replay decision.
- Invalidate only unfinished work on a failed lane; retain already admitted
  evidence and recover only a missing basis.
- Record session reuse, placement, native capacity, work identities, and
  artifacts in product-owned manifests.
- Keep the common runner generic while the contained session worker remains
  local to the Lumerical Adapter.

## TDD seam

Begin with a fake native Lumerical interface and observable session lifetime.
Then prove separate license pools, automatic lane count, paired basis work,
failure recovery, and manifest facts.

## Acceptance

- Candidate work reuses one session per lane.
- Callers provide no worker count and cannot bypass placement.
- The Adapter owns discovery, version, license, native construction,
  sessions, parsing, and manifests; the workstation owns placement only.
- Fake tests pass and marked live tests are present but not run by default.
- No GUI interface, generic license framework, or CST/COMSOL Adapter is added.
- Architecture tests, Pyright, and CSU pass.
- Rust has no diff.

## Verification

Implemented on 2026-07-28 without a commit or live solver run.

- Independent architecture, workstation, qualification, session, sweep,
  manifest, and evidence review: 77 passed in 19.1 seconds.
- Three candidates over two lanes opened two sessions, reused them across the
  second wave, and closed each once.
- Geometric x/y bases retain independent work identities, permits, receipts,
  artifacts, and missing-basis replay.
- Pyright: zero errors.
- CSU on touched files: zero hard violations.
- Rust diff: empty.

The workstation-contained native session path remains marked for the live
delivery in ticket 07.
