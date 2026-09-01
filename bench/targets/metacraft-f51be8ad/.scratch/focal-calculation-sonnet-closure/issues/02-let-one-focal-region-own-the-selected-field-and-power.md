# Let one focal region own the selected field and power

Status: completed

Resolution: completed by reusing one prepared vector spectrum for survey and
selected-plane materialization, admitting the exact Poynting-density object
with the focal region, and making high-NA evaluation consume that fact alone.
The contract distinguishes propagation distance from the selected plane's
world-coordinate position, so nonzero source planes cannot drift from their
power observation.

Blocked by: none

Parent: [map](../map.md) · [specification](../spec.md)

## Outcome

The admitted `FocalRegion` is sufficient to evaluate the selected focus.
Evaluation never calls propagation again, and the selected complex field and
matching longitudinal power-density plane cannot drift apart.

## Implementation

Deepen the existing survey/materialization path in
`src/metacraft/field/vector_angular_spectrum.py`: reuse the already prepared
vector spectrum when materializing the selected plane instead of repeating
padding and FFT. Extend the aim-owned focal-region fact and evidence storage to
retain the selected longitudinal power plane together with its selected Field,
distance, total input/output power, realization, and source references. Store
dense power samples as an immutable Authority object with an exact manifest
reference rather than embedding a large array in JSON.

Freeze the fixed-point focal-region and Result documents before the schema
change. Old application roots remain historical evidence and fail closed under
the new contract; do not migrate or rewrite them.

Change high-NA focus evaluation to consume only the restored `FocalRegion`.
Remove the second call to `propagate_electromagnetic_field` and any helper whose
only purpose was to reconstruct that plane. Preserve the ADR 0006 sequence:
propagate establishes the region; evaluate measures it. Low-NA focal regions
retain their component-power meaning and must not manufacture a Poynting plane.

## Acceptance

- High-Interface instrumentation proves one preparation, one selected-plane
  materialization, and zero propagation calls during evaluation; no production
  counting hook or test-only Interface is added.
- Focal-region document restoration proves exact power-plane bytes, shape,
  spacing, surface, source and binding references.
- A mismatched field/power plane is rejected before Focus formation.
- High-NA transmission and concentration are unchanged except for removal of
  redundant numerical execution; value/gradient or frozen Result witnesses
  show no drift.
- Replaying admitted focus evidence performs no Torch propagation.
- A fixed-point document witness is retained and stale focal-region restoration
  leaves the source application root unchanged.
- Focused VASM, FocalRegion, Focus, Authority storage, Result, CPU/CUDA, memory,
  Pyright, CSU, and diff gates pass.

## Guardrails

Do not persist prepared spectra or CUDA tensors, change search distances, alter
padding, or force low-NA routes into the vector power contract.

## Evidence

- TDD red witnesses: the survey performed four source FFTs instead of two;
  `FocalRegion` did not accept the selected input power and Poynting plane.
- Focused field, science, and architecture gate: 175 passed.
- Exact Authority round trip retains immutable float64 power bytes and rejects
  a mismatched world-coordinate surface before focus evaluation.
- The fixed-point witness records focal-region SHA-256
  `dab15e54fbb3168a40c09ff6e2884d303af86f94ea781b65f0035eca007beadc`
  and Result SHA-256
  `7dbc14895ac1cad90ad3dc89611219d5ab7c39c05463f2fcdaed076e6c01a8ac`;
  stale focal-region restoration fails closed without rewriting the witness.
- The changed manifest has the one-way schema identity
  `metacraft.science.metalens.retained_focal_region`; the retired
  `metacraft.science.metalens.focal_region` schema is audit-only and fails
  explicitly with `focal_region_schema_invalid`.
- Full Pyright: 0 errors, 0 warnings. CSU source scan: 0 blocking
  findings. `git diff --check`: clean.
