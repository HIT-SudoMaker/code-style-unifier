# 04 — Let field assumptions reveal their bias

Type: implementation

Status: resolved (2026-08-06)

Blocked by: 03 — Let blind cases bracket design and result.

Execution state: dependency satisfied; Ticket 03 resolved the approved
two-track evidence boundary on 2026-08-06.

## What to build

Using only the bounded representative evidence from Ticket 03, form controlled
external diagnostic fields that change one optical assumption at a time. Attribute the
field-end difference to assignment, phase, useful amplitude, polarization
conversion/leakage, or sampled-surface/vector effects without changing the
admitted Result.

These diagnostics characterize method-family assumptions. They are not exact
Yun, Yang, Arbabi, or Khorasaninejad paper-scale outcomes. Exact case
comparison remains unavailable until separately admitted exact Results exist.

## Requirements

- [x] Hold aperture occupancy, physical sampling, focal coordinates,
      propagation distance, incident field, and normalization fixed within
      each case.
- [x] Propagation cases use the applicable ordered subset of `ideal
      continuous`, `assigned target`, `realized phase`, `realized coefficient`,
      and `sampled surface`.
- [x] Geometric cases use the applicable ordered subset of `ideal pb`,
      `assigned orientation`, `realized jones`, and `sampled surface`.
- [x] The low-NA propagation representative retains finite 8/12/16 phase
      quantization; the low-NA geometric representative retains finite
      8/12/16 orientation quantization.
- [x] The high-NA propagation representative remains pointwise and the
      high-NA geometric representative retains continuous PB
      orientation; neither receives a fabricated finite-level diagnostic.
- [x] Propagation useful amplitude derives from admitted useful power and
      realized phase derives from the same admitted response.
- [x] Geometric diagnostics retain converted and retained Jones channels;
      they do not collapse PB response into an unrelated scalar coefficient.
- [x] High-NA sampled-surface diagnostics retain complete complex components,
      exact rectilinear-source provenance, uniform formation, vector
      propagation, and longitudinal power.
- [x] Each adjacent diagnostic difference has one natural-language
      attribution and the same metric dispositions as the endpoint report.
- [x] Diagnostic documents cite the exact case, Result, aperture, response,
      and field references they consume.

## Architecture constraints

- [x] Diagnostics live outside production Result meaning and never become
      Authority evidence for the completed Study.
- [x] Reuse existing field and scientific Modules through their Interfaces;
      do not copy propagation, focus, Jones, or reference-surface rules into
      examples.
- [x] Add no alternative conduct operation, mutable experiment object,
      benchmark runner, generic ablation framework, or case-specific workflow.
- [x] Perform zero Adviser, Native, Lumerical, permit, or product-session work.

## Verification

- [x] Tests prove exactly one assumption changes between adjacent variants.
- [x] Reordering diagnostics does not change their identities or values.
- [x] Original Results and application roots are byte-for-byte unchanged.
- [x] Focused tests, complete non-live tests, architecture tests, Pyright,
      blocking CSU, frozen Rust diff, and `git diff --check` pass.

## Stop condition

Stop after every endpoint deviation has either one first divergent diagnostic
step or an explicit no-divergence result. Do not inspect or execute a response
sweep in this ticket.

## Resolution

One external `diagnose_field_assumptions` Interface now restores an exact
bounded Result and returns canonical immutable diagnostic documents without
admitting new Authority truth. Coefficient variants pass through the existing
`aperture.form_field` Interface; high-NA variants pass through the existing
pointwise or geometric sampled-surface formation Interfaces. Only the ideal
target coefficient `exp(i target_phase)` is diagnostic arithmetic because no
production evidence owner exists for a counterfactual ideal aperture.

The complete representative matrix retains finite propagation and orientation
counts `8/12/16`, pointwise propagation, and continuous PB orientation. Its
first content-signature differences are:

- low-NA propagation 8/12/16: `assigned target`;
- low-NA geometric 8/12/16: `assigned orientation`;
- high-NA pointwise propagation: `realized phase`;
- high-NA continuous geometric phase: `assigned orientation`.

These are byte-level diagnostic-field differences, not exact paper-case
disagreement or acceptance verdicts. The field-measure dispositions are copied
unchanged from each endpoint comparison. No sweep evidence was inspected.

Focused Ticket 04 tests passed `2`; the relevant benchmark and architecture
selection passed `83`; project Pyright reported zero findings; the new example
Module reported zero blocking CSU findings; and Rust remains unchanged. The
parent six-ticket delivery owns the single final complete non-live suite, as it
does for the preceding dependent ticket.
