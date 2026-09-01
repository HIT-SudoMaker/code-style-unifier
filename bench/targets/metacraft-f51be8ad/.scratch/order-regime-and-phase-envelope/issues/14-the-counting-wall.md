# 14 — The counting wall: which knob moves

**Type:** `wayfinder:grilling`

**Blocked by:** 03, 13 (both resolved 2026-07-26) — now on the frontier.
Ticket 13 kept the gap floor, so only two knobs remain: the lateral step and
the all-three-quantizations rule.

**Status:** resolved (2026-07-26)

## Question

Under every defensible corrected period, every brief refuses on candidate count
before phase span is ever examined. At least one constant has to move. Which?

The wall: `form_phase_sets` (`propagation_phase.py:493-497`) builds all three of
the 8, 12 and 16 quantizations, so 16 binds; `propagation_phase.py:572-573`
raises `cell_library_insufficient:16` when fewer than 16 candidates exist.
Candidate count is
`|{d in [min_feature, period - min_feature] stepping by lateral_step}|`.

Measured counts under the repo's own rules:

```
lateral_step = 10 nm (compile.py:276 today)
  P=630   H500:50  H600:48  H700:46  H800:44
  P=270   H500:14  H600:12  H700:10  H800: 8
  P=240   H500:11  H600: 9  H700: 7  H800: 5
  P=200   H500: 7  H600: 5  H700: 3  H800: 0

lateral_step = 5 nm
  P=270   H500:29  H600:25  H700:19  H800:15
  P=240   H500:23  H600:19  H700:13  H800: 9
  P=200   H500:15  H600:11  H700: 5  H800: 0
```

At 10 nm no (period <= 270, height 500-800) pair reaches 16. At 5 nm, 270 nm
works for heights 500-650 and 240 nm for 500-650; 200 nm fails everywhere.

Three candidate knobs, and the decision is which of them is legitimately ours to
turn:

- **The minimum-gap floor** (`height.py:321`) — ticket 13 asks whether it was
  ever a real constraint. If it was not, this is the honest knob.
- **The 10 nm lateral step** (`compile.py:276`) — a repo policy constant, not a
  fabrication limit. Should it scale with the admissible period rather than sit
  fixed? Note it also sets the adjacent-step budget, so it moves both walls.
- **The all-three-quantizations rule** (`propagation_phase.py:493-497`) — must a
  study that supports 8 levels fail because it cannot support 16? Splitting the
  three quantizations into independently satisfiable results is a scientific
  decision, not a tuning knob.

Whatever moves must be defensible as physics or fabrication, never as tuning to
make a brief pass. This ticket sits above tickets 07 and 10: the refusal payload
and the envelope field set both depend on which wall is the live one.

## Resolution (2026-07-26)

Both remaining knobs move; neither is tuning:

- **The lateral step becomes a period-hooked policy**, declared as a
  fabrication-granularity fact: 5 nm when the physical period is below
  300 nm, 10 nm otherwise. The geometric route's analogue scales the same
  way; its exact value is fixed at spec time. The step also tightens the
  adjacent-step budget the envelope reports — it moves both walls in the
  honest direction.
- **The all-three-quantizations rule is retired** in favour of independently
  satisfiable quantizations. This aligns the code with `CONTEXT.md:47`,
  which already declares the three quantizations separate results — the
  code was stricter than the glossary, so this is a correction, not a
  loosening. A study delivers the quantizations it can prove and refuses
  the ones it cannot, each with its own finding.
- Post-change reality, from the measured table: 355 nm / P=200 / 5 nm tops
  out at 15 candidates — 8- and 12-level deliverable, 16-level refuses;
  400 nm / P=220 / 5 nm reaches 19 — all three deliverable. The gap floor
  stays per ticket 13.
- Whether the 355 nm demonstration moves to the geometric route is
  ticket 16 (numbers in flight).
