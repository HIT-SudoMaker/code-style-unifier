# Let field evidence hide its storage

Type: implementation

Status: resolved (2026-07-29)

Blocked by:
[Let dependencies flow without return](03-let-dependencies-flow-without-return.md).

## Outcome

Field evidence presents complete semantic storage operations. Metalens focal
evidence owns focal meaning without importing dtype, raw-media, reference, or
array-restoration mechanics.

## Scope

1. Add a failing architecture seam that demonstrates the current seven-name
   storage leak from field evidence into metalens focal evidence.
2. Deepen the existing field evidence Module so it owns complete field
   component storage and restoration mechanics.
3. Keep byte order, dtype, raw media validation, reference matching, array
   shape validation, and component restoration private to field.
4. Keep FocalRegion schema, axial observations, realization, focus distances,
   and metalens-specific validation in metalens.
5. Remove pass-through imports of private helpers from `field.evidence`.
6. Preserve exact document and raw-object bytes.
7. Strengthen the architecture ratchet against cross-Module storage leakage.

## Acceptance

- Metalens focal evidence imports no private storage constants or helper
  functions.
- `field._storage` is not part of a public Interface.
- Field and FocalRegion documents and raw component references round-trip
  byte-identically.
- Electric and optional magnetic components preserve basis, shape, order,
  frame, medium, and exact source references.
- Field evidence remains reusable without knowing focus or metalens.
- No duplicate frame, reference, number, or array decoder is introduced.

## Focused tests

- field document and restoration round-trip;
- focal-region document and restoration round-trip;
- corrupt raw media, dtype, order, shape, basis, reference, and source;
- electric-only and electric-plus-magnetic fields;
- architecture import seam.

## Verification

- focused field, focus, replay, and architecture tests;
- Pyright;
- touched-file CSU;
- production Rust diff is empty;
- fixed-range `git diff --check`.

## Stop and report

Stop before changing field physics, FocalRegion schema meaning, raw bytes,
Torch propagation, result metrics, or Rust.

## Do not add

Do not add a public FieldStorage type, codec hierarchy, storage registry,
generic artifact framework, compatibility export, or second raw-object format.

## Resolution

Field evidence now admits, describes, and restores components through three
semantic operations. Raw array format, media validation, reference matching,
and restoration remain private to `field._storage`; focal evidence retains only
focal meaning.

Focused field, focus, replay, and architecture checks pass. Pyright reports no
errors, touched production files have no CSU hard violations, the fixed-range
diff is clean, and production Rust is unchanged. Direct baseline comparison
confirmed byte-identical Field and FocalRegion documents.
