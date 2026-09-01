# 0020 - Let benchmark truth explain without directing

Status: accepted

## Research basis

This decision applies the primary-source findings in
[Published measure definitions for the four metalens benchmark cases](../research/2026-08-06-metalens-benchmark-published-measure-definitions.md)
and
[Four-case period and aspect-ratio brief audit](../research/2026-08-06-four-case-period-aspect-ratio-audit.md).

The records establish both positive facts and evidence limits. In particular,
a reported number can still be incomparable when its scope or normalization is
different, and an inaccessible or unjoined source is not the same as a paper
that did not report a fact.

## Context

ADR 0018 moved paper meaning out of production and gave one external
`MetalensBenchmarkCase` the only comparison operation. That direction is
preserved. Its concrete benchmark shape nevertheless stores paper facts,
measurement definitions, and comparison dispositions in overlapping values.
It requires every platform dimension to be known, requires a blind brief to
equal paper conditions, and permits a comparable record whose observation and
difference are absent.

Those constraints turn an evidence gap into a fabricated value and turn a
realistic target-near brief into an apparent reproduction. They also make
tests rewrite published truth in order to exercise Result restoration.

## Decision

### Keep one external case seam

The external cadence remains:

```text
select case -> conduct only its blind brief -> admit Result -> case.compare
```

Benchmark code remains outside production. It does not compile, conduct,
choose, admit, reject, or mutate science. `case.compare(completed_results,
fetch=...)` remains read-only and all-or-nothing. `Authority.fetch` and an exact
in-memory reader are the two Adapters at that seam. Their faults and missing
referenced bodies propagate; comparison does not translate them into ordinary
absence.

### Give four meanings one owner each

A **published reference** alone owns paper facts. Each fact is exactly one of
reported, derived, not reported, or unresolved. Reported facts carry a value
and primary-source locator. Derived facts also carry their cited inputs and
derivation. Not-reported and unresolved facts carry no fallback value and
remain distinct.

A **benchmark alignment** alone owns each brief/reference relation. Every
declared subject is exactly matched, adapted, independent, withheld, or
excluded. Alignment contains no comparison disposition, delta, success
threshold, or acceptance policy.

A **comparison contract** alone grants comparison permission. Every measure in
one fixed ordered frame has exactly one explicit signed-difference, context,
not-reported, or not-applicable rule. There is no default rule. A not-reported
rule requires an actual not-reported fact; an unresolved fact can produce only
non-numeric context.

Typed **benchmark Result measures** alone own the MetaCraft observation side.
They restore an admitted Result through the closed metalens Result variants
and project one complete fixed frame. They do not probe arbitrary attributes,
free-form keys, or unrelated decoders.

### Make numerical comparison indivisible

A comparable outcome requires all of the following in one value:

- one finite MetaCraft numeric observation;
- one finite reported or derived reference quantity;
- identical measure, unit, scope, normalization, and definition;
- every required alignment relation; and
- one finite signed `MetaCraft - reference` difference.

An empty comparable value is structurally invalid. Differently defined
efficiencies, widths, transmission quantities, and field quantities remain
context even when both sides have numbers.

### Preserve honest blindness

A blind brief carries realistic target and process inputs, not paper-selected
cell geometry or paper outcomes. Aspect limits are supplied inputs rather than
scan variables: Yun uses 10; Yang, Arbabi, and Khorasaninejad use 8. Yun's
numeric 10 is independent because MetaCraft applies it to both feature and gap,
whereas the source ratio describes a feature.

The selected Yun comparator has an 800 nm reported height. Its period remains
unresolved until one primary source joins a period to that exact comparator.
Evidence from a different-height supporting library supplies no fallback.

### Expand privately, contract once

The new values may coexist temporarily with the old model only as an
unexported implementation tracer. The existing four-case catalogue remains
the sole supported Interface until all four declarations are complete. The
public schema then changes once: old types, codecs, fixtures that rewrite paper
truth, and forwarding paths are deleted together. No compatibility reader,
alias, dual writer, registry, runner, manager, repository, or universal
benchmark type is introduced.

Small deterministic Result fixtures may prove the contract only when named as
contract fixtures. They are not Yun outcomes or substitutes for exact
published-device evidence.

The fixed catalogue owns strict case-document restoration because it alone
knows the complete admitted set. A case encodes itself but does not import the
catalogue, and restoration is not exported as a second root-level behavior.

## Supersession

This ADR supersedes only ADR 0018's concrete `PublishedPlatform`,
`PublishedComparison`, fidelity-field, design-end, field-end, and comparison
record shape. It preserves ADR 0018's external case ownership, selection and
compare cadence, production dependency direction, read-only fetch seam,
Result integrity, Authority behavior, scientific ownership, and stopping
rule. It changes no other accepted ADR.

## Consequences

- A source gap can remain visible without acquiring an invented number.
- Target-near briefs can test judgment without pretending to reproduce a
  paper.
- Case declarations become longer where evidence is genuinely distinct, but
  every fact, relation, permission, and observation changes in one local
  owner.
- Canonical identity covers the complete brief, fact state, provenance,
  alignment, rule, and exclusion set; changing any of them changes identity.
- Wrong caller types raise `TypeError`. Malformed values, foreign documents,
  wrong cases, and impossible comparisons raise stable-reason `ValueError`.
  Storage and Authority faults propagate unchanged.
- Production state owners and Result schemas remain unchanged.

The benchmark architecture stops deepening when the four cases use this one
contract, the old shape is deleted in the single cutover, blindness and strict
restoration pass, the fixed frame is complete, and deterministic gates agree.
"More Sonnet" alone is not a reopening condition.
