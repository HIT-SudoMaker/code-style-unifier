# Wayfinder

This folder is the local Markdown issue tracker for the restoration reset.
It keeps decisions separate from the documents and code they will eventually
govern.

## Wayfinding Operations

- A map carries `label: wayfinder:map`.
- Every ticket names its parent map and one of `research`, `prototype`,
  `grilling`, or `task`.
- `status: open` means unclaimed; `status: claimed` names the active assignee;
  `status: closed` includes a `## Resolution` section.
- `blocked_by` lists ticket titles. A ticket is on the frontier only when every
  listed ticket is closed.
- Claim a ticket before working it. Close at most one non-research ticket per
  session.
- When a ticket closes, append one linked gist to the map's
  `Decisions so far`; keep the detailed answer in the ticket.
- Create tickets before wiring new dependencies. Unshaped questions remain in
  the map's `Not yet specified` section.

The canonical map is [`restoration-map.md`](restoration-map.md).
