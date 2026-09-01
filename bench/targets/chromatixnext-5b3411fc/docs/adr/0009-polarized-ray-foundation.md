# ADR-0009: Polarized Ray and directional Encounter foundation

**Status:** Accepted — implemented present truth.

**Numerical refinement:** ADR-0010 owns binary64 admissibility and exact
preservation. ADR-0013 owns exact ambiguous-lane topology and Plane-local
projection representability. This ADR owns the domain model.

**Pose refinement:** `0015-ssrhm-tangent-pose-migration.md` owns the active
authored tangent-pose names without changing this polarized-Ray decision.

## Context

Ray Bundle is a direct polarized physical value, not a power-only carrier.
Surface actions must transport polarization consistently, while physical Cube
and Mirror devices require Terminal-bound incidence rather than a relative
branch label. Ray termination must describe a finite reason and must not be
confused with a physical Terminal.

## Decision

### Ray Bundle

Every Ray Bundle contains fixed-double position, unit direction, transverse
unit complex polarization direction, real power, refractive index, Optical
Path, status, and Spectrum. The layout is
`[batch..., spectrum, ray, xyz]` for vector state and
`[batch..., spectrum, ray]` for scalar state.

The status vocabulary distinguishes active lanes from Finished Rays. A
Finished Ray is non-active for one terminal reason such as surface miss,
vignetting, or total internal reflection; it is not a device Terminal and is
never an additional output route. A bundle may contain active or one Finished
reason, but never active plus Finished or several Finished reasons together.

### Existing Ray actions

`TraceTo` advances active lanes without changing polarization. `ReflectAt`
uses the same real Householder map for direction and complex polarization.
Successful `RefractAt` applies the unique minimal proper rotation, with normal
incidence as exact identity. `RetarderAt` remains the sole Plane-local
polarization Element and resolves its Jones frame per interacting lane.

Non-interacting and already-Finished lanes remain finite and retain their
incoming physical state exactly where the owning action promises identity.

### Directional Ray Encounters

An Assembly-issued `RayEncounter` references one registered directional owner
and exactly one incident physical Terminal. Each active lane attempts the
nearest forward intersection with the owner coating or mirror plane. Parallel
or rear-facing lanes become surface-missed Finished Rays. Produced values are
named by outgoing physical Terminal, and every energized output must be
connected, exposed, or ended by a Route End.

Cube and Mirror geometry derive outgoing direction and transverse-basis
transport. Polarizing response uses the geometry-derived p/s basis. The Ray
law carries power and polarization direction, not coherent Wave carrier phase;
Ray observational closure therefore waits for a qualified Ray Detection law.

### Inventory and boundary

The Optical Component inventory is twenty-four actions: four Sources, nine
Elements, eight Propagations, two Combinations, and one Wave Detection.
Directional owners, closed enums, and Encounter references are separate public
inventories. The two top-level public exports and the three production seams
remain unchanged.

## Exclusions

- No material Fresnel, coating leakage, extinction-ratio, or dispersion claim.
- No curved directional Retarder or arbitrary per-ray Jones operator.
- No Wave/Ray converter or common universal Optical State.
- No recurrence, inferred pass count, or automatic route search.
- No Ray observational claim before a real Ray Detection is qualified.

## Consequences

Ray polarization is mandatory and direction-aware. Physical directional
devices are authored as finite Encounters of one owner, while ordinary Ray
actions retain the paired Function/Component contract. The public vocabulary
contains no compatibility path to the removed relative-branch device model.
