# 18 — Sample solver-native indices at qualification

**Type:** implementation (spec phase 1)

**Status:** wontfix

**Superseded by:** [Metalens Sonnet convergence tickets 03 and 07](../../metalens-sonnet-convergence/spec.md#tickets).

**What to build:** Inside the session the qualification probe already opens,
sample `getindex` over a registered wavelength grid covering every standard
brief wavelength, for the solver-native materials the briefs bind (exact
native names probed via `materialexists`, never assumed). Record per material
and grid point: n and k, the fit target parameters (tolerance, max
coefficients), and the `|getfdtdindex - getindex|` residual on the same grid.
Confirm band coverage by reading the raw table via
`getmaterial(..., "sampled data")`; an out-of-band brief wavelength is a
finding, never an extrapolation. The sample is a separate admitted document
citing the solver binding — `LumericalBinding.as_mapping()` stays
byte-identical. The residual is recorded together with the exact
`(fmin, fmax)` span it was computed under, so it is recomputable; the
sample document must be recoverable from the authority view alone after a
restart — no dependence on dispatch memory. Per-brief resolution uses one
declared interpolation policy, linear in frequency. Also fix the licence
regex: it must accept FlexNet's singular form
(`Total of 1 license in use`).

**Acceptance:**

- Qualification admits the sample document; `_bind_material` still opens no
  session and holds no permit.
- Unit tests with a fake engine cover the grid, the residual, exact-name
  probing, and the out-of-band finding; a separately marked live test
  samples the real library once.
- The singular-form regex case is a regression test.
- Touched files leave `csu check` with zero hard violations.

Decisions: tickets 01, 04, 09; map Notes (CSU gate).
