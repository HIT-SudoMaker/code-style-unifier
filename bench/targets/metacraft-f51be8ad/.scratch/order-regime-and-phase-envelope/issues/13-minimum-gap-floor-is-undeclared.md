# 13 — The minimum-gap floor at `height.py:321` is an undeclared physical claim

**Type:** `wayfinder:grilling`

**Blocked by:** None — on the frontier.

**Status:** resolved (2026-07-26)

## Question

Is the gap required to obey the same aspect ratio as the pillar, and did anyone
ever decide that?

`height.py:312-320` computes `minimum_feature_nm = ceil(height / aspect_limit)`
onto the lateral step. That is the **pillar** aspect ratio — the brief says
"keep the aspect ratio at or below 8:1", meaning height over diameter. Then
`height.py:321` returns `period_nm - minimum_feature_nm` as the maximum
diameter, which silently asserts that the **gap** must also be at least
`height / aspect_limit`. Nobody declared that. `compile.py:273` duplicates it.

It matters now because the gap floor is one of the three constants that fix the
candidate count, and the count is the only refusal path that currently fires.

- Is a gap etch aspect ratio the same fabrication limit as a pillar aspect
  ratio? A published, fabricated Si3N4 UV metalens — Nanomaterials 10, 1439
  (2020), period 200 nm, height 600 nm, diameter 60-184 nm on glass, full 2*pi
  at 290 nm — implies a 16 nm minimum gap, a gap aspect ratio of 37.5. Its
  smallest pillar has aspect ratio 10, itself above this repo's limit of 8.
  **The current rule would reject a device that exists.**
- If the two limits are different, does the brief need to declare both, and what
  are they called? `aspect_limit` alone can no longer carry both meanings.
- If the gap floor is dropped or loosened, what replaces it — a minimum gap in
  nm, a separate gap aspect limit, or nothing?
- What does the maximum diameter become? `PropagationCell.__post_init__`
  (`propagation_phase.py:51-52`) independently rejects `diameter >= period`, so
  some floor is still needed.
- Does relaxing this weaken any claim already admitted, or is it purely a
  loosening of a constraint that was never justified?

This blocks ticket 14, because which knob to move depends on whether this one
was ever legitimate.

## Resolution (2026-07-26)

Decided by the map owner, with the reviewer's contrary recommendation and the
trade-off on the table: **the rule stays.** The gap is held to the same
aspect limit as the pillar — `maximum_feature = period - minimum_feature`
(`height.py:321`, duplicated at `compile.py:273`) — as a deliberate,
conservative fabrication policy of this laboratory. It is now declared, no
longer implicit, which is what this ticket asked for.

Consequences accepted explicitly:

- The published Si3N4 UV device with a 16 nm gap (gap aspect ratio 37.5,
  Nanomaterials 10, 1439 (2020)) would be refused here. That is a policy
  choice about this lab's process window, not a physics claim.
- The counting-wall table in ticket 14 stands as measured, and the gap floor
  is off the table as a knob — ticket 14 keeps only the lateral step and the
  all-three-quantizations rule.
- No new brief fact is introduced; `aspect_limit` deliberately carries both
  the pillar and the gap meaning, and the ticket-12 glossary entry must say
  so in words.
