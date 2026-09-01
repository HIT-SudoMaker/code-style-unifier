# 0015 — Let reference surfaces prove their own response

Status: accepted

## Context

ADR 0013 retired one over-broad periodic response and required transmission
and polarization to qualify independently. It described that decision as
“exactly two” responses while also anticipating a future third response.
MetaCraft now retains sampled reference-surface fields for multi-order work.
That evidence is neither a complex transmission coefficient nor a Jones
response, so reusing either capability would overstate its proof.

## Decision

ADR 0013 is amended from exactly two to exactly three independent,
route-neutral periodic response capabilities:

```text
periodic_transmission_response
periodic_polarization_response
periodic_reference_surface_response
```

Each response has its own native fixture. Transmission proves one finite
complex coefficient and power observation. Polarization proves both
independent input bases and their finite Jones components. Reference surface
proves finite sampled complex field components together with their surface,
frame, medium, component basis, requested input basis, and order regime.

No fixture grants either sibling capability. One product binding may support
any subset of the three. The names remain route-neutral: science chooses how
to use a response after the Adapter has proved only what it can observe.

## Consequences

- The historical reason for ADR 0013 remains intact; this decision narrows
  its obsolete count without rewriting it.
- Multi-order evidence no longer masquerades as a zeroth-order summary.
- A future response still requires one new name and one independent fixture,
  not a shared “full-wave” capability or a route-specific solver contract.

## Later sampling clarification

[ADR 0019](0019-form-uniform-fields-from-rectilinear-reference-surfaces.md)
preserves this capability and narrows its operational meaning. The capability
proves that a finite rectilinear reference surface is embedded in the
transmission or polarization observation from the same Native solve. It does
not prove uniform sampling, field formation, or propagation.

ADR 0019 also deletes the later-added independent
`PeriodicReferenceSurfaceRequest` round trip because it repeated the embedded
same-solve observation without owning another physical response. This does not
merge the capability with transmission or polarization qualification.
