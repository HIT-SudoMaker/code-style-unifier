# Evidence-gated Restoration endgame

- Status: active execution sequence
- Goal: obtain a defensible `continue / narrow / kill` decision before adding
  hardware or learning complexity
- Protected: Fixed archive, `data`, `layers`, `data/raw`, protocol assets, and
  `refresh_workspace.py`

Implementation checkpoint (2026-08-16): Day 1 action-space semantics and Day 2
software boundaries are complete on the architecture experiment branch. The
distribution evidence, physical metrology, and go/no-go decision are not.

## Exit contract

The design is ready for the claim-facing bench only when the oracle ladder is
physically distinct, one truth-blind episode preserves complete causal
evidence, the same-device fallback survives controls, and the hardware handoff
can replace simulation Adapters without changing the episode semantics.

## Day 1 — Repair and run the truth gate

- Replace the current phase-only O1 placeholder with a genuine arbitrary-
  complex physics upper bound.
- Keep O2 as ideal reference-assisted phase-only and O3 as calibrated
  delivered phase-only.
- Use the same clean endpoint, active crop, scene identities, and typed gain
  denominators.
- Run held-out light/medium/heavy scenes and report uncertainty rather than one
  selected image.

**Exit:** O1/O2/O3 answer three different questions with typed clean and
aberration-removal endpoints. A clean-headroom failure kills or narrows the
joint-restoration upgrade; it does not erase a separately supported
differential-correction core.

## Day 2 — Close information and evidence boundaries

- Keep SLM1 replay construction inside its input Adapter.
- Permit controlled replay to expose command (D), but not clean (X), hidden
  aberration, evaluator state, or oracle action.
- Centralize calibrated prediction, delivered projection, reachability, and
  Echo prediction behind one calibration identity. Calibrated uncertainty is
  a Day 3 distribution result, not a deterministic simulator field.
- Preserve locked predictions, raw frames, commands, delivered states,
  thresholds, decisions, dose, timing, every trial exposure, and prospective
  science in one write-once episode record. Score trial harm later with
  evaluator-only outcomes rather than inventing it inside the policy.

**Exit:** no ideal-propagator bypass and no runner-specific partial evidence.

## Day 3 — Falsify the same-device mechanism

- Run the `4 pre + 4 Echo + 1 science` episode against defocus, astigmatism,
  and one held-out mixture at two RMS levels.
- Compare safe, wrong-sign, equal-RMS random, phase conjugation, O2, and O3.
  Add `D-only` and `D + pre` as the conditional joint-restoration gate.
- Inject low SNR, delivery gain error, drift, registration error, and Echo
  mismatch; require abstain or revert where correction is unsupported.
- Keep B2-to-B0 removal and B2-to-clean fidelity separate.

**Exit:** mechanism evidence includes favourable, harmful, reverted, and
abstained episodes under matched budgets.

## Day 4 — Freeze the decision and prepare hardware

- Produce the distribution summary, coverage-risk curve, delivered-oracle
  regret, false-admit/false-reject rates, and complete event ledger.
- Draw a dated as-built topology diagram and measure the V-relay parity,
  conjugacy, scale, pupil, LUT, registration, timing, and current `RA-U` input
  route.
- Select NPBS or small-angle input extraction only from 638 nm metrology.
- If all gates pass, specify one removable processing-pupil passive-aberrator
  cartridge and its independent calibration. Otherwise narrow or kill.

**Exit:** one signed go/no-go record; no custom phase plate, third SLM, native
specimen, or learned policy is added to rescue a failed gate.

## Code order

1. ~~correct Oracle Ladder semantics~~;
2. ~~tighten the replay/episode information Seam~~;
3. ~~deepen calibrated prediction and reachability~~;
4. ~~make episode evidence canonical~~;
5. complete the same-device distribution and controls;
6. add an independent-aberrator Adapter only after the gate passes.

## Formal stop rules

- O1 has no clean headroom;
- O2 has no headroom when O1 does;
- O3 is no larger than repeatability or its confidence interval;
- `D + pre` does not improve decision value over matched `D-only`;
- Echo cannot distinguish conforming from failed delivery;
- later science affects its own action/admission decision;
- reference-on advantage vanishes under matched power, dose, and clock;
- same-SLM evidence is described as independent or native AO.
