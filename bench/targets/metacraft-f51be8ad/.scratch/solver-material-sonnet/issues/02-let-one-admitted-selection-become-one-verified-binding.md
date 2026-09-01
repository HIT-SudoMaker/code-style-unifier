# 02 — Let one admitted selection become one verified binding

Status: resolved (2026-07-30)

**Blocked by:** [Let one material library name one solver material](01-let-one-material-library-name-one-solver-material.md).

**Specification:** [Solver-material Sonnet convergence](../spec.md).

## Outcome

Connect the library to the existing material-binding task as one complete
vertical slice:

```text
ready task
→ exact pair selection
→ run admission
→ Lumerical Dispatch
→ verified sample
→ MaterialBinding
```

The slice must consume every new value it introduces. No admitted-selection
type may stop unused between application composition and the Adapter.

## Composition seam

- The application edge reads `materials/lumerical.toml` once for one fresh
  conduct opening and injects one validated `SolverMaterialLibrary`; the
  separate replay entry never requests or opens it.
- `available_science`, scientific Modules, and Lumerical Dispatch perform no
  project-file discovery.
- A ready material-binding task selects only its atom/substrate pair by exact
  solver and family, admits only those canonical documents as immutable
  records, and couples each selection to its Authority `Reference`.
- Repeated atom/substrate families are selected, admitted, and sampled once.

## Adapter seam

- Dispatch accepts admitted solver materials plus wavelength; it does not
  accept naked family strings or select from `LumericalConfig`.
- The Adapter verifies solver identity, exact native-name existence, requested
  wavelength coverage, and family/native-name preservation before returning a
  sample.
- The resulting `MaterialBinding` keeps atom/substrate roles and cites the
  exact sample and solver binding used.

## Acceptance

- One bounded fake task reaches one admitted `MaterialBinding` through the
  complete slice above.
- Missing registration yields
  `solver_material_not_registered`, opens no solver session, and does not
  inspect registrations for unrelated cases.
- Missing native material yields `native_material_not_found`; uncovered
  wavelength yields `material_wavelength_uncovered`. The three causes remain
  distinct through the existing Finding/waiting path.
- A repeated family produces one registration reference, one native sample,
  and two task roles where appropriate.
- The material-binding path obtains every native name from admitted
  selections and never reads `LumericalConfig.material_catalogue`. Ticket 03
  owns atomic removal of the now-retired field and prefix.
- Focused application, material-binding, fake-dispatch, waiting, repeated-
  family, and import-DAG tests pass.
- Rust source and manifest are unchanged; no real session or live marker runs.

## Stop and report

- Completion requires changing Rust, creating a second Authority, or adding a
  new broad exception hierarchy.
- Existing product qualification cannot pass an admitted selection without
  making science depend on Lumerical.
- The new path would require an environment fallback or two-source precedence
  rule to remain green.

## Do not add

- A hidden default library, project-global singleton, or project Authority;
- catalogue access, aliases, discovery, normalization, import, `addmaterial`,
  or substitution inside the Adapter;
- a common solver Interface before a second real Adapter exists.

## Verification

Implemented on 2026-07-30.

- Focused material, application, Dispatch, waiting, repeated-family,
  downstream fake-delivery, and import-DAG seams: 95 passed.
- Pyright: zero errors and warnings.
- CSU: zero hard violations across touched production Modules.
- `git diff --check`: clean.
- Rust source and manifests: unchanged.
- No live marker, Adviser, Lumerical, Torch, or complete test-suite run.
