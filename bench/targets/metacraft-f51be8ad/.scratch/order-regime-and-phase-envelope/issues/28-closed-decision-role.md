# The triage role of a closed decision

**Type:** `wayfinder:grilling`

**Status:** resolved (2026-07-26)

**Assignee:** Codex

**Parent:** [Order regime and phase envelope](../map.md)

**Blocked by:** None — on the frontier.

## Question

How does the local tracker represent a decision ticket that has been resolved
and closed?

The tracker says `Status` records a canonical triage role, but the canonical
set has no closed role while the seventeen completed decision tickets use
`resolved`. Re-labelling them `wontfix` would be false, and leaving an
undocumented sixth value makes queries unreliable. Decide whether `resolved`
joins the canonical role set or closure is represented separately from
triage.

Recommended answer: keep triage and lifecycle distinct. Add a canonical
`resolved` lifecycle value for closed local decisions and document that it is
not a triage role; open tickets continue to use the five triage roles.

## Resolution (2026-07-26)

Accepted by the owner.

- `Status` remains the single current-state field.
- Open tickets use one of the five canonical triage roles.
- A decision that has been accepted and recorded closes as
  `resolved (YYYY-MM-DD)`. This is a lifecycle value, not a triage role.
- `wontfix` retains its exact meaning and never substitutes for `resolved`.
- No parallel `State`, `Closed`, or `Resolution` field is introduced.
- Product specification and verification stages do not apply: this decision
  changes only the local tracker's metadata grammar.
