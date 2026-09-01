# 04 — Translate Lumerical construction and evidence language

**Type:** implementation (spec product boundary)

**Status:** wontfix

**Superseded by:** `../../metalens-sonnet-convergence/spec.md`

**Depends on:** ticket 01

## What to build

Reshape `solvers/lumerical_fdtd/cell.py` into a product-owned `template`
package with a small public construction seam. Rename solver construction
inputs to `PropagationConstruction` and `GeometricConstruction`; retain
scientific `Cell` for fabrication meaning. Rename `source_basis` to
`incident_axis`.

Use paired natural coordinate names such as `span_x_nm`, `span_y_nm`,
`lower_z_nm`, `upper_z_nm`, `source_plane_z_nm`,
`reflection_plane_z_nm`, and `transmission_plane_z_nm`. Keep
`reflection_offset_nm` and `transmission_offset_nm`.

Rename phase-plane evidence to `phase_planes`. Expand public material
frequency names and complex parts. Replace overloaded receipt `recover_*`
operations with `restore_*`. Translate vendor-native strings immediately
inside the session seam.

Shrink `lumerical_fdtd.__init__` to the actual caller Interface. Move fake
probe, session, and execution implementations under tests.

## TDD seam

Through Lumerical qualification and construction interfaces with the existing
fake engine, build and read back one propagation construction and one
geometric construction. Assert exact physical planes, materials, incident
axes, native translation, observation provenance, and manifest schema. Keep
live 2025 R2 tests present but opt-in.

## Acceptance

- Product construction owns mesh accuracy `4`, substrate thickness `2000 nm`,
  simulation time, and both `100 nm` plane offsets.
- The scientific package exports no product construction type.
- Native strings such as `S21_Gn`, `T_Gn`, and `"x span"` occur only at the
  Adapter/session boundary.
- No production fake is re-exported.
- The Lumerical package export ratchet passes.
- Existing sweep, qualification, construction, material, and manifest tests
  pass.
- Rust diff is empty and touched files pass CSU.

## Do not add

Do not add CST, COMSOL, GUI, a common solver construction Interface, or
caller-controlled worker counts.
