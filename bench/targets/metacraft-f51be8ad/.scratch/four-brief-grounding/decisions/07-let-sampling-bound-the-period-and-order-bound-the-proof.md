# Let sampling bound the period and order bound the proof

Label: `wayfinder:grilling`

Status: resolved (2026-08-09)

## Question

Should the order ceiling restrict the legal period candidates, or should it
classify the response evidence required after one sampling-legal period is
chosen?

## Resolution

The sampling ceiling is the sole hard upper bound on cell-period legality. A
candidate must remain on the declared fabrication grid and strictly below
`wavelength / (2 * numerical aperture)`; violating that spatial sampling
condition is fatal.

The order ceiling does not reject a sampling-legal candidate. It classifies
the chosen period as `zeroth order` or `multi order` and retains a visible
caution. A G0 coefficient may support a complete aperture-field proof only in
the zeroth-order regime. A multi-order choice requires a qualified sampled
reference-surface or other future order-resolved response before any complete
field claim may close. Missing that capability is an honest evidence boundary,
not a retroactive reason to shrink the upstream period domain.

The implementation handoff must create one focused ADR that supersedes the
period-legality clauses of ADR 0009 and amends the current glossary and
scientific description. Code and tests must not move ahead of that decision.

## Consequences

- Published multi-order designs can remain legal recommendations.
- G0-only evidence cannot silently overclaim a complete field.
- Period legality depends on the design target; proof applicability depends on
  the response method. Their dependency direction no longer runs backwards.
