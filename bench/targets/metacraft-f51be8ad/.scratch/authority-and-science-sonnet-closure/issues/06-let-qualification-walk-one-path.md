# 06 — Let qualification walk one path

Type: implementation

Status: resolved (2026-07-29)

Blocked by: ticket 05.

## Outcome

Production dispatch, fake tests, and explicitly enabled live checks observe
Lumerical through one ordered qualification interface:

`configured -> found -> versioned -> licensed -> qualified -> available`

## Scope

1. Consolidate the current `inspect -> qualify_observation` and
   `qualify -> _qualify_observation` paths.
2. Retain reached facts and one exact finding in the qualification outcome.
3. Keep configuration, discovery, version, and license observation free of
   scientific geometry construction.
4. Make `qualified` the first stage that performs one minimal native
   construction and engine acceptance check.
5. Derive `available` from a qualified binding plus fresh positive capacity.
6. Keep capacity refresh narrower than full qualification.
7. Use an injected fake probe at the same seam used by production.

## Acceptance

- One implementation determines qualification outcome for production, fake,
  and live callers.
- Each failure reports the last reached stage and exact finding.
- Installation and license checks cannot fail because of a periodic-template
  property.
- Qualification proves that the engine can accept minimal work.
- Capacity refresh does not repeat product discovery or native construction.
- Material sampling remains bound to the exact qualified product.
- No mutable solver status object is introduced.
- Rust is unchanged.

## Focused tests

- one case at every stage;
- license-only observation performs no construction;
- qualified performs one minimal construction;
- production and fake outcomes are structurally identical;
- capacity refresh uses only fresh license and workstation facts;
- explicitly enabled live tests remain disabled by default.

## Expected failures

Use typed failure only where dispatch or a live check must branch on the
qualification outcome. Preserve native diagnostic text inside the Adapter.

## Do not add

Do not add a global health service, installation singleton, retry loop,
background watcher, or product-neutral solver framework.
