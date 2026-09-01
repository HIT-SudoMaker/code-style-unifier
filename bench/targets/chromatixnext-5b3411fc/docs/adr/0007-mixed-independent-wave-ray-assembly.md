# Mixed independent Wave / Ray Assembly

**Status:** Implemented

**Implemented partial supersession:**
`0012-sonnet-combination-and-evidence-contract.md` (Accepted — implemented
present truth) narrows Wave Combination names and ports, adds fail-before-mix
placement contracts, and defines natural Wave/Ray symmetry without mirrored
implementations. That atomic migration has landed; the historical body below
is retained without rewrite.

**Directional-inventory supersession:** the "twenty-five public optical
actions" completeness wording in this ADR's Decision and Consequences sections
is superseded. Current truth is twenty-four Optical Component actions plus
separate public inventories of three state-only directional owners, three
closed Terminal/diagonal enums, and two Assembly-issued Encounter reference
types. ADR-0007's remaining content (mixed Wave/Ray Assembly) stays in force.

**Partial supersession of:** the "Direct calls versus Assembly" paragraph in
`0002-component-and-assembly-composition.md` that previously described
Assembly as Wave-oriented and deferred Ray Assembly authoring. That deferral
is closed by this ADR's implementation; ADR-0002's remaining content stays in
force.

**Partial supersession:** the power-only characterization of the Ray-producing
Source, `TraceTo`, `ReflectAt`, and `RefractAt` in the Decision and
Implementation status sections (these actions consume and produce a
`RayBundle` that carries no polarization, and the Ray-producing Source authors
only ray position, direction, and power) is partially superseded by
`0009-polarized-ray-foundation.md` re: the implemented polarized-Ray
foundation. Under ADR-0009 (live in production), `TraceTo` preserves
polarization exactly; `ReflectAt` applies the same real Householder reflection
map to direction and complex polarization; successful `RefractAt` applies the
unique minimal proper rotation (normal incidence is identity); the
Ray-producing Source authors an explicit transverse Polarization with no
hidden default; Plane-local `RetarderAt` and finite Terminal-bound directional
Encounters are installed.
The Wave-to-Ray and Ray-to-Wave conversion exclusions and ADR-0007's mixed
Wave/Ray Assembly decision stay in force. The older power-only-Ray wording
below stays in place as the bannered frozen record, not unbannered present
truth.

> **Superseded historical record below.** The Context through Consequences
> sections preserve the pre-directional inventory and pre-polarized-Ray
> wording that applied when this decision was accepted. The supersession
> banners above, not those historical counts or action lists, state the current
> inventory and Ray contract.

## Context

ADR-0002 closed Assembly as the one authored topology but deliberately scoped
it Wave-oriented: Ray Bundle results today travel only through a hosted
module-level calculation that uses the same Workstation replay boundary and
Named Outputs, and "lifting Ray state into Assembly authoring is deferred
until linear Ray paths require Assembly-owned exposure." That deferral leaves
mixed Wave/Ray optical paths without one checked Assembly and forces them into
ad-hoc module-level glue, which is the precise gap this ADR closes.

## Decision

Assembly is the one authored topology for the existing twenty-five public
optical actions. Wave-only, Ray-only, and mixed independent Wave/Ray subgraphs
are all legal Assembly shapes.

- Independent Wave and Ray subgraphs may coexist inside one frozen Assembly.
- A Wave-producing Source, Wave Element, Wave Propagation, Wave Combination,
  and Wave Detection continue to consume and produce `OpticalField` /
  `Intensity`.
- A Ray-producing Source, Ray Propagation (`TraceTo`), and Ray Elements
  (`ReflectAt`, `RefractAt`) continue to consume and produce `RayBundle`.
- Direct Wave-to-Ray and Ray-to-Wave connections remain illegal. No converter
  is being added; this initiative adds no optical capability.
- The three-step authoring grammar (`include`, `connect`, `expose`), the
  frozen fact, and the single private replay implementation are unchanged.
  Meta, memory, and real replay do not build parallel topology
  interpretations.
- Connection truth continues to be owned by `_assembly_facts.py`; the Assembly
  facade (`assembly.py`) only authors and checks.

## Why this is surprising

ADR-0002 explicitly described Assembly as Wave-oriented and deferred Ray
Assembly. This ADR reversed that deferral: Ray Bundle subgraphs now coexist
with Wave subgraphs inside one Assembly without first proving that a linear
Ray path requires Assembly-owned exposure. It is also surprising because the
project admits mixed Assembly while continuing to forbid any Wave↔Ray
converter, so the change is structural coexistence rather than physical
unification.

## Rejected alternatives

- **Wave↔Ray converter.** Rejected: adds unprovable physics and a new public
  capability, both forbidden by this initiative.
- **Universal Physical Value base.** Rejected: would destroy the Wave/Ray
  Physical Value distinction that ADR-0002 closes (`OpticalField`, `Intensity`,
  `RayBundle`).
- **Force all-Wave or all-Ray Assemblies.** Rejected: forbids legitimate
  mixed optical paths and pushes them back into ad-hoc module-level glue.
- **Parallel Ray Assembly runtime.** Rejected: violates the one-private-replay
  rule and the single-authoring-grammar rule.
- **Reuse of the existing Wave Combination for Ray mixing.** Rejected: a Ray
  Bundle is not a Wave input; Coherent and Incoherent Combination remain the
  only mixing semantics.

## Important cost

Assembly connection validation must distinguish a forbidden Wave↔Ray edge
from a legal independent Wave/Ray subgraph without introducing a universal
base or a runtime topology kind. The cost is paid inside the private
`_assembly_facts.py` owner and its compatibility aggregation; the public
authoring surface does not widen.

## Implementation status

Implemented by Ticket 14 of the final-seal initiative. One Assembly may
contain independent Wave and Ray subgraphs; Ray-producing Sources
(`CollimatedRaySource`), Ray Propagations (`TraceTo`), and Ray Elements
(`ReflectAt`, `RefractAt`) coexist with Wave Sources, Elements, Propagations,
Combinations, and Detections inside one frozen Assembly. Wave-only, Ray-only,
and mixed-independent Assemblies all check, freeze, host, and run through the
single authoring grammar and the single private replay implementation.

Cross-domain Wave↔Ray connections are rejected at authoring time
(`connect`) with the stable `assembly_connection_domain_mismatch` identity,
in both directions; no Wave↔Ray converter exists. The frozen
connection/execution fact is owned by `_assembly_facts.py` alone;
`_assembly_replay.py` consumes it; `Assembly.check()` reuses the frozen fact
when the assembly is already frozen rather than rebuilding a second
compatibility graph; meta, memory, and real replay share that one frozen
fact.

## Consequences

- One Assembly may contain independent Wave and Ray subgraphs; the
  twenty-five public optical actions remain the complete capability set.
- Mixed Assembly qualification reuses Component Evidence for each action plus
  the existing Assembly Check, without a new mixing layer.
- The closed Wave/Ray Physical Value set and the Wave-oriented Coherent /
  Incoherent Combination contracts are unchanged.
