# Place the aplanatic reference on its true plane

Status: completed

Resolution: implemented

Blocked by: 01, 02

Parent: [map](../map.md) · [specification](../spec.md)

## Outcome

Every aplanatic sample coordinate and stored physical surface describe the same
plane. A reference evaluated at geometric focus is never relabelled as the
realized focus plane.

## Implementation

In the current ideal-field formation slice, derive one explicit axial offset:

```text
axial_offset_m = found_focus_m - expected_focus_m
```

Use that offset for every requested aplanatic comparison coordinate and retain
the resulting reference on a `PlaneSurface` at `found_focus_m`. Keep transverse
coordinates centered on the admitted FocalRegion grid and preserve exact parity
and crop semantics. Validate that wavelength, medium, frame, spacing, shape,
and physical position agree before focal comparison.

Add independent analytic/translation fixtures for negative, zero, and positive
focus offsets. The nonzero fixtures must detect the old error: calculating at
zero axial offset and changing only surface metadata. Preserve the authored
aplanatic pupil and do not convert a plane Field into a pupil.

## Acceptance

- Nonzero focus offset changes calculated reference samples and stored surface
  position consistently.
- Zero offset remains a no-drift witness for the existing geometric-focus case.
- Positive and negative offsets preserve coordinate sign and do not silently
  clamp to the focal plane.
- Grid/surface mismatch produces a stable owner-local failure before agreement
  calculation.
- Focused aplanatic, field evidence, focal comparison, Result, CPU/CUDA,
  Pyright, CSU, and diff gates pass.

## Guardrails

Do not change the Richards--Wolf convention, introduce plane-to-pupil
relabeling, add coordinate interpolation, or use the realized focus to redefine
the geometric focal length.
