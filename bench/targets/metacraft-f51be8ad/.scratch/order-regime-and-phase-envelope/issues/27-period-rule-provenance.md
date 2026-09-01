# The durable provenance of the period rule

**Type:** `wayfinder:grilling`

**Status:** resolved (2026-07-26)

**Assignee:** Codex

**Parent:** [Order regime and phase envelope](../map.md)

**Blocked by:** None — on the frontier.

## Question

What durable artifact owns the literature reading and derivation behind the
zeroth-order period rule?

ADR 0005 currently points into this scratch map and says that no separate
Research Record exists. Repository traceability asks consequential decisions
to preserve `research record -> ADR -> spec -> ticket -> test`, or to record an
explicit reason when a stage does not apply. Decide whether to extract the
existing map findings into a Research Record or declare the research stage
not applicable and make the ADR fully self-contained.

Recommended answer: create one concise Research Record for the light-cone
derivation and make ADR 0005 cite it; `.scratch/` must not be durable
provenance for an accepted system decision.

## Resolution (2026-07-26)

Accepted by the owner as the Sonnet boundary:

- [Zeroth-order period rule](../../../docs/research/2026-07-26-zeroth-order-period-rule.md)
  owns the literature facts, derivation, assumptions, and applicability
  limits.
- [ADR 0005](../../../docs/adr/0005-derive-the-cell-period-from-the-zeroth-order-condition.md)
  owns MetaCraft's accepted rule and its consequences.
- The spec, implementation ticket, and tests carry the rule forward without
  repeating its scientific derivation.
- `.scratch/` remains planning history and is never the sole durable
  provenance of an accepted system decision.
