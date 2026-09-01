# The height-advice grounds Interface

**Type:** `wayfinder:grilling`

**Status:** resolved (2026-07-26)

**Assignee:** Codex

**Parent:** [Order regime and phase envelope](../map.md)

**Blocked by:** None — on the frontier.

## Question

What exact Interface lets one height-advice operation serve both current
metalens routes without inventing a geometric phase envelope?

Ticket [Advice behind the envelope](22-advice-behind-the-envelope.md) writes
`recommend_height(brief, domain, envelope)` as required and then says the
geometric route passes no envelope. Decide whether the Interface uses one
keyword-only optional envelope with a route invariant, or two explicit route
verbs. The answer must preserve one meaning for `recommend_height`, reject a
missing propagation envelope, and reject a fabricated geometric envelope.

Recommended answer: one verb with
`envelope: PhaseEnvelope | None = None`, keyword-only; propagation requires it
and geometric forbids it.

## Resolution

**One height-advice verb accepts route-specific grounds without inventing a
second operation.**

- The Interface is
  `recommend_height(brief, domain, *, envelope: PhaseEnvelope | None = None)`.
- Propagation phase requires the exact admitted envelope for that domain.
  Missing or stale envelope grounds are rejected before consultation.
- Geometric phase requires `envelope is None`; supplying one is rejected.
  Its prompt reads only the brief and admitted height domain.
- `HeightAdvice.envelope_reference` is `Reference | None`: exact for
  propagation, absent for geometric. This is route-specific provenance, not a
  fabricated common denominator.
- `choose_height` keeps one meaning and validates the same invariant when it
  adopts the advice.

Owner confirmation: “可以，没问题。”
