# Metalens benchmark proof

Status: resolved (2026-08-06)

## Context

MetaCraft owns exactly four external `MetalensBenchmarkCase` values. Together
they cover propagation phase and geometric phase at low and high numerical
aperture:

| Numerical-aperture regime | Propagation phase | Geometric phase |
| --- | --- | --- |
| low NA | Yun 2025 | Yang 2018 |
| high NA | Arbabi 2015 | Khorasaninejad 2016 |

The cases already share one container shape: a blind brief, published
platform, published comparison, fidelity, and fidelity notes. ADR 0018 keeps
that published truth outside production and freezes one behavioral entry:

```python
case.compare(completed_results) -> tuple[MetalensBenchmarkComparison, ...]
```

The sealed implementation can produce a bounded `3 + 3 + 1 + 1` Result
contract through real Result and evidence Interfaces. Those compact
method-family representatives are not the four exact paper-scale benchmark
outcomes. Exact case briefs can enter public conduct through recorded replay,
but a fresh create-only root honestly stops at the first missing replayed fact.

## Problem

The current case shape is structurally uniform but its comparison language is
not yet strong enough for a scientific benchmark:

- `PublishedComparison.measures` contains free-form strings, so spelling can
  drift and two cases can name the same quantity differently;
- a `PublishedMetric` names value, unit, scope, and paper label, but not the
  measurement definition needed to decide whether a MetaCraft value is
  numerically comparable;
- `MetalensBenchmarkComparison` places period and height advice beside paper
  context, but it does not restore the admitted Result's selected geometry or
  Focus evidence and therefore computes no endpoint difference;
- absent, method-inapplicable, and definition-incompatible measurements have
  no distinct representation;
- the current post-seal ticket proves cadence and identity, but it could pass
  without answering whether the blind design resembles the reviewed platform
  or whether the realized field differs because of phase, transmission,
  polarization conversion, sampled reference surfaces, or propagation.

Running parameter sweeps before these meanings are fixed would spend solver
work without a diagnostic question. Treating paper agreement as a universal
pass threshold would be equally wrong: the four cases have different fidelity
claims, and paper efficiency definitions may differ from MetaCraft's explicit
incident-power normalization and focal bucket.

## Principle

The benchmark follows six rules:

1. **One case shape, several honest physics paths.** Every case speaks one
   comparison contract; low/high NA and propagation/geometric phase retain
   their distinct applicability and evidence.
2. **Blind first, published second.** Production receives only the blind
   brief. Published platform facts are read only after exact matching
   `CompletedResults` exists.
3. **Definition before difference.** A numerical delta exists only when
   measure, unit, scope, normalization, and measurement definition agree.
4. **Observation is not acceptance.** Agreement or disagreement is a
   comparison result, never a hidden compiler constraint or scientific
   completion threshold.
5. **Bracket before drilling.** First compare the design and field endpoints;
   then isolate model assumptions; only a located discrepancy may select an
   intermediate response sweep.
6. **One deep external Interface.** The case continues to own one comparison
   operation. No benchmark runner, suite, registry, workflow, or production
   benchmark meaning is introduced.

## Architecture

### Uniform case contract

Each case retains these exact responsibilities:

```text
MetalensBenchmarkCase
├── name                  stable external identity
├── brief                 blind production input
├── published_platform    reviewed design-end truth
├── published_comparison  reviewed field-end truth
├── fidelity              strength of the reproduction claim
└── fidelity_notes        explicit exclusions and interpretation limits
```

Uniformity does not require every paper to publish every quantity. It requires
every present quantity to use one typed name and every absent or incompatible
quantity to be reported explicitly.

The proposed external comparison vocabulary is one `BenchmarkMeasure` enum.
It replaces free-form measure strings and covers the existing reviewed
questions:

```text
cell period
atom height
lateral geometry
phase coverage
transmitted magnitude
transmitted power
spatial phase sampling
orientation relation
polarization conversion
focus efficiency
focal shift
x half-maximum width
y half-maximum width
mean half-maximum width
vertical-cut half-maximum width
transmitted fraction
focused fraction
complex focal field
longitudinal power fraction
```

Mathematical component names such as `x`, `y`, and `z` remain values within a
complex-field comparison; they do not create per-component benchmark types.

Every quantitative `PublishedMetric` gains one required natural-language
`definition` and one primary-source locator accepted through Ticket 01's
Research Record. The definition states the normalization, integration region,
and other conditions needed to judge comparability. `scope` continues to name
the paper device or population to which the value applies. A qualitative
measure remains a typed measure without a fabricated numeric value.

### One comparison disposition

Each requested field measure returns exactly one disposition:

| Disposition | Meaning |
| --- | --- |
| `comparable` | Both sides use compatible measure, unit, scope, normalization, and definition; a signed difference may be reported. |
| `context only` | Both sides carry useful values or observations, but their definitions do not support a numerical delta. |
| `not reported` | MetaCraft calculated the measure but the reviewed paper case carries no corresponding value. |
| `not applicable` | The measure does not belong to this case's method, such as a longitudinal vector-field measure for a low-NA componentwise result. |

A malformed Result, missing admitted body, wrong case identity, non-finite
value, or contradictory definition is a fault and raises directly. It is not
converted into one of these dispositions.

### Deepened comparison Interface

The proposed case Interface is:

```python
case.compare(
    completed_results,
    *,
    fetch,
) -> tuple[MetalensBenchmarkComparison, ...]
```

`fetch(reference) -> bytes` reads immutable admitted evidence. The installed
path uses `Authority.fetch`; focused tests use an in-memory exact-reference
reader. These are two real Adapters at one read-only seam. The case hides
Result restoration, metric projection, published-definition matching, and
comparison formation behind its one operation.

This replaces rather than layers over the current comparison Interface. No
compatibility overload, `compare_with_evidence`, reader wrapper, or second
behavior is added. Within this six-ticket feature, the public behavior of
`conduct`, `CompletedResults`, Result schemas, production
`FocalFieldComparison`, root exports, Authority verbs, and Rust remains
unchanged. The review diff also contains the separately approved, preceding
Sonnet maintenance pass that removed the duplicate `known` Study parameter
and moved periodic-response ownership to its canonical Interface; that pass
preserves the public cadence and is not benchmark behavior.

ADR 0018 originally froze the no-`fetch` signature and the earlier comparison
fields. Tickets 01 and 02 established the paper definitions, accepted the
**Benchmark ownership** amendment, and completed the intentional Interface
cutover before the two-track Ticket 03 proof.

### Design-end comparison

Every comparison reports, without pass/fail thresholds:

- blind period advice, selected cell period, and published period;
- blind height advice, selected atom height, and published height;
- selected typed lateral geometry or selected range beside the published
  dimensions;
- fabrication step, lattice difference, fidelity, and exclusions needed to
  interpret the comparison;
- phase coverage and useful/leakage power when they belong to the Result.

An unpublished paper geometry remains absent with an explicit fidelity note;
it is never inferred from MetaCraft's selection. A published hexagonal lattice
does not silently become a production constraint when the blind case asks
only for the reviewed device class.

The current reviewed anchors remain unchanged:

| Case | Published period | Published height | Published lateral geometry |
| --- | ---: | ---: | --- |
| Yun | 400 nm | 800 nm | unpublished response table |
| Yang | 1500 nm | 340 nm | ellipse, 480 by 1350 nm |
| Arbabi | 800 nm | 940 nm | diameter 200–550 nm |
| Khorasaninejad | 325 nm | 600 nm | rectangle, 95 by 250 nm |

### Field-end comparison

All completed Results expose one fixed report frame. Applicability and paper
availability determine the disposition, not the presence or absence of a
dictionary key. The frame covers:

- focal shift;
- separate x/y half-maximum widths and a derived mean only when its definition
  matches the paper quantity;
- transmitted fraction, focused fraction, and focus efficiency as distinct
  meanings;
- phase coverage or polarization conversion as appropriate;
- high-NA complex x/y/z field errors, plus longitudinal field fraction only
  when exact admitted evidence establishes that distinct quantity;
- paper values and signed differences only for `comparable` measures.

The reviewed quantitative anchors remain external truth:

| Case | Reviewed quantitative context |
| --- | --- |
| Yun | simulated focus efficiency 0.828 |
| Yang | measured focus efficiency 0.26; theoretical focus efficiency 0.60 |
| Arbabi | reported maximum family focus efficiency 0.82 |
| Khorasaninejad | measured focus efficiency 0.73; measured vertical-cut FWHM 375 nm |

These values do not become Result acceptance thresholds. Arbabi's family
maximum, for example, is context-only unless its scope and normalization match
the compact plane-wave Result.

### Two honest proof tracks

```text
exact catalogue/cadence track
    -> select four exact cases in stable order
    -> conduct(case.brief, distinct fresh application root)
    -> typed WaitingStudies at the first absent recorded fact
    -> no partial Result and no comparison

bounded Result-contract track
    -> form compact low/high-NA propagation/geometric representatives
    -> admit and restore real Result/evidence documents
    -> CompletedResults in the exact 3 + 3 + 1 + 1 method-family shape
    -> representative.compare(..., fetch=authority.fetch)
    -> design-end + field-end contract comparisons
```

Published values do not enter consultation, compilation, evidence gathering,
selection, aperture formation, propagation, focus, or Result admission. A
runtime ratchet must prove that no published case field is read before
`CompletedResults` exists.

The two tracks must never be spliced into a false end-to-end claim. A bounded
representative has a distinct case identity and an explicit fidelity note; it
does not prove that `conduct(exact_case.brief)` returns a paper-scale Result.
The exact case receives a comparison only after a separately admitted exact
Result exists, such as an approved live Result from Ticket 06.

### Assumption isolation

Only after both endpoints are reported may the diagnostic proof form controlled
field variants from the same aperture, sampling, distance, and normalization.
No variant changes the admitted scientific Result.

Propagation-phase variants are:

| Variant | Amplitude | Phase | Diagnostic meaning |
| --- | --- | --- | --- |
| `ideal continuous` | unity | continuous target | optical upper reference |
| `assigned target` | unity | quantized or pointwise assigned target | assignment or quantization |
| `realized phase` | unity | selected cell phase | periodic phase error |
| `realized coefficient` | selected useful amplitude | selected cell phase | amplitude and phase together |
| `sampled surface` | admitted complex surface | admitted complex surface | high-NA surface and vector effects |

Geometric-phase variants are:

| Variant | Response | Diagnostic meaning |
| --- | --- | --- |
| `ideal pb` | ideal conversion with analytic PB phase | optical upper reference |
| `assigned orientation` | actual finite or continuous orientations with ideal conversion | orientation assignment |
| `realized jones` | admitted converted and retained Jones coefficients | conversion and leakage |
| `sampled surface` | admitted x/y reference surfaces | high-NA surface and vector effects |

Not every representative uses every variant. Low-NA propagation retains
finite phase levels; low-NA geometric retains finite orientation sets;
high-NA propagation remains pointwise; high-NA geometric retains continuous
PB orientation. A diagnostic must return `not applicable` rather than
manufacture a quantization that the method does not own. These results do not
become exact paper-case claims.

### Discrepancy-directed sweep

The next investigation is selected by the first divergent comparison:

```text
design end diverges
    -> inspect period/height advice, material binding, and fabrication domain

ideal field diverges
    -> inspect aperture, propagation, focus evaluation, and metric definition

assigned target agrees; realized phase diverges
    -> inspect phase coverage, candidate density, and selection

realized phase agrees; realized amplitude diverges
    -> inspect transmission or polarization-conversion power and leakage

coefficient field agrees; sampled surface diverges
    -> inspect reference-surface formation, sampling, and vector propagation

both endpoints agree
    -> open no additional response sweep
```

Recorded evidence is inspected first. A live Lumerical sweep requires a
separate human gate, fixed candidate/solve bounds, and one named discrepancy.
Geometric orientation is analytic after one anisotropic cell is admitted; it
never creates orientation-specific solver work.

## Error and state contract

- `CompletedResults` from another brief raises
  `metalens_benchmark_brief_mismatch`.
- A foreign Result, evidence reference, or fetched body raises directly.
- Missing recorded external response remains the existing typed unavailable
  conduct outcome; it is not a partial comparison.
- A Result that is completed but lacks required focus or fabrication evidence
  is malformed and raises.
- Definition incompatibility returns `context only`; missing paper values
  return `not reported`; method inapplicability returns `not applicable`.
- No benchmark state becomes current Authority truth. Comparisons are external
  immutable documents citing exact Result and case identities.
- Each exact cadence attempt owns one fresh application root. Bounded
  representative groups own distinct Authority roots. Neither track shares
  Authority truth, fetched bodies, Results, or comparison documents.

## Delivery tickets

1. **Let published measures state their exact meaning** — verify the paper and
   supporting-information definitions in one reviewed Research Record.
2. **Let four benchmark cases speak one contract** — approve the ADR 0018
   amendment and implement the typed, evidence-reading comparison Interface.
3. **Let blind cases bracket design and result** — prove the exact four-case
   catalogue reaches the honest typed replay boundary, then separately prove
   the bounded `3 + 3 + 1 + 1` method-family Result/comparison contract.
4. **Let field assumptions reveal their bias** — form controlled variants
   only from the bounded representatives, without changing admitted Results
   or claiming exact paper-scale outcomes.
5. **Let discrepancies select the response sweep** — inspect only the
   evidence segment selected by the endpoint and assumption comparisons.
6. **Let two corner cases earn live execution** — close with zero execution
   when no exact unresolved comparison earns bounded Live work; any future
   case requires a new exact bounded proposal.

Ticket dependencies are strict. Tickets 01–05 authorized no Native work.
Ticket 06 resolved with zero execution because Ticket 05 established no exact
Live question; the closure grants no standing Native authority.

## Testing decisions

- Interface tests use the same `case.compare(..., fetch=...)` operation as
  callers; they do not test private projection helpers.
- Golden case documents freeze all four revised identities and exact reviewed
  facts after the intentional schema cutover.
- One exact-catalogue test proves stable order, distinct roots, blind conduct,
  typed waiting, and zero partial Results. A separate representative test
  proves Result restoration, the `3 + 3 + 1 + 1` method-family cardinality,
  method-specific high/low-NA evidence, and one comparison per Result.
- A spy proves no published platform or comparison value is consulted before
  `CompletedResults`.
- Metric tests cover all four dispositions and reject invalid combinations.
- Focus efficiency, transmitted fraction, and focused fraction remain distinct
  and cannot be substituted by name or unit alone.
- Low-NA tests never require vector-only comparisons; high-NA tests require
  component-complete complex-field and longitudinal evidence.
- Assumption variants hold aperture, grid, propagation distance, and
  normalization fixed and change exactly one optical assumption at a time.
- Architecture tests keep examples out of production and the built wheel,
  keep one case behavioral entry, and forbid benchmark runners, registries,
  lifecycle wrappers, and compatibility aliases.
- Each ticket runs focused tests, the complete non-live suite, architecture
  tests, Pyright, blocking CSU, canonical round trips, `git diff --check`, and
  the frozen Rust diff.

## Out of scope

- Treating agreement with a paper as scientific completion.
- Whole-device Maxwell or experimental fabrication reproduction.
- Adding a fifth case, optimization, multiwavelength design, or a new metalens
  method.
- Feeding published period, height, geometry, efficiency, or width into
  production selection.
- Changing public `conduct` cadence or behavior, `CompletedResults`, production
  Result schemas, production `FocalFieldComparison`, root exports, Authority
  verbs, Rust, or the periodic vertical layout. This excludes the already
  approved, contract-preserving Sonnet maintenance named above from the
  benchmark feature; it does not reclassify that maintenance as benchmark
  scope.
- Adding a general benchmark framework, runner, suite, registry, workflow,
  result store, or solver Interface.
- Running Adviser or Lumerical before the explicit live ticket is approved.

## Trade-off

The proposed comparison Interface adds one exact read dependency and performs
an intentional external schema cutover. That cost is justified because the
case can then answer a complete benchmark question behind one small Interface.
Keeping the current no-`fetch` comparison would preserve a smaller signature
but leave Result restoration and metric interpretation scattered across every
caller or test.

The uniform report frame deliberately includes `not reported` and `not
applicable` entries. It is more verbose than omitting missing keys, but it
prevents absence, incompatibility, and method scope from collapsing into one
ambiguous state.

## Decision traceability

Ticket 01 recorded the paper measurement definitions, Ticket 02 amended ADR
0018 and cut over the comparison Interface, Ticket 03 recorded the owner-
approved two-track evidence boundary after the exact Yun resource probe, and
Ticket 04 isolated method-family field assumptions through immutable external
diagnostic documents without changing admitted Results. Ticket 05 added one
read-only discrepancy-selection Interface and found only bounded
field-assignment and propagation-phase hypotheses; none justified an exact
Live observation. Ticket 06 consequently recorded zero candidates, solves,
sessions, artifacts, qualifications, Results, and comparisons, and closed
without a product or licence probe. The accepted Research Record, ADR
amendment, this specification, implementation tickets, and Interface tests
form the durable chain.

## Conclusion

The feature stops when four heterogeneous physical cases speak one comparison
contract, exact cadence and bounded evidence remain visibly separate, each
assumption changes alone, and only an observed discrepancy can spend sweep
work.

The exact case asks blindly; absence answers honestly. Representatives test
the contract; only exact evidence may earn a future Live proposal.
