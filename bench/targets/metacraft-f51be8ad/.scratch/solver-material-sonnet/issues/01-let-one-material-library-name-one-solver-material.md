# 01 — Let one material library name one solver material

Status: resolved (2026-07-30)

**Blocked by:** none.

**Specification:** [Solver-material Sonnet convergence](../spec.md).

## Outcome

Establish one pure, deterministic material-library Module whose small
Interface turns reviewed TOML bytes into exact solver-material values. Close
the material-source language in the same ticket so no later ticket inherits
two spellings for one source.

## Interface

```python
SolverMaterialLibrary.from_bytes(source_bytes)
library.select(solver, family)
```

The Module performs no file I/O. Application composition will own the file in
Ticket 02.

## Acceptance

- `MaterialSource` has exactly `local table`,
  `refractiveindex.info dataset`, and `solver native`.
- `MaterialIntent.source` and `MaterialRecord.source_kind` use that one type;
  the former underscore spellings leave production, fixtures, examples, and
  canonical documents without a compatibility decoder.
- Canonical brief, study, and material-record hashes changed by that semantic
  spelling are updated in this ticket, with the reason recorded beside the
  affected golden values.
- Local-table and refractiveindex.info parsing, validation, interpolation, and
  sampling behavior remain otherwise unchanged.
- `SolverMaterial` contains only `solver`, `family`, `native_name`, and
  `provenance`, and round-trips through
  `metacraft.material.solver_material`.
- `SolverMaterialLibrary.from_bytes` accepts exactly the top-level fields
  `solver` and `materials`; each material accepts exactly `family`,
  `native_name`, and `provenance`.
- Unknown or missing fields, malformed TOML, an unsupported solver, an invalid
  material-source value, duplicate families, and empty family, native name, or
  provenance fail directly.
- A family must already be its canonical natural lowercase form. The parser
  does not trim, fold, normalize, or repair any identity field.
- Distinct families may explicitly select the same exact native name; this is
  not treated as an alias or duplicate registration.
- `select` returns one exact value or one exact absence. It performs no alias,
  case folding, fuzzy matching, or substitution.
- Entry order cannot change canonical document bytes or selection.
- `materials/lumerical.toml` copies only locally confirmed material values
  from the ignored `.env.lumerical`, without printing or changing unrelated
  paths, licence values, or secrets. The old lines remain until their atomic
  retirement in Ticket 03.
- `materials/lumerical.toml` contains only locally confirmed registrations.
  Unconfirmed families are recorded by family only in
  `.scratch/solver-material-sonnet/pending-materials.md`; no value is guessed.
- Focused material, brief, canonical-document, and import-DAG tests pass.
- Rust source and manifest are unchanged; no live marker runs.

## Stop and report

- A canonical family cannot be expressed without introducing an alias or a
  second current registration.
- A changed golden identity cannot be explained solely by the canonical
  material-source spelling.

## Do not add

- File I/O inside the library;
- roles, wavelengths, optical constants, solver versions, active flags, or
  history in `SolverMaterial`;
- CRUD, a registry base class, providers, plugins, or any portable-material
  redesign beyond the canonical source-type migration.

## Verification

Implemented on 2026-07-30.

- Material, canonical-document, standard-study, canonical-case, and import-DAG
  seams: 70 passed.
- Directly affected geometric, pointwise, scientific-identity, and delivery
  seams: 39 passed.
- Pyright: zero errors and warnings.
- CSU: zero blocking findings on touched production Modules.
- Two-axis standards and specification review: pass after two boundary fixes.
- `git diff --check`: clean.
- Rust source and manifest: unchanged.
- No live marker, Adviser, Lumerical, Torch, or complete test-suite run.
