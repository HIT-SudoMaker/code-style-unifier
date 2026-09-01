# Let the material library own reusable selection

Label: `wayfinder:grilling`

Status: resolved (2026-07-30)

## Question

Does “material library” mean a MetaCraft-held collection of portable material
records and explicit solver-native registrations, or the external Lumerical
Material Database searched afresh at runtime?

## Resolution

The material library is MetaCraft-held. Portable records retain optical data;
solver materials retain explicit selections of exact native records. The
Lumerical Material Database remains an external source that the Adapter
validates and samples. A material sample is evidence after observation, not a
substitute for registration before observation.
