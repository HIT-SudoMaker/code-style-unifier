# 07 - Let one brief compile, conduct, and conclude

Type: implementation

Status: resolved (2026-08-01)

Blocked by:

- [Let Study carry complete science](02-let-study-carry-complete-science.md)
- [Let four validation projects own published truth](03-let-four-validation-projects-own-published-truth.md)
- [Let one Authority session own one work life](04-let-one-authority-session-own-one-work-life.md)
- [Let metalens consultation answer two questions](05-let-metalens-consultation-answer-two-questions.md)
- [Let periodic response hide product work](06-let-periodic-response-hide-product-work.md)

## Outcome

Replace the split Python lifecycle with one atomic, brief-first vertical
cutover.

`compile_study` remains pure and returns a `CompileOutcome`. `conduct` owns one
fresh workspace from recall through completion and returns a
`ConductOutcome`. `Study` is the sole complete scientific state. A private
`StudyFrontier` owns ordered branches, monotonic successor validation,
checkpoint admission, restoration, convergence, and sibling preservation.

Production `Result` contains scientific conclusion only. Validation-project
identity, published facts, comparison rules, fidelity, advice comparison, and
observed-versus-published values remain outside production in the
`MetalensValidationProject` values established by Ticket 03.

This ticket is deliberately atomic. It does not close until the replaced
lifecycle and production result-meaning language have been deleted.

## Scope

### Public interface

Make the installed root export exactly:

```python
Authority
compile_study
conduct
```

Preserve these contracts:

```python
compile_study(brief) -> CompileOutcome

conduct(
    brief,
    *,
    workspace,
    consultation,
    periodic_response,
    materials,
) -> ConductOutcome
```

`CompileOutcome` distinguishes:

- one supported compiled `Study`;
- `InvalidBrief` for malformed or unknown vocabulary;
- `UnsupportedAim` for a known aim without an implemented scientific module.

`ConductOutcome` distinguishes:

- `WaitingStudies`;
- `CompletedResults`;
- the same invalid or unsupported compilation outcomes.

The public compile outcome is exactly:

```python
CompileOutcome = Study | InvalidBrief | UnsupportedAim
```

`InvalidBrief` is limited to facts attributable to the supplied brief:

- the value is not a `Brief`;
- a common name, wording, aim, objective, omission, or budget is empty,
  malformed, or duplicated where uniqueness is required;
- the aim vocabulary is unknown;
- an aim-specific brief value contradicts its declared aim;
- a metalens aim lacks a `MetalensBrief` or `MissingBriefFacts` identifies
  absent metalens facts;
- an explicit metalens fact has an invalid wavelength, focal length,
  numerical aperture, control strategy, material or geometry constraint,
  aspect limit, dimension step, period, height, aperture intent, or incident
  polarization value.

Aim-owned validation must identify those reasons before relationship and
Study formation. `compile_study` may translate only that explicit validation
or `MissingBriefFacts` into `InvalidBrief`. It must not catch a general
`TypeError` or `ValueError` around `compile_metalens`; an unexpected exception
from relationship selection, proof formation, codec work, or an injected
compiler raises unchanged with its original cause.

The three canonical but unimplemented aims return `UnsupportedAim`. Unknown
aim vocabulary returns `InvalidBrief("aim_unknown")`; it is not silently
grouped with an unimplemented canonical aim.

ADR 0010 and `CONTEXT.md` retain **method unavailable** as domain language for
a future valid supported input that has no applicable method. No such input is
reachable in the current closed `ControlStrategy` and metalens relationship
set. Delete the current `MethodUnavailable` implementation and
`science/refusal.py`; use exhaustive matching for the two implemented control
strategies. Do not add `MethodUnavailable` to the current public union. If a
future real input makes the term reachable, its specification must add the
typed outcome deliberately rather than reviving this exception privately.

Expected consultation or product absence during `conduct` becomes an
immutable waiting finding. Malformed protocol, corrupted references,
impossible successors, unexpected compiler faults, and unexpected Adapter
faults during conduct raise directly.

### Material activity closure

Ticket 09's fresh canary performs solver-native material verification before
periodic candidate observation. That verification opens one direct Lumerical
product session outside the Workstation placement used by periodic response.
The material interface must therefore carry Ticket 06's shared
`ExternalActivityClosure`; periodic closure alone cannot prove the full
canary.

Add one `activity: ExternalActivityClosure` field to:

- `VerifiedMaterialBatch`;
- `ObservedMaterials`;
- every `MaterialUnavailable` value.

Registration absence carries `NONE` activity with eight zero counts;
recorded-observation absence carries `RECORDED` activity with eight zero
counts. `RecordedMaterialResponse` restores the exact admitted material
document but returns a new recorded-zero activity value; activity is not added
to the material document or its reference. A successful native sample and
expected native-material or wavelength refusal carry the exact native
activity that produced them.

Make the private `NativeMaterialProbe.sample_materials` result pair its
`LumericalMaterialSample | MaterialVerificationRefusal` value with one
`ExternalActivityClosure`. The production probe records one opened and one
closed product session, zero Authority permit work, zero native solves, and
zero local placements. Test probes return an explicit activity value rather
than relying on hidden counters. If opening fails before a session exists, the
typed Lumerical composition exception raises directly. If sampling and close
both fail, retain both as a grouped direct fault and construct no outcome.

`_ProjectMaterialResponse` passes the verifier activity unchanged into the
fresh `ObservedMaterials` or `MaterialUnavailable` outcome. It must not encode
activity into the canonical observation, index, work identity, or scientific
evidence. No caller inspects the probe, engine, PID, or operating system.

This bounded repair owns `materials/verification.py`,
`materials/response.py`, `solvers/lumerical_fdtd/material_response.py`, and
only the material-sampling path of `solvers/lumerical_fdtd/probe.py`. It does
not change product discovery or periodic qualification semantics completed by
Ticket 06.

### Scientific lifecycle

Rewrite the final owners under:

- `src/metacraft/science/compile.py`;
- `src/metacraft/science/conduct.py`;
- `src/metacraft/science/result.py`;
- `src/metacraft/science/__init__.py`;
- `src/metacraft/science/metalens/conduct.py`;
- `src/metacraft/science/metalens/checkpoint.py`;
- `src/metacraft/science/metalens/result.py`;
- `src/metacraft/science/metalens/__init__.py`.

Let the existing metalens modules continue to own their scientific operations:

- `period.py`;
- `height.py`;
- `material.py`;
- `propagation_phase.py`;
- `geometric_phase.py`;
- `aperture.py`;
- `focus.py`;
- `pointwise.py`.

Do not introduce an operation registry or another application object.
Metalens conduct may select an aim-owned operation through an explicit closed
match over compiled method values. The operation consumes a `Study` and
returns immutable successor studies or one typed waiting finding. Admission,
revision, checkpoint, and work state remain hidden in conduct,
`AuthoritySession`, and `WorkExecution`.

The private frontier must:

1. retain one ordered family of identity-distinct studies;
2. replace exactly one live study with its ordered successors;
3. preserve every sibling after each transition;
4. reject loss of brief, design, proof, advice, evidence, binding, capability,
   or finding meaning;
5. collapse converged studies without duplicating a conclusion;
6. admit the complete frontier after each accepted transition;
7. restore the complete frontier without consultation, product work, Torch,
   or repeated admission;
8. admit each completed scientific result exactly once.

Monotonic successor validation is implementation owned by
`StudyFrontier.replace`. The method either performs the validation directly or
uses an instance-private implementation detail unreachable outside the
frontier. Moving the old top-level function under another top-level name does
not satisfy this ticket. Tests cross `replace`; no caller or test imports a
successor validator.

The supported start is a fresh workspace. Define one strict checkpoint shape
and one strict result shape. Do not decode the replaced
`metacraft.local.available_science` document.

### Result and Project seam

Production `Result` contains only:

- the scientific conclusion;
- exact fabrication output;
- evaluation and evidence references;
- the admitted Study closure;
- execution origin;
- replay provenance;
- scientific cautions grounded by that closure.

Delete production ownership of:

- `ResultMeaning`;
- `PublishedMeasure`;
- `PublishedMetric`;
- `AdviceComparison`;
- `ComparedPlatform`;
- `ComparedDimension`;
- case identity and case name;
- fidelity and fidelity notes;
- paper revision and comparison measures;
- published metric values;
- recommendation-versus-paper comparison;
- the result document's `meaning` and paper `comparison` sections.

Update `examples/metalens_projects.py` so a
`MetalensValidationProject` consumes `CompletedResults` after conduct. It may
compare its published truth with a scientific result and may write a
project-owned validation artifact. That artifact is not a production Result,
does not influence conduct, and is not imported by production.

The actual advice used by a project comparison must come from the admitted
Study reached through the Result interface. A caller must not submit the same
advice a second time as result context.

### Delete the replaced lifecycle

Delete these files:

- `src/metacraft/local.py`;
- `src/metacraft/_local/__init__.py`;
- `src/metacraft/_local/application.py`;
- `src/metacraft/_local/replay.py`;
- `src/metacraft/_local/geometric.py`;
- `src/metacraft/_local/propagation.py`;
- `src/metacraft/_local/proof_tail.py`.
- `src/metacraft/science/refusal.py`.

Delete these interfaces and implementation carriers:

- `available_science`;
- `replay_science`;
- the local `open_lumerical` composition wrapper;
- `AvailableScience`;
- `LocalScience`;
- `_Application`;
- `_ConfiguredScience`;
- `AdvanceOutcome`;
- `_Frontier`;
- `_Admission`;
- `_configured`;
- `_replayed`;
- `_admit`;
- `_validate_successor`;
- `_OPERATIONS`;
- `_operation_for`;
- `_native_result_meaning`;
- `AimUnavailable`;
- `MethodUnavailable`;
- the raw `meaning=` conduct-composition input.

Call the Lumerical Adapter through the `PeriodicResponse` interface from
Ticket 06. Do not replace the deleted local wrapper with another forwarding
module.

### Replace implementation-shaped tests

Delete or rewrite tests that import or inspect the carriers above, including:

- `tests/test_local.py`;
- `tests/test_method_binding.py`;
- private-shape cases in `tests/science/test_conduct.py`;
- `tests/science/test_conduct_frontier.py`;
- `tests/science/test_branch_checkpoint.py`;
- private admission use in `tests/result_fixtures.py`;
- private admission use in `tests/science/test_period_height_domain.py`;
- callback-carrier cases in `tests/science/test_ticket04_typed_outcomes.py`;
- replaced lifecycle assertions in
  `tests/architecture/test_frontier_replay_architecture.py`;
- `tests/architecture/test_ticket10_local_composition.py`;
- `LocalScience` source assertions in
  `tests/architecture/test_sonnet_architecture.py`.

Retain the scientific behavior they protected through public interface tests
or narrow package-internal codec tests. Do not preserve a test solely because
it describes the deleted implementation.

The currently deleted `tests/science/test_future_studies.py` is not accepted
as lost coverage. Move its three canonical future-aim cases into
`tests/science/test_compile_outcomes.py` and assert `UnsupportedAim`. Move its
unknown-aim case into the same file and assert `InvalidBrief("aim_unknown")`.
Add malformed-metalens and `MissingBriefFacts` cases there. Inject one
downstream `TypeError` and one downstream `ValueError` from `compile_metalens`
and prove that both propagate unchanged.

### Deterministic-seal ownership

Ticket 07 owns the remaining 69 CSU blocking findings in these source paths:

- `materials/verification.py` (23);
- `science/metalens/evidence.py` (22);
- `materials/response.py` (6);
- `science/metalens/conduct.py` (4);
- `solvers/lumerical_fdtd/material_response.py` (4);
- `science/conduct.py` (3);
- `science/metalens/consultation.py` (3);
- `science/metalens/checkpoint.py` (2);
- `science/metalens/compiler.py` (2).

Resolve only the reported documentation, import ordering, layout, and
annotation findings while completing this ticket. Do not extract a broad
documentation or formatting module. Ticket 07 hands off only when a complete
CSU run reports zero blocking finding across `src/metacraft`.

## TDD seam

Write failing tests first at these seams:

1. Root import exposes exactly `Authority`, `compile_study`, and `conduct`.
2. Pure compilation performs no filesystem, Authority, consultation, product,
   or numerical work.
3. Unknown vocabulary is `InvalidBrief`; a declared unimplemented aim is
   `UnsupportedAim`; a supported brief yields one deterministic `Study`.
4. Every explicit invalid-brief category above returns its exact reason while
   injected downstream `TypeError` and `ValueError` propagate unchanged.
5. A fresh workspace may return `WaitingStudies`, then resume from its exact
   admitted frontier.
6. A recorded consultation Adapter and recorded periodic-response Adapter can
   complete the bounded 3 + 3 + 1 + 1 result family through public `conduct`.
7. Reopening a completed workspace returns the same admitted Result references
   without calling consultation, product work, or field realization.
8. Two branches that converge produce one conclusion; one waiting branch
   cannot erase completed siblings.
9. Concurrent conducts rely on Rust revision admission and bounded
   re-observation, not a Python workspace lock.
10. Result documents contain scientific meaning only.
11. An external validation project compares after conduct and production never
    imports `examples`.
12. `StudyFrontier.replace` rejects every non-monotonic successor while the
    retired top-level validator and its name are absent.
13. Native material success and expected refusal expose one paired product
    session; registration and recorded outcomes expose eight zero counts with
    `NONE` and `RECORDED` origins respectively.
14. Material activity changes no canonical material document or reference,
    and concurrent sampling plus cleanup faults retain both exceptions.

Tests and callers cross the same public seam. Package-internal tests may cover
the strict Study, frontier-checkpoint, and Result codecs. No test imports a
frontier mutator, revision cursor, admission helper, task-operation lookup, or
application carrier.

## Acceptance

- The installed root interface is exact and cheap to import.
- `compile_study` is pure and returns only the agreed typed outcomes.
- Invalid brief classification is exhaustive and limited to supplied input;
  downstream compiler defects propagate unchanged.
- `MethodUnavailable`, `AimUnavailable`, and `science/refusal.py` are absent
  from implementation and tests while the domain term remains in
  `CONTEXT.md`.
- `conduct` owns recall, consultation, advance, checkpoint, conclusion, and
  replay behind one interface.
- `Study` is the only complete scientific state.
- Every frontier transition is monotonic and preserves all siblings.
- Monotonic validation has locality inside `StudyFrontier.replace`; no
  top-level successor validator remains.
- Fresh and recorded material outcomes carry the shared activity interface;
  direct native product sessions are closed without PID inspection.
- Material activity is absent from admitted material documents and therefore
  changes no existing material identity or reference.
- Completed replay performs no consultation, solver launch, Torch work, or
  repeated admission.
- Scientific Result contains no external validation meaning.
- The four validation projects still own exact published truth and compare
  only after conduct.
- Every replaced file and symbol in the deletion list is absent.
- Production and tests contain no cross-module import of a private lifecycle
  name.
- Runtime imports remain acyclic and production contains no `examples`
  dependency.
- Rust source and the four Authority verbs are unchanged.
- Focused tests and Pyright pass with no error or warning.

## Verification

Use only:

```text
C:\Users\Administrator\miniforge3\envs\research_env\python.exe
```

Run the final focused seam set, using the test paths created by this ticket:

```powershell
C:\Users\Administrator\miniforge3\envs\research_env\python.exe -m pytest -q -p no:cacheprovider `
  tests/science/test_compile_outcomes.py `
  tests/science/test_conduct.py `
  tests/science/test_conduct_replay.py `
  tests/science/test_scientific_result.py `
  tests/materials/test_material_response.py `
  tests/solvers/test_material_response_contract.py `
  tests/solvers/test_material_activity_closure.py `
  tests/examples/test_metalens_validation.py `
  tests/architecture/test_scientific_boundary.py `
  tests/architecture/test_runtime_import_dag.py

C:\Users\Administrator\miniforge3\envs\research_env\python.exe -m pyright
```

Run deletion and dependency searches:

```powershell
rg -n "available_science|replay_science|LocalScience|_ConfiguredScience|_Application|ResultMeaning" src tests examples
rg -n "AimUnavailable|MethodUnavailable|_validate_successor" src tests SCIENCE.md
rg -n "from examples|import examples" src/metacraft
Test-Path src/metacraft/local.py
Test-Path src/metacraft/_local
Test-Path src/metacraft/science/refusal.py
.\csu\bin\csu.exe check src\metacraft --format json --output .csu\ticket07.json --no-history
git diff --check
git diff --exit-code 40f2127 -- rust
```

The first search may find historical prose only outside the implementation
scope. The retired-refusal search, production dependency search, and Rust diff
must be empty. All three `Test-Path` commands must return `False`. CSU must
report zero blocking finding.

No live Adviser or Lumerical availability is required.

## Stop and report

Stop and report if:

- any required behavior needs a Rust source or protocol change;
- conduct cannot use the interfaces completed by Tickets 04 through 06;
- a validation project must be imported into production;
- a temporary result-meaning carrier appears necessary;
- a second lifecycle must remain green beside the target lifecycle;
- completion would require decoding a replaced Python workspace format;
- a focused test requires live Adviser, product discovery, or native solve;
- sibling preservation or result idempotence cannot be proved through the
  public conduct interface.

## Do not add

- a forwarding `local` module;
- a compatibility alias or decoder;
- a workspace migration;
- a parallel lifecycle;
- a public available-fact carrier;
- a public frontier or revision cursor;
- a workflow, registry, plugin, or dependency container;
- a generic solver interface;
- a second aim implementation;
- paper comparison fields in production Result;
- tests that lock source text, private class shape, callback order, or operation
  map membership.

## Comments

Resolved as one atomic brief-first cutover. The installed root now exposes
only `Authority`, `compile_study`, and `conduct` through offline lazy imports.
Compilation is pure and typed; conduct owns one Authority session, one private
ordered `StudyFrontier`, bounded revision re-observation, checkpoint
admission, sibling preservation, convergence, waiting, and exactly-once
scientific Result admission.

Production Result now carries only scientific conclusion and its admitted
closure. The four `MetalensValidationProject` values remain external project
fixtures that compare published truth only after conduct. The replaced
`local.py`, `_local/` package, lifecycle carriers, result-meaning values,
aliases, and implementation-shaped tests were deleted without a compatibility
decoder or parallel path.

Material work now follows the explicit
`MaterialObservationRequest -> MaterialVerificationRequest` seam.
Project-owned materials select and Authority-admit only requested solver
registrations; `LumericalMaterialVerifier` receives those exact admitted
values and only verifies native existence, wavelength coverage, and readback.
The complete library is absent from response context, observation identity,
and evidence closure. Recorded material response lives with materials and
replays the admitted exact request without opening a library. The pre-existing
metalens `MaterialIntent` retains its sole family-plus-source meaning.

Request artifacts use a Windows-safe short locator backed by an atomically
recorded full SHA-256 identity, append-only capacity generations, and
publish-if-absent immutable writes. Concurrent public conducts crossed the
external seams together, converged through Rust revision admission without a
Python workspace lock, returned identical Result references, bounded external
calls, and replayed with no new decision or product work.

Final verification passed 53 focused compile/conduct/replay/result/project
tests, the dedicated concurrent-conduct test, 368 architecture,
Authority/frontier/periodic-response/run-artifact tests, 54 material contract
tests, and all 10 example tests. Pyright reported zero errors and warnings;
retired lifecycle and production-example searches were empty; isolated root,
materials, and project imports remained offline; `git diff --check` was clean
apart from existing line-ending notices; independent standards/spec review
found no P1 or P2; Rust source and protocol remained unchanged. Live tests
remain reserved for Ticket 09 and the full repository suite for Ticket 10.

### 2026-08-01 - Reopened for exact fault and deletion contracts

The deterministic seal found that the explicitly retired
`_validate_successor` carrier remains defined and called. The current
`compile_study` also translates every downstream `TypeError` and `ValueError`
into `InvalidBrief`, which can disguise implementation drift as malformed user
input.

Keep the public compile outcome exactly `Study | InvalidBrief |
UnsupportedAim`. Convert only explicit brief validation into `InvalidBrief`;
let unexpected compiler and Adapter defects raise directly. Do not retain a
speculative public `MethodUnavailable` until a real supported input requires a
new typed outcome. Preserve monotonic successor behavior inside the private
`StudyFrontier` implementation while deleting the retired carrier name.
Synchronize `SCIENCE.md`, `CONTEXT.md`, tests, and exports with this exact
contract; do not redesign Study, Result, conduct, or the scientific lifecycle.

### 2026-08-01 - Exact repair contract approved

The owner approved this ticket revision, not implementation. The invalid-brief
taxonomy, current refusal union, ADR 0010 interpretation, frontier locality,
coverage migration, CSU ownership, and verification commands above are now
frozen. `CONTEXT.md` keeps the future domain term; implementation and
`SCIENCE.md` must stop claiming that the term is currently reachable.

### 2026-08-01 - Exact compile, frontier, and material closure implemented

The owner subsequently authorized dependency-ordered implementation through
the accepted agent protocol. One writing agent completed the repair and two
independent read-only agents reviewed ADR/spec conformance and repository
standards. Review found and closed incomplete invalid-brief vocabulary,
top-level successor-preservation helpers, missing exact taxonomy tests, and an
implementation-coupled source-name ratchet before both axes passed without a
P1 or P2 finding.

Compilation now translates only exhaustive supplied-brief validation and
`MissingBriefFacts`; downstream compiler exceptions propagate unchanged. The
current outcome remains exactly `Study | InvalidBrief | UnsupportedAim`, the
retired refusal implementation is deleted, and all four future/unknown aim
cases remain covered. `StudyFrontier.replace` owns every monotonic successor
and preservation rule behind its one interface.

Material outcomes now carry the shared external-activity value. Native
sampling and expected native refusal report one paired product session and no
Authority work, external solve, or local placement; registration and recorded
paths report their exact zero-activity origins. Sampling plus cleanup failure
retains both original exceptions, and activity changes no canonical material
document, index, evidence, or reference.

Root verification passed 119 exact focused tests, Pyright with zero findings,
a full CSU scan with zero blocking finding, deletion and dependency searches,
the Rust fixed-point check, and `git diff --check`. No Native execution or
commit occurred in this ticket.

### 2026-08-01 - Fresh application-workspace composition reused by Ticket 09

Ticket 09 review exposed a check/use split around its fresh application root.
This ticket was narrowly reopened and repaired without changing its resolved
status. Its application-owned private science module now derives the fixed
`root/authority` location used by ordinary `conduct` and owns the create-only
claim used by Ticket 09. The dependency direction remains science/application
to generic Authority, no public Authority verb was added, and existing,
racing, or partially initialized roots cannot be accepted as fresh workspaces.
