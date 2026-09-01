# 09 - Prove one fresh application root through a Native receipt

Type: implementation

Status: resolved (2026-08-05)

Execution state: fresh Native gate complete; tracked receipt independently
validated.

Blocked by: none.

Preconditions before Native execution:

- [Let one Sonnet baseline tell one truth](08.5-let-one-sonnet-baseline-tell-one-truth.md)
  is resolved.
- [Let Field export only shared language](08-let-field-export-only-shared-language.md)
  is resolved.
- [Let periodic response hide product work](06-let-periodic-response-hide-product-work.md)
  is resolved; this ticket's three successful qualification solves supplied
  its final Native acceptance evidence.
- [Let rectilinear observation form one uniform batch](08.6-let-rectilinear-observation-form-one-uniform-batch.md)
  is resolved with the frozen N=24 formation contract.
- [Retain solve completion before observation failure](08.7-retain-solve-completion-before-observation-failure.md)
  is resolved with execution persisted before observation.

Deterministic readiness is complete: the non-live suite passed 1,223 tests
with 6 deselected and 0 skipped, the architecture suite passed 105 tests,
Pyright reported 0 findings, and CSU reported 0 blocking findings. Ticket 09
is ready for its separately approved fresh five-solve Native gate; it is not
resolved until that gate and its postflight evidence pass.

The separately approved bounded Native gate completed once at fresh
application-root identifier `sonnet-ticket09-20260805-03`. No existing or
failed root was reused.

## Outcome

Run one explicit live canary in one fresh application root. Prove the installed
product, one complete Authority work life, exact artifacts, two geometric
basis observations, two Rust receipts, and read-only recovery at bounded
cost.

This is one shared evidence gate, not a dependency on Ticket 06's Native
resolution. Its three qualification solves close Ticket 06 only if the
installed product retains ADR 0017's exact layout and sampling behavior. Its
two candidate solves, receipts, inventory, and read-only recovery then close
this ticket. No second qualification run is permitted between those claims.

The canary performs exactly five native solves:

1. one propagation qualification solve, whose outputs independently qualify
   transmission and reference-surface response;
2. one x-linear qualification solve;
3. one y-linear qualification solve;
4. one x-linear solve for the selected geometric candidate;
5. one y-linear solve for the same candidate.

It does not execute a parameter sweep, form a complete library, conduct a
brief to Result, or claim validation of a published project.

## Scope

Prefer no production implementation change. If the interfaces completed by
Tickets 04 and 06 cannot express one bounded request and read-only recovery,
stop and reopen the owning ticket rather than widening production here.

Add an external canary harness, for example:

- `examples/native_receipt.py`;
- `tests/live/test_native_receipt.py`;
- a `lumerical_canary` pytest marker in `pyproject.toml`;
- a tracked, redacted canary record under
  `.scratch/sonnet-deep-architecture/`.

The harness must:

1. require `METACRAFT_RUN_LUMERICAL_CANARY=1`;
2. read `.env.lumerical` without displaying its values;
3. require an explicitly supplied application-root path that does not exist;
4. create all qualification and candidate artifacts beneath that root or
   its explicitly recorded run directory;
5. open the Lumerical Adapter through the final `PeriodicResponse` seam;
6. qualify transmission, polarization, and reference-surface response through
   the three native qualification solves;
7. preserve each same-solve reference surface with its finite, strictly
   increasing raw rectilinear axes; do not impose a uniform-spacing gate in
   the session or Adapter;
8. form every required reference surface as one qualified all-or-nothing batch
   on one common uniform grid through Ticket 08.6's Field-owned Interface;
9. use the registered 400 nm silicon-nitride and silica materials;
10. request one physically legal 600 nm-height rectangular candidate with
   100 nm short side and 220 nm long side;
11. gather x- and y-linear observations for that one candidate;
12. admit each observation through `WorkExecution` and retain its Rust receipt;
13. close every permit, session, lane, and product process on success or
    failure;
14. persist the existing `ProjectExecution` before observation; if observation
    fails, retain no diagnostic sidecar and create no `WorkRecord`, receipt,
    admitted result, recovery authority, or lifecycle transition;
15. reopen through the read-only recovery seam;
16. restore the same two work identities, observations, artifacts, and receipt
    references without another native solve;
17. write a redacted closure record.

The harness consumes only the final periodic-response and material interfaces:

- `response.context.qualification_closure` proves qualification activity even
  when one capability is absent and candidate observation cannot begin;
- `observed_materials.activity` proves the direct product session opened by
  solver-native material verification;
- the native observe outcome's `closure.observation` proves fresh candidate
  activity;
- the recorded observe outcome's `closure.observation` proves zero recovery
  activity;
- the Authority view independently proves that no permit remains open.

Delete process enumeration, PID extraction, `tasklist`, `subprocess` process
inspection, `os.kill`, and every `_product_process_ids`,
`_is_process_running`, or equivalent helper from the example. Delete the
hand-written `open_lane_count`, `open_session_count`, and
`open_process_count` record. Session and process-tree closure is accepted only
from Ticket 06's interface-owned paired counts.

The closure record retains the exact activity values rather than flattened
zero claims:

```text
qualification.activity = context.qualification_closure
materials.activity = observed_materials.activity
candidate.activity = native_outcome.closure.observation
recovery.activity = recorded_outcome.closure.observation
```

For a successful canary, qualification has three started and three settled
external executions and no Authority work. Candidate observation has two
acquired and settled Authority works and two started and settled external
executions. Each phase's opened and closed local-placement counts are equal to
the actual interface value; the ticket does not assume that session reuse
makes placement count equal solve count. Native material observation has one
opened and closed product session but zero external solves, Authority permit
work, and local placements. Recorded recovery has eight zero counts. Total
solve count is calculated as the sum of native started-execution counts across
qualification, materials, and candidate activity and must equal `3 + 0 + 2`;
it is not assigned as an independent literal. Every product-session pair
across those phases must also be equal.

The canary record may contain:

- relative application-root and artifact paths;
- product binding and capacity references;
- candidate dimensions and input bases;
- work identities;
- observation and receipt references;
- artifact hashes and sizes;
- the solve count;
- verification outcome.

It must not contain:

- an absolute user path;
- environment values;
- license-server text;
- credentials or tokens;
- raw product logs;
- machine-specific process command lines.

The record also contains an exhaustive application-root inventory. Walk every
file beneath the fresh application root after Native work and again after recovery. Record
each relative path, byte size, and SHA-256; reject absolute paths, `..`,
duplicates, symlinks escaping the application root, and any unclassified file. Every
file must belong to exactly one of the Authority store, the one qualification
run, the one candidate response, the two candidate work lives, or their exact
artifact manifests. Recovery must leave the inventory byte-identical.

Inventory classification must reject:

- a second qualification run directory;
- any qualification project outside the three declared purposes;
- any candidate directory other than the one fixed rectangular candidate;
- any candidate basis work other than exact x and y;
- any cell library, aperture, propagated field, focal region, focus, Result,
  benchmark comparison, or unclassified generated output.

The fixed canary candidate is an execution qualification input. It is not one
of the four `MetalensBenchmarkCase` values and must not be presented as
paper truth.

## TDD seam

Non-live tests may prepare the harness and recorded Adapter expectations, but
only the explicit live test can close this ticket.

The live test must assert:

1. the application root was absent before the run;
2. qualification produced all three periodic-response capabilities;
3. qualification used exactly three completed native projects;
4. exactly one candidate directory exists;
5. exactly two candidate work identities exist, one for each linear basis;
6. exactly two admitted observation references and two receipt references
   exist;
7. each execution origin is native;
8. each artifact manifest is complete and matches its files;
9. no permit remains open;
10. qualification and observation closure pairs are equal through the public
    interface, proving every session and product process tree is closed;
11. material verification reports one opened and closed product session and
    zero native solves through its public material outcome;
12. read-only recovery returns the same observation and receipt references;
13. recovery performs zero additional solves;
14. the exhaustive application-root inventory is unchanged by recovery and contains
    no extra qualification project, candidate work, or unclassified file;
15. no cell library, aperture, field propagation, focus, Scientific Result,
    or project comparison is produced;
16. the harness source contains no PID, process enumeration, `tasklist`,
    `os.kill`, or platform-process inspection.

Count solves from native started-execution activity and cross-check the same
3/0/2 total against completed qualification artifacts and candidate work
records. Neither source may contain an extra entry. Do not infer bounded
execution merely from elapsed time.

## Acceptance

- The explicit live gate passes against the configured local installation.
- The total native solve count is exactly five.
- Qualification proves three independent response capabilities.
- One candidate is observed in exactly two bases.
- Both observations are admitted and paired with Rust receipts.
- Reopen and recovery repeat no native work.
- All permits, sessions, lanes, and process trees close.
- Closure is proved only through periodic-response and material-outcome paired
  counts plus the public Authority view; the harness duplicates no Workstation
  or product-session policy.
- The application root contains complete, hashable artifacts.
- The tracked inventory is exhaustive, exclusive, and byte-identical after
  recovery; there is no extra qualification or candidate work.
- The tracked record is redacted and names the exact references and counts.
- The canary makes no published-project or scientific-result claim.
- Rust source and interface remain unchanged.
- The ordinary non-live suite remains independent of canary availability.

## Verification

Use only:

```text
C:\Users\Administrator\miniforge3\envs\research_env\python.exe
```

Required live availability:

- `.env.lumerical`;
- the configured executable and Python module;
- a valid GUI license and Solve license;
- at least one usable workstation lane;
- a writable run directory;
- registered silicon nitride and silica at 400 nm;
- `METACRAFT_RUN_LUMERICAL_CANARY=1`;
- an explicitly supplied absent application-root path.

OpenAI and Adviser availability are not required.

Run the non-live harness tests first:

```powershell
$projectPython = 'C:\Users\Administrator\miniforge3\envs\research_env\python.exe'

& $projectPython -m pytest -q --tb=short -p no:cacheprovider `
  -m "not integration and not advice_live and not lumerical_live and not lumerical_delivery and not lumerical_canary"

& $projectPython -m pytest -q -p no:cacheprovider `
  tests/examples/test_native_receipt.py `
  -m "not lumerical_canary"

& $projectPython -m pyright

.\csu\bin\csu.exe check src\metacraft --format json --output .csu\ticket09-preflight.json --no-history

& $projectPython -m pytest -q -p no:cacheprovider `
  tests/architecture/test_runtime_import_dag.py `
  tests/architecture/test_scientific_boundary.py `
  tests/architecture/test_sonnet_ratchets.py

git diff --exit-code 40f2127 -- rust
git diff --check
```

This deterministic preflight must pass before setting the live opt-in. Pyright
and CSU must report zero findings at their required severities, the runtime
graph and deletion ratchets must pass, and Rust must match the fixed point.
Do not spend the five native solves after a deterministic failure.

Then run the explicit live gate:

```powershell
$env:METACRAFT_RUN_LUMERICAL_CANARY = "1"
$env:METACRAFT_CANARY_APPLICATION_ROOT = "<absent-application-root-path>"
C:\Users\Administrator\miniforge3\envs\research_env\python.exe -m pytest -q -p no:cacheprovider `
  -m lumerical_canary `
  tests/live/test_native_receipt.py `
  -vv
```

After the run:

```powershell
C:\Users\Administrator\miniforge3\envs\research_env\python.exe -m pyright
git diff --check
git diff --exit-code 40f2127 -- rust
```

Record the five solves and every admitted identity in the tracked canary
record. Do not mark the ticket resolved on a skip.

## Stop and report

Stop and report if:

- any required live prerequisite is absent;
- the typed product outcome reports unavailable capacity or qualification;
- the application-root path already exists;
- opening one bounded request schedules more than the agreed five solves;
- a complete candidate library or complete brief execution begins;
- recovery would launch the product again;
- a permit, session, lane, or process remains open;
- any closure pair differs or closure must be inferred from PID/platform
  inspection;
- a receipt or artifact cannot be verified;
- application-root inventory contains an extra or unclassified path;
- a secret or absolute user path enters the tracked record;
- production must be widened to make the canary possible;
- Rust source or protocol would need to change.

An unavailable live environment leaves this ticket ready for explicit
execution. Do not substitute recorded or fake evidence for the native gate.

## Do not add

- a complete parameter sweep;
- a four-project delivery run;
- an Adviser call;
- aperture, propagation, focus, or Result work;
- published comparison or acceptance thresholds;
- a production canary mode;
- product-specific behavior in shared science;
- a second receipt path;
- automatic application-root deletion or reuse;
- environment or credential logging;
- a fake pass when live execution is skipped.
- a process scanner, PID probe, or second Workstation policy.

## Comments

### 2026-08-01 - Live gate stopped at qualification

- The first fresh-workspace attempt stopped before Authority admission or
  native work because the external harness pre-created the workspace leaf.
  The harness now follows the public Authority contract and passes the absent
  path directly to `Authority`; that attempt completed zero solves, opened no
  permit or product session, and its empty workspace was neither deleted nor
  reused.
- All live prerequisites were present. The second and final fresh-workspace
  attempt completed exactly three native qualification solves, but the
  admitted binding qualified only `periodic_transmission_response` and
  `periodic_polarization_response`. The required
  `periodic_reference_surface_response` capability was absent, so the gate
  stopped before candidate work as required.
- No candidate solve, candidate work identity, observation, receipt, recovery,
  or tracked `NATIVE-RECEIPT.json` record was produced. Read-only residue
  inspection found zero open permits, zero live qualification workers, zero
  product processes, and one fresh usable workstation lane.
- No environment value, licence-server text, credential, raw product log, or
  absolute workspace path was recorded here. The ticket remains
  `ready-for-agent` pending a fully qualified live environment.

### 2026-08-01 - Review found a missing closure seam

- Standards and specification review found that the external harness cannot
  repeatably prove session and complete process-tree closure after a failed
  bounded observation. Authority can prove that no permit remains open, but
  `PeriodicResponse` returns no typed Adapter lifecycle report and exposes
  neither its discarded session pool nor the workstation-owned worker.
- Direct `tasklist` or `os.kill` inspection in the example would duplicate the
  workstation's Windows process policy and is not an acceptable substitute.
  Reopen Ticket 06 to expose Adapter-owned typed closure evidence before this
  live gate is attempted again; Ticket 04 already supplies permit closure.
- Review also found that the harness must reject extra completed qualification
  projects or candidate work records and audit the workspace itself for
  forbidden scientific outputs. Those external-harness fixes are separable,
  but they do not remove the missing lifecycle seam or close this ticket.

### 2026-08-01 - Exact canary contract approved

The owner approved this ticket revision, not live execution. Ticket 09 remains
blocked by unresolved Tickets 06 through 08 and by availability of all three
qualified response capabilities. The repaired harness must consume paired
periodic and material activity, derive 3/0/2/0 solve activity, perform
exhaustive inventory, remove all process inspection, pass deterministic
preflight, and only then spend one fresh five-solve workspace.

### 2026-08-01 - Preflight passed; Native gate remains stopped

- Deterministic preflight passed 1,090 tests with 6 deselected; the receipt
  suite passed 30 tests, the architecture gates passed 38, Pyright reported
  zero findings, CSU reported zero blocking findings, and Rust plus diff
  checks were clean.
- One explicitly opted-in fresh Native gate stopped after exactly three
  qualification executions. Authority binding evidence contained
  transmission and polarization capabilities but not reference-surface;
  candidate work remained zero, Authority had zero open permits, and no
  tracked receipt was written. Three exact `before_p0.log` sidecars were
  observed, but their contents were not read.
- Post-live Pyright, Rust, and diff checks were clean. Independent reviews
  classified loss of fault-versus-absence evidence in Ticket 06 and the
  strict sidecar inventory mismatch in Ticket 09 as P1 findings, and discarded
  failure-path closure evidence as P2. Ticket 09 stays `ready-for-agent`,
  Ticket 10 remains blocked, and Ticket 06 remains resolved pending owner
  approval to revise or reopen it. No retry or commit is authorized.

### 2026-08-01 - Approved deterministic revision implemented

- Lumerical artifact ownership now derives the exact engine sidecar
  `before_p0.log` only from a constructed project named `before.fsp`. The
  external harness requires one such sidecar beside each of the three
  qualification solves and two candidate solves, records only its relative
  path, byte size, and SHA-256, and rejects absence, rename, `p1`, additional
  logs, and every other unclassified file. The durable `WorkRecord` manifest
  remains unchanged; qualification still cross-checks exactly three native
  `ExecutionRecord` documents.
- Before material verification or candidate construction, the canary strictly
  restores the ordered redacted `response_qualifications` from the admitted
  product binding, cross-checks the exact qualified subset against
  `PeriodicResponseContext.response_kinds`, materializes the paired
  qualification activity, and counts open permits through the public
  Authority view. Incomplete capability evidence raises the typed canary-local
  `NativeReceiptQualificationIncomplete` carrying only the three immutable
  redacted results, immutable qualification activity, and exact open-permit
  count. Its message is the code
  `native_receipt_capabilities_incomplete`; it retains no path, environment,
  licence, native payload, log, session, lane, or process identity and writes
  no receipt record.
- Non-live evidence proves an independently unqualified response stops with
  three started and three settled qualification executions, zero open permits,
  and no material or candidate call; missing, reordered, or context-conflicting
  evidence raises directly; a complete ordered result set reaches material
  observation. Workspace fixtures now require 12 qualification files and 10
  files in each candidate work directory.
- This revision authorizes no Native retry. Ticket 09 remains
  `ready-for-agent` until a new explicit five-solve workspace succeeds and the
  resulting redacted record passes every deterministic postflight gate.

### 2026-08-01 - Deterministic review repairs and conditional gate authority

- The fresh-run check/use split is removed. Ticket 07's application-owned
  private science composition operation atomically claims one absent root and
  creates generic Authority in its established `authority/` child. Existing,
  racing, and previously partial roots fail with
  `application_workspace_must_be_new` before repository prerequisites or
  product work. The public Authority interface remains exactly `check`,
  `view`, `fetch`, and `decide`.
- Ticket 07 was narrowly reopened and repaired while retaining resolved
  status. Ticket 09 consumes its shared application-workspace composition
  without inventing a canary-only Authority policy.
  Failed first attempts retain their exclusive root claim and can never be
  accepted or reused as fresh workspaces.
- The canary captures `WorkRecord.artifact_manifest()` once. Its durable
  qualification and candidate file sets, constructed-project name, and exact
  native sidecar now derive from that snapshot through
  `native_solve_sidecar`; repeated durable filename literals and redundant
  sidecar membership checks are gone.
- The owner's later “可以” authorizes exactly one new five-solve Native gate,
  but only after these two deterministic repairs pass double review and the
  root agent's complete deterministic preflight. At this deterministic
  checkpoint the gate had not yet run; its later failed execution is recorded
  below. No commit is authorized here, and Ticket 09 remains `ready-for-agent`.
- Writer verification passed 67 focused tests and 649 relevant non-live tests
  with 4 environment skips; Pyright reported zero findings, CSU reported zero
  blocking findings, and Rust plus diff checks were clean. Double review and
  root deterministic preflight remain pending and are not implied by these
  writer-local results.

### 2026-08-01 - One authorized gate consumed; Ticket 06 reopened

- Root deterministic preflight passed 1,126 non-live tests with 6 deselected;
  the ordinary receipt suite passed 41 tests and the architecture gate passed
  40. Pyright reported zero findings, CSU reported 4,437 findings with zero
  blocking, and the Rust fixed-point plus `git diff --check` were clean.
- Exactly one authorized fresh Native gate was then consumed. It completed
  three qualification execution records and three exact sidecars, faulted
  directly with `reference_surface_construction_mismatch`, and stopped with
  zero candidate work, zero open Authority permits, and no tracked receipt.
  The failed workspace remains retained and cannot be reused. No raw log was
  read and no process inspection occurred.
- Ticket 06 is now `needs-triage` and is Ticket 09's current blocker. No retry
  is authorized. Ticket 09 remains `ready-for-agent`, and Ticket 10 remains
  blocked by Ticket 09.

### 2026-08-01 - Failed gate diagnosis corrected

- The failed project's dataset z coordinate was already in world coordinates.
  The previously proposed 550 nm local plus 250 nm group-center conversion is
  rejected because it would double-convert the native result.
- The 804.347826 nm observation came from the internal `T` monitor's default
  `nearest mesh cell` sampling around its declared 800 nm plane. Ticket 06 now
  owns the approved `specified position` configuration/read-back repair and
  the single periodic vertical-layout revision in ADR 0017.
- Ticket 09 remains blocked by Ticket 06. The consumed workspace is retained
  evidence and is never reused. This correction authorizes no Native retry.

### 2026-08-02 - Ticket 06 deterministic repair accepted for Native review

- Ticket 06's code, strict IPC, naming, layout, sampling configuration, and
  deterministic evidence are complete. Its root gate passed 1,149 tests with
  6 deselected; Pyright and blocking CSU findings are zero; Rust is unchanged;
  both independent reviews have no open finding.
- Ticket 06 is `ready-for-human` because its exact `specified position`
  behavior has not yet been re-proved against the installed product. It is not
  resolved and remains this ticket's blocker.
- No retry is authorized by the deterministic repair. When separately
  approved, Ticket 09 must claim a new workspace and execute its original
  bounded five-solve gate; the failed workspace remains non-reusable evidence.

### 2026-08-04 - Planning removed the Ticket 06/09 dependency cycle

- Accepted ADR 0018 and Ticket 08.5 preserve `workspace` for Authority truth
  and name the outer directory `application root`.
- Ticket 09 no longer waits for Ticket 06 to be Native-resolved. It consumes
  Ticket 06's accepted deterministic handoff; its three qualification solves
  provide Ticket 06's missing installed-product evidence, and its remaining
  candidate, receipt, inventory, and recovery evidence close Ticket 09.
- Ticket 08.5 is the sole deterministic prerequisite for the next gate. This
  planning revision authorizes no implementation, Native retry, or commit.

### 2026-08-05 - Authorized gate stopped at the Ticket 06 product seam

- Deterministic preflight passed 1,203 non-live tests with 6 deselected; the
  receipt non-live suite passed 41, architecture passed 43, Pyright reported
  zero findings, CSU reported 4,440 findings with zero blocking, and Rust plus
  diff checks were clean.
- The one authorized gate claimed application-root evidence identifier
  `sonnet-ticket09-20260804-01` and stopped in
  both periodic-output and polarization qualification construction because
  the installed product rejected `setnamed` on the constructed internal `T`
  child. The tracked receipt is absent. The failed application root is
  retained evidence and is never reused.
- Ticket 09 stopped pending Ticket 06's deterministic setup-contract repair.
  That repair is now accepted, but it authorizes no Native retry; this
  ticket's future gate still requires separate approval and a new, absent
  application root.

### 2026-08-05 - Rectilinear prerequisites resolved

- Tickets 08.6 and 08.7 are resolved. Their formation and
  execution-before-observation seams passed focused verification.
- The complete non-live suite passed 1,223 tests with 6 deselected and 0
  skipped; architecture passed 105; Pyright and blocking CSU findings are
  both zero.
- At that deterministic checkpoint Ticket 09 had no blocker and was ready for
  separate approval of one fresh five-solve Native gate. No failed root could
  be reused. That readiness record did not itself resolve Ticket 09 or
  authorize a solve.

### 2026-08-05 - Fresh Native gate resolved

- `tests/live/test_native_receipt.py` passed once in 140.09 seconds against
  fresh application-root identifier `sonnet-ticket09-20260805-03`.
- `.scratch/sonnet-deep-architecture/NATIVE-RECEIPT.json` has SHA-256
  `5bf6e2170b82f077cfd313ed28c4c9268f773a1e857a4b92a838fbdd68b05416`.
- Independent non-live decoding accepted the strict
  `metacraft.native_receipt` schema and redaction contract. The record is
  canonical bytes plus one terminal newline, declares `verification` as
  `verified`, and contains exactly five solves: three qualification projects
  and two candidate basis executions.
- Qualification purposes are transmission plus reference surface, x-linear
  polarization, and y-linear polarization. Candidate executions are x-linear
  and y-linear, with two settled Authority work items and two Native
  executions.
- Formation is `periodic_rectilinear_bilinear_v1`, contains two formed
  surfaces on one 24 by 24 grid at 16.666666666666667 nm spacing, and retains
  each raw observation plus the formation qualification reference.
- Native and recovery inventories each contain 38 identical entries. Recovery
  origin is recorded and starts zero external executions.
- The strict non-live receipt suite passed 48 tests in 2.78 seconds without
  opening the Native application root.

Ticket 09 is resolved. The Native root remains closed and must not be reopened;
Ticket 10 consumes only the redacted receipt and its content hash.
