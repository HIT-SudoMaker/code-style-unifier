# Let Python accept only what Rust can say

Type: implementation

Status: resolved (2026-07-29)

Blocked by:
[Let one audit remember one generation](01-let-one-audit-remember-one-generation.md).

## Outcome

The Python authority Adapter accepts every valid Rust response and rejects
every shape, order, relation, or coercion Rust cannot emit.

## Scope

1. Add mutation tests around real Rust fixtures before changing decoders.
2. Validate revision as root or an exact canonical hash.
3. Validate Current order and uniqueness exactly as emitted by Rust.
4. Validate admitted decision and permit order, uniqueness, references, and
   relation to current values.
5. Validate Decision cross-field invariants for admitted and rejected
   outcomes, including revision movement and required references.
6. Replace raw `CheckReport.values` and `bool()` coercion with an exact typed
   decode of the Rust check schema.
7. Reject missing, surplus, wrongly typed, duplicate, or relationally
   impossible values.
8. Align the paired view and decision schema constant names while this Module
   is already being changed. Do not start a wider naming sweep.

## Acceptance

- Every current golden Rust response round-trips without changed bytes or
  meaning.
- `"false"` cannot become a true workspace-valid report.
- An admitted Decision without its required references is rejected.
- A rejected Decision cannot advance revision or carry admitted-state
  references.
- Duplicate or unsorted Current, Permit, or admitted-decision values are
  rejected when Rust would never emit them.
- No decoder fills defaults, coerces scalar values, repairs order, or accepts
  legacy spelling.
- Public authority semantics remain unchanged.

## Focused tests

- real Rust view, decide, and check fixtures;
- one mutation per field type, missing key, surplus key, order, duplicate, and
  cross-field invariant;
- root and hash revision forms;
- valid admitted and rejected decisions;
- malformed check findings, hashes, counts, protocol, schema, and validity.

## Verification

- focused authority tests;
- authority architecture tests;
- Pyright;
- touched-file CSU;
- production Rust diff is empty;
- fixed-range `git diff --check`.

## Stop and report

Stop before changing Rust output, canonical bytes, public authority verbs, or
finding meaning.

## Do not add

Do not add Pydantic, a schema registry, a compatibility decoder, aliases,
coercion helpers, or a second protocol package.

## Resolution

Python now decodes the exact public revision, view, decision, permit, and
check shapes emitted by Rust. It rejects coercion, impossible cross-field
relations, repaired ordering, invalid proposal references, and inconsistent
workspace validity while preserving Rust's chronological decision order.

Repeated record and Current decisions remain valid because Rust can admit the
same proposal more than once. Single-use permit, receipt, and close decisions
retain their stricter uniqueness and ordering constraints.

The closure pass also fixes the normalized UTC expiry spelling, verifies the
canonical metadata hash of every proposal reference, limits rejection findings
to Rust's public vocabulary, and indexes Current chronology once per view.

Verification completed with 194 focused authority tests, 36 authority-facing
architecture tests, project Pyright at zero errors and warnings, touched-file
CSU at zero blocking findings, an empty production Rust diff, and a clean
fixed-range diff check.
