# Canonical Specification — Seal MetaCraft without widening it

Status: resolved (2026-07-29)

Baseline: local `main` at `eb696a5`

## Context

MetaCraft has reached its intended large-scale division:

- Rust owns workspace truth, integrity, revision, capacity, permits, receipts,
  and closure.
- Python compiles scientific intent, coordinates admitted facts, and realizes
  ready scientific tasks.
- Metalens science owns period, height, phase, aperture, and focus.
- Field owns component fields, qualified Torch propagation, and field
  evidence storage.
- The Lumerical Adapter owns product qualification, native construction,
  sessions, observations, and product-specific failure translation.
- Workstation owns local topology, placement, and containment.
- Local composition connects these Modules explicitly without creating a
  second scientific vocabulary.

The architecture is already acyclic, evidence-led, and frozen at its major
seams. A final static review found six local residues: three exact defects and
three small deepening opportunities. They can be resolved without changing
Rust, physics, public lifecycle, or canonical brief content.

## Problem

### One execution fact has three decoders

`ExecutionRecord.from_mapping` already owns strict execution-record decoding.
Propagation and geometric artifact restoration duplicate the same field
parsing inside `sweep.py`. A contract change can therefore drift across three
implementations.

### Product wording can become durable science wording

`open_engine` currently places arbitrary `LumApiError` text in
`LumericalUnavailable.reason`. The local application records that reason in an
admitted diagnostic. Product wording is unstable and must not become durable
domain data.

### One implementation has no caller

`_complex_mapping` is defined in `sweep.py` and used nowhere.

### Current-revision contention has two owners

`authority/work.py` and `lumerical_fdtd/dispatch.py` independently implement
the same bounded optimistic decision loop.

### Available science names one aim's consultations

Generic `AvailableScience` carries `period_advice_reference` and
`height_advice_reference` beside its advice sequence. The parallel fields
split one consultation across two places and leak current metalens claim names
into a generic fact carrier.

### Ordinary quantization refusal is classified from exception text

`assess_phase_sets` catches `ValueError`, parses two string prefixes, and
converts them into `QuantizationRefusal`. Candidate shortage and coverage
shortage are expected formation answers, not exceptional faults.

## Principles

### One fact, one owner

Execution records decode in `ExecutionRecord`. Current-revision contention
resolves in one private Python authority Module. A document-bearing advice
record has one canonical document from which its exact reference is derived.

### Product text stops at the Adapter

Callers receive a stable reason. The original product exception remains
available through exception chaining for debugging, but never enters a
Finding, checkpoint, or diagnostic document.

### Expected answers return; broken invariants raise

A phase set or a quantization refusal is an ordinary scientific answer.
Malformed libraries, impossible values, and implementation drift still raise.

### Difference descends, commonality rises

Metalens compilers interpret period and height advice. Generic science keeps
one advice sequence without naming metalens claims. The checkpoint may retain
its current metalens byte shape without forcing those claim names into
`AvailableScience`.

### Delete before abstracting

Dead implementation is removed. No registry, framework, compatibility surface,
or speculative aim support is added.

## Architecture

### Lumerical execution records

The only execution-record decoder is:

```text
ExecutionRecord.from_mapping
```

Both:

```text
PropagationObservation.from_mapping
GeometricBasisObservation.from_mapping
```

delegate their nested execution value to that owner. They continue to own
their scientific response validation and canonical whole-observation
round-trip checks. A malformed nested execution record is chained beneath the
existing propagation- or geometric-artifact error; decoder reuse does not
leak a new caller-visible error surface.

### Native product absence

The native session-open path becomes:

```text
LumApiError
  -> internal chained cause
  -> LumericalUnavailable("native_product_unavailable")
  -> local diagnostic
  -> honest waiting Study
```

Other already canonical reasons such as `license_unavailable`,
`capacity_not_positive`, and `license_utility_not_found` retain their meaning.
No caller parses exception text.

### Current decisions

A private Module:

```text
authority/_decision.py
```

owns:

```text
decide_current(authority, proposal)
```

The operation:

1. observes the current Authority revision;
2. calls the existing public `decide`;
3. retries only `revision_mismatch`;
4. waits one millisecond after every mismatch, including the final mismatch;
5. returns the first non-mismatch Decision;
6. raises `authority_contention` after 32 attempts.

It is not exported from `authority.__all__` and adds no method to `Authority`.
`_WorkAuthority` and `LumericalDispatch` call this one operation.

### Advice identity, admission, and adoption

`AvailableScience` retains its one existing advice sequence:

```text
advice
evidence
capabilities
bindings
findings
```

It no longer exposes:

```text
period_advice_reference
height_advice_reference
```

No property, alias, alternate constructor, or compatibility shim preserves the
removed fields.

`PeriodAdvice`, `HeightAdvice`, and `DesignAdvice` keep their existing value
shapes. No admission state is added to an advice dataclass.

Where metalens science needs the identity of a period or height consultation,
it derives:

```text
reference_for(advice.document().to_bytes())
```

This `Reference` names immutable bytes; deriving it does not claim those bytes
have been admitted. The local consultation operation still admits the document
before adding the advice to `AvailableScience`, and verifies the returned
reference equals the derived reference. Replay begins from an Authority
reference and fetches the exact document before restoring advice. Rust
therefore remains the admission gate.

`DesignAdvice` has no canonical Authority document and receives no synthetic
reference.

`compile_study` and `compile_metalens` continue to accept one advice sequence.
The metalens compiler alone interprets concrete advice types:

- one Authority-recorded `PeriodAdvice` supplies the `period_choice`
  consultation;
- one Authority-recorded `HeightAdvice` supplies the `height_choice`
  consultation;
- ordinary `DesignAdvice` remains reviewable Study advice but supplies no task
  consultation.

Choice operations receive the advice record, not a parallel reference
parameter. They derive its exact document reference, verify that reference is
the ready task's consultation, and then produce `AdvisedPeriod` or
`AdvisedHeight` as the choice basis.

Authority admission and scientific adoption remain distinct:

```text
recommend -> admit -> choose
```

The admission proves identity only. `PeriodChoice` or `HeightChoice` alone
records that a validated recommendation became a scientific basis.

### Checkpoint and replay

The checkpoint's current advice projection remains:

```text
advice:
  period: <reference or null>
  height: <reference or null>
```

Checkpoint writing derives exact references from the concrete period and
height advice documents and projects them into that existing shape. Authority
checkpoint admission proves every projected reference exists. Replay fetches
each referenced document and restores its advice record into the one advice
sequence.

Ordinary `DesignAdvice` is not projected into the period/height checkpoint
slots and receives no fabricated admission during replay.

There is no second document shape, version key, legacy decoder, or migration.
A future implemented aim must make a separate schema decision when it has
real consultation requirements.

### Quantization answers

The private phase-set operation becomes:

```text
_attempt_phase_set(...) -> PhaseSet | QuantizationRefusal
```

It returns `QuantizationRefusal` for exactly:

```text
cell_library_insufficient
cell_library_coverage_inadequate
```

`levels`, `available_cells`, and `required_cells` remain separate arithmetic
facts. The reason contains no embedded level suffix.

`assess_phase_sets` gathers returned answers without catching or parsing
ordinary refusal exceptions. `form_phase_sets` retains its current public
meaning: it returns every successfully formed 8-, 12-, and 16-level phase set.
Unexpected invalid state raises directly.

## Interface contract

### Stable

- Rust and its four verbs are byte-for-byte and source-for-source unchanged.
- `Authority.check`, `view`, `fetch`, and `decide` keep their Python meaning.
- `compile_study`, `conduct`, `form_phase_sets`, and `assess_phase_sets` keep
  their operation meaning.
- `Study`, evidence, result, periodic response capability names, physical
  policy, and brief content remain unchanged.
- The checkpoint schema and advice projection remain unchanged. Newly emitted
  quantization-refusal reasons deliberately omit the redundant level suffix.

### Deliberately changed

- `AvailableScience` keeps its single `advice` field and removes the two
  metalens-specific reference fields.
- Period and height choice operations no longer accept a parallel advice
  reference parameter.
- No advice dataclass, canonical advice document, Study encoding, or Study
  identity changes.
- New native session-open diagnostics use
  `native_product_unavailable`.
- `QuantizationRefusal.reason` contains a stable reason without an embedded
  `:<levels>` suffix.

No compatibility surface is authorized for these deliberate changes.

## Data flow

### Advice

```text
provider consultation
  -> immutable Advice
  -> canonical document reference
  -> Rust admission
  -> AvailableScience.advice
  -> metalens compiler validation
  -> Study advice + exact task consultation
  -> PeriodChoice or HeightChoice basis
```

`DesignAdvice` follows only the ordinary path from provider consultation to
Study advice; it never enters admission or task identity.

### External absence

```text
native product exception
  -> Adapter-owned stable absence
  -> admitted diagnostic
  -> typed Finding
  -> waiting Study
```

### Quantization

```text
fixed-height cell library
  -> attempt 8
  -> attempt 12
  -> attempt 16
  -> PhaseSetFormation(phase_sets, refusals)
  -> branches only for formed phase sets
  -> complete formation report for every refusal
```

## State management

- No mutable workflow state is added.
- Advice records remain unchanged and immutable. `AvailableScience`,
  `PhaseSetFormation`, and `QuantizationRefusal` remain immutable.
- At most one period advice and one height advice can inform one metalens
  Study.
- Local execution admits advice before adding it to available science; replay
  restores advice only from fetched Authority documents.
- Rust rejects downstream structured admission if a derived consultation
  reference does not exist.
- Checkpoint replay reconstructs the same advice records from one Authority
  snapshot.
- Optimistic retry observes a fresh revision per attempt but stores no retry
  state.

## Error handling

| Condition | Behaviour |
| --- | --- |
| Nested execution mapping is malformed | Existing strict decoder error |
| Native Lumerical session cannot open | `native_product_unavailable` |
| Revision changes before admission | Bounded retry |
| Revision mismatches 32 times | `authority_contention` |
| Period or height advice is duplicated | Invariant error |
| Authority returns a reference unlike the canonical advice reference | Invariant error |
| Downstream structure cites advice absent from Authority | Rust rejection |
| Too few cells for one quantization | Returned refusal |
| Phase coverage cannot establish one quantization | Returned refusal |
| Malformed library or impossible phase state | Raise directly |

No new exception hierarchy is introduced.

## Naming

Names follow one mental order:

```text
decide_current
reference_for
_attempt_phase_set
QuantizationRefusal
native_product_unavailable
```

They name behaviour or domain meaning. No `manager`, `helper`, `utils`,
numbered module, provider-shaped scientific name, or compatibility name is
added.

## Documentation

- Clarify advice identity, Authority admission, and scientific adoption in
  `CONTEXT.md`.
- Update `SCIENCE.md` to describe derived advice references and returned
  quantization refusals.
- Do not add or modify an ADR. This effort implements ADR 0013 and ADR 0014;
  it does not reverse or extend their system decisions.
- Do not rewrite closed tickets.

## Ticket order

1. [Let one native record speak once](issues/01-let-one-native-record-speak-once.md)
2. [Let one current decision resolve contention](issues/02-let-one-current-decision-resolve-contention.md)
3. [Let advice own one identity](issues/03-let-advice-own-one-identity.md)
4. [Let each quantization answer directly](issues/04-let-each-quantization-answer-directly.md)

One ticket produces one commit. Implementation starts only after owner review
changes all four tickets to `ready-for-agent`.

## Verification strategy

Verification is local.

Each ticket runs only its listed focused tests or exact test nodes. Each ticket
also runs:

- Pyright over touched Python scope;
- CSU over touched production files;
- `git diff --check`;
- `git diff -- rust`, which must be empty.

The following are explicitly prohibited:

- the complete Python test suite;
- the complete architecture suite;
- Rust tests, formatting, Clippy, builds, or manifest generation;
- 304-, 1,504-, or 3,004-event diagnostics;
- maturin or native extension builds;
- Adviser, live Lumerical, canonical delivery, or four-brief tests.

If a focused seam cannot pass without widening scope, implementation stops and
reports the conflict. Unrelated defects are recorded but not fixed.

## Cleanup

After all four tickets and commits satisfy their local gates, delete only the
approved generated paths listed in `map.md`. Before recursive deletion, resolve
every absolute target and confirm it remains under the repository root.

Cleanup is not a fifth implementation ticket and does not modify tracked
source. Preserve the two unrelated Claude worktrees and every protected path.

## Trade-offs

- Advice remains free of lifecycle state, so Study canonical bytes and
  identities do not drift. The local application and Rust Authority enforce
  admission order; the pure compiler derives identity without pretending to
  observe Authority state.
- The generic carrier stays small, while the metalens compiler retains the
  concrete type knowledge needed to form exact consultation references.
- Checkpoint bytes remain metalens-shaped for now. Generalizing them before a
  second aim exists would create a hypothetical seam and a migration burden.
- A 32-attempt retry remains a small fixed application policy. Making it
  configurable would expose operational policy without a demonstrated need.
- Refusal reason strings remain exact data labels rather than a new enum or
  exception tree. Their arithmetic context lives in typed fields.
- The effort accepts a few large deep Modules. It removes duplicated
  responsibility rather than splitting files by length.

## Prohibited additions

Do not add:

- any Rust change;
- a new public Authority operation;
- a retry class, configuration field, database, or daemon;
- a compatibility alias for `AvailableScience`;
- `AdviceFact`, `AdmittedAdvice`, an advice registry, or a schema registry;
- a second checkpoint shape;
- a quantization exception hierarchy;
- a solver-neutral Adapter framework;
- new science, physics, brief content, or live execution;
- cleanup outside the approved whitelist.

## Completion

The effort is complete when:

1. all four tickets are resolved in order;
2. each ticket's focused tests pass;
3. touched Python scope passes Pyright and CSU;
4. `git diff --check` is clean;
5. `git diff -- rust` is empty;
6. `CONTEXT.md`, `SCIENCE.md`, code, and tickets agree;
7. the workspace is cleaned through the exact approved whitelist;
8. the only remaining untracked user paths are preserved;
9. canonical brief revision remains queued for the next design grill.

The intended final couplet is:

```text
one fact, one owner;
one answer, one form;
product words stop;
scientific truth remains.
```

## Closure

The four tickets closed in order:

```text
fbcbb56  Let one native record speak once
82dc28b  Let one current decision resolve contention
7f40af9  Let advice own one identity
d44a11f  Let each quantization answer directly
```

Each ticket passed its focused tests, touched-scope Pyright and CSU gates,
diff hygiene, and the frozen-Rust check. Final Standards review found no
violation or smell. Final Spec review found only the pending generated-path
cleanup; the approved whitelist was then removed and verified absent.

No full suite, Rust verification campaign, native build, live Adviser,
Lumerical execution, canonical delivery, or brief revision ran. The protected
Claude worktrees and user-owned untracked paths remain untouched.
