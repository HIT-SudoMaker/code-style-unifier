# 02 — Qualify only what one brief requests

**Type:** implementation

**Status:** wontfix

**Superseded by:** [Metalens Sonnet convergence](../../metalens-sonnet-convergence/spec.md).

**Blocked by:** ticket 01.

## Outcome

Product qualification establishes one installation without pre-binding
scientific materials. When `material_binding` becomes ready, the Adapter
samples exactly the two roles and wavelength requested by that design.
Unrelated material families neither block compilation nor leak into
construction.

## What to build

- Replace family-specific environment fields with the distributable catalogue
  form `LUMERICAL_MATERIAL_<CANONICAL_FAMILY>=<exact native product name>`.
- Encode a natural lowercase family into the key suffix by uppercasing its
  canonical words and joining them with `_`. Reject invalid word forms,
  duplicate decoded families, and collisions; never apply that transform to
  the exact native product value.
- Let the Lumerical environment reader admit only its fixed keys and a
  validated `LUMERICAL_MATERIAL_` prefix. Update the example environment only.
  Runtime may consume user-supplied values through the existing loader, but
  the implementation session must neither inspect nor rewrite the user's
  ignored `.env.lumerical`.
- Keep installation qualification limited to path, version, licence,
  resource, template mechanics, and capacity. Remove scientific material
  roles and global material samples from the product binding.
- When the compiled `material_binding` task is ready, ask the dispatch for
  exactly the atom family, substrate family, and wavelength. Sample a repeated
  family once.
- Probe exact native names and exact-wavelength optical data; never guess,
  normalize, silently substitute, or extrapolate product strings.
- Keep canonical material families in science documents and confine native
  product strings to Adapter observations and the admitted scientific
  MaterialBinding.
- Pass the admitted MaterialBinding into periodic construction. Templates do
  not reopen configuration or consult a product-global material map.
- Migrate the existing silica and silicon nitride paths without changing their
  scientific meaning.
- Report an absent mapping, absent native material, and out-of-band sample as
  three distinct `material_binding` findings.
- Add a configuration-only preflight that names every catalogue key required
  by the requested brief before a native session can open.

## TDD seam

Start with one fake qualified installation and two briefs that request
disjoint material pairs at different wavelengths. Prove that the same product
binding remains valid while each material-binding task asks for exactly its
own request.

## Acceptance

- Configuration is complete without predeclaring every material family.
- Catalogue-key round trips preserve natural family word order; malformed or
  colliding suffixes fail configuration without touching native values.
- The product binding is role-neutral and byte content does not change when a
  different brief requests materials.
- A material-binding observation contains exactly the requested families,
  exact native names, target wavelength, sampled indices, and source
  references.
- A same-family atom/substrate design performs one native sample and binds two
  scientific roles.
- Construction consumes the admitted scientific MaterialBinding rather than
  reopening configuration or embedding product strings.
- Missing catalogue entries, missing native materials, and out-of-band
  samples are distinguishable findings that leave the Study waiting.
- Missing catalogue keys are reported before any native session opens; the
  report contains no guessed replacement.
- Existing silica/silicon nitride fake tests continue to pass through the new
  catalogue.
- `.env.lumerical.example` demonstrates the four-example and retained
  development families, while the ignored local `.env.lumerical` remains
  byte-for-byte untouched.
- Focused tests, architecture tests, Pyright, and CSU on touched files pass.

## Do not add

- A universal material registry or plugin system.
- A brief, route, or scientific role in the product installation binding.
- Fuzzy matching against the Lumerical library.
- Hard-coded amorphous silicon, silica, or silicon nitride names in science
  Modules.
- Live solver execution.

## Comments

- 2026-07-27: Implemented the role-neutral product binding, reversible
  material catalogue keys, task-scoped exact-wavelength sampling, preflight,
  distinct waiting findings, and MaterialBinding-driven construction.
- 2026-07-27: Verification passed with 69 solver tests and 10 opt-in live
  tests deselected, 34 conduct/architecture tests with 3 unrelated opt-in
  tests deselected, Pyright at zero errors, and zero CSU hard violations in
  the touched production files and the ticket acceptance tracer. Rust remained
  unchanged and no live solver was started.
