# 02 — Let four benchmark cases speak one contract

Type: decision and implementation

Status: resolved (2026-08-06)

Blocked by: 01 — Let published measures state their exact meaning.

## What to build

Replace the current shallow, advice-only benchmark comparison with one deep
external Interface shared by all four `MetalensBenchmarkCase` values. Keep the
blind brief and reviewed paper truth separate, restore exact admitted Result
evidence through a caller-supplied immutable fetch operation, and return one
uniform design-end and field-end comparison frame.

## Decision requested

After accepting Ticket 01's Research Record, approve an explicit amendment to
ADR 0018's **Benchmark ownership** section:

```python
case.compare(
    completed_results,
    *,
    fetch,
) -> tuple[MetalensBenchmarkComparison, ...]
```

This replaces the frozen no-`fetch` signature; it does not add a second case
method. `Authority.fetch` is the installed Adapter and an exact in-memory body
reader is the focused-test Adapter. No implementation is authorized until
Ticket 01 is resolved and the owner accepts this amendment.

## Requirements

- [x] Replace free-form published measure strings with one typed
      `BenchmarkMeasure` vocabulary from the specification.
- [x] Give every quantitative `PublishedMetric` the accepted measurement
      definition and primary-source locator from Ticket 01 in addition to
      value, unit, scope, and paper label.
- [x] Return exactly one of `comparable`, `context only`, `not reported`, or
      `not applicable` for every requested field measure.
- [x] Compute a signed difference only for `comparable` measures.
- [x] Place exact advised, selected, and published period/height values in one
      design-end comparison without making paper values thresholds.
- [x] Place selected typed geometry or selected geometry range beside the
      published lateral dimensions and retain lattice/fidelity differences.
- [x] Restore Focus, phase-set/cell-choice, and high-NA focal-comparison
      evidence from the exact Result closure through `fetch`.
- [x] Keep focus efficiency, transmitted fraction, and focused fraction as
      three distinct measures.
- [x] Keep low-NA vector-only measures `not applicable`; require complete
      x/y/z and longitudinal evidence for high-NA Results.
- [x] Regenerate and freeze all four case and comparison identities after the
      deliberate external schema cutover; add no compatibility reader.
- [x] Amend ADR 0018 and its navigation relationship explicitly, then update
      `CONTEXT.md` only for accepted durable terms.

## Error contract

- [x] A mixed brief, foreign Result, stale reference, wrong fetched body,
      non-finite metric, or contradictory metric definition raises directly.
- [x] Definition mismatch produces `context only`, not an exception and not a
      numerical delta.
- [x] A missing paper metric produces `not reported`; method inapplicability
      produces `not applicable`.
- [x] Missing recorded external evidence remains the existing typed conduct
      outcome and never forms a partial comparison.

## Architecture constraints

- [x] `MetalensBenchmarkCase` retains one behavioral entry.
- [x] Production never imports examples or published truth.
- [x] `conduct`, `CompletedResults`, production Result schemas,
      `FocalFieldComparison`, Authority verbs, root exports, and Rust remain
      unchanged.
- [x] Add no benchmark runner, suite, registry, workflow, evidence store,
      reader wrapper, optional compatibility overload, or generic framework.

## Verification

- [x] Interface tests exercise only `case.compare(..., fetch=...)`.
- [x] Golden documents cover every case, measure, disposition, and metric
      definition.
- [x] A runtime spy proves no published field is read before exact matching
      `CompletedResults` exists.
- [x] Production-import, wheel-inventory, one-behavior, schema, and naming
      ratchets pass.
- [x] Focused tests, relevant architecture tests, Pyright, blocking CSU,
      canonical round trips, frozen Rust diff, and `git diff --check` pass.
- [x] The final six-ticket gate passed: 1263 non-live tests passed and 6
      explicitly Live or integration tests were deselected.

## Resolution

The revised Interface restores exact admitted evidence through `fetch` and
returns one typed design-end and field-end frame. All six reviewed quantitative
metrics remain `context only` with no signed difference. The Khorasaninejad
`375 nm` value is now a vertical-cut FWHM, not a mean width.
high-NA field ends expose exact x/y/z complex errors, while low-NA field ends
carry none. Through-plane input/output Poynting power is not mislabeled as a
longitudinal field fraction; that measure remains unobserved without exact
evidence. Focused tests pass;
the architecture suite passed 108 tests and reached one unrelated stale tracked
ticket-path failure caused by the concurrent planning cutover.

## Stop condition

Stop when all four current cases serialize and compare through the one revised
Interface and no endpoint benchmark execution has begun. Ticket 02 standardizes
the comparison contract; Ticket 03 exercises it.
