# Four-brief grounded baseline

Status: resolved (2026-08-12)

Decision source: [Four-brief grounding](../four-brief-grounding/map.md)

This specification turns the resolved decision tree into one bounded
implementation road. It authorizes no production, test, ADR, retained-evidence,
or cleanup mutation by itself. Tickets remain `ready-for-agent` until the owner
explicitly approves implementation against this exact contract.

## Context

MetaCraft already has one canonical `MetalensBrief`, one material-binding path,
one period-then-height consultation cadence, one resumable `conduct` lifecycle,
and one external benchmark contract. The four-case frame also already spans
low/high numerical aperture and propagation/geometric phase.

The accepted decisions change neither that cadence nor those public concepts.
They replace one weak low-NA propagation reference, correct one backwards
dependency between period legality and downstream proof capability, and expose
the existing admitted material/period/height facts at the harness boundary.

The active benchmark frame becomes:

| Case | Brief role | Wavelength | NA | Phase | Atom / substrate | Aspect limit |
| --- | --- | ---: | ---: | --- | --- | ---: |
| McClung | low-NA propagation | 550 nm | 0.20 | propagation | silicon nitride / fused silica | 8 |
| Yang | low-NA geometric | 1550 nm | 0.32 | geometric | silicon / silicon dioxide | 8 |
| Arbabi | high-NA propagation | 1550 nm | 0.89 | propagation | silicon / fused silica | 8 |
| Khorasaninejad | high-NA geometric | 532 nm | 0.80 | geometric | amorphous titanium dioxide / glass | 8 |

All four use a 10 nm fabrication increment, workstation budget, and the
existing `lumerical_fdtd` preference. Their user goals and implementation
premises are complete before compilation. Cell period and atom height are the
only scientific consultation omissions in this benchmark phase.

## Problem

Four inconsistencies prevent an honest baseline:

1. the current period domain makes the order ceiling part of candidate
   legality for coefficient-only routes, although order is a property of the
   evidence needed downstream;
2. Yun remains the active low-NA propagation case even though its selected
   comparator does not source-join a period and height suitable for this test;
3. the external capsule inspector shows period and height but omits the exact
   material binding that grounds both choices; and
4. historical Yun entry points and generated evidence cannot be classified
   safely until a replacement four-brief baseline exists.

Changing those concerns independently would create two roads: one legality
rule in consultation and another in proof, one current catalogue in examples
and another in acceptance support, or one retained Study that cannot be fully
inspected. The implementation must therefore move in four vertical slices.

## Principle

User intent bounds the design; material evidence grounds the choice; sampling
bounds the period; order bounds the proof.

Published references explain the result without directing the blind advice.
The harness sees only canonical brief, material, domain, request, and ground
documents until its answers are sealed. Paper period, height, geometry, and
efficiency enter only the post-hoc benchmark alignment.

One state change has one owner:

```text
complete MetalensBrief
  -> exact MaterialBinding
    -> sampling-legal PeriodAdvice -> PeriodChoice + order regime
      -> HeightAdvice -> HeightChoice
        -> WaitingStudies
```

No draft brief, provider client, recommendation service, benchmark-specific
compiler branch, or second conduct lifecycle is introduced.

## Architecture

### 1. Separate legality from applicability

The period domain retains both exact ceilings, but its grid-aligned
`period_limit_nm` is always the greatest 10 nm multiple strictly below the
sampling ceiling. The order ceiling remains admitted evidence and classifies a
selected period as `zeroth order` or `multi order`. It does not remove an
otherwise sampling-legal consultation candidate.

The proof boundary remains strict. A coefficient-only response cannot close a
complete-field claim for a multi-order choice. A qualified sampled
reference-surface or future order-resolved response may do so while retaining
the caution. A focused ADR supersedes only the conflicting period-legality
clauses of ADR 0009; the no-G0-overclaim rule remains.

### 2. Cut the catalogue over once

One ordinary `mcclung.py` replaces current `yun.py`. The case identity is
`mcclung-2024-low-na-propagation`; its compact brief uses 550 nm, NA 0.20,
200 um focal length, x-linear incidence, propagation phase, circular silicon-
nitride pillars on fused silica, aspect limit 8, and 10 nm fabrication steps.
It omits aperture, period, and height.

The `PublishedReference` separately retains the paper-scale device and every
source-supported fact in the existing fixed benchmark frame. The existing
alignment vocabulary records matched, independent, withheld, unresolved, or
adapted relationships internally; neither the case nor brief gains an
`adapted brief` name or lifecycle. Current catalogue, harness fixtures, and
active tests change atomically. Closed Yun research, ADRs, tickets, and
transcripts remain historical evidence.

### 3. Inspect and exercise four blind briefs

The existing test-side capsule inspection adds the admitted material family,
native record, optical sample basis, and references beside its existing advice
and choices. It adds no production report type.

Each case is then exercised in a clean application root. The caller receives
only blind canonical inputs and answers period, then height, through the
existing consultation documents. Exact selected values are not hard-coded in
production or copied from `PublishedReference`. Each capsule must finish as
`WaitingStudies`, have no current question, retain canonical answers, and make
material, period, height, grounds, order regime, and cautions inspectable.

After sealing, a post-hoc report may show distance from the paper period and
height. Proximity is diagnostic, not a hidden pass threshold; acceptance rests
on legality, source-grounded reasoning, conservative fabrication judgment,
traceability, and honest evidence boundaries.

### 4. Seal before cleanup

The final ticket runs deterministic gates, records the exact four-capsule
inventory, removes current Yun entry points already superseded by McClung, and
classifies generated workspace residue. The known old Yun brief-stage run may
leave only after the McClung replacement capsule is retained and its exact path
is reverified. No broad recursive purge, historical search-and-replace, or
presentation-content edit is allowed.

## Dependency graph

```text
01 -> 02 -> 03 -> 04
```

Every ticket is a vertical, independently reviewable slice. Ticket 04 performs
no semantic repair; a failed gate reopens the ticket that owns the defect.

## Frozen boundaries

- Preserve installed-root exports, Authority, canonical brief/consultation
  schemas, `conduct`, `WaitingStudies`, Study replay, and Result schemas.
- Preserve period-before-height ordering and material-before-period evidence.
- Preserve exact material registrations: Luke silicon nitride, Palik silicon,
  reviewed Palik silica-family selections, and Siefke titanium dioxide.
- Preserve benchmark code outside production and paper truth outside blind
  consultation.
- Do not add aliases, fuzzy material matching, silent substitution, paper-
  seeded advice, an in-process AI client, a generic provider/harness layer, or
  a benchmark-specific science policy.
- Do not run Lumerical, periodic sweeps, aperture assignment, propagation,
  focus calculation, or efficiency acceptance.
- Do not implement achromatic types, hexagonal/triangular templates, IRUE,
  spectral orchestration, Rust, or CST work.

## Trade-off

Allowing multi-order periods admits designs that coefficient-only evidence
cannot finish. That is intentional: upstream design legality should not be
shrunk to fit one downstream observer. The retained order regime and refusal
at the complete-field boundary make the limitation explicit.

Using paper-near cases without paper-seeded advice produces a less predictable
numeric comparison, but a more meaningful harness test. A recommendation may
differ from the paper and still be scientifically defensible; an unexplained
match is weaker evidence than a traceable difference.

## Conclusion

The movement closes when one legality rule, one four-case catalogue, four
inspectable blind brief capsules, and one deterministic seal agree. It stops at
`WaitingStudies`: material chosen, period chosen, height chosen; no sweep, no
field, no inflated claim. Further Sonnet refactoring, live solver work, or
achromatic expansion is not a closure condition.
