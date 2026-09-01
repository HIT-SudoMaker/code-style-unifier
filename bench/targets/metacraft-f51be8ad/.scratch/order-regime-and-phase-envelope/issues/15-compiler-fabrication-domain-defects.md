# 15 — Two defects on the compiler's fabrication-domain path

**Type:** `wayfinder:grilling`

**Blocked by:** None — on the frontier.

**Status:** resolved (2026-07-26)

## Question

Two concrete defects that a smaller period turns from harmless into
load-bearing. Both need a decision before the period changes.

**(1) An empty fabrication domain escapes as a bare `ValueError`.**

At a 200 nm period, `compile.py:268-275` computes
`minimum_feature = ceil(800/8) = 100`, `maximum_feature = 200 - 100 = 100`, and
hits `raise ValueError("fabrication_domain_empty")`. That is not
`BriefIncomplete` (`compile.py:33`), and `conduct.py:142-147` only catches
capacity-related `RuntimeError`s — so it escapes the whole pipeline. This
directly violates ticket 10's hard requirement that refusal yields an unfinished
`Study` carrying findings and never an exception.

Worse, the failure *mode* is period-dependent: at 220 nm compilation succeeds
and the run dies later at `cell_library_insufficient:16`. Twenty nanometres of
period changes which failure the user sees.

- Does `fabrication_domain_empty` become a `Finding` on an unfinished study, and
  under which `FindingKind` (`model.py:30`)?
- Should compilation refuse at all, or should the empty domain be discovered
  where the count wall is checked, so both refusals arrive by the same path?

**(2) Two different heights feed the same quantity.**

`compile.py:270` computes `minimum_feature` from `max(height_candidates) = 800`;
`height.py:312` recomputes it from the **chosen** height. The admitted 46-candidate
sweep (90-540 nm) went down the `height.py` path, so the compiler's value was
never the operative one.

- At a 630 nm period this inconsistency only wastes domain. At 200-270 nm it
  changes feasibility outright. Which height is correct for each use?
- Is the compiler-side value needed at all once `HeightDomain` owns the
  admissible period and recomputes bounds per height?

## Resolution (2026-07-26)

Refusal unifies in the evidence layer:

- **(1)** The compiler's `fabrication_domain_empty` raise is removed. The
  compiler performs structural validation only (`BriefIncomplete` stays);
  it cannot compute the real domain, because the real domain needs an
  index, which is evidence. Emptiness is discovered where it can be
  computed — the height-domain derivation — and lands as the
  `zeroth_order_domain_empty` finding on an unfinished Study. Payload and
  delivery are ticket 10's remit.
- **(2)** The compiler-side `minimum_feature` from `max(height_candidates)`
  is retired; `HeightDomain` computes per-height bounds and `height.py`
  stays the only rule. `CellPolicy` keeps the sampling ceiling and the
  step policy, and carries no feature bounds.
- One refusal path, one rule, no dual truth. The failure mode no longer
  depends on which side of 20 nm of period the brief lands.

## Supersession (2026-07-27)

ADR 0007 removes the order-ceiling refusal. A genuinely empty per-height
fabrication domain may still remain an ordinary fabrication finding, but a
`multi order` classification is now a non-blocking caution.
