# Let one narrow seam carry material truth

Label: `wayfinder:grilling`

Status: resolved (2026-07-30)

## Question

Where should solver-material values, catalogue parsing, run admission, native
verification, and scientific role binding meet without reversing dependencies
or growing a registry framework?

## Resolution

The `materials` package owns `MaterialSource`. `materials.solver` owns
`SolverMaterial`, `AdmittedSolverMaterial`, and the deep
`SolverMaterialLibrary` Interface. Application composition reads
`materials/lumerical.toml`, selects the exact materials needed by one ready
task, and admits them into the run. The Lumerical Adapter receives admitted
selections and only verifies and samples them. `MaterialBinding` retains the
task roles and evidence closure without reading the library or TOML.

The library exposes only construction from bytes and exact selection. TOML is
the reviewed human format; canonical `Document` bytes are the Authority and
replay format.
