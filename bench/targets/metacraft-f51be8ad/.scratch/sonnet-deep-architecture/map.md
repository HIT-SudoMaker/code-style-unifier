# Map - Sonnet deep architecture

**Label:** `wayfinder:map`

## Role

This file is a non-normative navigation index. It does not own architecture,
domain language, implementation truth, ticket status, or historical evidence.

- `CONTEXT.md` owns domain language.
- accepted ADRs own decisions and supersession.
- [spec.md](spec.md) owns current implementation intent.
- each ticket header owns that ticket's current status.
- each ticket's comments own its execution history and evidence.
- tests and tracked records own verification evidence.

When this map disagrees with one of those owners, repair the map.

## Destination

One breaking Python cutover produces:

- one cheap installed Interface: `Authority`, `compile_study`, `conduct`;
- one complete immutable scientific state: `Study`;
- one durable authority owner: the Rust-backed workspace;
- one application root that contains `authority/` and `runs/`;
- two real external seams: metalens consultation and periodic response;
- one route-neutral execution life behind deep Modules;
- four `MetalensBenchmarkCase` values outside production;
- one bounded Native proof followed by one deterministic seal.

Rust source, protocol values, persisted authority meaning, and the Authority
verbs `check`, `view`, `fetch`, and `decide` remain frozen.

## Decision chain

```text
external research where applicable
    -> ADR 0001 ... ADR 0017
    -> ADR 0018: one Sonnet baseline tells one truth
rectilinear product evidence
    -> ADR 0019: form uniform Fields from raw rectilinear surfaces
    -> Sonnet deep architecture specification
    -> Ticket 08.5 deterministic convergence
    -> Tickets 08.6/08.7 deterministic rectilinear and forensic seams
    -> Ticket 06/09 one Native evidence gate
    -> Ticket 10 deterministic seal
```

A new Research Record is not applicable to ADR 0018 and Ticket 08.5 because
they change internal ownership, dependency direction, naming, and delivery;
they introduce no external scientific fact.

## Dependency graph

```text
01 Python name
  -> 02 complete Study
  -> 03 external published-truth owner
  -> 04 Authority session and work life

02 -> 05 two-question consultation
04 -> 06 periodic response deterministic handoff

02 + 03 + 04 + 05 + 06
  -> 07 brief-first lifecycle
  -> 08 shared Field Interface

06 deterministic handoff + 08
  -> 08.5 one Sonnet baseline
       |-> 08.6 raw rectilinear observation -> qualified uniform batch
       `-> 08.7 persist existing ProjectExecution before observation

08.6 + 08.7
  -> 09 one fresh five-solve Native gate
       |-> qualification evidence closes 06 Native acceptance
       `-> candidate + receipt + recovery evidence closes 09

06 Native acceptance + 09
  -> 10 deterministic seal
```

Ticket 09 does not wait for Ticket 06 to become Native-resolved. It consumes
Ticket 06's accepted deterministic handoff and supplies the remaining Native
fact itself. This removes the former dependency cycle without adding a second
qualification run.

The first 2026-08-05 gate attempt contradicted the handoff's constructed-child
mutation mechanism. A later fresh attempt completed three qualifications and
established the next boundary fact: qualification observed a closed 43 by 43
uniform grid, while both candidate bases observed closed 36 by 33 strictly
increasing but nonuniform rectilinear axes. Ticket 08.6 owns that scientific
formation seam and Ticket 08.7 owns pre-observation persistence of the
existing `ProjectExecution`. Both tickets are resolved, so Ticket 09 has no
deterministic blocker. Failed application roots are never reused, and
deterministic closure alone authorizes no retry.

## Normative sources

- [CONTEXT.md](../../CONTEXT.md);
- accepted [ADRs 0001 through 0019](../../docs/adr/), applying explicit
  supersession clauses;
- [spec.md](spec.md), where it conforms to the glossary and ADRs;
- the linked implementation tickets, where they conform to those owners.

[ADR 0018](../../docs/adr/0018-let-one-sonnet-baseline-tell-one-truth.md)
supersedes the obsolete `runner` and product `dispatch` wording in ADRs 0002,
0003, and 0004 while preserving their scientific, capacity, permit, lane, and
qualification decisions. It generalizes ADR 0013's prohibition on exception-
text classification. ADR 0017 remains the sole owner of periodic vertical
layout and native reference-plane interpretation. ADR 0019 owns preservation
of raw rectilinear coordinates, deletion of the independent reference-surface
request path, and qualified uniform batch formation; it does not change ADR
0017's z/layout decision.

## Frozen Interfaces

```python
# installed root
Authority
compile_study
conduct

# Authority
check
view
fetch
decide

# brief-first composition
conduct(
    ...,
    application_root=...,
    consultation=...,
    evidence_adapter=...,
)
MetalensEvidenceAdapter.open(
    *, authority: Authority, runs_directory: Path
) -> tuple[PeriodicResponse, MaterialResponse]

# choice seams
resolve_period_choice(...) -> PeriodChoice | Finding
derive_height_domain(...) -> HeightDomain | Finding
resolve_height_choice(...) -> HeightChoice | Finding

# external benchmark seam
MetalensBenchmarkCase.compare(
    CompletedResults,
) -> tuple[MetalensBenchmarkComparison, ...]
```

The application root owns one fixed `authority/` workspace and `runs/`
product-artifact tree. `workspace` does not change meaning. No `Workspace`
wrapper, fifth Authority verb, compatibility reader, or second lifecycle is
introduced. Compilation precedes root creation; the root is create-only;
evidence opens exactly once; and no existing-root or second-call replay is
supported.

The current strict schemas are
`metacraft.examples.metalens_benchmark_case`,
`metacraft.examples.metalens_benchmark_comparison`, and
`metacraft.science.metalens.focal_field_comparison`.

## Ticket 08.5 movement

[Ticket 08.5](issues/08.5-let-one-sonnet-baseline-tell-one-truth.md) is one
deterministic, atomic cutover with four movements:

1. choice Modules return typed Findings and direct faults;
2. modules, files, classes, functions, test files, and run paths receive
   intention-revealing present-tense names;
3. benchmark cases own published truth and production focal-field comparison
   loses every published-source field;
4. glossary, canonical docs, current spec, architecture tests, and deletion
   ratchets close the baseline.

It adds no capability, abstraction framework, migration, Native solve, or
commit. The ticket is the exact scope and acceptance authority.

## Native gate

[Tickets 08.6](issues/08.6-let-rectilinear-observation-form-one-uniform-batch.md)
and [08.7](issues/08.7-retain-solve-completion-before-observation-failure.md)
are resolved deterministic prerequisites. The session accepts finite strictly
increasing rectilinear axes without a uniform-spacing gate; qualified uniform
formation belongs to the Field Module, and an execution-only artifact must not
claim a `WorkRecord`, receipt, diagnostic schema, or admitted result.
Ticket 08.6's accepted formation is `periodic_rectilinear_bilinear_v1`: one 24
by 24 half-open grid, periodic bilinear interpolation, maximum batch 256, no
extrapolation or normalization, and fixed diagnostic limits `0.0081`,
`0.0093`, and `0.0006`. The gate was qualified by read-only opening of retained
`after.fsp` files with zero solves; the failed root remains non-reusable.
The 24 by 24 target replaces a 64 by 64 candidate that crossed the qualified
1 GiB high-NA vector-field guard and passes all five delivery tests across the
four cases.

Their shared closure passed 1,223 non-live tests with 6 deselected and 0
skipped, 105 architecture tests, Pyright with zero findings, and CSU with zero
blocking findings. Ticket 09 was then ready for separate approval of one fresh
five-solve Native gate. That gate subsequently passed and Ticket 09 is
resolved.

[Ticket 09](issues/09-prove-one-fresh-workspace-through-a-native-receipt.md)
owns one fresh application root and exactly five solves:

1. one propagation qualification solve proving transmission and reference
   surface independently;
2. one x-linear polarization qualification solve;
3. one y-linear polarization qualification solve;
4. one x-linear candidate solve;
5. one y-linear candidate solve.

The three qualification results close Ticket 06 only when ADR 0017's declared
planes, specified-position sampling, half-nanometre center handling, and
substrate/PML coverage pass against the installed product. The complete five-
solve record, two receipts, exhaustive inventory, and zero-work recovery close
Ticket 09. A stopped or failed application root is retained and never reused.

The live receipt test passed once in 140.09 seconds at fresh application-root
identifier `sonnet-ticket09-20260805-03`. The independently validated redacted
receipt has SHA-256
`5bf6e2170b82f077cfd313ed28c4c9268f773a1e857a4b92a838fbdd68b05416`,
records exactly three qualification plus two candidate solves, contains two
formed 24 by 24 surfaces, and proves identical 38-entry Native and recovery
inventories with zero recovery execution. Tickets 06 and 09 are resolved.

No complete library, brief-to-Result conduct, full parameter sweep, or
published benchmark claim belongs to this gate.

## Seal

[Ticket 10](issues/10-seal-the-sonnet.md) verifies the already accepted and
implemented architecture. It owns no production repair and performs no live
work. It checks deterministic behavior, dependency direction, import cost,
deletion ratchets, package contents, the frozen Rust fixed point `40f2127`,
and Ticket 09's tracked redacted evidence.

Ticket 10 is resolved by the deterministic evidence recorded in
[CLOSURE-REPORT.md](CLOSURE-REPORT.md). It verified implementation commit
`eb6db2f`, the fixed point `40f2127`, the release wheel, and Ticket 09's
tracked receipt without reopening the Native root.

ADR 0018 was accepted before implementation. Ticket 10 wrote only the closure
record and status indexes; it did not invent or repair the architecture during
the seal. The implementation checkpoint is `eb6db2f`; commit history records
the immediately following non-production closure checkpoint.

## Ticket index

Ticket headers, not this list, own current status.

1. [Let one Python name describe one system](issues/01-let-one-python-name-describe-one-system.md)
2. [Let Study carry complete science](issues/02-let-study-carry-complete-science.md)
3. [Let four validation projects own published truth](issues/03-let-four-validation-projects-own-published-truth.md) - historical name, superseded for current vocabulary by ADR 0018
4. [Let one Authority session own one work life](issues/04-let-one-authority-session-own-one-work-life.md)
5. [Let metalens consultation answer two questions](issues/05-let-metalens-consultation-answer-two-questions.md)
6. [Let periodic response hide product work](issues/06-let-periodic-response-hide-product-work.md)
7. [Let one brief compile, conduct, and conclude](issues/07-let-one-brief-compile-conduct-and-conclude.md)
8. [Let Field export only shared language](issues/08-let-field-export-only-shared-language.md)
8.5. [Let one Sonnet baseline tell one truth](issues/08.5-let-one-sonnet-baseline-tell-one-truth.md)
8.6. [Let rectilinear observation form one uniform batch](issues/08.6-let-rectilinear-observation-form-one-uniform-batch.md)
8.7. [Retain solve completion before observation failure](issues/08.7-retain-solve-completion-before-observation-failure.md)
9. [Prove one fresh application root through a Native receipt](issues/09-prove-one-fresh-workspace-through-a-native-receipt.md)
10. [Seal the Sonnet](issues/10-seal-the-sonnet.md)

## Delivery protocol

Production implementation starts only after separate approval. For each open
implementation ticket:

1. the root freezes Interface, file ownership, and verification commands;
2. one implementation sub-agent writes the bounded ticket;
3. two read-only sub-agents review ADR/spec conformance and repository
   standards in parallel;
4. the root re-runs the gates and alone records the checkpoint;
5. no later ticket begins before the preceding deterministic dependency is
   accepted.

The dirty working tree is preserved. Before a writer starts, every overlapping
hunk is attributed as retained user work, superseded by approved scope, or
left untouched. No agent may stash, reset, revert, delete, or silently absorb
unrelated work. A recoverable attributed checkpoint precedes any claim of a
trusted baseline.

## Stages and stopping rule

```text
current deterministic handoff  -> Sonnet-shaped
Ticket 08.5 complete            -> Sonnet-ready
Tickets 08.6/08.7 complete      -> rectilinear-ready
Ticket 06/09 Native gate passes -> Sonnet-proven
Ticket 10 closes                -> Sonnet-sealed (current)
```

After each stage's declared gates pass, vague dissatisfaction is not a reason
to reopen it. Reopening requires a concrete contradiction in an ADR,
Interface, dependency direction, state owner, error contract, domain term,
behavioral test, or Native fact. A repeated blocker returns to its owning
ticket and triage record; it does not trigger speculative restructuring.

## Post-seal continuation

Only after Ticket 10 closes, follow the separate
[metalens benchmark proof](../metalens-benchmark-proof/spec.md). It exercises
the exact propagation/geometric-phase by low/high-NA two-by-two matrix through
recorded Adapters and expects the established `3 + 3 + 1 + 1` Result shape.
Deepen `select -> conduct -> compare` only if that real use reveals duplicated
policy at multiple callers. Complete Native execution of all four cases
requires a separate cost and scientific-value decision and is not part of the
five-solve Sonnet gate.
