# 08 — Let fields share one store

Type: refactor

Status: resolved (2026-07-29)

Blocked by: ticket 07.

## Outcome

`Field` and `FocalRegion` share one private implementation for immutable
component-array storage while preserving separate scientific values, schemas,
and manifests.

## Scope

1. Extract the duplicated byte restoration, dtype/shape validation,
   media-type checks, reference mappings, and fetch closure from
   `field/evidence.py` and `science/metalens/focus_evidence.py`.
2. Place the implementation under the field package without exporting it from
   `metacraft_next.field`.
3. Let `Field` and `FocalRegion` each retain their own document constructor,
   scientific invariants, schema identifier, and source-reference rules.
4. Reuse the private implementation in local admission without creating a
   universal document codec.
5. Replace tests of retired helpers with tests through field and focal-region
   document interfaces.

## Acceptance

- One implementation owns array bytes, dtype, shape, media type, and component
  reference restoration.
- `Field` still records one sampled electromagnetic fact and its component
  basis.
- `FocalRegion` still records the metalens-specific axial/transverse
  observation.
- Their schema identifiers and manifest shapes remain distinct.
- The shared implementation imports no metalens focus, propagation, solver, or
  result meaning.
- No shared helper is public from `metacraft_next.field`.
- Deleting the shared implementation would recreate real duplicate rules in
  both callers.
- Rust is unchanged.

## Focused tests

- round-trip electric-only and electric-plus-magnetic `Field`;
- round-trip multi-plane `FocalRegion`;
- reject wrong dtype, shape, media type, and content reference through both
  public document interfaces;
- verify identical binary facts receive identical storage treatment;
- architecture assertion that the private storage module is not exported.

## Do not add

Do not merge `Field` and `FocalRegion`, add a universal schema registry,
serialize Torch workspaces, or expose a generic storage manager.
