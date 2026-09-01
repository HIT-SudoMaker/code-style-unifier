# 05 — The model pair, and what makes one-way exclusion safe

**Type:** `wayfinder:grilling`

**Blocked by:** 02 (resolved 2026-07-26) — now on the frontier

**Status:** resolved (2026-07-26)

## Question

Which estimators does the envelope run, and what argument makes `ruled out`
safe to act on?

- The charting prototype used the exact step-index fundamental-mode eigenvalue
  equation with an air cladding, plus Maxwell-Garnett for transverse E. Do both
  survive ticket 02's finding, and is the pair still the right one?
- Span and adjacent-step density are anti-correlated: a model predicting more
  span predicts a steeper curve and coarser steps. So no single model is
  optimistic on both. Does the exclusion rule therefore become "rule out only
  when *no* model in the pair passes the full coverage predicate", evaluated on
  each model's whole predicted curve?
- What are the declared applicability conditions — single-mode cutoff, minimum
  gap, normal incidence, lossless, single order — and what does the envelope
  return when the conditions do not hold? `not ruled out` and
  `not applicable` must be distinguishable.
- Absorbing materials give a complex index. Does the envelope refuse to forecast
  when k exceeds a threshold, or fold loss in?
- Does the envelope forecast every height in the domain, or only the one about
  to be advised? The map's chain puts it before advice, which argues for every
  height.
- If ticket 02 finds no rigorous bound, does exclusion survive at all, or does
  the envelope degrade to reporting numbers without a verdict?

## Resolution (2026-07-26)

Three tiers as amended on the map, with the tier-(b) upgrade adopted:

- **(a) Arithmetic exclusion** — hard verdict, evaluated per quantization
  (ticket 14 made the quantizations independently satisfiable).
- **(b) Bounded exclusion** — hard verdict from the rigorous chain
  `max(1, n_iso(d_min)) <= n_Bloch <= n_lamFSM(d_max) <= n_pillar`
  (ticket 02 addendum): rule a height out only when even the
  circumscribed-lamellar-FSM span bound cannot reach the required turns.
  One offline calibration against a converged Bloch solve before first use;
  calibration is a development check, never runtime behaviour.
- **(c) Model pair** — isolated-pillar and Maxwell-Garnett estimates report
  numbers only and never produce a verdict; the non-authorizing word is
  `forecast insufficient`.
- **Applicability** — single-mode failure (d >= 145 nm at 355 nm per
  ticket 02) and any absorbing-material threshold produce `not applicable`
  annotations on the affected reaches, never verdicts. The envelope
  forecasts every height in the domain, since it precedes advice.
- The estimators are the exact isolated-pillar eigenvalue equation and the
  Rytov-exact lamellar equations — one-dimensional root finding, no solver,
  no session, no float leaving the module.

## Correction (2026-07-26)

The primary-source audit in
`docs/research/2026-07-26-phase-envelope-certified-roots.md` supersedes the
tier-(b) upgrade above. It found no published proof that the HE11 and Rytov
roots bracket the real two-dimensional periodic pillar array, and ordinary
floating-point special functions do not provide certified root intervals.

The hard bounded tier therefore uses only the elementary material interval
`ambient index <= axial index <= pillar index`. HE11 and Rytov may later
provide named, non-authorizing forecasts; they cannot hard-refuse a height
without a separate cross-geometry proof and certified arithmetic.

## Comments

### 2026-07-26 — ticket 02 resolved; this ticket's premise has changed

Ticket 02 came back negative: the isolated-pillar index is a **lower** bound on
the array Bloch index, not an upper one, and Maxwell-Garnett is not a defensible
lower bound either. The intended optimistic model is gone. Three consequences:

- The question is no longer "which two models bracket the truth". It is
  "which verdicts survive when no model bounds span from above". The map's
  amended one-way-exclusion decision proposes three tiers — arithmetic
  exclusion, bounded exclusion, model-pair-reports-only — and this ticket has to
  finalise them.
- The only rigorous span ceiling is
  `turns_max <= H * (n_pillar - n_floor) / lambda`, with `n_floor` a strict
  lower bound on the smallest-diameter atom index. At 355 nm, H=500 and a floor
  of 1.0 it gives 1.59 turns, so it excludes nothing across 500-800 nm. Decide
  whether a bound that never bites is worth carrying.
- The "no single model is optimistic on both span and step density" premise in
  the original question is **partly dissolved**: the adjacent-step budget also
  has a model-free counting form, and the counting form is where the teeth are.
  Rewrite that bullet when resolving.

Two findings that retire open sub-questions:

- **Fabry-Perot / interface resonance is not a material omission.** Modelling
  `t = t1*t2*exp(i*delta) / (1 + r1*r2*exp(2i*delta))` with the modal index
  changes the phase span by at most 1% in every configuration tested
  (200 nm/H=500: 0.552 -> 0.553; 270/700: 1.392 -> 1.397; 630/700:
  2.004 -> 2.014). This retires the whole class of "the envelope ignores
  resonant phase enhancement" objections; record it as a stated applicability
  condition rather than an open risk.
- **Single-mode operation may be unsatisfiable where it matters.** At 355 nm the
  isolated pillar exceeds V = 2.405 at `d >= 145 nm`. If `single mode` stays an
  applicability condition, decide what the envelope returns over the multi-mode
  part of the diameter domain, and whether an envelope that is `not applicable`
  across most of its domain is worth shipping at all.
