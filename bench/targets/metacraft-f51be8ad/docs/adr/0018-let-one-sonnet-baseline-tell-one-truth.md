# 0018 - Let one Sonnet baseline tell one truth

Status: accepted

## Context

MetaCraft has already separated Rust authority from Python science, reduced
the installed root to three operations, introduced deep execution Modules,
and proved the current metalens methods deterministically. The remaining
architecture is nevertheless described by several competing narrators:
historical ADRs still name a runner and product dispatch, the active Sonnet
specification still names validation projects, current production still
stores published comparison meaning in a scientific focal comparison, and the
outer application directory is sometimes called a workspace even though the
domain glossary reserves **workspace** for Authority-governed truth.

This is an internal ownership decision. It introduces no external scientific
claim, so a new Research Record is not applicable. Its evidence is the
accepted ADR history, the active Sonnet specification, the implementation
import graph, and the concrete contradictions recorded by Ticket 08.5.

## Problem

When several documents or Modules classify the same state, a repair can pass
its local tests while leaving the system semantically open. That has happened
in four ways:

- callers and conduct translate expected scientific outcomes by parsing
  exception text instead of receiving typed values from the Module that owns
  the rule;
- benchmark identity, published values, and scientific Result meaning are
  joined inside production even though comparison is an external example
  concern;
- `workspace` names both the durable Authority instance and the directory
  that also contains product artifacts;
- Ticket 06 waits for Native qualification while Ticket 09, which owns that
  exact bounded gate, declares Ticket 06 resolution as its prerequisite.

Further abstraction would not solve these contradictions. It would give the
same truth another narrator.

## Principle

The Sonnet baseline follows six rules:

1. **One meaning, one owner.** The Module that owns a scientific rule returns
   its expected outcome; the Authority workspace owns durable truth; a
   benchmark case owns published truth.
2. **One direction, no return.** Composition selects aim and product Adapters;
   aim science depends on shared values; shared values never select a
   consumer; production never imports examples.
3. **Small Interface, deep Implementation.** Existing deep Modules are kept
   where their deletion would scatter policy across callers. Pass-through
   helpers and duplicate result wrappers are deleted.
4. **Expected absence is data; defects are faults.** Findings carry ordinary
   scientific refusal or waiting. Stale identities, malformed documents,
   impossible order, broken protocol, and implementation drift raise
   directly.
5. **Names state domain intent.** `workspace`, `application root`, `benchmark
   case`, `published comparison`, `project execution`, and `product probe`
   each name one meaning. Ticket numbers and retired architecture names do not
   become permanent code vocabulary.
6. **Evidence closes the movement.** A decision flows through the current
   specification, one named ticket, Interface-level verification, and a
   checkpoint. A map indexes that chain but never duplicates its authority.

## Architecture

### Truth and documentation

The durable traceability chain is:

```text
Research Record or explicit not-applicable reason
    -> accepted ADR
    -> current Canonical Specification concern
    -> one implementation ticket
    -> Interface-level verification
    -> verified checkpoint
```

`CONTEXT.md` owns only ubiquitous language. ADRs own hard-to-reverse decisions
and supersession. `DESIGN.md` owns current system structure, `SCIENCE.md`
scientific and evidence flow, `DEVELOPMENT.md` enforcement and gates, and
`ROADMAP.md` future capability. Local maps are navigation indexes. Each ticket
header is the sole authority for that ticket's current status.

### Root, state, and storage

The installed root exports exactly `Authority`, `compile_study`, and
`conduct`. `Authority` retains exactly `check`, `view`, `fetch`, and `decide`.
Rust and its protocol remain frozen.

The storage names are exact:

```text
application root/
    authority/    # the Authority workspace and durable truth
    runs/         # product artifacts
```

`workspace` continues to mean the Authority-governed object store, ledger,
and projections defined by `CONTEXT.md`. `application root` means the outer
directory claimed once by the brief-first composition. The public conduct
parameter is `application_root`; private composition derives the Authority
workspace and run directories from it and rejects an existing root with
`application_root_must_be_new`. No `Workspace` wrapper, fifth Authority verb,
or second lifecycle is introduced.

The valid conduct seam is create-only and aim-specific:

```python
conduct(
    brief,
    *,
    application_root,
    consultation,
    evidence_adapter,
) -> ConductOutcome

MetalensEvidenceAdapter.open(
    *, authority: Authority, runs_directory: Path
) -> tuple[PeriodicResponse, MaterialResponse]
```

Compilation occurs before root creation. An invalid or unsupported brief
creates no root; an existing or partial root fails before `open`; and an open
fault propagates directly while the new root remains retained and
non-reusable. `open` occurs exactly once. Both returned ports validate their
product context through the same Authority, although their context references
need not be equal. There is no existing-root or second-call replay contract.

`Study` remains the sole complete immutable scientific state.
`StudyFrontier` remains its private ordered checkpoint owner.
`AuthoritySession` remains the sole observed-revision policy.
`WorkExecution` remains the sole permit-to-receipt or permit-to-close life.
`PeriodicBatchExecution`, `Session`, `SessionPool`, `RunDirectory`, and
`WorkRecord` retain the operational policies that their small Interfaces
hide. They are not replaced by a generic runner, dispatch framework,
dependency container, registry, or lifecycle framework.

### Scientific choice and faults

Metalens choice logic exposes three owning operations:

```python
resolve_period_choice(...) -> PeriodChoice | Finding
derive_height_domain(...) -> HeightDomain | Finding
resolve_height_choice(...) -> HeightChoice | Finding
```

An explicitly constrained value that violates a physical requirement returns
`Finding(kind=REFUSAL, ...)`. Missing, unavailable, invalid, outside-domain,
or ruled-out advice returns `Finding(kind=ADVICE, ...)`. A stale brief
identity, domain reference, or grounds reference; malformed document; wrong
runtime type; or impossible ordering is not an ordinary scientific outcome
and raises directly. The compiler owns only missing advice and typed
`AdviceStatus` handling. Conduct composes returned values and never classifies
`str(error)`.

The adviser Adapter classifies only missing configuration and an explicit
transport timeout as `UNAVAILABLE`. A received but scientifically invalid or
invalid-JSON answer is `INVALID`. A malformed provider envelope, parser defect,
unexpected exception, or contract mismatch raises directly. There is no broad
catch that turns every defect into unavailable advice and no error-prefix
parser.

### Scientific evidence and product execution

`PeriodicResponse` remains the route-neutral external seam. Science-owned
evidence Modules interpret its transmission, polarization, and reference-
surface observations. The Lumerical Adapter owns product qualification,
capacity, construction, session, project execution, artifacts, observation,
and cleanup without importing a metalens control strategy.

Names follow the owner rather than the ticket or historical mechanism:

- periodic cell observations become periodic cell evidence;
- reference-surface admission becomes reference-surface evidence;
- focal field comparison contains only observed-versus-ideal role evidence;
- a native project produces `ProjectExecution` and `ExecutedProject`;
- installation observation is owned by `ProductProbe`;
- run artifacts store capacity evidence under `capacity/`, not `dispatch/`;
- the material response that verifies selected registrations is a verifying
  material response, not a project manager.

### Benchmark ownership

The four reviewed examples are `MetalensBenchmarkCase` values outside the
built distribution. Each owns one blind brief, `PublishedPlatform`, one
`PublishedComparison`, fidelity, and comparison rules. Its only behavioral
entry is:

```python
case.compare(
    completed_results,
    *,
    fetch,
) -> tuple[MetalensBenchmarkComparison, ...]
```

This amended signature replaces the original no-`fetch` signature. The
installed Adapter is `Authority.fetch`; focused tests supply an exact
in-memory body reader. The case uses that read-only dependency to validate the
admitted Result body and restore its exact Focus, fabrication, and high-NA
focal-comparison evidence. It does not add another case behavior, reader
wrapper, runner, registry, or lifecycle.

`MetalensBenchmarkComparison` directly owns case identity, Result reference,
one design-end comparison, one field-end comparison, published platform,
published comparison, fidelity, and fidelity notes. The design end places
advised, admitted, and published period and height beside admitted geometry.
The field end uses one typed `BenchmarkMeasure` vocabulary and returns exactly
`comparable`, `context only`, `not reported`, or `not applicable` for every
measure. Only a quantitatively comparable definition permits a signed
difference. A high-NA field end also projects the exact admitted x/y/z complex
component errors while retaining its focal-comparison reference; a low-NA
field end carries neither. The focal comparison's input and output
longitudinal Poynting powers describe through-plane transmission, not the
fraction of electric-field power in a longitudinal component, so they never
populate `longitudinal power fraction`. That measure remains unobserved until
exact evidence establishes it. The accepted primary-source audit found that none of the six
current quantitative paper values meets that condition, so none carries a
delta. In particular, Khorasaninejad's `375 nm` observation is a vertical-cut
FWHM retained as context, not a mean x/y width.

There is no advice-comparison wrapper, conducted-project wrapper, names-only
forwarding helper, or production benchmark meaning. Production
`FocalFieldComparison` owns observed-versus-ideal role evidence only; it
contains no published value or source comparison. The measurement definitions
and source locators come from the accepted
[2026-08-06 benchmark Research Record](../research/2026-08-06-metalens-benchmark-published-measure-definitions.md);
the paper values remain external context rather than thresholds.

The current strict schema identifiers are:

```text
metacraft.examples.metalens_benchmark_case
metacraft.examples.metalens_benchmark_comparison
metacraft.science.metalens.unit_integral_focal_field_comparison
```

No compatibility reader accepts their retired schema identifiers.

The four cases are first exercised through recorded Adapters after the Sonnet
seal. Running all four natively requires a separate cost and scientific-value
decision.

### Delivery and proof

Ticket 08.5 is one deterministic convergence movement. It changes the choice
contracts, performs the naming and benchmark cutovers, updates canonical
documentation, and replaces source-shape tests with Interface behavior where
possible. It adds no scientific capability and runs no Native solve.

Ticket 09 owns the only remaining fresh five-solve Native gate. Its three
qualification solves provide the missing installed-product evidence for
Ticket 06; the same gate's two candidate solves, receipts, and recovery provide
Ticket 09 evidence. Ticket 09 therefore consumes Ticket 06's deterministic
handoff but does not wait for Ticket 06 to be Native-resolved. The
qualification portion closes Ticket 06, and the complete receipt portion
closes Ticket 09. Ticket 10 verifies and seals the already accepted
architecture; it does not invent an ADR or repair production.

The stages are named precisely:

```text
current deterministic handoff  -> Sonnet-shaped
Ticket 08.5 complete            -> Sonnet-ready
Ticket 06/09 Native gate passes -> Sonnet-proven
Ticket 10 closes                -> Sonnet-sealed
```

### Supersession

This decision preserves the scientific and authority meaning of ADRs 0001
through 0017. It supersedes only these obsolete operational clauses:

- ADR 0002's route-neutral `runner` is now `conduct` composed from the deep
  execution Modules above;
- ADR 0003's product-owned `dispatch` and shared `runner` names are replaced
  by product response composition, capacity evidence, `WorkExecution`, and
  `PeriodicBatchExecution`; its capacity, permit, lane, and qualification
  rules remain in force;
- ADR 0004's shared `runner` wording is replaced by the same composition; its
  claim-method proof topology remains in force;
- ADR 0013's prohibition on exception-text classification is generalized to
  every seam. Expected outcomes are classified by their owning Module;
  malformed protocol and unexpected defects still raise directly. Its three
  independent response semantics, as amended by ADR 0015, remain in force.

ADR 0017 remains the sole owner of the periodic vertical layout and native
reference-plane interpretation.

## Trade-off

This cutover deliberately spends compatibility. Python documents, module
paths, example schemas, and private names from the replaced architecture are
not migrated or aliased; a fresh application root is required. The cost is a
coordinated deterministic change and test rename. The gain is that each
retained name has one owner, each expected outcome has one type, and each
delivery gate has one responsibility.

The benchmark seam remains concrete and metalens-specific. The consultation
seam remains aim-specific. The periodic response seam remains response-
specific rather than becoming a universal solver Interface. These choices
accept some explicit composition in exchange for avoiding abstractions backed
by only one real variation.

## Conclusion

The architecture stops deepening when ADR 0018's Interfaces, dependency
direction, error table, benchmark ownership, naming ratchets, deterministic
gates, and one Native gate all agree. “Not Sonnet enough” alone is not a
reopening condition. A new change must identify a concrete violated decision,
Interface, dependency, state owner, error contract, test, domain term, or
Native fact.

One root receives; one Study remembers. One Authority admits; one Result
answers. Cases compare from outside, evidence closes from within.
