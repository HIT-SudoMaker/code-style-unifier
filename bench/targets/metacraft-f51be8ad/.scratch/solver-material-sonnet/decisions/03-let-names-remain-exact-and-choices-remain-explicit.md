# Let names remain exact and choices remain explicit

Label: `wayfinder:grilling`

Status: resolved (2026-07-30)

## Question

How should canonical material families relate to exact solver-native names,
especially when terms such as fused silica, silicon dioxide, and glass appear
related?

## Resolution

Each solver and canonical material family has at most one current solver
material. Selection is exact and explicit: no fuzzy matching, automatic alias,
or scientific equivalence is inferred. Distinct families may intentionally
point to the same native record through distinct registrations. Missing or
ambiguous choices remain waiting; an Adapter never substitutes a nearby
material.
