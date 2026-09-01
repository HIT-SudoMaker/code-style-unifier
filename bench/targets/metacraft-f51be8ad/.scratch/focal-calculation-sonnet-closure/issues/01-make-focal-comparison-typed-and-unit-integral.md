# Make focal comparison typed and unit-integral

Status: completed

Resolution: completed with one typed comparison boundary, one unit-integral
intensity-distribution metric, and one strict replacement schema. Historical
comparison evidence remains a read-only witness and the retired schema fails
closed without an alias or decoder.

Blocked by: none

Parent: [map](../map.md) · [specification](../spec.md)

## Outcome

One comparison Interface owns its structural failures and reports exactly named
shape metrics. Callers no longer classify exception text, and the intensity
metric states the normalization it actually performs.

## Implementation

Work through `src/metacraft/field/agreement.py` and
`src/metacraft/science/metalens/focal_field_comparison.py`. Replace the
`str(error)` branch for grid mismatch with a typed owner-local failure or an
equally narrow structural precondition that does not duplicate comparison
mathematics. Replace least-squares intensity rescaling with unit-integral
intensity distributions: divide each nonzero total intensity map by its sum and
report
`||I_o/sum(I_o) - I_r/sum(I_r)||_2 / ||I_r/sum(I_r)||_2` on the exact shared
uniform grid. Rename the stored/public field to
`unit_integral_intensity_error`; update Result restoration, benchmark measure
projection, delivery signatures, documents, tests, and active prose in the same
slice. Do not retain a deprecated alias, dual schema, or compatibility decoder.

Before changing the schema, freeze the fixed-point comparison document, Result
projection, and four benchmark signatures. Treat existing application roots as
immutable historical evidence: a stale comparison schema fails closed without
rewriting the root, while new journeys start from fresh roots.

Keep complex least-squares alignment as the distinct
`aligned_complex_error`, and keep `observed_to_ideal_scale` as provenance for
that complex comparison. Zero, nonfinite, component, and grid faults retain
stable direct ownership. Do not add success thresholds to physical focal
comparison.

## Acceptance

- Scale-only intensity changes produce zero unit-integral error; redistribution
  produces a nonzero independently calculated value.
- Component and grid mismatches are asserted by type/owner, never by parsing
  exception messages.
- Canonical document round trips, Result restoration, benchmark extraction,
  and four-case delivery tests use only the new name and formula.
- Nonfinite, zero or negative total intensity is rejected before division, and
  the independent oracle uses no production normalization helper.
- A fixed-point document witness is retained; stale-schema restoration fails
  explicitly and leaves its application root byte-for-byte unchanged.
- Searches find no production `normalized_intensity_error` and no caller
  classification of `field_agreement_grid_mismatch` text.
- Focused field/science tests, architecture error-ownership gates, Pyright,
  CSU, and `git diff --check` pass.

## Guardrails

Do not change propagation, aplanatic sampling, absolute Poynting values,
benchmark thresholds, or public Harness cadence in this ticket.

## Evidence

- TDD red witnesses first failed on the absent
  `FieldAgreementGridMismatch`, `FocalComparisonComponentsMismatch`, and
  `FocalComparisonGridMismatch` Interfaces; focused green verification then
  passed 53 tests across Field comparison, pointwise science, Result
  restoration, benchmark contracts, stale evidence, and architecture
  ratchets.
- The independent redistribution fixture establishes an exact unit-integral
  error of `0.5`; scale-only intensity changes establish zero, while zero and
  nonfinite samples fail before normalization.
- Fixed point `c46e663f1f6841830994de5e5198dae25b4d1082` retains comparison-document
  SHA-256
  `9396b88fed02b412e5f04224139096f2db61816bcdcb431bcbed4ed00bd4078e`
  together with four Result projection hashes and the four benchmark
  identities in `tests/fixtures/focal_comparison/fixed-point-c46e663.json`.
- Stale-schema restoration raises `focal_comparison_schema_invalid` and the
  witnessed application-root object remains byte-for-byte unchanged.
- Full Pyright reports 0 errors and 0 warnings. CSU reports no blocking
  finding in either Ticket 01 production path. `git diff --check` is clean and
  Rust is unchanged from the fixed point.
