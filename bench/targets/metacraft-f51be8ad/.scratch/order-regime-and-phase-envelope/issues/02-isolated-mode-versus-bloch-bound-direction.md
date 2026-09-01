# 02 — Isolated-pillar mode versus array Bloch mode: which way does the bound go?

**Type:** `wayfinder:research`

**Blocked by:** None — on the frontier.

**Status:** resolved (2026-07-26)

## Question

One-way exclusion is only safe if the optimistic model is genuinely an upper
bound. Is the isolated step-index fundamental mode index an upper bound on the
fundamental Bloch mode index of the same pillar in a square lattice?

- At the fill fractions this effort cares about — pillar diameter 60-180 nm in a
  200-220 nm period, gaps at 0.15-0.35 wavelengths — coupling is not weak.
  Does neighbour coupling raise or lower the fundamental mode index relative to
  the isolated pillar?
- The substrate breaks the symmetric-cladding assumption. Which direction does
  that push the index, and by how much at these contrasts?
- Maxwell-Garnett for cylinders with transverse E gives a clearly lower value
  than the isolated mode at high fill. Is it a defensible lower bound, or merely
  a different approximation?
- Is there a published bound — variational, or a rigorous EMT limit — that can
  be cited rather than asserted?

Primary sources: metasurface and photonic-crystal-fibre literature on effective
index of periodic dielectric pillar arrays. If no rigorous bound exists, say so
plainly; ticket 05 then has to decide what exclusion rule survives without one.

## Resolution (2026-07-26)

**No — the direction is reversed. The isolated-pillar mode index is a LOWER
bound on the array Bloch mode index.**

- With matched cladding, the array fundamental mode at Gamma has effective index
  greater than or equal to the isolated pillar's. One line: in the variational
  (min-max) characterisation of a z-invariant structure at fixed propagation
  constant, the quadratic form `integral (1/eps) |curl_beta H|^2` decreases
  pointwise as `eps` rises; adding neighbours raises `eps` pointwise, lowering
  omega at fixed beta, equivalently raising beta at fixed omega. Lee, Avniel &
  Johnson, Opt. Express 16, 9261 (2008), arXiv:0803.2850. The direction does not
  reverse with fill fraction, and the gap widens as the spacing closes.
  Experimental corroboration: Yagci & Demir, APL Photonics 6, 036101 (2021),
  arXiv:2012.06372, tune phase by pillar *spacing* at fixed diameter and
  describe coupling as "an additional refractive index".
- **The substrate does not shift the mode index.** Everything above the
  interface — pillar plus air — is z-invariant, so the Bloch index is fixed by
  `n_pillar`, the geometry, and air. The substrate enters only through the
  Rayleigh/diffraction condition and through the asymmetric-mirror Fabry-Perot
  formed by the two end faces, which moves the *extracted transmission phase*,
  not the Bloch index. Exception: a residual etch layer or index-matching layer
  under the pillars breaks this.
- **Maxwell-Garnett is not a defensible lower bound.** Air-host MG is the
  Hashin-Shtrikman lower bound in the quasi-static limit, but that limit is badly
  violated here: the exact isolated-pillar index at d=180 nm (1.692 at 355 nm,
  1.586 at 400 nm) already exceeds the HS *upper* bound (1.675 at period 200,
  1.553 at period 220). MG also sits *above* the isolated value at small
  diameters (1.038 versus about 1.000 at d=60 nm), so the two estimators cross
  inside the diameter domain and neither is a one-sided estimator across it.
- **One rigorous citable bound exists, and only one:**
  `n_eff(Bloch, Gamma) < n_pillar`, from the same variational theorem and from
  the textbook `k*n_min < beta < k*n_max` (Snyder & Love). An isolated-pillar
  calculation may be used in the envelope only at the *small*-diameter end, as a
  floor on the floor. It may never serve as a ceiling at the large-diameter end.

**Carry into ticket 05:** at 355 nm with `n = 2.12` and air cladding, the
isolated pillar stops being single-mode at `d >= 145 nm` (V = 2.316 / 2.647 /
2.978 at d = 140 / 160 / 180 nm). The array carries more modes still. The
transmission phase there is no longer `k0 * n_eff * h`, so the envelope's
single-mode applicability condition may be unsatisfiable over most of the
diameter domain — which would make the envelope return `not applicable` exactly
where it is needed.

## Addendum — a tighter rigorous ceiling (2026-07-26, research record)

The research record
`docs/research/2026-07-26-isolated-mode-versus-bloch-bound-direction.md` adds
one computable rigorous upper bound beyond `n_pillar`: circumscribe the pillar
with its bounding 1D lamellar grating (circle inside strip means pointwise
larger permittivity), whose fundamental space-filling-mode index has the exact
Rytov transcendental solution. The chain

`max(1, n_iso(d)) <= n_Bloch,Gamma(d) <= n_lamFSM(d) <= n_pillar`

is rigorous by the same variational monotonicity, and both ends are 1D
root-finding with no solver and no simulation. Carry into ticket 05: this can
tighten the map's tier (b) *bounded exclusion* from the rarely-biting
`n_pillar` ceiling to a diameter-dependent ceiling at zero model risk. How
loose the ceiling is at the large-diameter end is empirical — calibrate once
against a converged Bloch solve before trusting it near a threshold.
