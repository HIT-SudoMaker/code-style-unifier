# ADR-0008: Active polarization and directional-device foundation

**Status:** Accepted — implemented present truth.

## Context

The polarization foundation needs one active vocabulary for local field
transformation and for physical direction-changing devices. A local Retarder
is an ordinary Element action. A cube beam splitter or planar mirror is instead
a physical state owner whose behavior depends on an incident Terminal and a
finite Assembly route. Treating both as interchangeable actions loses geometry,
phase ownership, and the identity of one device reused at several occurrences.

This ADR supersedes its earlier lumped-splitter vocabulary. The migration is a
clean removal: no alias, warning shim, legacy checkpoint mapper, or parallel
direct-call implementation remains.

## Decision

### Local polarization action

`Retarder` and `retarder` remain the paired Wave Element forms. They accept a
transverse Optical Field and apply a lossless SU(2) transformation parameterized
by retardance cycles and one normalized polarization eigenstate. Zero
retardance is identity. The paired Component owns registered state; the
Function owns identity-free physics.

### Directional owners and closed vocabulary

The directional public surface consists of:

- `IdealNonpolarizingCubeBeamSplitter`;
- `IdealPolarizingCubeBeamSplitter`;
- `IdealPlanarMirror`;
- closed enums `CubeTerminal`, `CubeCoatingDiagonal`, and `MirrorTerminal`;
- Assembly-issued references `WaveEncounter` and `RayEncounter`.

The owners are `torch.nn.Module` state owners, not Optical Components. They
receive no Optical Role, offer no standalone physical action, and are executed
only through an Assembly Encounter. Each owner occurs once in the registered
module tree; several finite state-free Encounters may reference it by stable
owner and encounter names.

Cube Terminals are the physical sides `LEFT`, `TOP`, `RIGHT`, and `BOTTOM`.
Coating diagonal is `RISING` or `FALLING`. The planar Mirror exposes only
`FRONT` in this increment. Relative branch Ports are not device geometry.

### Phase and response ownership

The ideal Cube response owns its coating phase and output ordering. The ideal
Mirror owns its gauge-fixed complex Wave scalar `-1`. Homogeneous Propagation
owns Optical Path Reference advance. Route geometry validates endpoints,
directions, lengths, and bases but owns no phase, distance increment, Medium,
or registered state.

For a polarizing Cube, the coating-plane p/s basis is derived from incidence
geometry; it is not an authored free Jones basis. For a nonpolarizing Cube,
one mixing angle is the sole response parameter. Characterized leakage,
extinction, dispersion, and Fresnel material claims remain outside this ideal
closed model.

### Public inventory

The public Optical Component budget is exactly twenty-four actions: four
Sources, nine Elements, eight Propagations, two Combinations, and one Wave
Detection. The three directional owners, three closed enums, and two Encounter
reference types are counted separately. Top-level public exports remain
exactly `Workstation` and `install_state`.

## Consequences

- Polarization transformation stays local; directional routing stays physical
  and Terminal-bound.
- One owner can be reused without copying state or creating recurrence.
- Direct, qualified, star-import, module-object, and top-level import probes
  reject the removed surface.
- The one-way dependency remains `workstation.py -> optics -> _numerics`.
- Future characterized coatings replace response only behind the qualified
  typed adapter and require their own evidence.
