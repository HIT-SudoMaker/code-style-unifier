# 01 — Lumerical index-read semantics

**Type:** `wayfinder:research`

**Blocked by:** None — on the frontier.

**Status:** resolved (2026-07-26)

## Question

What exactly does each Lumerical index-read entry point return, and what does
it require to be callable?

- `getindex(material, frequency)` versus `getfdtdindex(material, frequency,
  fmin, fmax)`: which returns the tabulated material data and which returns the
  multi-coefficient fit the FDTD mesh actually uses?
- Does either require a live FDTD region with a configured frequency range, an
  open project, or a running analysis? A sample taken during
  `probe.py:240 verify_periodic_execution` has a fixture FDTD region available;
  a sample taken during `_bind_material` may not.
- What is the return shape and unit convention — complex index, separate n and
  k, array over frequency?
- Is the fit reported with an error metric that could be recorded alongside the
  sample?
- Does the returned value depend on the fixture's frequency span, so that a
  sample is only valid for the span it was taken under?

Answer from Ansys primary documentation. The answer decides whether ticket 04
can sample at qualification time or must sample per brief.

## Resolution (2026-07-26)

Answered from Ansys primary documentation only; full findings with citations
in `docs/research/2026-07-26-lumerical-index-read-semantics.md`.

- `getindex` returns the material-database table value, linearly interpolated
  between neighbouring tabulated frequencies. It takes no fit span, so a
  sample is brief-independent and reusable.
- `getfdtdindex` returns the multi-coefficient fit the FDTD mesh actually
  uses, recomputed over the passed `(fmin, fmax)`. A sample is valid only for
  the exact (data revision, max coefficients, tolerance, fmin, fmax) it was
  taken under — and matches the real solve only when the solve's fit range
  equals that span. `getnumericalpermittivity` confirms the mesh uses the
  square of this fit as dt→0.
- Both are callable in a bare `lumapi.FDTD(hide=True)` session: no FDTD
  region, no open project, no running analysis. The only precondition is
  that the material name exists in the session library (`materialexists`).
- Return shape: one complex refractive index per frequency point; frequency
  in Hz; anisotropy via an optional component argument.
- Fit targets (tolerance = target RMS, default 0.1; max coefficients,
  default 6) are readable material properties and belong in the sample
  record. The *achieved* RMS has no documented FDTD script read-back
  (Material Explorer only); a recordable residual is
  `|getfdtdindex - getindex|` computed on the same grid.
- `getmaterial(..., "sampled data")` reads the raw tabulated
  `[f, permittivity]` table — the only way to confirm 355/400 nm lie inside
  the tabulated band. Exact native names ("SiO2 (Glass)" versus
  "SiO2 (Glass) - Palik") must be probed, never assumed.

What this decides for ticket 04: callability is no constraint — a per-brief
bare session is cheap and legal. The decision is span semantics: a
`getindex` sample can be taken at qualification over a declared grid and
reused across briefs; a `getfdtdindex` sample is inherently per-brief (exact
wavelength, that brief's effective fit span), unless a versioned platform
fit-span policy is pinned and enforced on the solve side.

Undocumented residuals (probe at build time, do not assume): `fmin == fmax`
degeneracy, out-of-table extrapolation of `getindex`, exact numpy return
shape, and the default table's frequency coverage at 355 nm.
