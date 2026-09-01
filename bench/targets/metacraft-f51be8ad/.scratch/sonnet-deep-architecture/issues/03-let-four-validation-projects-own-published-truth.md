# 03 — Let four validation projects own published truth

Status: resolved (2026-07-31)

**Blocked by:** 01 — Let one Python name describe one system.

## Outcome

The repository-root external layer exposes exactly four
`MetalensValidationProject` values from
`examples/metalens_projects.py`. Each Project is the sole owner of its
concrete Brief, published platform facts, comparison rules, fidelity
statement, and validation expectations.

Production imports no Project and contains no concrete paper case. The
installed wheel contains no `examples` package. Ticket 07 remains the owner of
removing production Result meaning, changing Result bytes/schema, and moving
all comparison out of the scientific conclusion.

## Scope

- Add `examples/metalens_projects.py`.
- Define one immutable `MetalensValidationProject` with:
  - one exact `MetalensBrief`;
  - published citation and selected-device facts;
  - published material, geometry, period, height, aperture, and polarization
    facts;
  - threshold-free comparison measures and published metrics;
  - fidelity wording and explicit exclusions;
  - canonical document bytes and content identity.
- Move the four concrete project factories into that module:
  - Yun 2025 low-NA propagation;
  - Yang 2018 low-NA geometric;
  - Arbabi 2015 high-NA propagation;
  - Khorasaninejad 2016 high-NA geometric.
- Give the external layer intention-revealing selection operations:
  - `metalens_validation_projects()`;
  - `metalens_validation_project_names()`;
  - `select_metalens_validation_project(name)`.
- Update `examples/__init__.py`, offline inspection, local Lumerical example
  composition, and all test imports to use Project language.
- Delete the concrete-case module and case/delivery naming after all callers
  move.
- Keep all Project code outside `src/metacraft`.
- Preserve the current production Result meaning seam only as the temporary
  caller required by the current lifecycle. Do not deepen or duplicate it.
  Its complete deletion is part of Ticket 07.

Concrete published truth must occur once in the external Project module. Tests
may assert it but must not restate complete project constructors or maintain a
second expected-value catalogue.

## TDD seam

Write the external seam tests first:

```python
projects = metalens_validation_projects()
project = select_metalens_validation_project(projects[0].name)
document = project.document()
restored = MetalensValidationProject.from_document(document)
```

Tests must prove:

- exactly four Projects exist in one stable order;
- each Project round-trips through its canonical document;
- name selection returns the exact Project;
- unknown names fail directly;
- Project inspection performs no Authority access, consultation, solver
  discovery, Torch import, workstation observation, or filesystem mutation;
- each Brief remains aligned with its published wavelength, numerical
  aperture, focal length, control strategy, polarization, material families,
  and atom geometry;
- blind Briefs do not acquire hidden published cell dimensions;
- production imports no `examples` module;
- a built wheel contains no `examples/` path.

Use `tests/examples/test_canonical_cases.py` as the starting test file, then
rename it to Project language in the same ticket. Update delivery and advice
tests to consume the Project seam instead of importing concrete factories.

## Acceptance

- [ ] `examples/metalens_projects.py` is the sole concrete source for all four
      Projects and their published truth.
- [ ] The external type is named `MetalensValidationProject`.
- [ ] Project selection names are explicit, deterministic, and
      intention-revealing.
- [ ] Production imports no external Project module.
- [ ] Production contains no concrete paper citation, platform, metric, or
      four-case factory.
- [ ] Offline Project inspection opens no scientific or native dependency.
- [ ] No case/delivery forwarding functions remain.
- [ ] The installed wheel excludes `examples`.
- [ ] Rust source and protocol values remain unchanged.
- [ ] Production Result meaning and Result schema are unchanged in this
      ticket and explicitly remain for Ticket 07's atomic cutover.

The Project document identity may change because `MetalensCase` becomes
`MetalensValidationProject`. The scientific content of each Brief and each
published fact must not change as part of this structural move. No reader for
the replaced Project document is added.

## Verification

```powershell
$projectPython = 'C:\Users\Administrator\miniforge3\envs\research_env\python.exe'

& $projectPython -m pytest -q --tb=short -p no:cacheprovider `
  tests/examples/test_canonical_cases.py `
  tests/advice/test_adviser.py `
  tests/science/test_conduct.py `
  tests/science/test_delivery_matrix.py `
  tests/science/test_geometric_delivery.py `
  tests/science/test_propagation_delivery.py `
  tests/solvers/test_lumerical_dispatch_gather.py

& $projectPython -m pyright

& $projectPython -m maturin build --release --locked `
  --interpreter $projectPython `
  --out <temporary-wheel-directory>

rg -n "MetalensCase|PaperFacts|canonical_cases|delivery_cases|delivery_briefs|select_case|select_brief" `
  src tests examples

rg -n "from examples|import examples" src/metacraft
git diff --check
git diff -- rust
```

After test files are renamed during implementation, update the focused command
to their final paths. The replaced case/delivery-name search, production
external-import search, and Rust diff must be empty. The complete non-live
suite is reserved for Ticket 10.

## Stop and report

Stop without moving Result work forward if:

- Project extraction requires changing production Result meaning or Result
  schema;
- published truth must be duplicated between production and external code;
- a Project cannot remain offline and deterministic;
- a concrete paper fact is ambiguous or internally inconsistent;
- production must import `examples`;
- packaging cannot exclude the external layer;
- a Rust source or protocol change appears necessary.

Report the exact Project, conflicting fact, dependency edge, and focused test.
Leave Result cutover to Ticket 07.

## Do not add

- A `projects/` package or another external project location.
- A production Project type, project registry, plugin, or dynamic discovery.
- Concrete paper truth under `src/metacraft`.
- Case/delivery compatibility functions or forwarding imports.
- Production Result meaning, Result-schema, or Result-byte changes.
- A Python record migration or compatibility reader.
- Native adviser calls, Lumerical solves, parameter sweeps, or workstation
  observation.
- Rust source or protocol changes.

## Comments

Resolved by replacing the concrete case module with one external
`MetalensValidationProject` catalogue and exactly three selection operations.
The four Briefs and all published comparison truth now occur only in
`examples/metalens_projects.py`; production imports no external Project.

The science package initializers now load exports lazily, so offline Project
inspection opens no Torch, native Authority, adviser, solver, or workstation
dependency. The installed release wheel built by the implementing agent
contained 92 entries and no `examples/` path. Independent verification passed
89 focused tests and Pyright with zero findings. Old case/delivery identifiers,
production paper truth, production-to-examples imports, and the Rust diff were
all absent. The temporary `result_meaning` caller remains isolated in the
external Project and is reserved for deletion by Ticket 07.
