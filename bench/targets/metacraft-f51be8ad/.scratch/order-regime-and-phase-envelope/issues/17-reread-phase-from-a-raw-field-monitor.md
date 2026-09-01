# 17 — Re-read the phase from a raw field monitor before retiring the evidence

**Type:** `wayfinder:task`

**Blocked by:** None — on the frontier.

**Status:** resolved (2026-07-26)

## Question

Before the 46-candidate sweep is declared void, run the one cheap check that can
distinguish "the cell diffracts" from "the phase extraction has a bug".

The whole map rests on the first reading. The second reading would be far worse
news, because an extraction bug follows us down to a 200 nm period and gets
*harder* to see there, not easier.

The check: take three or four already-solved candidates from
`runs/20260725t172432z-...-height-700nm/`, open their `engine.fsp`, and read the
transmitted phase from a **raw field monitor** rather than from the grating
analysis group's `S21_Gn`. Pick candidates spanning the useful-power range —
one healthy (d=140 nm, `T_G0 = 0.897`), one middling (d=300 nm, 0.070), one
collapsed (d=530 nm, 0.0068).

What each outcome means:

- Raw-monitor phase agrees with `S21_G0` and is equally erratic — the cell
  really is diffracting, `S21_G0` is one Fourier coefficient of a multi-order
  field, and the evidence is void for the reason the map says.
- Raw-monitor phase is smooth and monotonic while `S21_G0` is erratic — the
  extraction path is at fault, period is not the root cause, and shrinking the
  period fixes nothing. The map's central finding would need rewriting.

Current reading of the data favours the first: the phase curve is smooth and
slowly varying with adjacent steps mostly under 0.3 rad, the single -2.20 rad
jump sits at `T_G0 = 0.68%`, and amplitude resonates strongly with diameter
(0.897 down to 0.0037). That is what a real diffracting cell looks like, not
what an analysis bug looks like. But the map should not rest on a reading when a
ten-minute run can settle it.

The engine work is already done — this reopens saved projects and reads a
different monitor. No new solve is required.

**This blocks ticket 11:** nothing should be archived or retired until this
returns.

## Resolution (2026-07-26)

**Extraction correct — the void verdict stands.** Six candidates
(d = 90/140/210/300/400/530 nm) re-read from raw `T` monitor fields in the
saved projects, read-only, no solve, no save:

- The phase of the plane-averaged field — by definition the G0 Fourier
  coefficient — matches the recorded `S21_G0` phase up to one global
  constant, 2.7443 ± 0.0019 rad across all six, with |average field|
  matching |S21| to <= 0.2% on every candidate.
- The monitor holds exactly one frequency point (355.000 nm), so a wrong
  frequency index is impossible; the analysis group's
  `target_grating_order_out` is 0 as expected.
- Re-running the grating analysis on `after.fsp` reproduces the recorded
  `observation.json` values bit-for-bit; `T_G0 = |S21|^2 / n_glass` verifies
  numerically on every candidate — normalization is self-consistent.
- On-axis phase diverges from the averaged phase by up to 1.7 rad, and at
  d = 530 nm the on-axis |Ex| is 20x the plane average while G0 carries
  0.9% of the plane intensity — the direct signature of a multi-order
  field. The erratic phase is physics, not a bug.

Anomaly recorded: the in-project analysis group is named `grating_response`
(`cell.py:488-511`), not the qualification fixture's `grating_s_parameters`
(`probe.py:184`). Raw numbers: `phase_readback_results.json` in the session
scratchpad. Ticket 11 is unblocked; the map's central finding needs no
rewriting.
