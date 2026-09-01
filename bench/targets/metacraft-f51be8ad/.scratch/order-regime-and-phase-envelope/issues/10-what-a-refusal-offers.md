# 10 — What a refusal offers, and what we regress against

**Type:** `wayfinder:grilling`

**Status:** resolved (2026-07-26)

**Blocked by:** 05 (resolved 2026-07-26); ticket 14 above it also resolved.

## Question

The corrected period plus `aspect_limit=8` and Si3N4 rules out every current
standard brief. What does the system hand back, and what do we test against?

- A bare `phase_reach_insufficient` leaves no way forward. Should the refusal
  report the feasible boundary — the aspect limit, lateral step, or index that
  would admit coverage — and is that a finding payload, a document field, or
  something the adviser is asked to explain?
- Reporting a required index edges toward recommending a material the brief did
  not declare. Where is the line between reporting a boundary and choosing for
  the user?
- Every brief in `examples/briefs.py` will refuse. Do we need a feasible
  regression brief, and what changes to make it feasible — a longer wavelength,
  a higher-index atom, a relaxed aspect limit? Whatever is chosen must be
  physically defensible, not tuned to pass.
- `lateral_step_nm` is hardcoded to 10 nm at `compile.py:276` and becomes a
  binding constraint at a 200 nm period. Does the refusal name it, and does that
  make it a brief fact rather than a compiler constant?
- Refusal must yield an unfinished `Study` carrying findings, never an exception
  and never a failed FDTD task. Confirm the path through
  `conduct.py:132-157` when `advance` cannot progress.

## Resolution (2026-07-26)

**The refusal states arithmetic facts and nothing else.**

- Payload per refused quantization: the candidate count and the required
  count, which wall bit (arithmetic count or bounded span), the current
  values of the two ceilings, the step, the aspect limit, and the
  per-height feature bounds — every number recomputable from admitted
  evidence.
- No inverse recommendations: the refusal names no step, aspect, index, or
  material that would pass. Reporting the boundary is arithmetic; choosing
  among the ways out is the user's move. The line between reporting and
  choosing sits exactly where CONTEXT places advice — outside evidence.
- The adviser is not asked to explain refusals; determinism holds. The AI
  reads findings as inputs on the next study.
- Regression baseline: the 400 nm pair, feasible under the corrected rules
  without tuning (19 candidates at 5 nm; all three quantizations). The
  355 nm demonstration awaits ticket 16.
- Delivery was settled by ticket 15 (findings on an unfinished Study, never
  an exception); the step policy by ticket 14.
