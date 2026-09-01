# 01 — Let one Python name describe one system

Status: resolved (2026-07-31)

**Blocked by:** none.

## Outcome

The distribution, source namespace, native extension path, examples, tests,
and active tooling all use `metacraft`. The replaced source namespace is
absent and no forwarding namespace remains.

This ticket changes Python packaging only. Rust source, Rust protocol values,
and the `Authority` interface remain frozen.

## Scope

- Move the complete production tree into `src/metacraft/` and remove the
  replaced source directory in the same change.
- Update every active import in `src/`, `tests/`, and `examples/`.
- Update `pyproject.toml`:
  - set the Maturin module path to `metacraft._authority`;
  - point Pyright at `src/metacraft` and the current external examples.
- Update path-aware architecture tests, subprocess import checks, source-root
  scanners, and wheel assertions.
- Rename Python realization and worker identities that intentionally contain
  the source namespace, including the Field realizations and the Lumerical
  lane worker.
- Preserve lazy loading of the native extension.
- Leave historical research records and resolved trackers unchanged.

Python scientific records written before this cutover are unsupported. It is
therefore correct for changed Python realization identities to produce
different binding, task, work, and result references in a fresh workspace.
Rust `Document`, `Reference`, `Revision`, `Proposal`, `Decision`,
`AuthorityView`, relation kinds, findings, and transition semantics do not
change.

## TDD seam

Write the failing package tests before moving implementation:

- `import metacraft` succeeds.
- The root remains cheap to import and does not eagerly load `_authority`.
- Accessing `metacraft.Authority` loads `metacraft._authority`.
- `Authority` still exposes exactly `check`, `view`, `fetch`, and `decide`.
- The runtime import graph discovers modules under `src/metacraft`.
- A built wheel contains `metacraft/`, exactly one `_authority` extension,
  and no external examples.
- Importing the replaced namespace fails.

The final root interface is completed by Ticket 07. This ticket must not
prematurely add `compile_study` or `conduct` to the installed root.

## Acceptance

- [ ] `src/metacraft/` is the sole production Python source namespace.
- [ ] No active source, test, example, or tooling import uses the replaced
      namespace.
- [ ] No forwarding package, module remapping, import hook, or fallback
      import exists.
- [ ] `pyproject.toml` names `metacraft._authority` and checks
      `src/metacraft`.
- [ ] Root import remains lazy with respect to the native extension.
- [ ] The four Authority verbs and all Rust protocol value shapes are
      unchanged.
- [ ] Python realization and worker identities use the final namespace.
- [ ] Runtime import-DAG and Authority interface tests pass.
- [ ] A release wheel builds and passes an isolated installed import smoke.
- [ ] Rust source has no diff.

## Verification

Use only the repository Python interpreter:

```powershell
$projectPython = 'C:\Users\Administrator\miniforge3\envs\research_env\python.exe'

& $projectPython -m pytest -q --tb=short -p no:cacheprovider `
  tests/authority/test_boundary.py `
  tests/authority/test_public_contract.py `
  tests/architecture/test_runtime_import_dag.py `
  tests/architecture/test_scientific_boundary.py `
  tests/architecture/test_debye_realizations.py `
  tests/solvers/test_lumerical_template_boundary.py `
  tests/examples/test_canonical_cases.py

& $projectPython -m pyright

cargo fmt --manifest-path rust/Cargo.toml --all -- --check
cargo clippy --manifest-path rust/Cargo.toml --workspace --all-targets -- -D warnings
cargo test --manifest-path rust/Cargo.toml --workspace --all-targets

& $projectPython -m maturin build --release --locked `
  --interpreter $projectPython `
  --out <temporary-wheel-directory>

rg -n "metacraft_[a-z]+" src tests examples pyproject.toml
git diff --check
```

The final `rg` command must return no active match. The complete non-live suite
is reserved for Ticket 10.

## Stop and report

Stop without broadening the ticket if:

- changing the native module path requires a Rust source edit;
- any Rust protocol field, schema, relation, finding, or transition changes;
- the release wheel needs both Python namespaces;
- an active import cannot move without a forwarding namespace;
- a package-only rename changes a Brief's scientific content.

Report the exact file, failing command, and smallest observed contradiction.

## Do not add

- A forwarding namespace or import compatibility layer.
- A Python record migration or compatibility reader.
- A numbered or version-labelled package name.
- Root exports owned by Ticket 07.
- A second native extension.
- Changes to Rust source, historical research records, or resolved trackers.

## Comments

Resolved with one atomic source-tree rename and no forwarding namespace.
Independent verification passed 325 focused tests, Pyright with zero findings,
an isolated lazy native import smoke, active-name absence checks, the Rust
no-diff gate, and `git diff --check`. The release-wheel smoke performed by the
implementing agent contained one native extension and excluded external
examples.
