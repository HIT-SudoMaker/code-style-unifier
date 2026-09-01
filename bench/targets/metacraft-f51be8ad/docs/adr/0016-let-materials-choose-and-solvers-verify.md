# 0016 — Let materials choose and solvers verify

Status: accepted

## Research basis

This decision applies the solver-ownership findings in
[Solver-native materials in FDTD and CST](../research/2026-07-12-solver-native-materials-fdtd-cst.md)
and the Lumerical sampling semantics in
[Lumerical index-read semantics](../research/2026-07-26-lumerical-index-read-semantics.md).
The former establishes that native material meaning belongs to one exact
solver context; the latter distinguishes database response from the fitted
response used by FDTD.

## Context

MetaCraft supports portable material records and solver-native material
sampling. The first Lumerical implementation placed the relationship between a
canonical material family and an exact native product name in
`.env.lumerical`. That kept native strings outside science, but it also made a
product configuration file act as the material library.

The distinction matters. A brief states scientific material intent. A project
selects which native record represents that intent. A solver verifies what its
current installation actually contains and reads back. A run records the exact
selection and observation it used. Combining those facts in environment
configuration obscures ownership and makes reusable material choices look like
machine secrets.

## Decision

This decision amends ADR 0003 only by separating solver-material selection
from solver-material validity. A selection may exist in the project material
library; it becomes valid scientific evidence only after verification inside
one qualified solver binding.

The project material library owns solver-material selection. One solver
material links one canonical material family to one exact native record in one
named external solver and retains non-empty registration provenance.

The current Lumerical catalogue is a reviewed, version-controlled project
input. It contains at most one current selection for each canonical material
family. It performs no fuzzy matching or automatic aliasing. Distinct material
families may point to the same native record only through distinct, explicit
registrations.

When a material-binding task becomes ready, the application selects only the
solver materials requested by that brief and admits their canonical documents
into the run Authority. The Lumerical Adapter receives those admitted values;
it neither opens the project catalogue nor chooses a substitute. It verifies
native existence, reads material data and fit conditions, and produces a
binding-scoped, wavelength-specific material sample.

The sample cites the selected solver materials. The scientific material
binding cites the sample and solver binding. Replay follows that admitted
closure without reopening the project catalogue.

`.env.lumerical` retains product paths, licence configuration, artifact
location, and explicit execution switches. It contains no material-family to
native-name catalogue. Existing material values are migrated once; no
compatibility reader remains.

## Consequences

- Material selection becomes reusable, reviewable project science rather than
  implicit product configuration.
- Solver-native names remain exact and product-specific; no external material
  database is copied or treated as portable optical data.
- A changed registration creates a new material-sample identity. A changed
  solver binding always requires validation and read-back.
- Missing registration, missing native material, and uncovered wavelength
  remain distinct waiting reasons. Malformed catalogues and invalid read-back
  remain direct defects.
- Rust authority and its public protocol remain unchanged.
- Local tables and refractiveindex.info records retain their current portable
  material path; this decision adds no universal registry or solver plugin
  framework.
