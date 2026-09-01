# 21 — The propagation envelope module

**Type:** implementation (spec phase 3, after 18-20)

**Status:** wontfix

**Superseded by:** [Metalens Sonnet convergence ticket 03](../../metalens-sonnet-convergence/issues/03-let-period-choose-before-height.md).

**What to build:** `science/routes/propagation_envelope.py` (converged on
the core noun after review), one public verb:
`estimate_phase_envelope(domain, contrast) -> PhaseEnvelope`. The field set
is ticket 07's resolution: reference-only `source_references`, one global
`bound_checks` block, grid facts, one `bounded_reasoning` block (floor
index, ceiling index with polarization, rigorous turns ceiling), one
`forecast` block (model spans, optional steepest adjacent step, per-level
budgets, `forecast insufficient` annotation), one `applicability` block
(kept when empty), and the single `standings` table {levels, standing,
deciding tier, reason}. Verdict tiers are ticket 05's resolution: arithmetic
and bounded exclusions may rule out; model estimates never do. The only
current hard numerical envelope is the elementary material interval from
ambient to pillar index. It is intentionally loose but does not depend on an
unproved cross-geometry inequality.

Primary-source review in
`docs/research/2026-07-26-phase-envelope-certified-roots.md` corrected the
earlier estimator decision: exact isolated-pillar HE11 and Rytov-exact
lamellar TE/TM roots are implementable as named forecasts, but the reviewed
sources do not prove that they bound the real two-dimensional periodic pillar
array. Ordinary floating-point Bessel and trigonometric evaluation is not a
certified interval proof either. Those roots must therefore remain
non-authorizing forecasts until both blockers are closed; they may never
replace the material hard bound by implication. Proof graph: one method
`estimate_phase_envelope` -> claim `phase_envelope`, requires
`(material_binding, height_domain)`, capability `None` — **the envelope
closes only this narrow claim; it never closes periodic transmission, cell
library, or phase set**; propagation's `choose_height` requires gains
`phase_envelope`; the geometric route is untouched. `OpticalContrast` is built from the qualification samples; no
samples means the envelope is unavailable, never invented.

**Acceptance:**

- Public-seam test
  `test_admitted_envelope_reveals_advice_without_closing_response` visibly
  admits the exact envelope through typed `Authority`, reopens and checks the
  workspace, then recompiles from `view()`: the envelope claim closes and the
  height-advice finding appears, while periodic transmission, cell library,
  and phase set remain open under the same envelope reference.
- The three material-bound checks hold on every run (ceiling closes to the pillar
  index, floor closes to the ambient index, floor remains below ceiling) and
  are carried once in `bound_checks` with their supporting values.
- `source_references` contains references only. A missing, failed, or
  uncertified bound check prevents a bounded-exclusion verdict.
- Exact document round-trip tests pin the current non-invented field shape.
  Future named-model golden bytes must come from an independent derivation
  that imports no production code.
- HE11/Rytov implementation and Bloch comparison remain follow-up forecast
  work. Neither can authorize a bounded verdict without a separate published
  cross-geometry proof and certified special-function arithmetic.
- Architecture tests pin the module's placement and the untouched
  `science.__all__`; touched files leave `csu check` with zero hard
  violations.

Decisions: tickets 02, 05, 07, 26, 29, 30; charted naming and placement.
