# 03 — Let one material proof retain one identity

Status: resolved (2026-07-30)

**Blocked by:** [Let one admitted selection become one verified binding](02-let-one-admitted-selection-become-one-verified-binding.md).

**Specification:** [Solver-material Sonnet convergence](../spec.md).

## Outcome

Harden the evidence identity and remove the retired environment catalogue in
one migration. Selection, observation, and binding must remain distinguishable
and exactly linked:

```text
SolverMaterial reference
→ LumericalMaterialSample
→ MaterialBinding
```

## Evidence contract

- The sample document retains registration references keyed by canonical
  family.
- The sample key is derived from one canonical encoding of the exact
  solver-binding `Reference`, deterministically ordered registration
  `Reference` values, requested wavelength, and exact fit span. A family name
  or lone content-hash fragment is not a complete identity.
- A changed registration or fit span therefore creates a different sample
  key.
- `MaterialBinding` cites the sample and solver binding and rejects any
  denormalized family or native-name value that differs from the cited sample.

## Read-back contract

- Solver identity and native names compare exactly; native strings are never
  normalized.
- Frequencies, band endpoints, refractive indices, extinction coefficients,
  fit residuals, and fit tolerance must all be finite.
- The fit span is ordered and contains the requested frequency; fit
  coefficients are positive; material points are non-empty, shape-valid,
  deterministically ordered, and canonical.
- Missing native material and uncovered wavelength remain honest waiting
  causes. Non-finite, malformed, identity-changing, or non-canonical read-back
  fails directly as an Adapter defect.

## Catalogue retirement

- Confirmed local `LUMERICAL_MATERIAL_*` values already represented in
  `materials/lumerical.toml` are removed from the ignored
  `.env.lumerical` without exposing or changing paths, licence values, or
  secrets.
- `LumericalConfig`, production environment readers, allowlists,
  `.env.lumerical.example`, configuration tests, and normative documentation
  contain no material-catalogue prefix.
- No production code recognizes `LUMERICAL_MATERIAL_*`; no compatibility
  reader, importer, precedence rule, or dual-source fallback remains.
- Pending families remain only in
  `.scratch/solver-material-sonnet/pending-materials.md`, with no proposed
  native value.

## Acceptance

- Round-trip and negative tests cover registration references, sample keys,
  binding equality, every finite/shape invariant above, and the three distinct
  absence/defect classes.
- Environment tests prove ordinary product configuration still loads while
  any material-catalogue key is rejected as unknown.
- Focused material-sample, configuration, dispatch, binding, and architecture
  tests pass.
- Rust source and manifest are unchanged; no real session or live marker runs.

## Stop and report

- The installed Lumerical interface cannot establish one of the required
  read-back facts without live research not already captured by the cited
  records.
- Removing the prefix would delete or reveal a non-material environment
  value.

## Do not add

- Approximate equality for identity fields;
- a material-discovery cache, migration utility, or retained legacy decoder;
- invented fit metrics that Lumerical does not expose.
