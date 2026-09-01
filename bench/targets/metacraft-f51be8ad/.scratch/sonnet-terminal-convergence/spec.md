# Canonical Specification — Close MetaCraft in one Sonnet

**Status:** resolved (2026-07-29)

**Baseline:** local `main` at `ca90c27`

## Context

MetaCraft already has the intended large-scale division:

- Rust owns authority, lifecycle, durable truth, and the fixed
  `check -> view -> fetch -> decide` Interface.
- Python compiles scientific intent, gathers evidence, schedules local work,
  and adapts external products.
- A brief compiles into an immutable study; evidence, not workflow position,
  makes another claim ready.
- Propagation phase and geometric phase share one metalens result path while
  retaining their real scientific differences.

The baseline passes 649 non-live tests, Pyright, Rust formatting, Clippy, and
Rust tests. Those green gates do not cover several exactness gaps found by an
independent Standards, Spec, and deep-Module audit.

## Problem

Seven residual problems prevent a phase-final architecture:

1. Rust may audit an old view, release the writer, observe a new generation,
   and remember the mismatched pair as verified.
2. Python authority decoders still accept relationships Rust cannot emit;
   `CheckReport` remains an unvalidated mapping.
3. Three runtime import strongly connected components make dependency
   direction depend on delayed imports.
4. Metalens focal evidence reaches through field evidence to seven storage
   mechanics.
5. Frontier mutation can silently miss a leaf; replay may combine several
   authority snapshots and repeatedly scan one ledger; the common metalens
   relationship tail is still declared twice.
6. Lumerical qualification converts arbitrary implementation failures into
   ordinary capability absence and can accept one polarization basis as two.
7. Canonical science prose, architecture ratchets, ticket lifecycle, durable
   performance evidence, and scoped Git hygiene do not yet agree.

## Principles

### Proof before progress

One verified authority state is born from one atomic proof. A failure to
observe or refresh truth never authorizes an older answer.

### Exact words, exact relations

Python accepts only values and relationships Rust can emit. No adapter repairs,
coerces, defaults, or guesses.

### Difference descends, commonality rises

Aim-specific interpretation stays with the aim. Generic science owns only
proof formation shared by every aim. Field storage owns storage; metalens owns
focus.

### Expected absence is data; drift is error

An unavailable external product may become a typed diagnostic and a waiting
study. Broken implementation, corrupt protocol, or failed invariant raises.

### One observation, one state

One replay observation restores one coherent scientific snapshot. One frontier
transition records one complete family.

### No return edge

The production Python runtime import graph is a DAG. Composition roots may
know concrete aims and platforms; generic values never import their consumers.

## Architecture

### Authority

The Rust `Authority` keeps a private verified state:

```text
workspace generation + revision + authority view
```

Audit, generation capture, and verified-state replacement occur under one
writer lifetime. Local atomic commit advances durable truth and verified truth
as one logical transition. Any generation observation failure leaves the
Authority unverified.

The common path protects cooperative writers and ordinary observable durable
changes. Deliberate raw-byte tampering that preserves file size, metadata, and
governed head facts is outside the fast-view threat model; explicit complete
check remains the integrity operation. Stable view must not hash the whole
database.

### Authority adapter

Python decodes:

- references and revisions;
- proposals and decisions;
- current values, admitted decisions, and permits;
- authority views;
- check reports.

Decoding verifies exact keys, scalar types, canonical order, uniqueness, hash
form, and cross-field invariants. In particular, an admitted decision carries
the references and revision transition required by the Rust protocol; a
rejected decision cannot pretend to advance durable truth.

### Compiler

The compiler is arranged in three layers:

```text
science/compile.py
    explicit composition and public compile_study
        ↓
science/metalens/compiler.py
    metalens brief, design, advice, and relationship
        ↓
science/compiler.py
    aim-neutral proof, task, evidence, and Study formation
```

`Study` exposes generic `design`, never `.metalens`. The metalens Module owns
the single strict narrowing operation `metalens_design(study)`.

Generic advice is described by one structural `Advice` Interface. Existing
design, period, and height advice satisfy it without inheritance, registration,
or conversion. Concrete advice interpretation remains aim-local.

`science.relationships` owns only the `Method` and `Relationship` values. Aim
selection belongs to the composition root.

### Workstation

`workstation.model` forms a layout only from explicit `Demand` and `Host`
facts. `workstation.windows` observes Windows and starts workers. The package
Interface preserves `workstation.plan`: when no Host is supplied, the outer
composition first observes and then calls the pure planner.

### Field evidence

Field evidence owns complete semantic operations for storing and restoring
field components. Its private storage Module owns dtype, byte order, raw-media
validation, reference resolution, and array restoration.

Metalens focal evidence owns the FocalRegion schema and its metalens-specific
values, but it does not import or re-export the private storage vocabulary. No
public storage class, codec tree, or registry is introduced.

### Conduct and replay

A private `_Frontier` owns the ordered live branches, exact replacement,
exact removal, snapshot formation, and transition invariants. It is not
exported and knows no metalens phase level or solver product.

Scientific operations produce deterministic sibling order. Conduct preserves
that order and fails if the expected leaf is absent.

Replay reads one Authority view, indexes it once, and restores branches,
results, and formation from that same snapshot. It does not call `view`
separately for each result or state fragment.

Propagation and geometric relationships retain different preludes. Their
identical:

```text
aperture -> field -> focal region -> focus
```

tail has one declaration owner and one execution owner.

### Periodic responses

The only response capabilities remain:

- `periodic_transmission_response`;
- `periodic_polarization_response`.

They are independent and route-neutral. Transmission qualification runs its
own fixture. Polarization qualification proves exactly two distinct input
bases and validates both outputs.

Scientific non-finite or insufficient response returns capability false.
Expected native product absence follows existing typed outcomes. If no Study
exists yet, preflight surfaces the typed reason. If a live branch already
exists, the application admits one diagnostic record, attaches its reference
to a Finding, and returns an honest waiting Study. Programming error,
invariant failure, malformed shape, and protocol drift raise directly.

Independent sibling fixtures are attempted without losing cleanup. Session,
worker, permit, and lane closure remain exact.

## Public Interface contract

The following meanings remain stable:

- Rust exposes one Authority and exactly `check`, `view`, `fetch`, `decide`.
- Python exports `compile_study`, `conduct`, Brief, Study, Result, and the
  authority Adapter.
- Package-level `workstation.plan` still accepts an optional observed Host.
- Brief, authority, evidence, result, and replay document bytes do not change
  unless an existing exact decoder proves the baseline bytes invalid.
- Periodic capability names do not change.

Internal module paths and the non-canonical convenience property
`Study.metalens` may be removed without aliases.

## Data flow

```text
brief
  -> explicit aim compiler
  -> generic Study formation
  -> ordered ready tasks
  -> qualified binding
  -> external observation
  -> validated evidence proposal
  -> Rust decision
  -> one new Study
  -> Result or honest waiting Study
  -> one-snapshot replay
```

No external adapter mutates lifecycle state. No generic compiler calls a
solver. No Rust code contains scientific meaning.

## State management

- Rust verified state is private, replace-only, and invalidated on any failed
  generation observation.
- Study, AvailableScience, Frontier snapshots, Evidence, and Result remain
  immutable values at their public seams.
- Frontier replacement and removal are total operations: success changes one
  named leaf; absence raises.
- Replay observes one revision and never mixes state from another observation.

## Error handling

| Condition | Behaviour |
| --- | --- |
| Expected external product absence before Study | Existing typed exception |
| Expected external loss during a branch | Admitted diagnostic + Finding + waiting Study |
| Scientific fixture does not establish a response | Capability false |
| Rust protocol shape or relation is impossible | Decoder error |
| Frontier leaf is absent | Invariant error |
| Implementation drift or programming error | Raise directly |
| Generation cannot be observed | Forget verified proof and fail closed |

No new exception hierarchy is added.

## Runtime dependency contract

Every runtime import under `src/metacraft_next` participates in the dependency
graph, including imports inside functions. Imports guarded only by
`TYPE_CHECKING` are excluded. Every strongly connected component must have
size one. The architecture test reports the complete cycle when this fails and
uses no allowlist.

The three baseline cycles to delete are:

```text
science.study <-> science.metalens.design
science.relationships <-> science.metalens.relationship
workstation.model <-> workstation.windows
```

## Trade-offs

- Explicit composition gains a visible edit point when another aim is added;
  it intentionally rejects automatic discovery and registry machinery.
- The authority fast path does not defend against an adversary that preserves
  every observed file identity. Full database hashing would discard the
  measured common-path gain.
- A private Frontier adds one owner but deletes scattered partial operations.
- Aim-specific compiler Modules add two clear seams while removing generic
  type unions and return imports.
- Public science meaning remains stable even though internal imports and
  `Study.metalens` change.

## Prohibited additions

Do not add:

- a public Frontier or workflow engine;
- an aim, solver, method, advice, or storage registry;
- plugin discovery;
- compatibility aliases or legacy import shims;
- a second decoder;
- a new exception inheritance tree;
- a public field-internals Interface;
- synthetic advice;
- a new Rust verb or scientific Rust type;
- live execution inside an implementation or verification ticket.

## Ticket order

1. [Let one audit remember one generation](issues/01-let-one-audit-remember-one-generation.md)
2. [Let Python accept only what Rust can say](issues/02-let-python-accept-only-what-rust-can-say.md)
3. [Let dependencies flow without return](issues/03-let-dependencies-flow-without-return.md)
4. [Let field evidence hide its storage](issues/04-let-field-evidence-hide-its-storage.md)
5. [Let one frontier return one science](issues/05-let-one-frontier-return-one-science.md)
6. [Let each periodic response fail honestly](issues/06-let-each-periodic-response-fail-honestly.md)
7. [Let code and record close together](issues/07-let-code-and-record-close-together.md)

Tickets 04 and 05 are structurally independent after Ticket 03, but the
canonical single-agent order remains numeric.

## Verification strategy

Per implementation ticket:

- write the failing focused seam first;
- run only the focused tests needed by that ticket;
- run Pyright over touched Python scope where practical;
- run CSU over touched production files;
- run `git diff --check` over the ticket range.

Ticket 01 additionally runs Rust format, Clippy with warnings denied, all Rust
tests, release scale diagnostics, Python extension import smoke, and source
manifest verification. Production Rust then freezes.

Ticket 07 runs:

- the complete non-live Python suite with the repository interpreter;
- Pyright;
- architecture ratchets, including the runtime DAG;
- Rust format, Clippy, and tests without changing Rust;
- fixed-range `git diff --check`;
- durable performance and closure evidence.

No live marker is enabled.

## Completion

The effort is complete when all seven tickets are resolved, focused and final
gates are green, production runtime imports are acyclic, the old planning
records and new tracker agree with Git, and canonical live delivery remains
explicitly blocked for a human decision.
