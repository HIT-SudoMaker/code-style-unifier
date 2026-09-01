# 04 — Let each periodic response prove itself

Type: implementation

Status: resolved (2026-07-29)

Blocked by: tickets 02 and 03.

## Outcome

Periodic transmission and periodic polarization are independent,
route-neutral capabilities. Each is issued only after its own native fixture
has succeeded, and every expected product failure crosses the Adapter seam as
typed facts rather than parsed text.

## Scope

1. Begin with failing qualification tests showing that one periodic fixture
   can currently grant more capability than it proves.
2. Retire `periodic_full_wave_response` and use exactly:
   `periodic_transmission_response` and
   `periodic_polarization_response`.
3. Keep discovery ordered as configured, found, versioned, licensed,
   qualified, available. Construct no scientific geometry before the
   qualified stage.
4. Qualify periodic transmission through one propagation construction,
   engine execution, and finite complex-transmission observation.
5. Qualify periodic polarization through both independent input bases needed
   to establish one finite Jones response.
6. Issue each capability independently. One product binding may support
   transmission only, polarization only, both, or neither.
7. Bind propagation-phase science to periodic transmission response and
   geometric-phase science to periodic polarization response.
8. Keep the product Adapter ignorant of propagation and geometric control
   strategies. It exposes physical response ability, not route names.
9. Carry expected discovery, qualification, license, capacity, and execution
   failures as narrow typed Adapter outcomes.
10. Translate those outcomes at the local application seam into admitted
    diagnostics and Findings, then let `conduct` return an honest waiting
    Study.
11. Let malformed protocol, impossible lifecycle state, invariant violation,
    and implementation drift raise directly.
12. Close or release every session, permit, lane, and work record on success,
    expected failure, cancellation, and unexpected fault.
13. Exercise fake and production product bindings through the same
    qualification Interface.
14. Update canonical science and solver decisions with the two response
    capabilities and their distinct proof fixtures.

## Acceptance

- Propagation qualification can issue transmission response without
  polarization response.
- Two-basis polarization qualification can issue polarization response
  without transmission response.
- Both successful fixtures produce both bindings under one product identity.
- Failure of one fixture does not suppress the independently proven sibling.
- A one-basis or non-finite polarization result cannot qualify polarization
  response.
- A non-finite transmission observation cannot qualify transmission response.
- The Lumerical Adapter imports no propagation-phase or geometric-phase
  strategy name.
- `conduct` imports no Lumerical error and parses no exception string.
- Expected product absence produces a diagnostic, Finding, and honest waiting
  Study.
- Invariant and protocol corruption remain direct faults.
- All work-life resources close on every outcome.
- No retired capability alias remains.

## Focused tests

- independent transmission success, polarization success, dual success, and
  dual failure;
- each polarization input basis missing, malformed, or non-finite;
- version, license, capacity, session, execution, and observation failures;
- cancellation and unexpected fault at every owned work-life boundary;
- fake and production-shaped probes crossing the same qualification seam;
- propagation and geometric method binding to their exact capability;
- architecture scans for route names in the Adapter, string-classified
  failures, retired capability names, and leaked work-life concerns.

Live fixtures may be written or updated where needed but remain deselected.

## Verification

- focused qualification, dispatch, permit, conduct, and replay tests;
- Pyright with zero errors;
- CSU on every touched production file with zero hard violations;
- updated canonical science documentation and solver ADR;
- an empty Rust production diff;
- `git diff --check`.

## Stop and report

Stop if the product API cannot independently observe the two required
polarization bases, if a current canonical method legitimately needs a third
response, or if typed expected failure would require a generic cross-project
error framework.

## Do not add

Do not add a solver registry, product-neutral Adapter hierarchy, generic
capability framework, route-aware solver logic, retry database, health
daemon, string error classifier, CST, COMSOL, RCWA, or live execution.

## Resolution

Commit `6337676` retired the shared periodic response capability and let
transmission and polarization prove themselves independently. Expected
product loss became typed data; implementation drift remained an error.
