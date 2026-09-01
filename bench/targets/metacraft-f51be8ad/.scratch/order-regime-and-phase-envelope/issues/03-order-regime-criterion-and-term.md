# 03 — The order regime: criterion and term

**Type:** `wayfinder:grilling`

**Blocked by:** None — on the frontier.

**Status:** resolved (2026-07-26)

## Question

Which criterion fixes the admissible period, and what do we call the fact?

- Normal-incidence suppression is `P < lambda / n_max`, giving 240.5 nm at
  355 nm. Including the lens's maximum deflection gives
  `P < lambda / (n_substrate + NA)`, giving 202.2 nm. The second is stricter but
  uses the whole-aperture NA, while a given cell's local deflection is smaller
  than that almost everywhere. Do we take the conservative global bound, or a
  position-dependent bound the cell library cannot express?
- Does the bound apply to both bounding media, or only the transmission side?
  The incident silica side carries 21 propagating reflected orders at the
  current period; reflection into higher orders is loss, not phase corruption.
- Is `order regime` the right term, paired with the existing `aperture regime`
  in `CONTEXT.md:97`, taking values `single order` / `multi order`?
- Where does the derived maximum live — a field on `HeightDomain`, or a value
  the domain computes and does not retain?
- What is the finding code when the compiled Nyquist period exceeds the
  admissible one, and does it name the admissible maximum so a human can act?

Also settle rounding: the current period floors to 10 nm at `compile.py:264`.
Flooring an upper bound is safe; confirm it stays that way.

## Comments

### 2026-07-26 — Claude Code, verification pass (position, not resolution)

- Proposed stance: one rule, `admissible period = min(lambda/(2*NA),
  lambda/(n_high + NA))` with `n_high` the larger sampled index of the two
  bounding media. A position-dependent bound cannot be expressed by a
  position-agnostic cell library, so the whole-aperture NA is the honest
  global worst case.
- The domain should *retain* the admissible period, not just compute it:
  `choose_height` (`height.py:199-204`) rebuilds the domain document
  byte-for-byte from the study, so anything the domain owns must be a
  retained, recomputable field anyway. Retaining also keeps the refusal
  auditable.
- Cross-fact for the finding payload: at a ~200 nm period the fabricable
  diameter grid holds well under 16 candidates
  (`_form_phase_set` raises `cell_library_insufficient` below `levels`,
  `propagation_phase.py:572`), so the refusal will usually bite on candidate
  count before span. The finding should name both the admissible maximum
  period and the resulting candidate count so a human sees which wall they
  hit. Ties into tickets 06 and 10.

## Resolution (2026-07-26)

Settled across two grilling rounds — the second after the literature findings
landed on the map. Recorded as [ADR 0005](../../../docs/adr/0005-derive-the-cell-period-from-the-zeroth-order-condition.md).

- **Criterion.** `period_nm = floor_10nm(min(lambda/(2*NA), lambda/(n_sub+NA)))`
  — whole-aperture NA, both bounding media, worst-case local deflection.
  `n_sub` is the solver-native sample at the brief wavelength (sampling seam:
  ticket 04). The rule is *derived*, not cited — ADR 0005 carries the
  derivation and sources; no primary source adjudicates one standard, and
  none drops the substrate condition. Landed values: 355 nm -> 200 nm,
  400 nm -> 220 nm. Position-dependent bounds rejected: the cell library is
  position-agnostic.
- **Term.** Glossary gains `order regime` with values `zeroth order` /
  `multi order`, pairing with `aperture regime`. "single order" abandoned —
  published collision (single-order transmission gratings, JOSA A 33, 1641).
  The criterion sentence is the *zeroth-order condition*. Wording lands in
  CONTEXT.md via ticket 12.
- **Two ceilings, one pair.** "Admissible period" is retired — it collides
  with the authority family admit/admitted/admission. The Nyquist bound is
  the `sampling ceiling` (the demoted `CellPolicy.period_nm`); the
  diffraction bound is the `order ceiling`; the physical period is the
  floored minimum of the two. Domain field: `order_ceiling_nm`. Existing
  "admissible" wording across map and tickets is cleaned in ticket 12.
- **Domain document is fully self-describing.** It retains the corrected
  physical `period_nm`, the `order_regime`, the `order_ceiling_nm`, and the
  substrate index sample value with its reference — a refusal audits from
  the document alone. The byte-exact rebuild discipline of `choose_height`
  (`height.py:199-204`) extends over the new fields.
- **Finding.** `zeroth_order_domain_empty`, distinct from the compiler's
  coarse `fabrication_domain_empty`, carrying the order ceiling, the sampled
  index, and per-height min/max feature and candidate counts. Delivery
  (unfinished Study, never an exception) is ticket 10's remit; the current
  `ValueError` escape is defect (1) of ticket 15.
- **Rounding.** Flooring the ceilings to 10 nm stays — flooring an upper
  bound is conservative.

Unblocking: ticket 14 now waits only on ticket 13; ticket 12 waits only on
ticket 04.

## Supersession (2026-07-27)

ADR 0007 supersedes the hard-cap portion of this resolution. The sampling
ceiling now selects the current physical period; the order ceiling remains in
the height domain as a diagnostic threshold. `multi order` produces the
non-blocking `higher orders possible` caution and no longer refuses work.
