# Authority and science Sonnet closure

Status: superseded by ../sonnet-performance-and-reliability/spec.md (tickets 01–09 implemented 2026-07-29)

## Context

MetaCraft already has the right governing idea: Rust owns generic workspace
authority; Python owns scientific meaning and execution. The core is small,
the scientific lifecycle is compiled, and the current low-na metalens proof
supports both propagation phase and geometric phase without placing either
mechanism in Rust.

The remaining risk is not a missing framework. It is loss of exactness at a
few seams:

- a test freezes Rust by reading Git history rather than distributable source;
- Python callers unpack raw authority mappings;
- one compiled method may have no application operation and look like an
  honest wait;
- propagation-phase branches are admitted separately and replay restores only
  the latest branch;
- the Lumerical Adapter guesses native property names and qualifies through
  two paths;
- science callers still know sweep work-life details;
- `Field` and `FocalRegion` duplicate binary-array storage rules.

These are local defects with system-wide consequences. The answer is a
single ordered convergence, not another architecture layer.

## Problem

The current implementation can preserve individual facts while losing their
relationship:

1. authority truth is typed in Rust but becomes loose mappings in Python;
2. compiler meaning is explicit but application dispatch is partial;
3. propagation phase forms several valid scientific branches but replay keeps
   one latest checkpoint;
4. natural MetaCraft names become guessed product strings at the Lumerical
   seam;
5. solver work life leaks upward into science;
6. binary storage knowledge repeats across two scientific values.

The architecture therefore reads correctly at rest but can become ambiguous
in motion.

## Principle

**Authority is exact; science is expressive. State is admitted; meaning is
compiled.**

The implementation follows five rules:

1. deepen existing modules before inventing new ones;
2. keep one interface at each real seam;
3. make dependency direction visible and one-way;
4. preserve scientific distinctions even when implementations share storage
   or lifecycle;
5. replace shallow tests with tests at the deepened interface.

In particular, phase quantization follows physical mechanism:

- propagation phase forms independent 8-, 12-, and 16-state phase sets when
  the admitted cell library supports them;
- geometric phase selects one admitted anisotropic cell and derives
  continuous analytic orientations;
- geometric phase may later accept an explicit fabrication orientation grid,
  but it does not participate in the propagation phase-set frontier.

## Architecture

### 1. Keep authority exact

The Rust source remains organized as:

`python_binding -> authority -> workspace`

The public interface remains:

`Authority.check -> Authority.view -> Authority.fetch -> Authority.decide`

Ticket 01 audits lifecycle invariants, canonical protocol bytes, generic
finding semantics, and replay integrity. It also exercises ledger replay at
representative scale and replaces the Git-history freeze test with a committed
source manifest that works in a source archive.

The performance exercise is diagnostic. It records behavior at hundreds,
thousands, and several thousand ledger entries without inventing an arbitrary
time threshold. Production Rust changes only if the exercise exposes a clear,
reproducible defect that can be corrected without weakening integrity.

Rust closes before Python begins:

- `cargo fmt --check`;
- Clippy on all targets with warnings denied;
- all Rust tests;
- release build;
- Python import smoke through the research environment;
- source-manifest verification.

### 2. Let the view speak in values

The Python authority Adapter decodes the Rust view once:

- `Current` owns a key, current body reference, and superseded references;
- `AdmittedDecision` owns the admitted proposal and body references needed by
  replay;
- `Permit` owns scope, state, close reason, and receipt relationship;
- `AuthorityView` contains immutable tuples of those values.

Callers do not parse `state`, `close_reason`, `key`, or reference mappings.
Malformed wire values fail at the Adapter seam. Rust bytes and Rust source do
not change.

### 3. Let every method find its work

Scientific relationships remain the source of method meaning. The local
application owns the implementation operation for each method.

The relationship is exhaustive:

- every method emitted by the current compiler has exactly one local
  operation;
- every local operation corresponds to an emitted method;
- a missing implementation raises an explicit internal fault;
- ordinary absence of prerequisites remains an honest waiting `Study`.

The common metalens proof tail is declared once. Propagation and geometric
modules retain only their real scientific differences. No public registry,
plugin mechanism, workflow engine, or dynamic discovery surface is added.

### 4. Let propagation branches return together

One application advance may yield one or several immutable
`AvailableScience` branches. Checkpoint storage accepts and records that
complete tuple as one document. Replay returns the complete tuple.

For propagation phase:

- the possible phase-set branch identities are `8`, `12`, and `16`;
- each independently supported phase set becomes one branch;
- the checkpoint retains the complete formation report, including every
  delivered and refused quantization with its exact refusal reason;
- a refused quantization is reported but never represented as a fabricated
  scientific branch;
- branches are stored and restored in ascending quantization order;
- a crash after checkpoint admission cannot reduce the frontier to its last
  branch.

For geometric phase:

- one cell choice and continuous orientations remain one branch;
- no synthetic 8/12/16 phase sets are created;
- no per-orientation solver work is introduced.

The checkpoint shape is replaced directly. Existing solver artifacts remain
untouched, but resumed work uses a new workspace rather than a compatibility
reader for the old checkpoint shape.

### 5. Let native names be exact

The Lumerical session owns an exhaustive product dialect for every native
object kind constructed by current templates.

The dialect maps in both directions:

- natural MetaCraft property -> exact native property and unit conversion;
- exact native property -> natural MetaCraft value and inverse conversion.

There is no underscore-to-space fallback. Unknown object kinds or properties
fail before the engine call. Current mappings include the exact native names
for simulation time, source offset, start wavelength, stop wavelength, spans,
positions, boundaries, shapes, materials, and grating settings used by the
periodic templates.

Product vocabulary stays inside the Adapter. No product-version branch or
compatibility alias is added.

### 6. Let qualification walk one path

Qualification follows one public mental order:

`configured -> found -> versioned -> licensed -> qualified -> available`

One qualification implementation carries the reached facts and one exact
finding:

- `configured`, `found`, `versioned`, and `licensed` do not construct
  scientific geometry;
- `qualified` is the first stage that performs one minimal native
  construction and engine check;
- `available` combines a qualified binding with fresh positive capacity;
- production dispatch, fake tests, and explicitly enabled live checks use the
  same interface.

An installation or license check cannot fail because a periodic template has
an unrelated property defect. Capacity refresh does not repeat full
qualification.

### 7. Let dispatch contain one work life

The science-facing execution verbs are:

- `gather_periodic_transmission`;
- `gather_jones_library`.

Material sampling remains qualification evidence, not a sweep verb.

The Lumerical dispatch implementation owns candidate planning, lane placement,
session leasing, permits, native projects, artifacts, observations, receipts,
capacity renewal, and recovery. `LumericalSweep` and `open_sweep` cease to be
caller knowledge.

The workstation remains the one local placement module. The Lumerical Adapter
requests lanes; it does not duplicate topology, affinity, SMT, NUMA, or memory
policy.

No common solver interface is introduced. Lumerical is still the only real
solver Adapter.

### 8. Let fields share one store

`Field` and `FocalRegion` keep separate scientific meanings and schema
identifiers. They share one private field-storage implementation for:

- immutable array bytes;
- shape and dtype validation;
- media-type checks;
- component-reference mappings;
- fetch and restore closure.

The private storage interface knows binary component facts, not metalens
focus, propagation algorithms, or result meaning. It is not exported from
`metacraft_next.field`.

The deletion test must hold: deleting this implementation would recreate the
same storage rules in both field and focal-region modules.

### 9. Let the architecture close as one

The final ticket:

- removes superseded shallow tests after replacement tests cover the deepened
  interfaces;
- adds architecture ratchets for dependency direction, retired names, typed
  authority values, total method binding, private Lumerical work life, and
  private field storage;
- reconciles the active `.scratch` status with the implemented Git baseline;
- runs the complete non-live suite once.

Expected cross-seam failures receive typed values only where callers must
classify them. Local invariant and input failures remain direct `ValueError`
facts. No broad exception hierarchy is created.

## Data flow

```text
brief
  -> compiler
  -> immutable study
  -> local application
  -> qualified realization
  -> dispatch
  -> raw observation
  -> admitted evidence
  -> recompiled study
  -> one result or several propagation-quantization results
```

Authority surrounds every mutation:

```text
Python proposal -> Rust decide -> immutable reference -> Python meaning
```

Replay preserves the same direction:

```text
Rust view -> typed Python values -> complete available-science branches
          -> deterministic recompile -> result or waiting study
```

## Interface contracts

| Seam | Small interface | Hidden implementation |
| --- | --- | --- |
| Rust authority | `check`, `view`, `fetch`, `decide` | ledger, object store, integrity, replay |
| Python authority Adapter | typed `AuthorityView` | wire decoding and validation |
| compiler/application | emitted method -> one operation | operation selection and execution |
| checkpoint replay | remember/recall complete branch tuple | document shape and reference closure |
| Lumerical session | natural object construction and inspection | native names, units, engine calls |
| Lumerical qualification | one ordered observation | paths, version, license, construction, capacity |
| Lumerical dispatch | two gather verbs | lanes, sessions, permits, artifacts, receipts, recovery |
| field storage | store/restore component arrays | bytes, dtype, shape, media type, references |

## State management

Rust remains the only mutable authority. Python values are immutable snapshots.
A branch frontier is an immutable checkpoint document, not mutable progress.
Capacity is an admitted current fact; permits reserve bounded work; receipts
close permits. Scientific tasks have no mutable status.

## Error handling

Errors follow ownership:

- Rust returns stable generic findings and protocol errors;
- the Python authority Adapter rejects malformed mappings;
- the compiler distinguishes scientific unavailability from implementation
  faults;
- qualification returns the exact reached stage and finding;
- dispatch exposes typed expected execution failures;
- local invariant violations remain local and direct.

String-prefix parsing is removed only where it currently crosses a real seam.
Internal native messages may remain diagnostic text inside the owning Adapter.

## Trade-off

This convergence deliberately chooses depth over speculative uniformity:

- a direct checkpoint replacement is cleaner than a compatibility layer, at
  the cost of starting resumed work in a new workspace;
- exhaustive product mappings require deliberate maintenance, but prevent
  late live failures caused by guessed names;
- one deep Lumerical Adapter is less superficially generic, but keeps product
  knowledge local until a second solver proves a real shared seam;
- shared binary storage reduces duplication without pretending that `Field`
  and `FocalRegion` mean the same scientific thing;
- sequential tickets are slower than one large patch, but keep Rust-first
  ordering and make every architectural claim independently reviewable.

## Verification

Each ticket runs:

- focused behavior tests through the changed interface;
- affected architecture tests;
- Pyright with the required research Python;
- CSU on touched production files with zero hard violations;
- `git diff --check`;
- the Rust source-manifest gate after ticket 01.

Ticket 01 runs the complete Rust gate. Ticket 09 runs the complete non-live
Python suite once. No ticket runs the four canonical live briefs.

## Tickets

1. [Keep authority exact](issues/01-keep-authority-exact.md).
2. [Let the view speak in values](issues/02-let-the-view-speak-in-values.md).
3. [Let every method find its work](issues/03-let-every-method-find-its-work.md).
4. [Let propagation branches return together](issues/04-let-propagation-branches-return-together.md).
5. [Let native names be exact](issues/05-let-native-names-be-exact.md).
6. [Let qualification walk one path](issues/06-let-qualification-walk-one-path.md).
7. [Let dispatch contain one work life](issues/07-let-dispatch-contain-one-work-life.md).
8. [Let fields share one store](issues/08-let-fields-share-one-store.md).
9. [Let the architecture close as one](issues/09-let-the-architecture-close-as-one.md).

## Conclusion

The target is not more machinery. It is fewer interpretations:

**Rust keeps truth. Python keeps meaning. Propagation branches together;
geometric rotation remains free. Native names are exact; scientific names
remain clear.**
