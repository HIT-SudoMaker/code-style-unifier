# 05 — Converge local language and ratchet the architecture

**Type:** implementation (spec closure)

**Status:** wontfix

**Superseded by:** `../../metalens-sonnet-convergence/spec.md`

**Depends on:** tickets 01-04

## What to build

Finish the source audit without aesthetic churn.

- `workstation.Cpu` becomes `LogicalProcessor`; its identifiers, physical
  core, cache index, NUMA memory, demand, command, handle, and SMT fields use
  exact natural names.
- Route-local discardable receipt maps become `PropagationCache` and
  `GeometricCache`.
- Private helpers use verbs that disclose whether they require, restore,
  form, assemble, propagate, or evaluate.
- `numpy` replaces the local production alias `np`.
- Bare public coordinate and result fields gain their scientific noun and
  unit.
- Boolean fields become one readable proposition or a typed origin/status;
  mixed `native` and `synthetic` provenance is separated.

Add AST and dependency ratchets for the accepted vocabulary, Field boundary,
single Authority adapter, small Lumerical export surface, and unchanged Rust
tree. Delete dead compatibility exports and uncalled legacy modules.

## TDD seam

Exercise workstation `plan` and the standard public package imports, then run
both standard briefs through `conduct`. Architecture tests inspect production
AST and dependencies, not private call counts.

## Acceptance

- Forbidden production identifiers include `PhaseMethod`, `phase_method`,
  `CellPolicy`, `propagate_scalar_field`, `propagate_channel_fields`, bare
  `kx`/`ky`/`kz`, and public `is_vector`.
- Axis literals, unit suffixes, established technology nouns, and exact native
  strings at their boundary remain allowed.
- `Brief -> compile_study -> Study -> conduct -> Result` remains unchanged.
- Workstation placement remains four physical cores, no SMT siblings, one
  locality cell, and 16 GiB per lane.
- Full non-live Python suite passes.
- Touched files pass CSU with zero hard violations.
- `git diff -- rust` is empty.

## Do not rename

Keep the accurate short nouns `Field`, `Cell`, `Aperture`, `Lane`, `Brief`,
`Study`, `Method`, `Route`, `Proof`, `Binding`, and `Result`. Do not rewrite
equations, vendor API names, or unrelated prose for visual uniformity.
