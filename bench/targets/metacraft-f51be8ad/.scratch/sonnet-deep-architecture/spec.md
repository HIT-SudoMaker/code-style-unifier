# Sonnet deep architecture

Status: resolved (2026-08-05)

## Context

MetaCraft already separates Rust authority from Python science and has proved
the present metalens routes. The Rust core owns workspace truth through one
`Authority` class and the four verbs `check`, `view`, `fetch`, and `decide`.
Python owns briefs, consultation, compilation, scientific execution, evidence,
and conclusions.

The next phase is not another feature layer. It is a deliberate Python
cutover before the four external metalens benchmark cases are exercised.
The owner accepts breaking Python interfaces and a fresh application root.
Records written by the replaced Python architecture are unsupported. Rust
source, protocol values, persisted authority meaning, and the four-verb
interface remain frozen.

[ADR 0018](../../docs/adr/0018-let-one-sonnet-baseline-tell-one-truth.md)
is the accepted system-wide decision for this convergence. This specification
is its current implementation contract; it does not override the ADR.

[ADR 0019](../../docs/adr/0019-form-uniform-fields-from-rectilinear-reference-surfaces.md)
is the accepted rectilinear-sampling amendment. Tickets 08.6 and 08.7 are
resolved: the qualified formation and minimal execution-persistence seams now
implement that contract. Ticket 09 is also resolved by its approved fresh
five-solve Native gate and tracked receipt. Ticket 10 has completed the
deterministic architecture seal recorded in
[CLOSURE-REPORT.md](CLOSURE-REPORT.md).

This specification follows the public scientific cadence:

`brief -> study -> result`

and the architectural cadence:

`name -> state -> case -> authority -> consultation -> response ->
lifecycle -> field -> convergence -> rectilinear formation -> forensics ->
native proof -> seal`

## Problem

The installed distribution is named `metacraft`, while the source namespace
uses a different name. Public science is split between `compile_study`,
`conduct`, `local.py`, and a private application package. Callers can see
available-fact carriers and must participate in lifecycle assembly.

Scientific state is projected several times. `Study` carries the compiled
proof, while result restoration and checkpoint restoration independently
decode parts of the same shape. Revision policy is also repeated across
conclusion admission, current-value admission, work permits, and receipts.

Consultation has the right two scientific questions, but its interface lives
inside the local application. Product work has several response-specific
entry points whose orchestration leaks into callers. The field package root
eagerly exports numerical realizations and imports Torch, so shared vocabulary
and expensive implementation are not separated.

Published paper facts still travel through production focal-comparison
meaning. This makes a scientific conclusion depend on an external source
comparison. The four benchmark cases therefore cannot test production from
the outside while keeping their expected comparison outside production.

Expected period and height outcomes also cross their owning functions as
`ValueError` text. Compiler and conduct then repeat the scientific rule by
matching prefixes or exact messages. The same state consequently has a value
owner and a separate classification owner.

Finally, `workspace` names both Authority-governed durable truth and the outer
directory that also contains product runs. Ticket 06 needs one Native
qualification fact, while Ticket 09 owns the exact five-solve gate that can
provide it; making each ticket wait for the other creates a delivery cycle.

The result is capable but rhythmically uneven: state has several narrators,
work has several cursors, and tests often cross private implementation shapes.
The architecture is hard to delete in pieces because the pieces are shallow
and mutually aware.

## Principle

The cutover applies the following rules.

1. **One meaning, one owner.** `Study` owns complete scientific state.
   `AuthoritySession` owns one observed revision. `WorkExecution` owns one
   permit-to-receipt life. `Result` owns one scientific conclusion. A
   `MetalensBenchmarkCase` owns published truth.
2. **Small interface, deep implementation.** Callers learn three root
   operations, two consultation questions, and one aim-specific evidence
   opening method. Reobservation, admission, product work, and conclusion
   remain hidden.
3. **Dependencies flow inward once.** Composition depends on aim-owned
   science; aim-owned science depends on shared values; shared values never
   select a consumer. Product Adapters do not interpret metalens meaning.
4. **Immutable science, singular authority.** Python values are immutable.
   Rust is the only mutable workspace authority. Python owns no second
   lifecycle or mutable progress store.
5. **Expected absence is data; defects are faults.** Invalid wording,
   unsupported aims, waiting science, unavailable consultation, unavailable
   product work, and completed results use explicit values. Corruption,
   malformed protocol, impossible transitions, and implementation drift
   raise.
6. **Replace, do not layer.** Interface tests replace tests of private
   carriers. No forwarding package, compatibility decoder, migration,
   alternate lifecycle, generic registry, or speculative solver framework is
   introduced.
7. **Names reveal intent.** Files and modules use concise snake-case domain
   nouns; types use precise PascalCase nouns; functions and methods use clear
   snake-case verb phrases; Boolean values begin with `is`, `has`, `can`, or
   `should`. Broad ownership names and duplicated context are removed.
8. **One decision chain closes one concern.** Research or an explicit
   not-applicable reason leads to an ADR, current specification, one ticket,
   Interface verification, and a checkpoint. Maps index this chain; they do
   not own status or architectural truth.

## Architecture

### Public interface

The installed root exports exactly:

```python
Authority
compile_study
conduct
```

The root stays cheap to import. Requesting `Authority` may load the native
extension lazily. Importing the root or `metacraft.field` must not load Torch
or Lumerical.

Compilation is pure:

```python
compile_study(brief) -> CompileOutcome
```

It performs no filesystem access, authority mutation, consultation, solver
work, or numerical execution. A valid supported brief yields a `Study`.
Malformed or unknown vocabulary yields `InvalidBrief`. A known aim without an
implemented scientific module yields `UnsupportedAim`.

The current compile union is exactly `Study | InvalidBrief |
UnsupportedAim`. `InvalidBrief` covers only explicit input validation:
wrong Brief type, malformed or duplicated common facts, unknown aim
vocabulary, aim/brief mismatch, missing metalens facts, `MissingBriefFacts`,
and malformed metalens fact values. Aim-owned validation occurs before
relationship and Study formation. A downstream `TypeError` or `ValueError`
from the compiler propagates unchanged; `compile_study` does not catch those
base exception types around `compile_metalens`.

`CONTEXT.md` retains **method unavailable** as future domain language required
by ADR 0010, but the current closed metalens strategies all select an
implemented relationship. The speculative `MethodUnavailable` implementation
is deleted and is not part of the current compile union. A future real valid
input with no applicable method must add that typed outcome deliberately.

Conduct is brief-first and create-only:

```python
conduct(
    brief,
    *,
    application_root,
    consultation,
    evidence_adapter,
) -> ConductOutcome
```

It compiles before storage access. A valid brief claims the application root,
then calls the aim-specific opening seam exactly once:

```python
MetalensEvidenceAdapter.open(
    *, authority: Authority, runs_directory: Path
) -> tuple[PeriodicResponse, MaterialResponse]
```

Both returned evidence ports validate their product context through that same
Authority, but their context references need not be identical. Conduct owns
advice, proof advancement, checkpointing, and conclusion. It returns
`WaitingStudies` or `CompletedResults`, and may return the same invalid or
unsupported compilation outcome. A caller does not handle an Authority,
revision, frontier, task execution Module, or result meaning.

The storage language is exact:

```text
application root/
    authority/    # the Authority workspace and durable truth
    runs/         # product artifacts
```

`workspace` retains its glossary meaning: one Authority-governed object store,
ledger, and set of projections. The private application composition claims one
absent application root, derives the fixed Authority workspace and run paths,
and raises `application_root_must_be_new` for an existing or partially claimed
root before opening evidence. An Adapter-opening fault propagates directly and
leaves the claimed root retained and non-reusable. There is no `Workspace`
wrapper, second storage lifecycle, existing-root continuation, or second-call
Result replay.

### Modules and dependency direction

```text
root composition
    -> science lifecycle
        -> metalens compiler and conclusion
            -> shared science and field vocabulary
        -> consultation seam
        -> metalens evidence-opening seam
            -> periodic-response and material-response seams
                -> Lumerical Adapter
        -> authority session
            -> frozen Rust Adapter and protocol values

examples/metalens_benchmark_cases.py
    -> public root interface
```

Production never imports `examples`. Lumerical never imports a metalens
control strategy, benchmark comparison, or result meaning. Shared science never
imports an aim consumer. Shared field vocabulary never imports numerical
realizations.

### Scientific state

`Study` is the sole complete immutable scientific state. It carries the brief,
design, advice, proof, evidence, capabilities, bindings, ready tasks, and
findings needed to understand and resume one branch. It owns canonical
encoding and strict restoration. A private `StudyFrontier` owns one ordered
family of studies, validates monotonic successors, and owns checkpoint
encoding and restoration.

The strict current schema identifiers are
`metacraft.examples.metalens_benchmark_case`,
`metacraft.examples.metalens_benchmark_comparison`, and
`metacraft.science.metalens.focal_field_comparison`. No old-schema decoder or
compatibility alias exists.

The frontier has no public mutation interface. A checkpoint is a canonical
document admitted through Authority, not a mutable progress database. A fresh
application root is the supported start for this cutover.

### Authority and work

One private `AuthoritySession` owns:

- the Authority handle;
- the currently observed view and revision;
- structured document admission;
- current-value compare-and-swap;
- contention recovery through re-observation.

One `WorkExecution` uses that same session and owns:

`capacity -> permit -> observation -> receipt`

or:

`capacity -> permit -> close`

No Python workspace lock is introduced. Revision mismatch triggers one
re-observation and a bounded retry. Protocol rejection, corrupted references,
and impossible work transitions remain faults.

External material-binding and periodic-response absence is one typed
`UNAVAILABLE` Finding with one inline diagnostic reason. Conduct retries by
kind only. A scientific `REFUSAL` remains non-retryable regardless of reason
wording.

### Scientific choice

The owning metalens operations are:

```python
resolve_period_choice(...) -> PeriodChoice | Finding
derive_height_domain(...) -> HeightDomain | Finding
resolve_height_choice(...) -> HeightChoice | Finding
```

An explicitly constrained value that violates a physical requirement returns
a `REFUSAL` Finding. Missing, unavailable, invalid, outside-domain, or ruled-
out advice returns an `ADVICE` Finding. Stale identity or grounds, malformed
documents, wrong runtime types, and impossible ordering raise directly.

`diagnose_period_advice` and `choose_constrained_height` are deleted. The
compiler handles only missing advice and typed `AdviceStatus`; conduct admits
the returned value and never parses exception text.

### Consultation

`MetalensConsultation` answers exactly two questions:

```python
recommend_period(...)
recommend_height(...)
```

The production adviser Adapter and a recorded Adapter satisfy the same
interface. Period and height advice remain untrusted immutable inputs. The
interface owns no result comparison, product selection, authority mutation, or
end-to-end workflow.

Missing configuration and an explicit transport timeout are unavailable
advice. Received invalid JSON or a scientifically invalid payload is invalid
advice. A malformed provider envelope, parser defect, unexpected exception,
or contract mismatch raises directly. The Adapter contains no broad
unavailable conversion or error-prefix parser.

### Periodic response

`PeriodicResponse` has one method and sealed route-neutral requests. The
supported request values cover transmission and polarization; either response
may carry a rectilinear reference surface observed from that same solve.
Transmission, polarization, and `periodic_reference_surface_response` keep
independent qualification and capability meanings.

The Lumerical Adapter and a recorded Adapter satisfy this interface. Science
constructs requests and interprets responses. The Adapter owns candidates,
lanes, sessions, permits, native projects, artifacts, observations, receipts,
and recovery. It chooses no metalens route or fabrication conclusion.

`periodic_cell_evidence.py` owns `PropagationEvidenceBatch` and
`JonesEvidenceBatch`. ADR 0019 deletes the shallow independent
reference-surface request path: `PeriodicReferenceSurfaceRequest`,
`ReferenceSurfaceWork`, `ObservedPeriodicReferenceSurface`,
`AdmittedPeriodicReferenceSurface`, their codecs, and the second no-solve
observation call. The product execution Module is
`lumerical_fdtd/project_execution.py`; `ProjectExecution` and
`ExecutedProject` describe its two immutable results. `ProductProbe` observes
one configured product, and capacity artifacts live under `capacity/` rather
than the retired `dispatch/` path.

Each observation exposes intention-revealing immutable fields. Exact mapping
codecs remain private to the root Interface behind the owner-facing internal
Interface in `science.periodic_response`; callers do not import
underscore-prefixed codec implementation. The owner preserves work
identities, receipt bytes, and admitted scientific documents. Every success
and expected unavailability outcome also carries typed closure evidence for
qualification and observation work.

The typed observation vocabulary is closed: one cell value, one Decimal-pair
complex value, transmission fields, polarization fields, and rectilinear
reference-surface fields carrying their actual horizontal and vertical
coordinates. Construction completion, solver completion, execution and
placement documents remain validated private-codec invariants rather than
Mapping or Boolean carriers a caller must interpret. A private admission
wrapper is the only periodic value that satisfies `WorkExecution`'s mapping
requirement.

Raw reference-surface axes must be finite and strictly increasing; they need
not be uniform, square, or equal in count. The session and Adapter preserve
that raw observation and contain no uniform-spacing gate, interpolation, or
fallback. One specialized Field Module owns qualified batch formation from
one or more rectilinear surfaces onto one common uniform grid and returns the
existing `Field` values all-or-nothing. Its Python numerical qualification is
separate from product qualification. Ticket 08.6 freezes
`periodic_rectilinear_bilinear_v1`: a common 24 by 24 half-open grid, periodic
bilinear interpolation, a maximum batch of 256, no extrapolation or
normalization, and diagnostic limits of `0.0081`, `0.0093`, and `0.0006`. The
six root Field exports and the existing `Field` and `PlaneSurface` contracts
remain frozen.

The superseded 64 by 64 candidate crossed the qualified 1 GiB high-NA vector-
field guard. The final 24 by 24 target has a 16.67 nm step at 400 nm period,
comparable to the retained Native maximum step of 15 nm, and passed all five
delivery tests across the four cases.

Ticket 08.7 persists the existing `ProjectExecution` before observation. A
later observation fault propagates unchanged; no failure record, sidecar, or
exception classifier is added. An execution-only artifact is never a
`WorkRecord`, receipt, admitted evidence, recovery authority, or lifecycle
state.

Closure is exact and route-neutral. One shared `ExternalActivityClosure` in
`metacraft.external_activity` serves the two real native callers: periodic
response and solver-native material verification. It carries a `none`,
`native`, or `recorded` origin and four count pairs: acquired/settled Authority work,
started/settled external execution, opened/closed product session, and
opened/closed local placement. All counts are non-negative exact integers and
every pair must be equal before the value can be constructed; `none` and
recorded activity have eight zero counts.
`PeriodicResponseClosure` binds one request identity to qualification and
observation closures. `PeriodicResponseContext` exposes the qualification
closure after successful Adapter construction, including when capability is
incomplete, and every observe outcome carries the same qualification value
plus current-call observation activity.

The evidence exposes no product object, session identity, worker, PID, handle,
lane, path, command, or platform inspection policy. Callers never derive
closure from artifact directories or operating-system process inspection.

A closure value is constructible only after its owner has settled every
acquired resource. Cleanup failure is a direct fault, including when the
primary observation also fails; concurrent primary and cleanup failures are
retained together as a grouped direct fault. Configuration or installation
absence before Adapter construction remains a direct typed
`LumericalUnavailable` composition exception after internal cleanup and does
not fabricate a periodic outcome. Closure evidence
is operational verification; it is not scientific evidence, Authority state,
Result meaning, or part of a periodic observation document.

### Field realization locality

The `metacraft.field` root continues to expose exactly the six shared field
values. Scalar and vector numerical realizations share one private owner for
CUDA, Windows, and POSIX device-memory observation. Each realization retains
its own memory-budget and numerical applicability policy. No resource value,
realization selector, registry, or compatibility export is added to the field
root.

That owner is `field/_device_memory.py` with exactly the private immutable
`AvailableDeviceMemory(device, available_bytes)` value and the
`observe_available_device_memory(device)` operation. It observes one already
selected device. Device selection, CUDA ordinal validation, scalar reserve,
vector reserve, batching, applicability, and fallback policy remain with the
two callers. A selected CUDA failure never falls back to CPU.

### Result and benchmark cases

Production `Result` contains only:

- the scientific conclusion;
- exact fabrication output;
- evaluation and evidence references;
- admitted closure;
- execution origin;
- replay provenance.

It contains no benchmark-case identity, paper metric, published platform,
advice comparison, or recommendation-versus-paper verdict.

Production `FocalFieldComparison` owns observed-versus-ideal field evidence
only. `SourceComparison`, `published_value`, and `source_comparisons` are
deleted from production without a compatibility reader.

The four external values become `MetalensBenchmarkCase` instances in
`examples/metalens_benchmark_cases.py`. A case owns its blind brief,
`PublishedPlatform`, `PublishedComparison`, fidelity, and comparison rules.
It calls only the installed root interface and is absent from the built wheel.

```python
case.compare(completed_results) -> tuple[MetalensBenchmarkComparison, ...]
```

Each comparison directly owns case identity, Result reference, period advice,
height advice, published platform, published comparison, fidelity, and
fidelity notes. There is no advice-comparison wrapper, conducted-project
wrapper, names-only forwarding helper, or production benchmark meaning.

### Data flow

```text
MetalensBenchmarkCase
    -> brief
    -> compile_study
    -> Study
    -> conduct
        -> claim fresh application root
        -> open MetalensEvidenceAdapter exactly once
        -> ask MetalensConsultation when required
        -> request PeriodicResponse when required
        -> admit evidence through AuthoritySession
        -> recompile immutable Study
        -> checkpoint StudyFrontier
        -> conclude and admit Result
    -> WaitingStudies | CompletedResults
    -> external benchmark comparison
```

Solver-native material outcomes also carry one `ExternalActivityClosure`.
Lumerical material verification reports its direct product session as
opened/closed, zero native solves, zero Authority permit work, and zero local
placements. Local preflight absence uses `none` with eight zero counts;
portable or recorded material observation uses its matching zero-count
origin. This keeps Ticket 09's complete-process claim at the material
interface instead of reviving an operating-system process scanner.

### Error handling

| Situation | Contract |
| --- | --- |
| malformed or unknown brief vocabulary | `InvalidBrief` |
| known aim without implemented science | `UnsupportedAim` |
| current valid metalens control strategy | one implemented relationship; no speculative refusal |
| valid science lacking advice/evidence/capability | `WaitingStudies` |
| explicit period or height violates physical constraints | returned `REFUSAL` Finding |
| advice missing, unavailable, invalid, outside, or ruled out | returned `ADVICE` Finding |
| adviser configuration missing or explicit timeout | typed unavailable advice |
| received invalid JSON or scientific payload | typed invalid advice |
| malformed provider envelope or unexpected adviser defect | direct fault |
| expected product absence before Adapter construction | direct typed composition exception after cleanup |
| completed proof | `CompletedResults` |
| revision contention | private re-observation and bounded retry |
| stale identity, reference, or advice grounds | direct fault |
| malformed Rust mapping or broken reference | direct fault |
| impossible scientific successor | direct fault |
| unexpected Adapter defect | direct fault with chained cause |

No control flow parses exception text, and no broad catch converts unexpected
adviser defects into ordinary unavailability.

### Verification strategy

TDD is applied only at the agreed seams:

- root import and public exports;
- `Study` canonical round trip;
- external benchmark-case ownership;
- typed period and height choice outcomes;
- Authority session and complete work life;
- the two consultation questions;
- one periodic-response method through both Adapters;
- raw rectilinear reference-surface observation and qualified all-or-nothing
  batch formation through the exact Ticket 08.6 Interfaces;
- pre-observation persistence of the existing `ProjectExecution` without a
  false `WorkRecord`, receipt, diagnostic schema, or admitted result;
- `compile_study` and `conduct`;
- shared field import cost;
- shared private Field memory observation through both numerical realizations;
- a bounded native receipt canary.

Focused and affected tests run during each ticket. Pyright runs regularly.
Each implementation receives independent ADR/spec and standards reviews
before resolution. The complete non-live suite runs once in the seal ticket.
Rust verification observes the frozen source and contract; Rust is not
rewritten.

Tickets 06 and 07 have already removed the historical 153 blocking CSU
findings. Ticket 06's deterministic handoff passed 1,149 tests with 6
deselected, Pyright and blocking CSU at zero, architecture review, and an
empty Rust fixed-point diff. Ticket 08.5 repeats the complete deterministic
baseline after the error, naming, benchmark, documentation, and test cutovers.
Tickets 08.6 and 08.7 closed their deterministic seams with 1,223 non-live
tests passed, 6 deselected, 0 skipped, 105 architecture tests passed, and zero
Pyright or blocking CSU findings. Ticket 09 then passed its one approved fresh
five-solve Native gate; its strict redacted receipt independently validates.

The first 2026-08-05 installed-product gate rejected post-setup mutation of a
constructed grating child. A later fresh attempt completed all three
qualifications and then exposed the rectilinear boundary: the qualification
surface was a closed 43 by 43 uniform grid, while both candidate bases were
closed 36 by 33 strictly increasing but nonuniform grids. Tickets 08.6 and
08.7 own that deterministic repair. The final gate used a new application root
exactly once; every earlier failed root remains non-reusable evidence.

The live receipt test passed once in 140.09 seconds. Receipt SHA-256 is
`5bf6e2170b82f077cfd313ed28c4c9268f773a1e857a4b92a838fbdd68b05416`;
its strict schema records three qualification and two candidate solves, two
formed 24 by 24 surfaces, two admitted receipts, identical 38-entry Native and
recovery inventories, and zero recovery execution. Tickets 06 and 09 are
resolved. Ticket 10 verified the tracked receipt without reopening the Native
root and is resolved by the deterministic seal.

Ticket 10 used `40f2127` as the literal architecture fixed point, unique OS
temporary directories for wheel and isolated install, an executable
unexpected-skip audit with one frozen no-lane environmental exception,
explicit Rust manifest commands, and exact wheel inventory. Its
implementation checkpoint precedes closure-report writing; its closure
checkpoint follows the repeated gates. ADR 0018 is already accepted and the
seal verified rather than invented it. Implementation commit `eb6db2f` and
the immediately following history-recorded closure commit form the two frozen
checkpoints without self-referential report wording.

### Delivery tickets

1. [Let one Python name describe one system](issues/01-let-one-python-name-describe-one-system.md)
2. [Let Study carry complete science](issues/02-let-study-carry-complete-science.md)
3. [Let four validation projects own published truth](issues/03-let-four-validation-projects-own-published-truth.md)
4. [Let one Authority session own one work life](issues/04-let-one-authority-session-own-one-work-life.md)
5. [Let metalens consultation answer two questions](issues/05-let-metalens-consultation-answer-two-questions.md)
6. [Let periodic response hide product work](issues/06-let-periodic-response-hide-product-work.md)
7. [Let one brief compile, conduct, and conclude](issues/07-let-one-brief-compile-conduct-and-conclude.md)
8. [Let Field export only shared language](issues/08-let-field-export-only-shared-language.md)
8.5. [Let one Sonnet baseline tell one truth](issues/08.5-let-one-sonnet-baseline-tell-one-truth.md)
8.6. [Let rectilinear observation form one uniform batch](issues/08.6-let-rectilinear-observation-form-one-uniform-batch.md)
8.7. [Retain solve completion before observation failure](issues/08.7-retain-solve-completion-before-observation-failure.md)
9. [Prove one fresh application root through a native receipt](issues/09-prove-one-fresh-workspace-through-a-native-receipt.md)
10. [Seal the Sonnet](issues/10-seal-the-sonnet.md)
11. [Let one post-seal maintenance pass remove residue](issues/11-let-one-post-seal-maintenance-pass-remove-residue.md)

## Trade-off

The cutover spends compatibility to buy one language and one lifecycle.
Existing Python workspace records are intentionally unsupported, so there is
no decoder that would preserve the architecture being removed. The cost is a
fresh application root for the benchmark phase; the gain is that every retained
type states present meaning.

`MetalensConsultation` is aim-specific rather than prematurely generic.
`PeriodicResponse` is product-neutral only at the response seam, not a common
solver framework. These choices reduce speculative abstraction while keeping
the two real external dependencies replaceable by recorded Adapters.

Ticket 07 was deliberately large. Public compilation, conduct, frontier,
scientific result, external-case use, and deletion of the replaced
lifecycle are one atomic vertical cutover because splitting them would leave
two lifecycles or a temporary result-meaning carrier.

Ticket 08.5 is also atomic, but bounded. Its error contracts, naming cutover,
benchmark ownership, and documentation ratchets must land together because
any partial order would preserve two current vocabularies. It introduces no
new Module: the deletion test retains only Modules whose policy would otherwise
return to multiple callers.

Ticket 08.6 isolates the scientific transformation from raw rectilinear
observation to qualified uniform `Field` values; Ticket 08.7 moves persistence
of the existing `ProjectExecution` before observation. Keeping those cuts
separate prevents numerical policy from leaking into the Adapter and prevents
solve completion from acquiring scientific or lifecycle authority.

The native gate is deliberately small. It proves qualification, one geometric
candidate in x and y bases, admission, receipt, reopen, and resume. It does not
perform a complete parameter sweep, so it verifies architecture without
turning closure into an expensive experiment.

After the deterministic seal, the separate
[metalens benchmark proof](../metalens-benchmark-proof/spec.md) exercises the
sealed public cadence through recorded Adapters. Its four cases form the exact
two-by-two matrix of propagation phase and geometric phase at low and high
numerical aperture. The bounded proof expects three low-NA propagation
Results, three low-NA geometric Results, one pointwise high-NA propagation
Result, and one pointwise high-NA geometric Result. This continuation adds no
second lifecycle or benchmark runner. Complete Native execution of all four
cases still requires its own cost and scientific-value decision.

The same bounded five-solve gate supplies the missing evidence for Tickets 06
and 09. The qualification portion closes Ticket 06; the candidate, receipt,
inventory, and recovery portion closes Ticket 09. This is one evidence chain,
not two mutually blocking gates.

## Conclusion

The delivery stages are explicit:

```text
current deterministic handoff  -> Sonnet-shaped
Ticket 08.5 complete            -> Sonnet-ready
Tickets 08.6/08.7 complete      -> rectilinear-ready
Ticket 06/09 Native gate passes -> Sonnet-proven
Ticket 10 closes                -> Sonnet-sealed (current)
```

After the acceptance gates pass, “not Sonnet enough” alone cannot reopen the
architecture. A new change must identify one concrete ADR, Interface,
dependency, state, error, domain, test, or Native contradiction.

The target is not a wider framework. It is a shorter sentence:

**One name at the door; one Study in the middle. One Authority admits; one
Result answers. Cases compare from outside, and the architecture closes from
within.**
