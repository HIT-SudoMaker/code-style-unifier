# 06 — Let periodic response hide product work

Type: implementation

Status: resolved (2026-08-05)

Blocked by: ticket 04.

Native acceptance dependency:

- [Let rectilinear observation form one uniform batch](08.6-let-rectilinear-observation-form-one-uniform-batch.md)
- [Retain solve completion before observation failure](08.7-retain-solve-completion-before-observation-failure.md)
- [Prove one fresh application root through a Native receipt](09-prove-one-fresh-workspace-through-a-native-receipt.md)

ADR 0019 amends this ticket's reference-surface portion without reopening its
accepted deterministic handoff. `periodic_reference_surface_response` remains
an independent capability, but it proves only that transmission or
polarization observation can include a rectilinear surface from the same
solve. The former `PeriodicReferenceSurfaceRequest`, `ReferenceSurfaceWork`,
`ObservedPeriodicReferenceSurface`, `AdmittedPeriodicReferenceSurface`, and
second no-solve observation path are deleted by Ticket 08.6. Any contrary
historical wording below is superseded by ADR 0019 and Ticket 08.6.

## Outcome

One internal `PeriodicResponse` interface exposes one method:

```python
observe(request) -> PeriodicResponseOutcome
```

Its request family is sealed and route-neutral. The supported values cover
periodic transmission and periodic polarization; either observation may
include a same-solve rectilinear reference surface.
`LumericalPeriodicResponse` and `RecordedPeriodicResponse` satisfy the same
interface.

Science constructs requests and interprets observations. The Lumerical
Adapter hides candidates, lanes, sessions, permits, native projects,
artifacts, observations, receipts, and recovery without choosing a metalens
route or fabrication conclusion.

## Problem

Qualification already proves the three physical capabilities independently,
but execution still exposes route-specific methods and imports metalens
meaning:

- dispatch accepts `Study`, `HeightChoice`, and `MaterialBinding`;
- sweep and template code import control strategy, aperture, propagation
  phase, geometric phase, and metalens design;
- evidence restoration plans metalens candidates and validates metalens
  tasks;
- product records form propagation cell libraries and interpret Jones
  libraries;
- callers choose among several gather methods and manually reconnect their
  admitted work.

The Adapter therefore observes physical response and interprets its metalens
use at the same seam.

## Scope

1. Add one shared periodic-response module containing:
   - `PeriodicResponse`;
   - a sealed `PeriodicResponseRequest` union;
   - exact route-neutral request values for transmission, polarization, and
     reference surface;
   - matching immutable observation and typed unavailability values.
2. Give `PeriodicResponse` exactly one `observe` method.
3. Make the sealed union exhaustive. An additional physical response requires
   an intentional edit to the union and every exhaustive match; external
   subclassing is unsupported.
4. Put only physical and execution facts in requests:
   - exact request and work identity;
   - wavelength and period;
   - typed cell geometry and height;
   - selected native material identities and admitted source references;
   - input and output bases;
   - order regime;
   - response-plane and sampling facts where applicable;
   - exact binding and capacity scope.
5. Keep `Study`, brief, design, control strategy, claim orchestration, phase
   set, orientation set, result meaning, and project comparison out of every
   request.
6. Add `LumericalPeriodicResponse`.
7. Let that Adapter construct route-neutral product candidates, invoke ticket
   04 `WorkExecution`, place lanes, open and close sessions, write artifacts,
   parse native output, admit receipts, and recover exact work.
8. Preserve independent qualification for:
   - `periodic_transmission_response`;
   - `periodic_polarization_response`;
   - `periodic_reference_surface_response`.
9. Reuse sampled reference surfaces from the same native solves. A
   reference-surface observation must not repeat an already admitted solve.
10. Add `RecordedPeriodicResponse`. Resolve only an exact request/work
    identity and binding, strictly decode its admitted observation, and
    perform no product discovery, qualification, capacity renewal, native
    session, or artifact write.
11. Move metalens candidate interpretation, library completeness, phase-set
    formation, polarization interpretation, and reference-surface scientific
    use to metalens-owned modules.
12. Remove all Lumerical imports of `science.metalens`, `Study`,
    `HeightChoice`, and control strategy.
13. Remove response-specific gather methods from dispatch. Do not retain
    aliases.
14. Keep material selection in the project material library and native
    material verification in the Lumerical Adapter. Do not turn material
    sampling into a generic solver interface.

### Observation interface

Replace each public `values: Mapping[str, object]` carrier with immutable,
intention-revealing fields. The shared module owns these exact value shapes;
they are internal science interface values, not installed-root exports:

```python
PeriodicCellObservation(
    cell_identity: str,
    height_nm: int,
    geometry: PeriodicCrossSection,
)

PeriodicComplexValue(
    real_part: Decimal,
    imaginary_part: Decimal,
)

PeriodicTransmissionObservation(
    cell: PeriodicCellObservation,
    transmission: PeriodicComplexValue,
    useful_power: Decimal,
    leakage_power: Decimal,
    realized_phase: Decimal,
    phase_planes: str,
    warnings: tuple[str, ...],
    reference_surface: PeriodicReferenceSurfaceObservation | None,
)

PeriodicPolarizationObservation(
    input_basis: str,
    cell: PeriodicCellObservation,
    output_x: PeriodicComplexValue,
    output_y: PeriodicComplexValue,
    phase_planes: str,
    warnings: tuple[str, ...],
    reference_surface: PeriodicReferenceSurfaceObservation | None,
)

PeriodicReferenceSurfaceObservation(
    requested_input_basis: str,
    output_basis: ComponentBasis,
    order_regime: str,
    surface: PlaneSurface,
    frame: CoordinateFrame,
    medium: Medium,
    electric_components: tuple[FieldComponent, ...],
    incident_reference_power: Decimal,
    transmitted_power: Decimal,
    wavelength_m: Decimal,
)
```

The existing closed basis and order-regime vocabularies remain unchanged.
Typed construction validates completion, finite values, complete bases,
canonical phase, power complement, and surface shape. Consequently
`construction_valid=True` and `solver_status="complete"` remain codec
invariants rather than Boolean fields callers must interpret.

One private codec in `science/periodic_response.py` is the sole owner of the
existing canonical observation documents. A private admission wrapper, not a
public observation value, satisfies `WorkExecution`'s mapping requirement.
The codec retains the existing candidate, execution, placement,
`construction_valid`, `solver_status`, power, phase, warning, and optional
same-solve surface keys byte for byte. Decoding validates the complete private
document and returns the typed value. No Lumerical or metalens caller keeps a
second mapping codec.

### Shared external-activity closure

Periodic qualification and solver-native material verification both open
product sessions, while only periodic work starts native solves and uses local
placements. One periodic-only closure would therefore leave the material
session invisible to Ticket 09. Add one shared invariant value in
`src/metacraft/external_activity.py`; it is justified by these two real
callers and introduces no solver interface or lifecycle operation.

Freeze the route-neutral values as:

```python
class ExternalActivityOrigin(str, Enum):
    NONE = "none"
    NATIVE = "native"
    RECORDED = "recorded"

ExternalActivityClosure(
    origin: ExternalActivityOrigin,
    acquired_authority_work_count: int,
    settled_authority_work_count: int,
    started_external_execution_count: int,
    settled_external_execution_count: int,
    opened_product_session_count: int,
    closed_product_session_count: int,
    opened_local_placement_count: int,
    closed_local_placement_count: int,
)

PeriodicResponseClosure(
    request_identity: str,
    qualification: ExternalActivityClosure,
    observation: ExternalActivityClosure,
)
```

Every count is a non-negative exact integer. Construction requires acquired
Authority work to equal settled Authority work, started external execution to
equal settled external execution, opened product session to equal closed
product session, and opened local placement to equal closed local placement.
An activity with `NONE` or `RECORDED` origin has eight zero counts. Counts
describe activity performed by the current call, so exact replay reports zero
rather than recounting previously admitted work. Do not add an `is_closed`
Boolean.

`PeriodicResponseContext` gains one `qualification_closure` field. It is
available after a successfully constructed Adapter even when a required
capability is absent and no observation request can be issued. Every observe
outcome gains one `closure`; its request identity equals the outcome identity
and its qualification value equals `context.qualification_closure`.

Qualification owns no Authority work. The Lumerical implementation forms its
qualification closure from the actual product sessions, native executions,
and local placements it opened and settled, including the discovery engine
and every independent qualification fixture. Fresh observation forms its
closure from `WorkExecution`, product session, native execution, and
Workstation placement facts. Recorded replay reports zero activity. No caller
derives these facts from artifacts, session pools, workers, PIDs, commands, or
platform inspection.

Configuration or installation absence before a `PeriodicResponse` Adapter is
successfully constructed remains a direct typed composition-time
`LumericalUnavailable` exception after internal cleanup. It does not fabricate
a request identity or periodic outcome. Once the Adapter exists, expected
capacity or native absence from `observe` is a `PeriodicResponseUnavailable`
carrying the same complete closure contract as a successful outcome. Keep
`observe` as the sole behavior method; do not add an opening outcome or a
second lifecycle method.

### Deterministic-seal ownership

Ticket 06 owns the 84 CSU blocking findings in these existing source paths:

- `science/periodic_response.py` (41);
- `science/metalens/periodic_response.py` (11);
- `work_execution.py` (9);
- `solvers/lumerical_fdtd/periodic_execution.py` (8);
- `science/metalens/periodic_request.py` (6);
- `science/metalens/propagation_execution.py` (3);
- `solvers/recorded_periodic_response.py` (2);
- `solvers/lumerical_fdtd/periodic_response.py` (1);
- `solvers/lumerical_fdtd/__init__.py` (1);
- `authority/session.py` (1);
- `science/metalens/geometric_execution.py` (1).

Resolve only the reported documentation, import ordering, layout, and
annotation findings while performing this ticket. Do not widen an interface
or move unrelated behavior merely to satisfy CSU. At handoff, none of these
paths may retain a blocking finding; the only remaining blockers must belong
to Ticket 07's declared paths.

Primary shared and metalens files:

- `src/metacraft/external_activity.py`;
- `src/metacraft/science/periodic_response.py`;
- aim-owned request construction and observation interpretation under
  `src/metacraft/science/metalens/`.

Primary Lumerical files:

- `src/metacraft/solvers/lumerical_fdtd/dispatch.py`;
- `src/metacraft/solvers/lumerical_fdtd/sweep.py`;
- `src/metacraft/solvers/lumerical_fdtd/evidence.py`;
- `src/metacraft/solvers/lumerical_fdtd/reference_surface.py`;
- `src/metacraft/solvers/lumerical_fdtd/template/periodic.py`;
- `src/metacraft/solvers/lumerical_fdtd/template/__init__.py`;
- `src/metacraft/solvers/lumerical_fdtd/qualification.py`;
- `src/metacraft/solvers/lumerical_fdtd/probe.py`;
- `src/metacraft/solvers/lumerical_fdtd/__init__.py`.

Primary focused tests:

- `tests/solvers/test_periodic_response_contract.py`;
- `tests/solvers/test_ticket04_periodic_response.py`;
- `tests/solvers/test_ticket06_reference_surface.py`;
- `tests/solvers/test_lumerical_native_dialect.py`;
- `tests/solvers/test_ticket07_work_life.py`.

Delete without aliases:

- `gather_periodic_transmission`;
- `gather_jones_library`;
- `gather_propagation_reference_surfaces`;
- `gather_geometric_reference_surfaces`;
- product-owned `PropagationLibraryRecord`;
- product-owned `JonesLibraryRecord`;
- Lumerical-owned metalens candidate planning and scientific library
  interpretation.

Replace strategy-bearing product names with route-neutral request,
observation, and work names. Do not preserve the replaced spellings through
forwarders.

## Typed error contract

Expected absence after successful Adapter construction is a
`PeriodicResponseUnavailable` value carrying one exact reason and one complete
closure. Independently unqualified capability, fresh capacity, and expected
native availability may produce that value. Configuration or installation
failure before construction remains the composition-time fault defined above.

Successful outcomes are exact matching values:

- observed periodic transmission;
- observed periodic polarization;
- observed periodic reference surface.

The following remain direct faults:

- request/outcome variant mismatch;
- malformed physical request;
- non-finite response;
- missing independent polarization basis;
- reference-surface construction mismatch;
- malformed native payload;
- duplicate or conflicting recorded observation;
- artifact or session lifecycle failure;
- AuthoritySession or WorkExecution invariant failure.

If a primary observation fault and one or more cleanup faults occur together,
raise one direct grouped fault retaining every original exception. Adding a
text note to the primary fault is insufficient evidence. A cleanup fault by
itself raises directly and no closure value is constructed.

`LumericalUnavailable`, `LumericalObservationFailed`, and work-capacity
details do not cross the `PeriodicResponse` interface. No caller parses an
exception string.

## TDD seam

Write one shared contract suite and run it against:

- `LumericalPeriodicResponse` using the same injected native session seam as
  production;
- `RecordedPeriodicResponse` using admitted recorded observations.

Cover:

- exact construction and validation of each sealed request;
- rejection of an unknown request type;
- transmission never satisfying polarization;
- polarization requiring two distinct finite input bases;
- reference surface retaining surface, frame, medium, basis, order regime,
  and exact source references;
- independent response qualification;
- typed product absence;
- malformed native payload remaining a direct fault;
- recorded response opening zero native sessions;
- exact request restoring byte-identical observation;
- same-solve reference-surface reuse;
- unchanged work identities and receipt bytes;
- exact typed observation fields with no public Mapping carrier;
- byte-identical private codec projection for all three observations;
- qualification closure through `PeriodicResponseContext` when capability is
  incomplete;
- qualification closure includes the direct discovery product session and
  every independently opened fixture session while counting only three native
  solves;
- closure equality through every success and expected-unavailability outcome;
- native, mixed recovery, exact recorded replay, and same-solve closure
  counts;
- primary failure plus cleanup failure retaining both direct faults;
- closure remaining absent from observation documents, work identities, and
  receipt bytes;
- a runtime import assertion that Lumerical imports no metalens module.

Tests cross `PeriodicResponse`, not dispatch or sweep private methods.

## Acceptance

- `PeriodicResponse` has exactly one method.
- Its request union is sealed, exhaustive, and route-neutral.
- Lumerical and recorded Adapters satisfy the same interface.
- Lumerical imports no metalens module, `Study`, `HeightChoice`, or control
  strategy.
- Each physical response retains independent qualification.
- Reference-surface recovery repeats no native solve.
- Public observation values expose typed fields and no Mapping carrier.
- The private codec preserves every existing canonical observation document,
  work identity, body reference, and receipt byte.
- Context and every outcome expose the exact closure interface and all four
  resource pairs are settled.
- Recorded replay reports zero current-call activity.
- Cleanup failure cannot produce closure evidence or be hidden behind a
  primary fault.
- Metalens owns scientific interpretation; Lumerical owns product execution.
- No response-specific dispatch gather method remains.
- No compatibility alias or parallel response lifecycle remains.
- Rust source and protocol fixtures are unchanged.

## Verification

Use the required project interpreter:

```powershell
$projectPython = 'C:\Users\Administrator\miniforge3\envs\research_env\python.exe'

& $projectPython -m pytest `
  tests/test_external_activity.py `
  tests/solvers/test_periodic_response_contract.py `
  tests/solvers/test_periodic_response_closure.py `
  tests/solvers/test_ticket04_periodic_response.py `
  tests/solvers/test_ticket06_reference_surface.py `
  tests/solvers/test_lumerical_native_dialect.py `
  tests/solvers/test_ticket07_work_life.py

& $projectPython -m pyright

rg -n "science\.metalens|ControlStrategy|HeightChoice|Study" `
  src/metacraft/solvers/lumerical_fdtd

rg -n "gather_periodic_transmission|gather_jones_library|gather_(propagation|geometric)_reference_surfaces" `
  src tests

.\csu\bin\csu.exe check src\metacraft --format json --output .csu\ticket06.json --no-history

git diff --exit-code 40f2127 -- rust
git diff --check
```

The first search must return no result. The second may mention replaced
spellings only in explicit absence assertions. The CSU report must contain no
blocking finding in the 11 owned paths above; every remaining blocking finding
must belong to Ticket 07's declared ownership.

## Stop and report

Stop before implementation if the design requires a generic solver
framework, dynamic request registration, a metalens import inside Lumerical,
repeated native work for a recorded request, changed work identity or receipt
bytes, public execution or placement mappings, a second lifecycle method, or
any Rust edit.

## Do not add

Do not add a solver registry, plugin mechanism, generic solver Protocol,
extensible request hierarchy, route name in a product request, product choice
inside science values, mutable solver status, background worker, compatibility
alias, record migration, or duplicate work runner.

## Comments

Resolved with one sealed, route-neutral `PeriodicResponse.observe(request)`
contract. Transmission, polarization, and reference-surface request families
now validate exact batch and variant invariants; observations strictly decode
and rebuild their canonical projections before any receipt can be restored.

Metalens owns candidate planning, fixed-grid completeness, propagation and
Jones interpretation, circular projection, and same-solve surface admission
through three purpose-named modules. The Lumerical Adapter owns qualified
product execution through `periodic_response.py` and
`periodic_execution.py`. Recorded replay is the symmetric outer Adapter in
`solvers/recorded_periodic_response.py`; the shared science contract no longer
depends on Authority sessions, permits, receipts, native sessions, or
artifacts.

The replaced dispatch and sweep files, route-specific gather methods, product
library records, forwarding names, and implementation-shaped tests were
deleted. Their behavioral coverage now crosses the shared contract, scientific
projection, work-life, native-dialect, reference-surface, and canonical-byte
seams. A bounded fake-native polarization test proves two linear-basis work
lives, two receipts, embedded same-solve surfaces, session closure, and replay
with no additional permit or native session.

Two method strings remain only as frozen canonical values in the Authority
work-identity preimage. They are not callable aliases; only the resulting
opaque work hash crosses the Rust permit seam. The run capacity artifact name
is likewise centralized as one canonical recovery value.

Independent verification passed 55 core contract/architecture tests, 161
ticket seam tests, and 158 affected non-live caller tests. Pyright reported
zero findings, the retired-seam searches were clean apart from the two
documented work-identity constants, Rust was unchanged, and independent review
closed with no P1 or P2 finding. Full and live suites remain reserved for their
accepted closure tickets.

### 2026-08-01 - Reopened for interface-owned closure

Ticket 09 proved that the shared interface cannot currently verify complete
Adapter-owned session and process-tree closure without duplicating
Workstation policy in the example caller. The owner accepted a bounded repair:

- replace public observation `Mapping[str, object]` carriers with
  intention-revealing immutable fields;
- retain strict private codecs and preserve work identities, receipt bytes,
  and admitted observation documents;
- add one typed `PeriodicResponseClosure` to every success and expected
  unavailability outcome;
- distinguish qualification work from the current observation work;
- expose only route-neutral counts for settled Authority work, external
  execution, and local placement;
- let closure-construction failure, malformed payload, corrupt receipt, and
  unexpected Adapter defects raise directly.

Keep `PeriodicResponse.observe(request)` as the only method. Preserve the
sealed requests, three independently qualified capabilities, Lumerical and
Recorded Adapters, and all existing scientific meanings. Do not expose a
session object or identity, worker, PID, handle, lane, path, process command,
or platform policy.
Tests cross the public interface on success, expected unavailability, replay,
and cleanup failure; private fake state is supporting evidence only.

### 2026-08-01 - Exact repair contract approved

The owner approved this ticket revision, not implementation. The observation,
closure, composition-failure, grouped-cleanup, CSU ownership, and verification
contracts above replace the underspecified reopening note. No production
change or native execution is authorized by this planning approval.

### 2026-08-01 - Interface-owned closure implemented

The owner subsequently authorized dependency-ordered implementation through
the accepted agent protocol. One writing agent completed the repair and two
independent read-only agents reviewed ADR/spec conformance and repository
standards. Review found and closed stale-retry undercounting, cleanup-group
misclassification, recorded-context activity drift, and an exception-attribute
side channel before both axes passed without a P1 or P2 finding.

`PeriodicResponse` now exposes typed observations and exact qualification and
observation closure while one private codec preserves canonical documents,
work identities, and receipt bytes. `WorkExecution.execute` returns one typed
completion or waiting value with owner-produced activity; its typed fault and
the periodic execution fault retain original failures without constructing
closure before cleanup settles. Recorded response context and outcomes report
recorded-zero activity, while Lumerical same-solve surface reuse retains the
native qualification closure.

Root verification passed 172 required focused tests, Pyright with zero
findings, Rust fixed-point and diff checks, and the forbidden dependency
searches. CSU reports zero blocking finding in every Ticket 06 owned or newly
changed path. Its 69 remaining blockers are exactly the paths assigned to
Ticket 07. Material activity propagation remains Ticket 07 work by its frozen
ownership contract. No Native execution or commit occurred in this ticket.

### 2026-08-01 - Native reference-surface evidence revision implemented

The approved Ticket 06 evidence repair now preserves the Lumerical Adapter's
exact response truth without widening the shared `PeriodicResponse`
interface. The internal `T` dataset is accepted only as one finite rank-five
closed periodic grid with uniform matching axes and matching terminal field
planes. Its duplicate terminal x and y samples are removed exactly once, with
no interpolation, so the observed 43-by-43 native grid becomes the physical
42-by-42 `PlaneSurface` whose sample count times spacing equals the 660 nm
period. Endpoint-span, terminal-plane, spacing, shape, context, and non-finite
defects remain direct faults.

Qualification now closes one ordered, redacted
`PeriodicResponseQualification` for each exact response kind. The sole
unqualified status is the explicit internal `response_not_returned` value;
`KeyError`, `TypeError`, `ValueError`, malformed payloads, non-finite values,
and construction mismatches survive as direct faults after the product
session closes. `PeriodicResponseProof` and `LumericalBinding` retain these
three results as their only truth, derive response capabilities, and persist
only response kind plus status. The binding decoder proves canonical JSON
round-trip, ordering, and per-response redaction.

TDD first failed because the old Adapter emitted all 43-by-43 samples and had
no typed per-response result. The focused repair then passed 51
qualification/reference-surface/closure tests and the Ticket 06 verification
set passed 179 tests. Architecture passed 99 tests; Pyright reported zero
findings; CSU reported zero blocking finding in `qualification.py`, `probe.py`,
and `session.py`; the Rust fixed-point diff against `40f2127` and
`git diff --check` were empty. No live or native execution ran, no commit was
created, and the ticket status remains resolved.

### 2026-08-01 - Review findings resolved

Review found that the first evidence revision still admitted two reverse
capability constructors, kept product absence behind a probe-only test value,
duplicated reference-surface construction parsing in the probe, and proved
binding persistence only by self round-trip. The corrected implementation
removes both `from_capabilities` constructors and migrates every production,
fake, and test caller—including the Ticket 09 naming test—to an explicit
complete ordered tuple of three `PeriodicResponseQualification` values.
Missing, duplicate, unknown, and out-of-order evidence is rejected; response
capabilities only derive from those results.

One private IPC-safe optional-result outcome now belongs to the Lumerical
session vocabulary. `LumericalSession` runs exact `haveresult` inventory
checks for group `S` and `T`, `S_polarization`, and internal `T` monitor `E`
and `T`; `_NativeSession`, the lane worker, the template-facing session
protocol, and `FakeSession` carry the same strict envelope. Only an inventory
absence yields `response_not_returned`. Present malformed results continue
through the existing strict `result` operation and remain direct faults after
qualification cleanup. Required production observations still use `result`.

`periodic_reference_surface_request` is now the one deep owner of normalized
surface parsing, period and transmission-plane validation, and request
construction. Its explicit `Medium` parameter records the intentional
qualification context (`transmission medium`) and production context (`air`);
the probe and periodic execution both call this owner. The probe retains no
shape-times-spacing or position parser. A fixed redacted binding fixture now
asserts exact canonical bytes containing all three ordered qualification
results, independently of decoder round-trip.

TDD captured three review-specific failures: the reverse constructors were
still present, `LumericalSession` lacked `optional_result`, and the shared
surface request could not accept its medium context. The resolved tree passes
79 focused qualification/reference-surface/closure/IPC tests, all 272 solver
tests with 4 deselected, all 99 architecture tests, and the corrected full
non-live gate with 1,110 passed and 6 deselected. Pyright reports zero
findings; CSU reports zero blocking finding across the complete Lumerical
directory; Rust remains identical to fixed point `40f2127`; and
`git diff --check` is clean. The map now distinguishes the historical stopped
Native attempt from this deterministic repair and states that Ticket 09
awaits its new live gate. No live or Native execution ran, no compatibility
path was added, no Rust file changed, and no commit was created. Ticket 06
remains resolved.

### 2026-08-01 - Authorized Native gate contradicts the resolved position contract

One authorized fresh Native gate ran after a green deterministic preflight and
contradicted Ticket 06's resolved reference-surface position contract. The
gate completed exactly three qualification `ExecutionRecord` documents and
three exact `before_p0.log` sidecars, then faulted directly with
`reference_surface_construction_mismatch`. Candidate work remained zero,
Authority had zero open permits, and no tracked receipt was written. The
failed workspace was retained and is not reusable. No raw log was read and no
process inspection occurred.

The high-confidence root cause is one missing product-coordinate seam. With
relative coordinates, the grating internal `T` dataset's local z coordinate
was emitted unchanged while `grating_planes` normalized its z coordinate to
world space. The existing fake hardcoded a world-space z value and therefore
could not expose the disagreement.

The proposed narrow repair is exact: one private Session-owned local-to-world
z conversion must be shared by `grating_planes` and reference-surface result
construction. Deterministic tests must cover both relative and absolute
coordinate modes plus the qualification regression. The repair must preserve
the source-faithful 43-to-42 closed-grid normalization, the 660 nm period, the
existing reference-surface validator, all shared interfaces, the product
template, and Rust. Owner approval is required before this ticket may move to
`ready-for-agent` or implementation.

### 2026-08-01 - Native diagnosis corrected and layout revision approved

The preceding local-to-world diagnosis is superseded. Direct read-back of the
retained failed project showed a declared world `T` plane of 800 nm, an
internal relative child position of 550 nm, `nearest mesh cell` sampling, and
a dataset world z coordinate of 804.347826086957 nm. A separate aligned native
probe returned the same relative child at exactly 800 nm in the dataset. The
dataset is already world-coordinate evidence; adding the group center would
double-convert it.

The exact product repair is Session-owned: run the grating setup, set the
internal `T` monitor spatial interpolation to `specified position`, read the
setting back, then read source, reflection, and transmission planes in world
coordinates. Dataset z remains unchanged and the existing strict reference-
surface validator remains authoritative. The red regression must prove that a
nearest-cell displacement such as 804.347826 nm is rejected while the exact
declared plane is accepted.

ADR 0017 accepts the owner-approved vertical template policy. One periodic
layout owns substrate, meta atom, solver, source, reflection, and transmission
placement. The substrate/meta-atom interface is `z = 0`; substrate height is
`max(2000, wavelength rounded outward to 100 nm)`; source depth is half that
height rounded outward to 100 nm; source and both reference clearances are
fixed at 100 nm; the solver upper edge is
`meta_atom_height + wavelength / 2` rounded outward to 100 nm. All formulas
use exact integer rational arithmetic.

Implementation is owner-approved in sub-agent mode. The template must replace
the public `GratingFrame` and four-way construction/build dispatch with one
route-neutral periodic construction seam, retain independent transmission and
polarization qualification, keep native group placement private, and add no
policy registry, coordinate compatibility path, or tolerance widening. No new
Native gate is authorized by this revision; deterministic implementation and
double review precede any separate gate decision.

### 2026-08-02 - Deterministic repair and Sonnet refactor complete

The approved implementation now has one route-neutral
`PeriodicConstruction` prepared from one `PeriodicWork`. Its private periodic
layout is the sole owner of substrate, interface, meta atom, solver, source,
reflection, and transmission placement. It uses exact integer rational
ceiling and proves the 400/500, 1550/800, and 2050/800 cases from ADR 0017.
Callers no longer choose propagation versus geometric construction and then a
second builder; `GratingFrame`, both specialized construction classes, both
builders, and every compatibility alias are absent.

The Session now owns one `prepare_grating_response` operation. It runs native
group setup, sets `grating_response::T` to `specified position`, strictly
reads the setting back, and returns one frozen three-plane world-coordinate
value. That value crosses worker IPC through exact-key, exact-integer encoding
and rejects coercion, missing keys, and additional keys. Dataset z remains
unchanged world-coordinate evidence. The validator still rejects a nearest-
mesh displacement and no group-center addition or tolerance widening exists.

MetaCraft uses `meta_atom_*` throughout its template and Session Interface;
Lumerical's `metamaterial center/span` spelling exists only inside the native
dialect. Odd integer atom heights retain their exact half-nanometre native
center. Only SI round-trip noise within `1e-9 nm` is normalized to that half-
nanometre grid; a real 400.6 nm read-back remains visible and produces a
construction translation mismatch.

TDD first produced the expected missing-interface, forged-layout, odd-height,
IPC, and off-grid read-back failures. The final root gate passed 1,149 tests
with 6 environment-selected tests deselected. Pyright reported zero errors and
warnings. The complete Lumerical directory produced 852 CSU under-review
findings and zero blocking findings. `git diff --check` was clean and the Rust
diff was empty. Independent specification and standards/Sonnet reviewers both
closed with no P0, P1, or P2 finding.

No Native gate ran. Ticket 06 therefore moves to `ready-for-human`, not
`resolved`. One fresh, never-reused workspace must still prove that this
installed Lumerical version preserves `runsetup -> setnamed -> save -> run`,
returns the qualification reference-surface dataset on its declared plane,
accepts the exact half-nanometre center, and remains numerically stable
with the expanded substrate/PML coverage. The consumed Ticket 09 workspace is
evidence only and cannot be reused.

### 2026-08-05 - Constructed-child failure and approved deterministic repair

The next authorized Ticket 09 gate stopped during qualification before any
candidate or receipt closure. Both periodic-output and polarization fixture
construction reached `prepare_grating_response` and the installed product
rejected post-setup child mutation with `constructed objects not allowed for
setnamed operation`. The failed application root is retained and cannot be
reused; no Native retry is authorized.

The owner approved one bounded Session-owned repair. `specified position` is
written into a fixed marked block in the parent grating group's existing setup
script before `runsetup`; vendor script content is preserved, an exact block
is idempotent, and partial, repeated, or conflicting markers fail directly.
Constructed children are read only. After `before.fsp` is saved, every owned
grating response is read back again before `run`; a mismatch stops without
analysis-mode recovery. This approval changes no physical layout, world-z
meaning, public Interface, Rust source, failed root, or retry authority.

The deterministic repair is complete and its handoff is accepted. The final
non-live suite passed 1,212 tests with 6 environment-selected tests
deselected; the focused solver suite passed 117 tests; and the architecture
suite passed 105 tests. Pyright reported zero errors, warnings, and notes. CSU
reported zero blocking findings, and the delivery matrix passed its one
case. Independent specification and standards/Sonnet final reviews both
closed with zero findings.

At that checkpoint Ticket 06 remained `ready-for-human`, not Native-resolved.
Native closure depended on Ticket 09 receiving separate authorization and
qualifying this accepted deterministic handoff at a new, absent application
root.

### 2026-08-05 - Native acceptance resolved

Ticket 09's one fresh five-solve Native gate passed. Its three qualification
projects proved transmission plus embedded reference surface, x-linear
polarization, and y-linear polarization against the installed product. The
two candidate solves then completed the admitted x/y evidence and receipt
chain without reusing a failed root.

`tests/live/test_native_receipt.py` passed once in 140.09 seconds. The redacted
receipt has SHA-256
`5bf6e2170b82f077cfd313ed28c4c9268f773a1e857a4b92a838fbdd68b05416`
and independently validates as exactly five solves. Ticket 06's remaining
Native acceptance is therefore closed; the application root remains closed.
