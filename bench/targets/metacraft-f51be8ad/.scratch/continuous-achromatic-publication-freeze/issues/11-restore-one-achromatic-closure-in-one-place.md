# 11 - Restore one achromatic closure in one place

Status: ready-for-agent

Assignee: unassigned

Label: `ready-for-agent`

Blocked by: [05 - Let spectral qualification own one verdict](05-let-spectral-qualification-own-one-verdict.md)

Parent: [Publication freeze](../spec.md)

## Work

Replace the two achromatic closure-restoration implementations used by conclude
and Result replay with one private restorer. It owns the exact qualification,
library, aperture, field-family, focus, origin, and reference checks. Public
callers remain `conclude` and `restore_result`.

This is a local-substitutable deepening: Authority fetch remains the existing
seam, and tests use the current in-memory Authority implementation. Do not add a
new public restorer Interface.

## Acceptance

- Conclude and replay produce byte-equal `AchromaticResult` values through their
  existing public Interfaces.
- Missing, wrong-schema, wrong-origin, and cross-linked closure documents fail
  identically from both entry paths.
- Replay performs no numerical propagation, focus evaluation, or Adapter work.
- Deleting the private restorer would force one closure policy back into both
  callers; no pass-through wrapper remains.

## Non-goals

No change to monochromatic Result schemas or public lifecycle.
