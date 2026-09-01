# 04 — Let propagation branches return together

Type: bug fix

Status: resolved (2026-07-29)

Blocked by: ticket 03.

## Outcome

One application advance records all returned scientific branches in one
immutable checkpoint, and replay restores them together.

## Problem

Propagation phase may form independent 8-, 12-, and 16-state phase sets.
`LocalScience.advance` currently admits one checkpoint per returned branch,
while replay returns only the latest checkpoint for the brief. A crash can
therefore collapse a valid multi-result frontier to its last branch.

## Scope

1. Change checkpoint remember/recall to accept and return the complete branch
   tuple produced by one advance.
2. Store one checkpoint document per advance.
3. Retain the complete `PhaseSetFormation` outcome in that checkpoint:
   delivered levels and refused levels with exact reasons.
4. Order propagation branches by `PhaseSet.levels`.
5. Preserve one refusal branch when no quantization can form.
6. Keep geometric phase as one branch: one selected anisotropic cell and
   continuous analytic orientations.
7. Replace the checkpoint shape directly. Preserve existing run artifacts, but
   do not read the old checkpoint shape.

## Acceptance

- A propagation advance that forms 8/12/16 admits one checkpoint and recalls
  three branches in that order.
- If only 8 and 12 form, replay recalls exactly those two branches and never
  manufactures 16; the same checkpoint reports the exact 16-state refusal.
- If none form, replay recalls the exact refusal branch.
- A crash after checkpoint admission cannot reduce the recalled set to the
  latest branch.
- A geometric advance recalls exactly one branch and contains no phase-set
  quantization.
- Repeated replay is deterministic and starts no adviser, solver, or Torch
  work.
- No mutable branch status, progress database, or compatibility reader exists.
- Rust is unchanged.

## Focused tests

- 8/12/16 round trip;
- partial 8/12 round trip retaining the 16-state refusal report;
- total refusal round trip;
- geometric single-branch round trip;
- repeated recall byte identity;
- architecture assertion that 8/12/16 language stays propagation-only.

## Do not add

Do not quantize geometric orientations, create a universal branch manager, or
store one mutable checkpoint row per branch.
