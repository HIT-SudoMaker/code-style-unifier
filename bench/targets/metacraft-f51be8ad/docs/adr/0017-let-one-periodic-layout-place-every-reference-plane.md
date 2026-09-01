# 0017 - Let one periodic layout place every reference plane

Status: accepted

## Research basis

This decision applies the native read-back findings in
[Lumerical periodic reference-plane read-back](../research/2026-08-01-lumerical-periodic-reference-plane-readback.md)
and supersedes the provisional vertical distances in
[Lumerical FDTD low-NA metalens template contract](../research/2026-07-23-lumerical-fdtd-low-na-metalens-template-contract.md).

## Context

The periodic template placed its source and solver bounds from separate
half-wavelength expressions, retained substrate height outside the coordinate
frame, and later reconstructed the expected transmission plane from the atom
read-back. The same physical layout therefore had several owners.

A fresh native qualification exposed a separate product detail. The internal
transmission monitor was declared at 800 nm but its default nearest-mesh-cell
sampling returned 804.347826 nm. An earlier diagnosis incorrectly treated the
dataset coordinate as group-local; a native comparison proved that result
datasets already report the world coordinate.

## Decision

The substrate top and meta atom bottom share the declared `z = 0` interface.
`Substrate` is the supporting medium below that interface. `Meta atom` is the
generic patterned element above it; `nano pillar` is used only when the
element is pillar-shaped.

One immutable periodic layout owns every vertical extent and reference plane.
For integer wavelength `w` and meta-atom height `h`, all in nanometres, let
`ceil100` round outward to the next multiple of 100 without floating-point
arithmetic:

```text
substrate height = max(2000, ceil100(w))
source depth     = ceil100(substrate height / 2)
source z         = -source depth
reflection z     = source z + 100
solver lower z   = source z - 100
solver upper z   = ceil100(h + w / 2)
transmission z   = solver upper z - 100
```

The substrate spans from its negative height through `z = 0`, so it crosses
the lower absorbing boundary rather than terminating inside the solver. The
meta atom spans from `z = 0` to `h`. The layout rejects overlapping planes or
non-positive exact integer inputs.

The Lumerical template privately translates this physical layout into its
native grating group. The group lower edge equals the solver lower edge, its
upper edge equals the transmission plane, and its source offset is 100 nm.
Group center, span, relative coordinates, and native property spellings never
leave the Adapter.

Before native group setup, the Session preserves the vendor body and appends
one marked construction contract to the parent group's `setup script`. That
contract selects the internal `T` monitor and sets its spatial interpolation
to `specified position`. The Session then runs setup and only reads the child
setting back; it never mutates a constructed child. Saving the constructed
project is followed by the same strict read-back before execution. Result
dataset z coordinates remain world coordinates and are compared strictly with
the declared transmission plane. The Adapter neither adds the group center
nor widens the construction tolerance.

The template exposes one route-neutral periodic construction operation.
Transmission and polarization retain their independent request and
qualification evidence, but callers no longer choose a second construction
builder after selecting the response.

## Consequences

- At 400 nm wavelength and 500 nm height, the substrate is 2000 nm, the
  solver spans -1100 to 700 nm, and source/reflection/transmission are
  -1000/-900/600 nm.
- At 1550 nm wavelength and 800 nm height, the solver spans -1100 to 1600 nm
  and source/reflection/transmission are -1000/-900/1500 nm.
- At 2050 nm wavelength and 800 nm height, the substrate is 2100 nm, the
  solver spans -1200 to 1900 nm, and source/reflection/transmission are
  -1100/-1000/1800 nm.
- The fixed distances are conservative template policy, not an
  index-corrected wavelength formula. A changed policy changes construction
  evidence and requires fresh qualification.
- No spacing strategy Protocol, registry, generic solver interface,
  compatibility alias, dataset coordinate repair, or tolerance exception is
  introduced.
