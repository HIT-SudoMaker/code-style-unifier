# 07 - Execute the Native publication proof matrix

Status: ready-for-agent

Assignee: unassigned

Label: `ready-for-agent`

Blocked by:

- [04 - Freeze one traceable spectral study specification](04-freeze-the-traceable-spectral-study-specification.md)
- [05 - Let spectral qualification own one verdict](05-let-spectral-qualification-own-one-verdict.md)
- [10 - Let aperture own the continuous physical Lattice](10-let-aperture-own-the-continuous-physical-lattice.md)

Parent: [Publication freeze](../spec.md)

## Work

Provide three source-level showcase cases without changing the frozen four-case
historical benchmark catalogue: one representative propagation case, one PB
case, and the continuous-compensation case.

Execute and retain the publication specification's P1--P5 Native rows: current
TiO2 target, same-aperture PB-only baseline, blind holdouts, neighboring
higher-delay refusal challenge, and frozen lateral/height fabrication
perturbations. Use identical field propagation, focus evaluation, normalization,
and aperture facts wherever comparison requires them.

The continuous route may close only as a complete candidate/Result or an exact
typed evidence stop. A synthetic fixture is never the publication outcome.

## Acceptance

- Every Native request and receipt cites the exact specification, binding,
  profile, solver binding, geometry, wavelength, and input basis.
- P1 includes all 5 design and 4 holdout wavelengths and one fixed 63-site
  central-diameter Lattice for the current target.
- P2 reuses byte-equal aperture coordinates and evaluation contracts.
- P3 was excluded from spectral fitting and is reported separately.
- P4 proves correct refusal and no false Result.
- P5 retains nominal and perturbed geometries without silently changing the
  selected nominal design.
- Interrupted work resumes without duplicate scientific claims; failed and
  incomplete receipts remain in the released manifest.

## Stop rule

If the complete TiO2 library is refused or device focus is incomplete, close
the software evidence honestly and open a new realization decision. Do not
weaken NA, aperture, band, fabrication rules, or qualification in this ticket.

## Comments

### 2026-08-15 - Source-level showcase slice

The three additive showcase cases now exist without changing the frozen
four-case historical benchmark catalogue:

- `examples/propagation_phase_showcase.py` exposes admitted target/realized
  propagation states, geometry, Field/focus, and exact Result references.
- `examples/pb_phase_showcase.py` exposes admitted target/realized PB states,
  fixed geometry/orientation, converted Field/focus, and exact Result
  references.
- `examples/continuous_achromatic_showcase.py` exposes the fixed physical
  geometry/orientation maps, geometry-controlled phase, PB phase, target and
  realized composition, role-separated design/interleaved-validation/blind
  Field and focus evidence, PASS band verification, and exact Result
  references. It states explicitly that PB orientation contributes no group
  delay and that geometry-controlled and PB responses belong to the same
  anisotropic structure.

Each runner enters through public `conduct`. Waiting, consultation, invalid,
and unsupported outcomes are returned unchanged; only an already admitted
`CompletedResults` value is projected. `execution_origin` is explicit, and the
examples do not manufacture numerical or Native evidence. The continuous test
uses a content-addressed synthetic Result fixture solely to verify replay and
projection; it is not a publication outcome.

Focused validation: 15 showcase/catalogue tests passed in 66.66 s, including
the unchanged four-case catalogue; Pyright reported 0 errors for all three
showcase sources. Ticket 05's final integration gate and this ticket's P1--P5
Native campaign remain outstanding, so this ticket stays open.
