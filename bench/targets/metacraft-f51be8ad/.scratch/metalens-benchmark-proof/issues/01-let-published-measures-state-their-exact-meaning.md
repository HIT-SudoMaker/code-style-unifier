# 01 — Let published measures state their exact meaning

Type: research

Status: resolved (2026-08-06)

Blocked by: none

## Decision requested

Approve one bounded primary-source audit of the four reviewed papers and their
supporting information before the benchmark case schema is changed. This audit
may verify existing values and establish measurement definitions; it may not
change code, case facts, thresholds, or scientific methods.

## What to produce

Create one Research Record under `docs/research/` that states, for every
quantitative value currently carried by the four benchmark cases:

- the exact paper device, wavelength, and comparison scope;
- whether the value is simulated, measured, theoretical, or a family maximum;
- the quantity's numerator, denominator, normalization, integration region,
  focal bucket or width convention, and polarization channel when reported;
- the exact article, figure, table, methods paragraph, or supporting-information
  locator that supports the value and definition;
- whether MetaCraft's current measure is `comparable`, `context only`, or
  cannot yet be classified because the paper definition is unavailable;
- any conflict between the source and the currently encoded value, unit,
  scope, or fidelity note.

## Source discipline

- [x] Use the cited primary paper and official supporting information first.
- [x] Record bibliographic and source locators precisely; do not cite a search
      result, secondary summary, or remembered convention as evidence.
- [x] Quote only the minimum text needed to disambiguate a definition and
      otherwise paraphrase.
- [x] Distinguish an absent definition from an inaccessible source and from a
      definition that is present but incompatible with MetaCraft's measure.
- [x] Do not infer an efficiency denominator, focal integration radius, width
      convention, or uncertainty that the source does not state.
- [x] Preserve each currently reviewed case value until a separately approved
      correction explicitly replaces it.

## Required case coverage

- [x] Yun: simulated focus efficiency `0.828` for the conventional full-turn
      comparator.
- [x] Yang: measured focus efficiency `0.26` and theoretical focus efficiency
      `0.60` for one circular-polarization sublens.
- [x] Arbabi: reported maximum family focus efficiency `0.82` and its relation
      to the compact plane-wave benchmark.
- [x] Khorasaninejad: measured focus efficiency `0.73` and measured mean focal
      width `375 nm` for the 532 nm device.
- [x] Record qualitative definitions relevant to phase coverage, transmitted
      magnitude or power, orientation relation, polarization conversion,
      complex focal field, spatial phase sampling, and longitudinal field.

## Fault and decision contract

- [x] A source conflict is reported to the owner; it is not silently repaired
      in the Research Record or case code.
- [x] An unavailable paper definition is recorded as unavailable and later
      prevents a numerical delta.
- [x] A different paper scope or normalization is recorded as context-only,
      not as agreement or disagreement.
- [x] No ADR, `CONTEXT.md`, benchmark schema, production file, or test changes
      in this ticket.

## Stop condition

Stop when all encoded quantitative values and the named qualitative measures
have one primary-source disposition. Return the Research Record for human
review before Ticket 02 amends ADR 0018 or changes the case Interface.

## Resolution

The bounded audit is recorded in
[`docs/research/2026-08-06-metalens-benchmark-published-measure-definitions.md`](../../../docs/research/2026-08-06-metalens-benchmark-published-measure-definitions.md).
Every encoded published metric and named qualitative measure has a primary-
source disposition. The record preserves the inaccessible Khorasaninejad
supplementary definition and the conflict between its reported vertical-cut
`375 nm` FWHM and the currently encoded mean-width name; neither was silently
repaired.
