# 0013 — Let each periodic response prove itself

Status: accepted

## Context

Until this decision, the Lumerical Adapter exposed one shared periodic
response capability — `periodic_full_wave_response` — used by BOTH the
propagation-phase and the geometric-phase metalens methods. That capability
was issued after a single propagation fixture: one minimal construction,
engine execution, and finite complex-transmission observation. The geometric
phase, however, needs a finite Jones response, which is a different physical
ability established by two independent input bases. One transmission fixture
therefore granted more capability than it had proved: a product that could
only observe transmission was admitted as if it could also establish
polarization.

The same closure also found that expected product or capacity absence crossed
the Adapter seam as classified exception strings. `conduct` matched capacity
unavailability by parsing `str(error)`, and `open_lumerical` matched a dispatch
unavailability by an exception-text prefix. Text classification is brittle: it
hides the difference between expected absence (data) and an internal defect
(fault), and it breaks the moment a reason string changes spelling.

## Decision

The Lumerical Adapter exposes exactly two route-neutral periodic response
capabilities, each issued only after its own native fixture succeeds:

```text
periodic_transmission_response
periodic_polarization_response
```

`periodic_full_wave_response` is retired. No compatibility alias remains.

### Distinct proof fixtures

Product discovery keeps the existing order
`configured -> found -> versioned -> licensed -> qualified -> available`. The
first four stages construct no scientific geometry. At the `qualified` stage
the probe runs each response's own fixture through the same native dialect and
session implementation used by production work:

- **periodic_transmission_response** — one propagation construction, engine
  execution, and a finite complex-transmission observation (finite real and
  imaginary parts, finite power within `[0, 1]`).
- **periodic_polarization_response** — both independent input bases (`x` and
  `y` linear excitations), each executed, each yielding finite output on both
  orthogonal components. A one-basis or non-finite result cannot qualify
  polarization.

Each capability is issued independently. One product binding may support
transmission only, polarization only, both, or neither. The failure of one
fixture never suppresses the independently proven sibling. The Adapter knows
only the responses it can establish; it imports and interprets no
propagation-phase or geometric-phase control strategy. The science
relationships bind `propagation phase -> periodic_transmission_response` and
`geometric phase -> periodic_polarization_response`.

### Typed expected absence

Expected discovery, qualification, license, capacity, and execution failures
cross the Adapter seam as narrow typed values, not as classified text:

- `CapacityUnavailable` (in the runner) carries one exact `reason`
  (`capacity_stale`, `capacity_not_positive`).
- `LumericalUnavailable` (in the Adapter) carries one exact `reason`
  (`configuration_incomplete`, `license_unavailable`, `capacity_not_positive`,
  …).
- `LumericalObservationFailed` (in the Adapter) carries the capacity scope and
  the underlying ordered failures from one bounded gather.

There is no broad exception hierarchy and no common solver-error framework.
The local application seam is the sole owner of translation: it catches these
typed outcomes via `isinstance`, attaches one `CAPABILITY` finding naming the
exact reason, and returns an honest waiting branch. `conduct` imports no
runner and no Lumerical type, parses no exception text, and lets invariant
violation, impossible lifecycle, malformed protocol, and implementation drift
raise directly.

## Consequences

- A propagation-only product no longer pretends to support Jones work, and a
  polarization-capable product is no longer blocked by a transmission fixture
  it does not need.
- Capability names describe physical responses, not metalens strategies, so
  solver qualification stays route-neutral.
- Adding a future third periodic response is one new constant plus its own
  fixture; it does not widen a shared capability.
- Reason strings remain as exact labels carried by typed values; they are
  never parsed by a caller.
