# Design

MetaCraft separates truth from interpretation: Rust admits durable authority
state, Python owns scientific meaning, and AI supplies untrusted advice.

## Public composition

The installed root is deliberately small:

```python
Authority
compile_study
conduct
```

`Authority` preserves the native constructor and exactly four verbs:
`check`, `view`, `fetch`, and `decide`. One Python Adapter may import the
private native module. All other Modules exchange typed Python values and
never construct raw proposals, parse raw decisions, or keep a second view of
authority state.

`compile_study(brief)` is pure. `conduct(...)` is the only brief-first
application operation. It compiles before touching storage, claims one absent
`application_root` on the first call, and resumes only its exact checkpointed
brief on later calls. The root retains fixed `authority/` and `runs/`
directories. An evidence Adapter is optional and opens only when genuinely
ready executable evidence requires it:

```python
MetalensEvidenceAdapter.open(
    *, authority: Authority, runs_directory: Path
) -> tuple[PeriodicResponse, MaterialResponse]
```

The two returned ports validate their product context through that same
`Authority`; their admitted references need not be identical. An invalid brief
creates no root; foreign, partial, or brief-mismatched roots fail without
repair. The next request is re-derived from `StudyFrontier`, never stored as a
cursor. A per-root execution lock serializes answer adoption, while Authority
current admission remains the scientific checkpoint. Repeating a pause or
completed result opens no product.

## Module boundaries

The dependency direction is one way:

```text
application composition
    -> aim science
        -> shared field/material/authority values
    -> product Adapter
        -> workstation placement

external benchmark cases -> installed root Interface
production -X-> examples
workstation -X-> solver products
shared values -X-> aim consumers
```

- `science/metalens/` owns the metalens brief, domains, choices, proof,
  evidence interpretation, aperture realization, focus, and conclusion.
- `field/` owns only cross-aim field values and qualified numerical
  realizations. `field/rectilinear.py` owns raw rectilinear plane geometry;
  `field/reference_surface_formation.py` owns qualified all-or-nothing batch
  formation onto one common uniform grid. Neither expands the six-name Field
  root Interface.
- `materials/` owns material language and response contracts.
- `solvers/lumerical_fdtd/` owns product discovery, qualification, capacity,
  native project execution, artifacts, raw observation, and cleanup. It
  preserves actual reference-surface coordinates and owns no interpolation or
  uniform-spacing policy. Its periodic construction also owns the bounded
  structure-aware time budget and closes it from native termination evidence;
  neither science nor a caller supplies solver femtoseconds.
- `workstation/` owns local topology, lanes, memory limits, and process-tree
  containment without knowing science or a solver product.
- The external `examples` layer owns the four metalens benchmark cases. Behind
  their one selection-and-compare Interface, published reference remembers,
  benchmark alignment explains, comparison contract permits, and typed
  benchmark Result measures observe. The layer is absent from the built wheel.

Deep execution Modules remain where deleting one would scatter a real policy
across callers: `AuthoritySession`, `StudyFrontier`, `WorkExecution`,
`PeriodicBatchExecution`, `Session`, `SessionPool`, `RunDirectory`, and
`WorkRecord`. They are not generalized into a runner, dependency container,
registry, or lifecycle framework.

`periodic_reference_surface_response` proves only that a transmission or
polarization solve embeds a reference surface from that same solve. There is
no independent reference-surface request/work/admission lifecycle. The Adapter
persists the existing `ProjectExecution` before observation; an execution-only
artifact is not `WorkRecord`, receipt, evidence, recovery authority, or
scientific state. Observation failure remains the unchanged fault of the
current call, with no new diagnostic schema or sidecar.

These ADR 0019 boundaries are implemented and resolved by Tickets 08.6 and
08.7. Formation owns the qualified numerical transformation; execution
persistence retains only the existing `ProjectExecution` before observation.

The formation Module's fixed 24 by 24 target closes both numerical and system
resource contracts. The earlier 64 by 64 candidate crossed the qualified 1
GiB high-NA vector-field guard; target density therefore cannot be treated as
an interpolation-only concern or exposed as a caller tuning knob.

## State, data, and errors

The scientific data flow is:

```text
exact canonical brief document -> brief -> compile_study -> immutable Study
      -> admitted period domain -> content-addressed consultation request
      -> validated external answer -> provider-free period advice
      -> deterministic period choice
      -> admitted height domain [+ propagation phase envelope]
      -> content-addressed height consultation request
      -> validated external answer -> provider-free height advice
      -> deterministic height choice
      -> conduct -> admitted evidence -> recompiled Study
      -> admitted Result
      -> external MetalensBenchmarkCase.compare

same-solve raw rectilinear surface
      -> qualified uniform batch formation
      -> existing Field values
```

`Study` is the complete immutable scientific state. `StudyFrontier` owns its
ordered private checkpoints; `AuthoritySession` owns observed-revision
admission; product work owns permits, receipts, and cleanup. No mutable
workflow object or parallel authority exists.

Generic `Study` restoration preserves each advice subtree as opaque canonical
structure. It does not import an aim's advice class and does not require
provider, status, prompt, or transport fields. Metalens science owns strict
period and height restoration and interpretation. Their distinct public
shells share one private closed-record implementation for structural
validation, indexed restoration, and exact-byte proof; each shell still owns
its schema, physical quantity, document keys, stable faults, and, for height,
the optional envelope reference. The shared consultation module owns only
closed request and answer values; each metalens question owns its grounds,
legal candidates, answer validation, advice document, and deterministic
choice. This shared shape does not create a generic choice framework or erase
the period-before-height dependency.

`MetalensEvidence.recompile` is the sole advice replay Interface. It proves
period before height by requiring the retained document's Authority admission
and exact fetched bytes, restoring the current domain and propagation-only
envelope, and re-forming every closed research-mode question. Exactly one
request identity must match. Replay reconstructs the retained recommendation
or evidence requirement through the same question-owned acceptance rules; only
a regenerated byte-identical advice value reaches the pure compiler. This proof
is read-only and the later finding path does not authenticate advice again.

Expected scientific absence is returned as typed values. Period and height
choice operations return a choice or `Finding`; invalid and unsupported
briefs return their typed outcomes. Stale references, malformed documents,
wrong runtime types, impossible ordering, unexpected external envelopes,
product faults, and cleanup faults raise directly. No caller classifies
exception text. A task-scoped external absence is an `UNAVAILABLE` finding;
its one inline reason is diagnostic only. Scientific `REFUSAL` findings do
not retry.

The repository-owned `skills/metacraft-design/SKILL.md` is the sole behavioral
guide for an external harness. Codex and Claude Code discover that same file
through byte-identical project routers. The skill drives the installed command;
production science imports neither the command nor skill files, and MetaCraft
contains no model transport, harness detector, plugin, or second lifecycle.
Acceptance support closes those two real external conventions into the fixed
acceptance-only tuple `CodexAcceptanceProfile(), ClaudeAcceptanceProfile()`.
Each concrete profile owns its native preflight, capsule overlay, environment,
invocation, event dialect, command envelope, and explanation; the shared test
runner owns confinement, redaction, scientific inspection, classification,
sealing, and reporting. This is neither a production harness Adapter nor an
extension registry.
The runner collects both profile preflights before claiming one absent evidence
root, retains all eight planned cells, starts only eligible cells at most once,
and records unavailable profiles without synthetic session artifacts. Its
blind and post-hoc manifests close one partial campaign without an overall pass
or winner. Historical correction records remain immutable provenance verified
read-only; the active runner owns only fresh campaign writing.

The metalens brief owns one strict decoder paired with its canonical encoding.
It rejects missing, unknown, duplicate, mistyped, and non-canonical document
structure before compilation without repairing wording or scientific values.
`compile_study` remains the owner of `InvalidBrief` when a structurally exact
brief still lacks a required scientific fact. Material-family clarification
belongs to the material-library boundary: it can frame one exact registered
candidate as a confirmation question, but cannot search, rank, rewrite, or
apply that candidate to the brief.

## Stability rule

Scientific growth happens behind the three installed entries and four
Authority verbs. A new aim, method, control strategy, solver, material source,
evaluator, or optimizer must not require a Rust change. Rust changes only for
an authority invariant, storage-integrity defect, protocol defect, ABI defect,
or security defect.

The architecture stops when accepted ADRs, these boundaries, behavioral
tests, deterministic gates, and the separately approved Native gate agree.
Another abstraction is justified only by a concrete second variation or a
named contradiction in ownership, dependency, state, contract, error, or
evidence.
