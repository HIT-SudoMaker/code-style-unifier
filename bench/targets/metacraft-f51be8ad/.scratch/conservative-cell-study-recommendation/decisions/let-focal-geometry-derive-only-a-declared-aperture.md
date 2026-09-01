# Let focal geometry derive only a declared aperture

Label: `wayfinder:grilling`

Status: resolved (2026-08-10)

Map: [Let one conservative cell study begin every metalens design](../map.md)

Blocked by: [Let recommendation preserve user authority](let-recommendation-preserve-user-authority.md)

## Resolution

The current metalens Method owns an air-side, circular aperture. It derives
the physical radius from the admitted numerical aperture and focal length,
then derives lattice-site count from that radius and the admitted period. The
cell-study Interface therefore does not expose ambient index or footprint as
recommendation fields. A non-air output medium or non-circular footprint is a
new Method decision with its own contract, not a silent option in this one.

## Question

Under which declared output medium, focal-length convention, and aperture
footprint may MetaCraft derive a physical aperture and lattice-site count from
focal length, numerical aperture, and admitted period, and when must an
omission remain a user clarification instead of silently assuming air and a
circular footprint?
