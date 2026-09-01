# Place material candidacy before evidence-backed refusal

Status: resolved (2026-08-15)

Assignee: unassigned

Label: `wayfinder:grilling`

Blocked by: none

Parent: [Freeze the evidence-compiled continuous-achromatic metalens](../map.md)

## Question

Where should titanium-dioxide recommendation, broad Method applicability,
spectral material evidence, realizable geometry support, and full-band response
qualification meet so that TiO2 is preferred while an explicit alternative is
accepted, declared unsupported, or refused for an exact evidence-backed reason?

## Decision

Amorphous TiO2 on glass is the preferred visible first-slice recommendation and
the provenance of the initial 600 nm rectangular-fin study specification. It is
not a name-based performance fact.

Method applicability owns only structural requirements: continuous spectrum,
circular input, transmissive anisotropic rectangle, compatible intent, and
available Adapter capabilities. An explicit non-TiO2 material is not rejected
solely by family name. It proceeds to material/periodic evidence when the same
template is meaningful, becomes `unsupported` when the configured evidence
source cannot represent it, or receives a realization-specific physical refusal
from the complete qualification.

No alternative material template is added in this freeze. GaN IRUE, SiN,
compound-fin, multilayer, and freeform routes need their own later maps.

## Consequence

Replace the exact TiO2/glass applicability gate; retain the current
`MaterialResponse` and `PeriodicResponse` seams. Recommendation, applicability,
evidence availability, and qualification remain distinct concepts.
