# What the phase envelope records as checks

**Type:** `wayfinder:grilling`

**Status:** resolved (2026-07-26)

**Assignee:** Codex

**Parent:** [Order regime and phase envelope](../map.md)

**Blocked by:** None — on the frontier.

## Question

Where do the three deterministic sanity checks of a `PhaseEnvelope` live?

Ticket [Fix the PhaseEnvelope and HeightReach field set](07-phase-envelope-field-set.md)
and [The propagation envelope module](21-the-propagation-reach-module.md)
currently say that `source_references` carries rows proving the ceiling closes
to the pillar index, the floor closes to one, and the floor remains below the
ceiling. A reference names immutable bytes; it is not a calculation row.
Decide whether those checks are admitted fields on the envelope or
implementation-only assertions.

Recommended answer: keep `source_references` reference-only and add one
`bound_checks` block to the envelope, because a hard exclusion should carry
the checks that make its numerical derivation auditable.

## Resolution (2026-07-26)

Accepted by the owner.

- `source_references` contains references only: the exact admitted material
  sample, height domain, and solver binding used by the calculation.
- `bound_checks` is one envelope-level block, not repeated inside each
  `HeightReach`. It records three named checks:
  `ceiling_reaches_pillar`, `floor_reaches_ambient`, and
  `floor_stays_below_ceiling`.
- An endpoint check carries the expected endpoint and its certified interval
  or residual. The ordering check carries the minimum certified separation
  over the evaluated grid. Each check records whether it holds; it is not a
  bare boolean without its supporting values.
- A missing, failed, or uncertified bound check permits reported numbers but
  forbids a bounded-exclusion verdict.
- Public planning language uses *bound check*, never the vague
  `sanity_check`.
