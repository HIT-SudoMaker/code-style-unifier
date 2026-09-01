# 16 — Is the geometric route the honest deliverable at 355 nm?

**Type:** `wayfinder:grilling`

**Blocked by:** None — on the frontier.

**Status:** resolved (2026-07-26)

## Question

If the propagation route refuses at every defensible period, is the right answer
to fix the propagation route, or to say that 355 nm belongs to the geometric
route?

The map currently treats the geometric route only as something that *inherits*
the single-order correction. It has never been costed as an **alternative**.

- Published and fabricated: Si3N4 nanorods, height **340 nm**, period 240 nm,
  cross-section 85 x 150 nm on SiO2, 250-400 nm operation, full 0-2*pi,
  77% focusing efficiency, NA 0.75 (PMC7153589). The height is half what the
  propagation route needs, which is exactly why the aspect-ratio squeeze that
  kills the propagation route does not bite: geometric phase comes from
  **rotation**, not from accumulated propagation, so it needs no phase span at
  all from the geometry.
- `science/routes/geometric_phase.py` and the geometric sweep already exist. How
  much of the effort's Layer 1 work does the geometric route need, and how much
  of Layer 2 becomes irrelevant to it? A phase envelope forecasting propagation
  span is meaningless for a PB cell; its analogue is half-wave-plate quality and
  cross-polarisation conversion.
- `long_focus_geometric_brief()` already exists at `briefs.py:97`. Does it
  survive the corrected period where its propagation twin does not?
- Does this change the destination? If the honest answer at 355 nm is "use the
  geometric route", then the propagation-route envelope is still worth building,
  but the *demonstration* moves.
- Would a geometric-route counterpart of the envelope even have exclusion teeth,
  or is its feasibility question purely a count question too?

Answering "yes, geometric" does not retire the propagation work; it changes what
the regression baseline in ticket 10 should be.

## Resolution (2026-07-26)

**All four briefs stay; expectations become the regression contract.**

- No brief changes. Expected outcomes, recorded as the regression contract:
  355 propagation → 8- and 12-level libraries deliverable, 16-level refuses
  honestly on the counting wall; 355 geometric → feasible (the geometric
  showcase; best cells near h = 550-600, e.g. 90 x 130 nm fins at
  delta ≈ 180 degrees); 400 propagation → all three quantizations (the
  propagation showcase); 400 geometric → feasible.
- Grounding: PB needs exactly one good cell — `choose_cell` requires >= 1
  with an argmin rule, code-verified — so the counting wall does not bite
  the geometric route. Feasibility numbers from the calibrated Rytov
  estimator (`pb_feasibility.md` in the session scratchpad), calibrated
  against the published fabricated Si3N4 device (PMC7153589); today's
  20 nm geometric step already suffices at h <= 600.
- Demonstration emphasis: 355 → geometric, 400 → propagation. Layer 1
  (zeroth-order correction) serves both routes; Layer 2 (the envelope)
  stays propagation-only by design.
