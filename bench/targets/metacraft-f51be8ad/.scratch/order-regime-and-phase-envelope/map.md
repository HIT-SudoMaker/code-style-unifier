# Map — Order regime and phase envelope

**Label:** `wayfinder:map`

## Destination

One implementable specification that settles three things:

1. How the **zeroth-order cell** becomes admitted evidence — the physical
   period and fabrication domain derived from sampled solver-native indices,
   failing closed when no valid domain exists.
2. The module boundary, naming, and exclusion semantics of the **phase
   envelope** — a pure-Python, zero-solver estimator that can rule a height out
   but can never claim coverage.
3. Whether **session reuse** in the Lumerical adapter is worth its licence cost
   while remaining inside the workstation contract.

The map is done when nothing remains to decide before someone writes that spec.
Implementation is the next road, not this one.

**Way clear (2026-07-26):** all seven decisions exposed by the external
read-only review are resolved and reflected in the specification and
implementation tickets. This map is the audit archive; the sole implementation
entry remains [spec.md](spec.md).

## Notes

**Domain:** dielectric metasurface / metalens design; propagation phase and
Pancharatnam-Berry geometric phase; Lumerical FDTD as the only external solver.

**Skills every session should consult:** `codebase-design` (deep-module
vocabulary), `domain-modeling` (this repo's normative glossary lives in
`CONTEXT.md` and is enforced by `tests/architecture/test_scientific_boundary.py`),
`grilling`.

**Standing constraints for this effort:**

- The phase envelope starts no external process — no FDTD, no RCWA, no MODE, no
  Lumerical session. It reads admitted evidence only.
- Rust is frozen. `tests/architecture/test_scientific_boundary.py:18` pins the
  commit and `:202-238` forbids domain words in Rust sources.
- The envelope may prevent a hopeless sweep; it may never close
  `periodic_transmission` or any coverage claim.
- `canonical.py:40` rejects `float`. Every emitted number is `Decimal` or a
  formatted string.
- Public exports need docstrings and `science.__all__` is asserted exactly by
  `tests/architecture/test_scientific_boundary.py:31-52`.
- Python design follows the Sonnet standard (`DEVELOPMENT.md:16`); CSU is the
  lower bound (`csu\bin\csu.exe check`), and code must also read in the
  domain's mental order. Recorded 2026-07-26 from the map owner's direction.
  Baseline that day: 113 hard violations (106 missing public contracts, 7
  import sorting), 1702 under review — the bar is normative, not yet standing.
- CSU gate for this effort (decided 2026-07-26): every file the effort
  touches leaves `csu check` with zero hard violations, including the file's
  pre-existing ones (`science/aperture.py` alone carries 30). Repo-wide
  cleanup is a separate effort — see Out of scope.

## Decisions so far

Entries marked `(charted)` were settled while charting this map and have no
ticket; the rest link the ticket that holds the detail.

- [The hidden session's workstation contract](issues/24-hidden-session-workstation-contract.md)
  — no GUI concept or unguarded process exception; reuse requires workstation
  placement, containment, and memory accounting, otherwise two sessions stay.
- [The height-advice grounds Interface](issues/25-height-advice-grounds-interface.md)
  — one keyword-only optional envelope: exact and required for propagation,
  absent and forbidden for geometric phase.
- **Scope covers all three layers** `(charted)` — exact single-order domain,
  forecast phase envelope, and session-reuse throughput ship as one spec, cut
  into independent phases at plan time.
- **Physics correction lands in the evidence layer** `(charted)` — `HeightDomain`
  gains `requires material_binding` and owns the admissible period;
  `CellPolicy.period_nm` is demoted to the phase-sampling ceiling. Rejected:
  a separate `cell_geometry` claim, and a compiler-side hardcoded index ceiling.
- **The envelope is an ancestor of `height_choice`** `(charted)` — the gate is a
  dependency edge, not task ordering. Reverses an earlier sibling-placement
  decision whose only benefit (resuming the 700 nm receipts) was already void.
- **One-way exclusion** `(charted, amended 2026-07-26)` — the envelope may
  return `ruled out` only when even the optimistic bound fails; a sufficient
  bound means `not ruled out`, never `covered`. Supersedes an earlier proposal
  to grade gate strength by calibration state.
  **Amendment:** ticket 02 destroyed the intended optimistic model, so the
  verdict splits into three tiers of different epistemic standing, to be
  finalised in ticket 05:
  (a) *arithmetic exclusion* — candidate count against `levels`, determined
  entirely by period, height, `aspect_limit` and `lateral_step`. Zero model
  risk, indisputable, and today it already excludes every standard brief.
  (b) *bounded exclusion* — `turns_max <= H * (n_pillar - n_floor) / lambda`
  with `n_floor` a strict lower bound on the smallest-diameter atom. Rigorous
  but very loose: 1.59 turns at 355 nm and H=500, so it rarely bites.
  (c) *model pair* — single-pillar and Maxwell-Garnett estimates report numbers
  and never produce a verdict, because neither bounds span in the needed
  direction. Do not promote (c) to a verdict to make the envelope feel useful.
  If span must have teeth, the only honest options are a verdict word that does
  not authorise a stop (`unlikely`, `forecast insufficient`), or a solver —
  and a solver is out of scope.
- **Refractive indices are solver-native** `(charted)` — sampled through the
  session that qualification already opens, bound to product version and native
  material name. `materials/portable.py` becomes a cross-check, not the source.
- **`science/routes/propagation_reach.py`** `(charted; amended after review —
  the module lands as `propagation_envelope.py`, converging on the core
  noun)` — the envelope is
  propagation-only and does not belong in the route-neutral `science/height.py`.
  The single-order correction is route-neutral and stays in the shared
  foundation, because the geometric route builds the same periodic frame.
- **Naming** `(charted)` — `phase envelope`, `height reach`, `optical contrast`.
  No `n_eff`, `neff`, `calc_neff`, `EffectiveIndexCalculator`, or `utils.py`.
  Effective-index bounds stay internal derivation variables.

- [01 — Lumerical index-read semantics](issues/01-lumerical-index-read-semantics.md)
  — `getindex` is span-free interpolated table data, reusable across briefs;
  `getfdtdindex` is the solve-time fit, valid only for the exact fit-span
  conditions it was taken under; both callable in a bare hidden session, so
  the ticket-04 choice is span semantics, not callability. Findings:
  `docs/research/2026-07-26-lumerical-index-read-semantics.md`.

- [02 — Isolated-pillar mode versus array Bloch mode](issues/02-isolated-mode-versus-bloch-bound-direction.md)
  — **the direction is reversed.** The array Bloch mode index is greater than
  or equal to the isolated-pillar mode index, by the variational
  characterisation of a z-invariant structure at fixed propagation constant
  (Lee, Avniel & Johnson, Opt. Express 16, 9261 (2008)). Adding neighbours
  raises permittivity pointwise, which lowers frequency at fixed beta, i.e.
  raises beta at fixed frequency. The gap never reverses with fill fraction.
  So the single-pillar estimate is a **lower** bound on span, and using it to
  rule a height out is exactly the unsafe exclusion the gate promised never to
  make. Maxwell-Garnett is not a defensible lower bound either — the
  quasi-static assumption fails here, and it crosses above the isolated value
  at small diameters. The only citable rigorous bound is
  `n_eff(Bloch, Gamma) < n_pillar`. Later primary-source review found exact
  HE11 and Rytov roots but no published cross-geometry proof that turns the
  circumscribed lamellar root into a hard bound for the two-dimensional
  pillar array; see the durable research record and ticket 21 correction.

- [03 — The order regime: criterion and term](issues/03-order-regime-criterion-and-term.md)
  — physical period = floored min of two paired ceilings: the `sampling
  ceiling` (Nyquist, the demoted `CellPolicy.period_nm`) and the `order
  ceiling` (`lambda/(n_sub+NA)`, solver-native index, whole-aperture NA, both
  media), recorded by [ADR 0005](../../docs/adr/0005-derive-the-cell-period-from-the-zeroth-order-condition.md)
  as *derived*, never cited. Term: `order regime` {`zeroth order`,
  `multi order`} — "single order" abandoned (published collision),
  "admissible period" retired (authority-language collision). Domain document
  fully self-describing; finding `zeroth_order_domain_empty`; 10 nm flooring
  stays. 355 nm -> 200 nm, 400 nm -> 220 nm.

- [13 — The minimum-gap floor](issues/13-minimum-gap-floor-is-undeclared.md)
  — the rule stays, by owner decision with the trade-off on the table: the
  gap is held to the pillar aspect limit as a declared conservative
  fabrication policy (it would refuse a published 16 nm-gap device). The
  counting wall keeps only two knobs: the lateral step and the
  all-three-quantizations rule.

- [04 — Where the solver-native material sample is taken](issues/04-material-sample-point-and-binding.md)
  — at qualification, `getindex` over a registered wavelength grid through
  the probe's session; the sample is a separate document citing the binding
  (binding bytes unchanged); fit targets and the `|getfdtdindex - getindex|`
  residual are recorded; out-of-band wavelengths are findings;
  `_bind_material` stays session-free and permit-free.

- [06 — Share the coverage predicate](issues/06-share-the-coverage-predicate.md)
  — the full three-stage predicate (`covers_uniform_levels`: existence plus
  distinct assignment) moves into `science/phase.py`; loss weighting stays in
  the route; names join `phase.__all__` only; byte-neutral via
  `cyclic_distance` as the sole comparison primitive.

- [05 — The model pair, and what makes one-way exclusion safe](issues/05-model-pair-and-exclusion-safety.md)
  — three tiers finalised: arithmetic exclusion hard per quantization;
  bounded exclusion currently uses only the loose ambient-to-pillar material
  interval; exact isolated-pillar and Rytov roots remain non-authorizing
  forecast models until a cross-geometry proof and certified
  special-function arithmetic exist. Missing forecast support is reported as
  `forecast insufficient`; it never creates a verdict.

- [14 — The counting wall: which knob moves](issues/14-the-counting-wall.md)
  — both: the lateral step becomes a period-hooked fabrication-granularity
  policy (5 nm below a 300 nm period, 10 nm otherwise), and the
  all-three-quantizations rule is retired for independently satisfiable
  quantizations, aligning code with `CONTEXT.md:47`. Result: 355 nm
  delivers 8/12 levels, 400 nm delivers all three.

- [15 — Two defects on the compiler's fabrication-domain path](issues/15-compiler-fabrication-domain-defects.md)
  — refusal unifies in the evidence layer: the compiler's emptiness raise
  and its max-height minimum feature both retire; `HeightDomain` computes
  per-height bounds; one refusal path, no dual truth.

- [17 — Re-read the phase from a raw field monitor](issues/17-reread-phase-from-a-raw-field-monitor.md)
  — **extraction correct, void stands**: plane-averaged raw phase equals
  `S21_G0` phase up to one global constant (2.7443 ± 0.0019 rad across six
  candidates), amplitudes match to 0.2%, one frequency point only, analysis
  reproduces the recorded observations bit-for-bit. The erratic phase is
  physics. Ticket 11 unblocked.

- [10 — What a refusal offers](issues/10-what-a-refusal-offers.md)
  — refusals state arithmetic facts only (counts, walls, ceilings, bounds),
  never inverse recommendations and never adviser prose; regression
  baseline is the 400 nm pair, feasible without tuning; 355 nm awaits
  ticket 16.

- [11 — Disposition of the voided evidence](issues/11-disposition-of-voided-evidence.md)
  — leave ledger and run directories exactly as they are (ticket 17 was
  possible only because they were kept); forward legibility via the
  physical period and order regime in future run manifests.

- [09 — Measure licence seat occupancy](issues/09-measure-licence-seat-occupancy.md)
  — **different pools**: the CAD session draws `lumerical_gui`, the engine
  draws `lumerical_solve`, 500 seats each; session reuse does not halve
  concurrency and ships with no capacity-rule change. Bonus defect: the
  probe's lmstat regex fails on FlexNet's singular "1 license in use" —
  spec must fix.

- [12 — CONTEXT.md terminology revision](issues/12-context-terminology-revision.md)
  — W1-W9 ratified and written into `CONTEXT.md`: height domain rewritten;
  new entries phase envelope, height reach, optical contrast, order regime,
  sampling/order ceilings, aspect limit; material sample extended; avoided
  language gains `single order`, `admissible period`, `n_eff`.

- [16 — Is the geometric route the honest deliverable at 355 nm?](issues/16-geometric-route-as-the-alternative.md)
  — all four briefs stay; expectations become the regression contract:
  355 propagation delivers 8/12 and honestly refuses 16; 355 geometric is
  feasible and becomes the geometric showcase (PB needs one good cell —
  the counting wall does not bite); 400 propagation delivers all three.
  Emphasis: 355 → geometric, 400 → propagation.

- [Rework the advice seam](issues/08-advice-seam-rework.md)
  — superseded in placement by the external review: the application seam
  answers the advice finding and recompiles; `choose_height` only chooses.

- [07 — Fix the PhaseEnvelope and HeightReach field set](issues/07-phase-envelope-field-set.md)
  — fixed from the filled prototype and tightened after the owner's Sonnet
  challenge: one per-quantization `standings` table (merging the
  prototype's duplicated verdict lists), single `bounded_reasoning`,
  `forecast`, and `applicability` blocks, optional absent-when-undefined
  adjacent step, reference-only `source_references`, and one global
  `bound_checks` block. Golden fixture cut from the prototype at
  implementation time.

- [What the phase envelope records as checks](issues/26-phase-envelope-checks.md)
  — references name immutable inputs; one global `bound_checks` block carries
  the certified endpoint and ordering evidence that may authorize exclusion.

- [The durable provenance of the period rule](issues/27-period-rule-provenance.md)
  — a concise Research Record owns the literature and derivation; ADR 0005
  alone owns the accepted rule. Scratch history is not durable provenance.

- [The triage role of a closed decision](issues/28-closed-decision-role.md)
  — five triage roles remain unchanged; `resolved (YYYY-MM-DD)` is the one
  local-decision closure value, not a sixth role or a parallel state field.

- [Public-seam acceptance](issues/29-public-seam-acceptance.md)
  — three natural tests share only `propose -> admit -> replay -> mean`; the
  typed Authority calls remain visible and no seam harness owns their stories.

- [The durable source of the golden envelope fixture](issues/30-golden-envelope-fixture.md)
  — an independent derivation proposes, human review accepts, two fixtures
  remember, and one production test compares exact public bytes.

### Findings that forced this map

- The 355 nm sweep ran at period 630 nm against a subwavelength bound of
  240.5 nm — 2.62x over, with 9 propagating transmitted orders. `power.useful`
  is `T_G0`; 15 of 46 candidates kept under 30% of their power in the zeroth
  order, one as low as 0.37%. That evidence is scientifically void, not merely
  negative.
- `T_G0 / |S21_G0|^2 = n_air / n_sub` holds at `1/1.476078` across all 46
  candidates with spread `2e-15`, recovering the solver-native silica index
  exactly from admitted evidence at zero solver cost.
- `compile.py:263` uses the Nyquist sampling bound `lambda/(2*NA)` and omits the
  diffraction bound. A pure compiler cannot compute the latter — it needs an
  index — which is what forces the correction into the evidence layer.
- **Corrected 2026-07-26 — the original wording of this finding was refuted.**
  It claimed a corrected period plus `aspect_limit=8` and Si3N4 makes every
  standard brief infeasible *because* phase span falls short and every
  one-turn configuration overshoots the `2*pi/16` step budget by roughly 2x.
  The conclusion holds; all three reasons were wrong. An independent converged
  Fourier-modal solver reached 1.04-1.18 turns at every height 500-800 nm at a
  270 nm period, and the worst step overshoot reproduced was 1.28x, not 2x.
  The corrected finding:

  > Under any defensible corrected period (270 nm and below) every current
  > standard brief refuses, but the refusal lands on **candidate count**, not
  > on phase span. `form_phase_sets` (`propagation_phase.py:493-497`) requires
  > all three of 8/12/16 to succeed, and `propagation_phase.py:572-573` raises
  > `cell_library_insufficient:16` before span is ever examined. The count is
  > fixed by three code constants acting together — the minimum-gap floor at
  > `height.py:321`, the 10 nm lateral step at `compile.py:276`, and the
  > all-three-quantizations rule. At a 10 nm step no (period <= 270 nm,
  > height 500-800 nm) pair reaches 16 candidates at all. At a 5 nm step,
  > 270 nm works for heights 500-650 and 240 nm for 500-650, while 200 nm
  > fails at every height (15 candidates at best). Whether span reaches one
  > turn is secondary, and the single-pillar model can only bound span from
  > **below**, so it can never establish infeasibility.

  The teeth of this effort are arithmetic, not physics.

- The admissible-period rule has **no single citable standard**, and the
  literature does not adjudicate which medium's index enters it. Two families
  run in parallel: the zeroth-order-grating condition
  `P/lambda <= 1 / [max(n_i, n_t) + n_i*sin(theta)]` (Delacroix et al., Proc.
  SPIE 7731, 77314W (2010), Eq. 1), which degenerates to `P < lambda/n_max` at
  normal incidence and binds **both** sides; and the Nyquist sampling condition
  `P <= lambda/(2*NA)`, which is the only one Ansys states. `lambda/(n_sub+NA)`
  appears verbatim in no primary source — it is the real-space form of the
  light-cone criterion `G >= k + k0` (eLight 5, 28 (2025)) and must be recorded
  in an ADR as *derived*, never as cited. Arbabi et al., Nat. Nanotechnol. 10,
  937 (2015) judge both sides; Byrnes et al., Opt. Express 24, 5110 (2016) treat
  substrate-side leakage as pure loss and call that conservative. No primary
  source argues the substrate condition may be dropped. The four candidate
  bounds, recomputed against the evidence-recovered silica index:

  | brief | `l/(2NA)` Nyquist | `l/(1+NA)` air cone | `l/n_sub` normal | `l/(n_sub+NA)` silica cone |
  |---|---|---|---|---|
  | 355 nm, NA 0.28 | 633.93 -> **630** | 277.34 -> **270** | 240.50 -> **240** | 202.15 -> **200** |
  | 400 nm, NA 0.30 | 666.67 -> **660** | 307.69 -> **300** | 272.09 -> **270** | 225.98 -> **220** |

  At this NA the Nyquist bound is nearly toothless — the index family always
  binds. Flooring an upper bound to 10 nm (`compile.py:264-266`) is safe and
  stays.

- `single order` collides with an established published meaning: "Single-Order
  Transmission Diffraction Gratings" (J. Opt. Soc. Am. A 33, 1641 (2016)) names
  dispersion-engineered gratings that concentrate power into the zeroth order —
  a different thing. Ticket 03 should take `zeroth order` / `multi order`, or
  reuse the literature's `subwavelength`.

## Not yet specified

Nothing. Every child decision is closed, and [spec.md](spec.md) with tickets
18–23 is the sole implementation road.

## Out of scope

- **RCWA in any form** — Lumerical RCWA still needs a session, and a qualified
  Python RCWA is a separate effort with its own qualification burden.
- **Any Rust change** — the authority core is frozen for this effort.
- **Replacing FDTD evidence with a forecast** — the envelope gates work; it
  closes only its narrow `phase_envelope` claim and never closes periodic
  transmission, a cell library, or a phase set.
- **A resident hidden session per lane** — the advanced throughput step. It
  needs session-crash, licence, lane-retirement, and project-cleanup semantics
  that this map deliberately does not open.
- **Repo-wide CSU debt cleanup** — 113 hard violations and 1702 under-review
  findings across `src` (2026-07-26 baseline). This effort clears only the
  files it touches; the rest is its own effort with its own map.
