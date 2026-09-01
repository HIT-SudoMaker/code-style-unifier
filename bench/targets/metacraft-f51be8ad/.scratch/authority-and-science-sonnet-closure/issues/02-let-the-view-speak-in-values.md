# 02 — Let the view speak in values

Type: implementation

Status: resolved (2026-07-29)

Blocked by: ticket 01.

## Outcome

The Python authority Adapter decodes Rust wire mappings once and exposes
immutable `Current`, `AdmittedDecision`, and `Permit` values inside
`AuthorityView`.

## Scope

1. Add the three values beside the existing authority protocol values.
2. Make `AuthorityView.from_mapping` validate and decode its `current`,
   `decisions`, and `permits` collections.
3. Move reference decoding into those values.
4. Update runner, replay, conduct, and Lumerical callers to use attributes
   rather than raw key lookup.
5. Preserve the Rust bytes and proposal/decision protocol exactly.

## Acceptance

- `AuthorityView.current` is `tuple[Current, ...]`.
- `AuthorityView.decisions` is `tuple[AdmittedDecision, ...]`.
- `AuthorityView.permits` is `tuple[Permit, ...]`.
- Malformed nested mappings fail at `AuthorityView.from_mapping`.
- No caller outside the authority Adapter parses `state`, `close_reason`,
  `key`, `body_reference`, `receipt_body_reference`, or `superseded` from a
  view mapping.
- Replay and permit scheduling retain their current behavior.
- Rust source and the Rust protocol fixture are unchanged.

## Focused tests

- decode one complete view and compare all three value collections;
- reject malformed references and invalid permit states;
- replay one record/current chain through typed decisions;
- reserve, consume, close, and inspect permits through typed values;
- architecture scan for retired raw view-key parsing.

## Do not add

Do not add mutable projection objects, mapping compatibility properties,
generic deserializers, or a duplicate Python lifecycle.
