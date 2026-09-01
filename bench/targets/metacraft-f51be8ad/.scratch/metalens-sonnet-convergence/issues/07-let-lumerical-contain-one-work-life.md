# 07 — Let Lumerical contain one work life

Type: implementation

Status: resolved (2026-07-28)

Blocked by: ticket 05A.

## Outcome

The Lumerical Adapter owns one complete product work life behind a narrow,
truthful caller Interface.

## What to build

- Rename and deepen the product probe as `InstallationProbe`.
- Make its Interface explicitly own installation/version inspection,
  license observation, solver-native material sampling, and capacity refresh
  used by production dispatch. Keep deterministic qualification over those
  observations in the existing qualification Module.
- Delete the dormant `DirectEngine` and its implementation-specific tests.
- Make `WorkstationExecution` the sole production execution path.
- Hide session creation behind `SessionPool`; let it return `SessionLease`
  values and accept only one private `open_session` operation for internal
  tests.
- Remove public `SessionFactory`, caller-supplied execution/session pairs,
  and every exported fake.
- Keep `work_identity`, `session_identity`, and `lane_identity` independent.
  Reopening a session on one lane must create a new session identity.
- Introduce `WorkRecord` as the owner of construction, execution,
  observation, log, native-project, placement, capacity, and session facts.
- Deepen `RunDirectory` with domain operations for that standard artifact
  set. Sweep code must not handwrite file names or rebuild manifests.
- Keep one hidden Lumerical session per admitted lane and retain already
  admitted basis/candidate work after a lane failure.
- Preserve separate `lumerical_gui` and `lumerical_solve` limits and admit the
  tightest of those limits and workstation lanes.
- Keep automatic four-core, no-SMT, locality-aware, 16 GiB placement. Callers
  provide no worker count.
- Shrink `lumerical_fdtd.__all__` to the actual caller Interface.

Preserve the physical order:

```text
work identifies
→ permit admits
→ lane places
→ session opens
→ execution solves
→ observation records
→ receipt closes
```

For a new lease, `WorkstationExecution` places the process tree before the
native session reports ready. Reuse never changes the lease's lane.

## TDD seam

Use the existing fake native product behind the Adapter's private seam:

1. observe installation, version, both license pools, material samples, and
   capacity;
2. dispatch multiple candidates over multiple lanes;
3. prove one session is reused per lane;
4. close and reopen one session on the same lane and distinguish identities;
5. recover one missing geometric basis without repeating admitted work;
6. restore one complete WorkRecord from its RunDirectory.

Keep the real Lumerical smoke collected but disabled.

## Acceptance

- The public caller supplies workspace/product configuration and receives
  dispatch; it cannot inject execution, sessions, lanes, or worker counts.
- `InstallationProbe` declares every operation dispatch performs.
- Product qualification consumes Probe observations; the Probe does not
  declare scientific capability by itself.
- `SessionPool` and its private opener are not public package exports.
- Each work, session, and lane identity records one meaning only.
- WorkRecord is the sole owner of the standard artifact manifest.
- Product-native names remain inside the Adapter/session/template seam.
- Existing templates, grating planes, mesh accuracy, offsets, and solve
  behavior are scientifically unchanged.
- Focused qualification, workstation, session, sweep, artifact, and
  architecture tests pass.
- Pyright reports zero errors; touched files have zero CSU hard violations.
- `git diff -- rust` is empty.

## Verification

- Focused lifecycle, runner, qualification, sweep, and architecture tests:
  59 passed in the primary-agent recheck.
- Complete non-live suite: 345 passed, 15 live tests deselected, zero
  skipped.
- Pyright: zero errors and zero warnings.
- CSU: 15 touched production files, zero hard violations.
- Specification review: passed.
- Standards review: passed.
- Rust source and physical Lumerical templates: unchanged.
- Real Lumerical smoke and delivery remain explicitly reserved for ticket 10.

## Do not add

Do not add GUI concepts, a common solver base class, generic license
framework, CST/COMSOL code, public test seams, or caller-controlled parallel
policy.
