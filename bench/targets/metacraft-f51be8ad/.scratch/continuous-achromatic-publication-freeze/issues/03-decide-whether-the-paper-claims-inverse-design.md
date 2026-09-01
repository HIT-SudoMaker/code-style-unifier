# Decide whether the paper claims inverse design

Status: resolved (2026-08-15)

Assignee: unassigned

Label: `wayfinder:grilling`

Blocked by: none

Parent: [Freeze the evidence-compiled continuous-achromatic metalens](../map.md)

## Question

Will the publication implement and benchmark a real bounded optimizer with an
objective, budget, stopping rule, and convergence evidence, or will it name the
current capability precisely as evidence-governed metalens design and reserve
inverse-design language for later work?

## Decision

Do not add a generic optimizer and do not headline this release as a general
metasurface inverse-design framework. The paper's claim is evidence-governed
scientific compilation from Brief to whole-device Result or typed stop.

The bounded mapping from required phase/delay to a qualified
geometry/orientation library may be described precisely as deterministic
discrete inverse assignment. Its objective, work ceiling, tie-breaks, and
failure modes must be content-addressed. It does not justify claims of learned,
continuous, topology, or self-evolving optimization.

## Consequence

Preserve the existing compiler and Method hierarchy. No optimizer Adapter,
agent planner, dynamic registry, or third public `ControlStrategy` is permitted
by this feature.
