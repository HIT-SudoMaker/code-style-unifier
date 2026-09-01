# 15 — Name the native simulation time

Type: bug fix

Status: resolved (2026-07-28)

Blocked by: ticket 10 live attempt three.

## Problem

The bounded Lumerical smoke reaches the installed 2025 R2 (`25v2`) product,
then fails while constructing the propagation fixture:

`native_session_failed:LumApiError:"in set, the requested property
'simulation time fs' was not found"`

`simulation_time_fs` is a public, unit-bearing MetaCraft name. The session
adapter currently derives the native label by replacing underscores, producing
`simulation time fs`. Lumerical owns the native property `simulation time`;
the unit suffix belongs only to MetaCraft's public value.

## Outcome

The session adapter explicitly maps `simulation_time_fs` to the native
`simulation time` property and preserves the existing femtosecond-to-second
conversion. No template, simulation duration, mesh, material, brief, or
scientific policy changes.

## Acceptance

- A focused fake-session test proves the exact native property name and value.
- Existing session and periodic-template tests remain green.
- No compatibility alias or version branch is added.
- Rust is unchanged.
- The repair does not run a live solver.

## Resolution

The session Adapter now explicitly maps the public
`simulation_time_fs` property to Lumerical's native `simulation time`
property. The existing `_fs` conversion remains unchanged, so `1_000`
femtoseconds is sent as `1e-12` seconds.

The focused fake-engine test observes the exact native `set` call. Its red
state recorded `("simulation time fs", 1e-12)`; the repaired green state
records `("simulation time", 1e-12)`. No template, brief, duration, mesh,
material, or scientific policy changed.

## Verification

- focused periodic/session tests: `11 passed in 1.48s`;
- Pyright: `0 errors, 0 warnings, 0 informations`;
- CSU on the touched production file: zero hard violations;
- `git diff --check`: empty;
- `git diff -- rust`: empty;
- no live solver, network, or full non-live suite was run.
