# Solver-material Sonnet convergence

Status: resolved (2026-07-30)

## Research basis

This specification implements the boundary established by:

- [Solver-native materials in FDTD and CST](../../docs/research/2026-07-12-solver-native-materials-fdtd-cst.md),
  which establishes exact solver ownership and rejects cross-solver
  substitution; and
- [Lumerical index-read semantics](../../docs/research/2026-07-26-lumerical-index-read-semantics.md),
  which distinguishes database values from the fitted values used by FDTD and
  binds the latter to one fit span.

[ADR 0016](../../docs/adr/0016-let-materials-choose-and-solvers-verify.md)
turns those external facts into the system decision implemented here.

## Context

MetaCraft already separates portable material records, solver-native samples,
task-scoped material bindings, and qualified solver execution. Its first
Lumerical path nevertheless keeps the relationship between a canonical
material family and an exact native product name in `.env.lumerical`.

That decision was safe enough for two early materials, but it gives a product
configuration file scientific selection authority. The four canonical
metalens cases expose the mismatch: paper language names scientific materials,
the project must state which Lumerical record represents each material, and
the Adapter must verify what the installed 25v2 database actually contains.

## Problem

The current flow is:

```text
brief family
→ environment catalogue
→ exact native name
→ Lumerical sample
→ MaterialBinding
```

It has four weaknesses:

1. machine configuration owns a reusable scientific choice;
2. canonical families and native names have no admitted registration between
   them;
3. a changed registration reuses the old sample key and supersedes its
   meaning;
4. replay can recover the sample but cannot name the project selection that
   caused it.

Filling more `LUMERICAL_MATERIAL_*` variables would enlarge the mistake. Fuzzy
matching or automatic substitution would be worse: fused silica, silicon
dioxide, and glass may share a product record without becoming one scientific
material.

## Principle

> Materials choose, solvers verify; samples observe, bindings apply.

- The brief owns material intent.
- The project material library owns reusable selection.
- The run Authority owns the exact selection used.
- The solver Adapter owns native verification and read-back.
- The material sample owns observed optical data.
- MaterialBinding owns atom and substrate roles for one task.

One fact has one owner. Dependencies flow inward; evidence flows outward.
Rust remains unchanged.

## Architecture

### Project shape

```text
materials/
└── lumerical.toml

src/metacraft_next/materials/
├── portable.py
└── solver.py
```

`materials/lumerical.toml` is a reviewed project input:

```toml
solver = "lumerical fdtd"

[[materials]]
family = "fused silica"
native_name = "SiO2 (Glass) - Palik"
provenance = "confirmed against the local Lumerical material database"
```

The file contains at most one entry for each canonical family. It contains no
paths, license values, roles, wavelengths, optical constants, product version,
fit settings, aliases, active flags, or history chain. Git retains project
history; each run retains the selected snapshot.

### Domain values

The `materials` package owns:

```text
MaterialSource
```

`materials.solver` owns:

```text
SolverMaterial
AdmittedSolverMaterial
SolverMaterialLibrary
```

`MaterialSource` has exactly:

```text
local table
refractiveindex.info dataset
solver native
```

Both brief material intent and portable material-record provenance use this
one type. The migration changes canonical source spelling and identities, not
portable parsing, interpolation, or sampling behavior.

`SolverMaterial` contains:

```text
solver
family
native_name
provenance
```

Its canonical schema is `metacraft.material.solver_material`. All text is
non-empty. `solver` is the natural domain value `lumerical fdtd`; code and
filesystem identifiers continue to follow their language casing conventions.

`AdmittedSolverMaterial` couples one SolverMaterial to its exact Authority
Reference. It adds no behavior.

`SolverMaterialLibrary` has one small Interface:

```python
SolverMaterialLibrary.from_bytes(source_bytes)
library.select(solver, family)
```

The implementation owns TOML parsing, exact-field validation, duplicate
detection, deterministic ordering, and canonical document construction. The
top level accepts exactly `solver` and `materials`; each entry accepts exactly
`family`, `native_name`, and `provenance`. Missing or unknown fields, empty
text, a non-canonical lowercase family, an unsupported solver, and duplicate
families fail directly. Native names are preserved exactly. Distinct families
may explicitly select the same native name. Input order cannot change
canonical bytes.

### Composition

The application edge reads and validates `materials/lumerical.toml` once for
one fresh conduct opening, then passes the library explicitly:

```python
available_science(..., materials=library)
```

Neither `available_science` nor a scientific Module opens a project file.
The separate replay entry does not request or open the library.
When `material_binding` becomes ready:

1. select the atom and substrate SolverMaterial values;
2. admit only those values as immutable records in the run Authority;
3. couple each value to its returned Reference;
4. pass the admitted values and wavelength to Lumerical Dispatch.

Repeated atom and substrate families select, admit, and sample once. Selection
is scoped to the atom/substrate pair requested by the ready task; absent
registrations for another canonical case do not block it.

### Adapter seam

Lumerical Dispatch no longer accepts a family and looks it up in
`LumericalConfig`. It receives the already admitted solver materials:

```text
AdmittedSolverMaterial(s)
+ wavelength
```

The Adapter verifies:

- the solver value is exactly `lumerical fdtd`;
- each native name exists;
- read-back preserves family and native identity;
- the tabulated band covers the requested wavelength;
- every frequency, refractive index, extinction coefficient, fit residual, fit
  tolerance, and band endpoint is finite;
- fit coefficients and point arrays are non-empty, positive where required,
  shape-valid, deterministically ordered, and canonical.

It never opens the project material library, chooses an alias, normalizes a
native string, imports a replacement, or creates a material.

### Evidence closure

```text
SolverMaterial
    ↓ cited by
LumericalMaterialSample
    ↓ cited by
MaterialBinding
    ↓ consumed by
period, height, cell, result
```

The material-sample document retains registration references by family. Its
key is derived from the canonical encoding of:

```text
solver-binding identity
+ solver-material registration identities
+ requested wavelength
+ fit span
```

Each identity is the exact Authority `Reference`, not a family name or a lone
content-hash fragment.

A changed registration or fit span therefore creates a new sample identity
rather than superseding another observation beneath an old key.

MaterialBinding continues to retain task roles and the verified family/native
values needed by construction. Those denormalized values must equal the cited
sample. It cites the sample and solver binding; the sample is the direct owner
of registration references.

Replay follows admitted references only. It does not reopen TOML, read an
environment file, call Adviser, start Lumerical, or execute Torch.

### State and failure

Catalogue defects fail directly:

- malformed TOML;
- unknown or missing fields;
- duplicate family;
- invalid solver;
- empty family, native name, or provenance.

A non-canonical material-source value is a brief/domain-value defect and also
fails directly; it is not misreported as a catalogue defect.

Expected scientific absence returns the existing typed Finding/waiting path:

- `solver_material_not_registered`;
- `native_material_not_found`;
- `material_wavelength_uncovered`.

Invalid or identity-changing read-back is an Adapter defect and fails
directly. No new broad exception hierarchy is introduced.

### Migration

The existing ignored `.env.lumerical` is read once for migration of material
values only. Confirmed selections become reviewed entries in
`materials/lumerical.toml`. Material lines are then removed from the local
file.

Production support for `LUMERICAL_MATERIAL_*` is deleted in the same change.
No compatibility reader or dual-source precedence remains.
`.env.lumerical.example` retains only paths, licence, runs, capacity freshness,
and explicit execution switches.

Canonical case materials without a confirmed native record receive no
placeholder. `.scratch/solver-material-sonnet/pending-materials.md` names
missing families without suggesting values. Ticket 10 may open material smoke
only with one complete registered atom/substrate pair; a case sweep opens only
after the complete pair for that case is explicitly registered.

### Verification

Verification proceeds from narrow to broad:

1. domain-value, TOML, canonical-document, duplicate, and ordering tests;
2. run admission, repeated-family, and task-local preflight tests;
3. fake Adapter verification, sample-key, binding-closure, and waiting tests;
4. bounded downstream-result and zero-execution replay tests;
5. runtime-DAG ratchets, Pyright, and CSU;
6. one complete non-live suite at closure.

No implementation ticket enables a live marker, Adviser call, Lumerical
session, solver sweep, or canonical delivery.

### Delivery slices

1. **Name:** establish `MaterialSource`, `SolverMaterial`, the pure library
   Interface, reviewed registrations, and their canonical identities.
2. **Bind:** carry one selected and admitted atom/substrate pair through
   Dispatch into one verified `MaterialBinding`.
3. **Prove:** bind registration identity into the sample, harden read-back, and
   retire the environment catalogue without a compatibility path.
4. **Return:** prove downstream source reachability and zero-configuration
   replay, then return Ticket 10 to its human-only live frontier.

Each slice consumes every value it introduces and leaves its focused tests
green. The complete non-live suite runs once in the final slice.

## Trade-off

The project material library introduces one reviewed file and two small domain
values. In exchange, it removes an open-ended environment namespace, makes
selection replayable, and prevents the Adapter from interpreting scientific
language.

The design deliberately declines automatic discovery. Exact native records
may differ across installations, and a stable full-database enumeration
contract is not established. Human-reviewed registration followed by native
verification is slower than guessing once and safer than debugging a false
material later.

The design also declines a universal material registry. Portable records and
solver materials remain distinct deep Modules and meet only at
MaterialBinding. A second real solver may later reveal a useful shared
Interface; Lumerical alone does not justify one now.

## Conclusion

The resulting chain is short and closed:

```text
intent → selection → admission → observation → binding → result
```

The material library chooses once. Each run remembers exactly. Lumerical
verifies locally. Replay depends on evidence, not configuration.

## Do not add

- Rust changes;
- automatic aliases or fuzzy material matching;
- automatic `addmaterial`, import, or substitution;
- a generic solver registry, plugin system, or common solver Interface;
- environment compatibility for `LUMERICAL_MATERIAL_*`;
- a second Authority for the project material library;
- material roles, wavelength, optical constants, or solver version in
  SolverMaterial;
- live tests or full canonical delivery.
