# 04 — Where the solver-native material sample is taken, and what it binds to

**Type:** `wayfinder:grilling`

**Blocked by:** 01 (resolved 2026-07-26) — now on the frontier

**Status:** resolved (2026-07-26)

## Question

At which seam is the solver-native refractive index sampled, and what identity
does the sample carry?

- Qualification (`probe.py:240`) already opens a session and runs a fixture. A
  sample taken there is brief-independent, so it must cover a wavelength grid
  and later be resolved — introducing interpolation error. A sample taken in
  `_bind_material` knows the brief's exact wavelength and needs no
  interpolation, but opens one short session per brief.
- If the sample lands inside `LumericalBinding.as_mapping()`, the binding
  document changes and every task's `binding_reference` changes with it. If it
  lands in a separate document citing the binding, the binding stays
  byte-identical. Which expresses `CONTEXT.md:107` honestly?
- Does `_bind_material` need a permit and capacity scope if it opens a session,
  given that `optical_material` is currently a permit-free local capability?
- Which materials, and what does the sample record — n only, n and k, the fit
  error from ticket 01?
- Is the `T_G0 / |S21_G0|^2` recovery of the substrate index worth encoding as
  a cross-check, and does a disagreement beyond tolerance produce a finding?
- What does `materials/portable.py` become — a cross-check with a stated
  tolerance, or unused on this path?

## Resolution (2026-07-26)

**Sample at qualification, through the session the probe already opens.**

- `getindex` table samples over a registered wavelength grid, taken inside
  the qualification session. The grid must cover every standard brief
  wavelength; band coverage is confirmed by reading the raw table via
  `getmaterial(..., "sampled data")` (research 01). A brief wavelength
  outside the tabulated band is a finding, never an extrapolation.
- Sampled materials are the solver-native names the briefs bind (silicon
  nitride and silica), with exact native names probed via `materialexists`,
  never assumed.
- The sample lands in a **separate document citing the solver binding** —
  `LumericalBinding.as_mapping()` stays byte-identical, which expresses
  `CONTEXT.md:107` honestly: solver-native identity is valid only inside the
  named binding.
- Recorded per material and grid point: n and k, the fit target parameters
  (tolerance, max coefficients), and the `|getfdtdindex - getindex|`
  residual on the same grid as the recordable fit-quality proxy (the
  achieved RMS has no scripted read-back).
- Per-brief resolution uses one declared interpolation policy — linear in
  frequency, matching `getindex`'s own semantics.
- `_bind_material` opens no session and keeps no permit: it reads the
  qualification-admitted sample and cites it.
- `materials/portable.py` stays a cross-check, not the source (charted
  decision upheld). The `T_G0 / |S21_G0|^2` substrate-index recovery remains
  a diagnostic cross-check, not an admission requirement.
