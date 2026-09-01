# Metalens benchmark Sonnet surgery

Status: resolved (2026-08-07)

## Problem Statement

As a MetaCraft maintainer, the user needs the four metalens benchmark cases to
test whether MetaCraft makes scientifically defensible design judgments from
realistic blind briefs. The benchmark must not reproduce a paper by copying its
answer into the input, and it must not let published truth become a production
constraint or Result acceptance threshold.

The current benchmark is close to this goal but is not yet reliable enough for
long-term use. Paper facts, brief-to-paper fidelity, and comparison permission
overlap in broad values. Some paper facts cannot express "not reported" or
"not yet resolved". Tests manufacture representative benchmark cases by
rewriting published truth and repeatedly use an arbitrary 200 nm period.
Comparison code discovers Result meaning through weakly typed object probing,
can form an empty comparable outcome, and catches an error category that does
not match the installed Authority fetch contract. The current four briefs also
do not preserve the approved fabrication assumptions: Yun requires an aspect
limit of 10, while Yang, Arbabi, and Khorasaninejad require 8, without scanning.

There is one additional production ownership defect. Metalens conduct owns the
correct outer orchestration but also contains direct-Debye field construction,
realization restoration, Torch storage crossing, and focal-field comparison.
Those behaviors belong to the existing field-execution Module.

The user needs a bounded architectural surgery that fixes these concrete
defects, remains green throughout implementation, preserves the established
Authority/Science dependency direction, and stops when the approved contracts
are proved. The work must not become another indefinite attempt to make the
code aesthetically "more Sonnet".

## Solution

Keep `MetalensBenchmarkCase` as the single external benchmark seam. A caller
selects one of four immutable cases, reads only its blind brief and identity,
runs the existing production conduct cadence, and gives exact admitted Results
back to the same case for external comparison. No new benchmark runner,
registry, manager, workflow, or production benchmark meaning is introduced.

Inside each case, separate four meanings:

- a published reference owns what the reviewed source reports, derives, does
  not report, or cannot yet establish;
- benchmark alignment owns how each blind brief input or omission relates to
  one published fact;
- a comparison contract alone owns whether each fixed-frame measure permits a
  signed difference, context-only output, non-reporting, or non-applicability;
- typed benchmark Result measures restore only the admitted MetaCraft
  observations needed for comparison.

All four cases use one ordered measure frame and one strict comparable
invariant. A comparable outcome exists only when the MetaCraft observation and
numeric published fact both exist, their measure, unit, scope, normalization,
and definition agree, the required alignment holds, and a finite signed
MetaCraft-minus-reference difference is formed. An unresolved source is
context-only and carries no fallback number. A not-reported source is distinct
and can only form a not-reported outcome.

Implementation uses a private expand-then-contract sequence. The new case
model may coexist with the old model only as unexported feature-branch staging
while each paper is migrated through the complete fact, alignment, comparison,
identity, and test path. After all four cases are complete, the public examples
seam switches once and the old schemas, types, codecs, imports, and fabricated
representative helpers are deleted. No public compatibility reader, alias,
dual writer, or deprecation layer is permitted.

Independently, move the field implementation behavior from metalens conduct to
the existing field-execution Module. Conduct keeps qualification, consultation,
ready-task selection, one-step dispatch, and immutable Study evolution. The
move does not change public conduct, scientific methods, Result schemas,
Authority behavior, solver behavior, or numerical results.

## User Stories

1. As a MetaCraft maintainer, I want one benchmark case Interface, so that a
   benchmark has one obvious entry and no competing workflow.
2. As a benchmark user, I want to select exactly four stable metalens cases, so
   that low/high numerical aperture and propagation/geometric phase remain
   visibly covered.
3. As a benchmark user, I want to see the blind brief without paper answers, so
   that MetaCraft's design judgment is genuinely exercised.
4. As a benchmark user, I want paper truth revealed only after an exact Result
   exists, so that comparison cannot influence production choice.
5. As a scientific reviewer, I want each paper fact to state whether it is
   reported, derived, not reported, or unresolved, so that absence is not
   hidden behind optional fields.
6. As a scientific reviewer, I want every reported fact to carry its exact
   scope, meaning, and primary-source locator, so that the benchmark is
   auditable.
7. As a scientific reviewer, I want every derived fact to retain its source
   inputs and derivation, so that a calculated paper fact is not mistaken for
   a direct report.
8. As a scientific reviewer, I want non-reporting and unresolved research to
   remain distinct, so that "not found" is not rewritten as "not published".
9. As a benchmark author, I want each brief/reference relation declared as
   matched, adapted, independent, withheld, or excluded, so that fidelity prose
   no longer controls behavior.
10. As a benchmark author, I want target-near briefs to be valid without exact
    paper equality, so that realistic workflow testing does not become paper
    reproduction.
11. As a fabrication-aware user, I want Yun's brief aspect limit to be 10, so
    that it reflects the intended process assumption.
12. As a fabrication-aware user, I want the Yang, Arbabi, and Khorasaninejad
    brief aspect limits to be 8, so that each case uses its approved realistic
    process assumption.
13. As a benchmark user, I want aspect limits treated as supplied inputs rather
    than scan variables, so that the benchmark tests design judgment rather
    than an invented optimization study.
14. As a scientific reviewer, I want Yun's selected-device period to remain
    unresolved until a primary source joins it to the selected 800 nm-height
    comparator, so that 400 nm is not presented with false certainty.
15. As a benchmark user, I want every measure to have one explicit comparison
    rule, so that a default branch cannot invent meaning.
16. As a benchmark user, I want every comparison to return the same ordered
    measure frame, so that all four cases are inspectable in one vocabulary.
17. As a scientific reviewer, I want comparable results to contain both values
    and a finite signed difference, so that an empty comparable record is
    impossible.
18. As a scientific reviewer, I want differently defined efficiencies and
    widths to remain context-only, so that unlike measurements are not
    numerically compared.
19. As a benchmark maintainer, I want admitted Result observations restored
    into typed values, so that comparison does not depend on arbitrary
    attributes or string-key probing.
20. As an Authority user, I want missing referenced bodies and storage faults
    to propagate, so that data corruption is not treated as ordinary absence.
21. As a caller, I want wrong runtime types to raise `TypeError`, so that API
    misuse is distinguishable from malformed values.
22. As a caller, I want malformed benchmark and Result values to raise stable
    `ValueError` reasons, so that deterministic tests can identify contract
    failure without parsing arbitrary exception text.
23. As a benchmark maintainer, I want canonical case identity and strict
    restoration, so that a changed or foreign case document cannot be accepted.
24. As a benchmark maintainer, I want all-or-nothing comparison, so that one
    malformed Result cannot leave a partial benchmark artifact.
25. As a benchmark maintainer, I want each paper declaration to remain directly
    readable, so that source evidence is not hidden by a universal builder.
26. As a MetaCraft architect, I want production to remain unable to import
    external examples, so that dependency direction stays one-way.
27. As a MetaCraft architect, I want benchmark state kept immutable and outside
    `Study`, Authority sessions, work execution, and Result closure, so that no
    second state machine appears.
28. As a test maintainer, I want exact case tests to stop honestly at typed
    replay absence when exact evidence is unavailable, so that no fabricated
    benchmark completion is claimed.
29. As a test maintainer, I want contract fixtures named as fixtures rather than
    paper cases, so that method proof is not confused with published-device
    evidence.
30. As a test maintainer, I want the duplicated representative-case builders
    and arbitrary 200 nm defaults removed, so that tests no longer alter paper
    truth.
31. As a field-science maintainer, I want field construction and comparison in
    the field-execution Module, so that conduct has one orchestration
    responsibility.
32. As a conduct caller, I want the field ownership move to preserve the same
    scientific Results and errors, so that the refactor changes structure but
    not behavior.
33. As an architecture maintainer, I want tests to prove Interfaces,
    dependency direction, and error outcomes, so that harmless private layout
    changes do not cause false architectural failures.
34. As a repository maintainer, I want every implementation slice to remain
    testable in one fresh context, so that sub-agent execution can be reviewed
    and recovered safely.
35. As a repository maintainer, I want one final deterministic closure gate, so
    that the whole expand-contract migration is proved before it is called
    complete.
36. As the project owner, I want an explicit stopping rule, so that this
    architecture cannot be reopened merely because further refactoring is
    imaginable.

## Implementation Decisions

- The single external feature seam is `MetalensBenchmarkCase`: stable
  selection, blind brief, canonical identity, and one comparison operation.
- The existing production conduct cadence remains the only route from a blind
  brief to admitted Results. Benchmark code observes this outcome but never
  compiles, conducts, admits, rejects, ranks, or mutates production science.
- Published reference, benchmark alignment, comparison contract, and typed
  benchmark Result measures each have one responsibility and are immutable.
- Published facts use four closed states: reported, derived, not reported, and
  unresolved. Legal combinations are represented by types rather than an enum
  plus optional values.
- Alignment uses five closed states: matched, adapted, independent, withheld,
  and excluded. Alignment contains no disposition, delta, or acceptance
  threshold.
- Comparison uses four closed rules: signed difference, context, not reported,
  and not applicable. Only the comparison contract grants comparison
  permission.
- An unresolved fact can only contribute non-numeric context. A not-reported
  rule requires an actual not-reported fact. These meanings are never merged.
- Every case supplies exactly one explicit rule for every measure in the fixed
  ordered frame. No implicit default or missing dictionary key carries domain
  meaning.
- Result restoration uses a closed typed projection and exhaustive dispatch
  over supported Result variants. It does not accept arbitrary objects, probe
  attributes dynamically, or try unrelated document decoders until one works.
- Comparison is strict and all-or-nothing. A signed difference is
  MetaCraft-minus-reference and requires compatible numeric meaning on both
  sides.
- Wrong caller types raise `TypeError`; malformed values raise stable-reason
  `ValueError`; Authority, protocol, storage, and missing-body faults propagate
  unchanged. Ordinary absence exists only in fact and rule values.
- The four paper declarations share types and validation but not a universal
  builder. Publication-specific facts, locators, derivations, and rationales
  remain independently auditable.
- Yun uses aspect limit 10; Yang, Arbabi, and Khorasaninejad use 8. These are
  independent process inputs, not a scan. Yun's numeric 10 is not a matched
  paper fact because MetaCraft constrains both feature and gap.
- Yun's selected-device period is unresolved and has no numeric fallback.
  Other paper facts retain the states and scopes established by the accepted
  Research Records.
- The public schema changes once. Internal unexported expansion is allowed only
  to keep intermediate slices green. It creates no supported compatibility
  contract. After all four cases migrate, the old model and every forwarding
  path are deleted in one contraction.
- Canonical document codecs remain private to the values they encode. There is
  no generic decoder, compatibility reader, double writer, service layer, or
  benchmark repository.
- The fixed four-case catalogue owns strict case-document restoration. Cases
  encode themselves without importing the catalogue, and restoration does not
  become another root-level benchmark behavior.
- Production state owners remain unchanged: `Study`, `StudyFrontier`,
  `AuthoritySession`, `WorkExecution`, and Result closure do not receive
  benchmark meaning or state.
- The field-execution Module takes ownership of field realization restoration,
  direct-Debye ideal-field construction, polarization translation, Torch
  storage crossing, focal evidence restoration, and focal-field comparison.
- Metalens conduct retains qualification, consultation, ready-task selection,
  dispatch, refusal formation, and immutable Study evolution. Dependency flows
  from conduct to field execution and never returns.
- The field move introduces no new public Interface, callback protocol,
  registry, manager, dependency container, or changes to numerical behavior.
- Names use the repository's domain language and Python casing conventions.
  Public names are intention-revealing and avoid broad terms such as data,
  info, manager, helper, and utils.
- The accepted ownership decision is recorded in a new ADR that supersedes
  only the concrete benchmark-shape clauses of ADR 0018. Historical ADRs are
  not rewritten, and the glossary remains implementation-free.
- Completion requires the approved contract, exact four-case declarations,
  strict error behavior, clean dependency graph, field ownership move, and all
  deterministic gates. "More Sonnet" alone is not a reopening condition.

## Testing Decisions

- The highest feature test seam is the existing `MetalensBenchmarkCase`. Tests
  select a case, verify brief blindness and identity, and compare only exact
  admitted Results through the case's one operation.
- The field ownership move is tested through existing conduct outcomes and
  evidence values. No test-only public seam is added to field execution.
- Tests assert external values, signatures, canonical identities, error types,
  comparison outcomes, and dependency direction. They do not pin dataclass
  field order, private function location, or exact importer lists.
- Closed-value tests cover every published-fact, alignment, and comparison-rule
  variant, including all invalid state combinations.
- All four cases prove stable selection, canonical round-trip, independent
  source traceability, exact aspect limits, complete alignment, and one rule
  per fixed-frame measure.
- Comparable tests require an observation, a numeric published fact, compatible
  meaning, required alignment, and a finite signed difference. Separate tests
  prove that context, unresolved, not reported, and not applicable cannot carry
  forbidden numeric fields.
- Strict fetch tests exercise the installed Authority missing-object behavior
  as well as an exact in-memory read Adapter. Broad catches may not convert
  either malformed bodies or storage faults into absence.
- All-or-nothing tests prove that a wrong case, malformed document, mismatched
  identity, missing body, or unsupported Result yields no partial comparison.
- Exact catalogue cadence tests use the four unmodified cases. Each case either
  reaches exact admitted Results or returns the existing typed replay-absence
  boundary. No other case's evidence is substituted.
- Small typed fixtures may test comparison contracts, but their names and
  assertions must make clear that they are not paper devices or completed
  benchmark outcomes.
- Existing recorded-evidence tests, benchmark selection/codec tests, benchmark
  comparison tests, Result fixtures, runtime import-DAG tests, scientific
  boundary tests, Sonnet ratchets, and direct-Debye tests are the repository's
  prior art.
- Architecture ratchets reject public compatibility aliases, retired schemas,
  dynamic object projection, duplicated comparison permission, fabricated
  representative cases, arbitrary benchmark-period defaults, and production
  imports of examples.
- Field preservation tests cover scalar and vector propagation, direct-Debye
  ideal-field formation, focal-field comparison, realization faults, memory
  refusal, evidence references, dispatch, and immutable Study evolution.
- Every implementation ticket runs focused tests and static checking at its
  boundary. The final gate runs the full non-live deterministic suite, Pyright,
  architecture checks, canonical/link checks, source analysis, and diff
  whitespace checks.
- Live adviser, Lumerical, delivery, integration, and canary tests are excluded.
  A skipped or excluded Native test is never reported as a Native pass.

## Out of Scope

- Native Lumerical execution, a parameter sweep, an intermediate response
  investigation, or a paper-reproduction claim.
- Changing the physical cell-period selection rule, substrate/monitor layout,
  source position, mesh accuracy, or any solver template.
- Changing Rust, Authority verbs, durable workspace semantics, permit/receipt
  behavior, or production Result schemas.
- Changing the public conduct cadence, consultation contract, evidence Adapter
  tuple, material binding, periodic response, or solver bindings.
- Interpreting an empty metalens advancement outcome or redesigning the Study
  frontier.
- Splitting deep science Modules merely because they are large.
- A universal benchmark framework, metasurface base class, generic case
  registry, workflow engine, dependency container, manager, or repository.
- Generalizing the four metalens cases for frequency-selective, holographic, or
  quasi-BIC metasurfaces before a concrete second implementation requires it.
- Adding a public compatibility reader, alias, dual writer, migration period,
  or old-schema restoration.
- Cleaning unrelated workspace content, rewriting historical ADRs, or changing
  existing Research Record evidence during implementation.

## Further Notes

The primary-source audits remain evidence, not architecture authority. The new
ADR will preserve their fact boundaries and record the one-owner model. Local
planning documents remain non-normative until their decisions are reflected in
the ADR, glossary, canonical design documents, implementation, and tests.

The private expand-then-contract sequence resolves the implementation tension
between a one-time public schema cutover and the requirement that each ticket
be independently reviewable. Intermediate new case values are not exported and
cannot become a supported second API. The only consumer-visible moment is the
final contraction, when all four cases are ready and the old model disappears.

The benchmark has two honest outcomes. An exact case with exact recorded
evidence may produce admitted Results and comparisons. A case without exact
replay evidence must stop at the typed waiting boundary and make no comparison
claim. Contract fixtures prove comparison semantics but never stand in for a
published-device result.

The architectural cadence is:

`reference remembers -> alignment explains -> contract permits -> case compares`

The delivery cadence is:

`prefactor safely -> expand privately -> migrate four cases -> contract once -> prove -> close`

The feature stops when all acceptance conditions are deterministic, the old
model is absent, production remains independent of examples, field behavior has
one owner, and the final diff contains no compatibility layer or speculative
framework. Any later reopening must name a concrete violated owner, Interface,
dependency, state, error contract, domain term, or scientific fact.
