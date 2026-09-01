# Component and Assembly composition

**Status:** Accepted

**Implemented partial supersession:**
`0012-sonnet-combination-and-evidence-contract.md` (Accepted — implemented
present truth) narrows the Combination language, Physical Value ports, Optical
Path Reference ownership, and minimum-sufficient-evidence rules. That atomic
migration has landed; the historical body below is retained without rewrite.

**Partial supersession:** the "Direct calls versus Assembly" paragraph below
previously described Assembly as Wave-oriented and deferred Ray Assembly
authoring. That deferral is closed by
`0007-mixed-independent-wave-ray-assembly.md` (implemented by Ticket 14 of
the final-seal initiative): one Assembly may now contain independent Wave
and Ray subgraphs. The rest of ADR-0002 remains in force.

**Partial supersession:** the `RayBundle` Physical Value description below
(which states that a Ray Bundle "does not carry complex amplitude, Wave
coherence, Polarization Representation, Source Lineage, or Spatial Grid") and
the Ray-producing Source bullet (whose added call shape
`(SpatialGrid) -> RayBundle` owns collimated ray launch and carries no
Polarization Representation) are partially superseded by
`0009-polarized-ray-foundation.md` re: the implemented polarized-Ray
foundation. Under ADR-0009 a `RayBundle` carries a mandatory normalized
transverse `complex128` polarization direction plus separate real power, and
a Ray-producing Source authors an explicit transverse Polarization with no
hidden default; both are now live in production. Only the Ray-polarization
aspects named here are narrowed; the Wave-to-Ray and Ray-to-Wave conversion
exclusions and the Assembly composition decisions stay in force. The older
power-only-Ray wording below stays in place as the bannered frozen record,
not unbannered present truth.

**Partial supersession:** the Assembly bullet below that states
"`expose` assigns a user-facing name to a final Physical Value. Assembly
retains that authored exposure, while populated Named Outputs exist only as
the result of Workstation Run." is partially superseded by
`0011-assembly-topology-contract.md` (Accepted — implemented present truth,
converged by the sonnet-assembly-topology-closure initiative) re: the
implemented Authored Exposure semantics. Under ADR-0011 `expose` names one
computed Physical Value output (an Authored Exposure) that becomes a final
Named Output; that output may be topologically intermediate and may coexist
with one downstream connection, while remaining physically non-consuming,
and one stable Component-output anchor has at most one Authored Exposure.
Only the "final Physical Value" qualifier on what `expose` may name is
narrowed; the "populated Named Outputs exist only as the result of
Workstation Run" clause, the closed Physical Value set, and the rest of the
Assembly composition decisions stay in force. The older "final Physical
Value" wording below stays in place as the bannered frozen record, not
unbannered present truth.

## Context

The legacy architecture modelled optical paths as a typed acyclic Optical
Graph (historical ADRs 0015, 0023), qualified them through a Contract
Resolution and Preflight framework (0033, 0036, 0039), and indexed reusable
actions through a registry of Named Scientific Operations (0021, 0022, 0056,
0063, 0067). That produced parallel function and object APIs, a public
Graph/Node framework, execution-plan objects, and a universal operator
interface — all of which obscured the physical reading order and made simple
calculations require a runtime.

The refactor replaces that with two composition forms that share one
Component definition.

## Decision

### Optical Functions and Components

- A reusable physical action may expose two name-paired public call shapes
  only when they share one physical implementation: a stateless Function for
  one-off calculation, and an ordinary `torch.nn.Module` Component for
  trainable or fixed state, reuse, hosting, and Assembly membership.
- A Source is deliberately not such an action pair. One Source instance must
  preserve its private Source Lineage across calls, while a separately created
  or copied Source must own a different Lineage. A stateless Function cannot
  satisfy both invariants without exposing identity, deriving identity from
  physics, or adding a registry; all three are excluded.
- A Component conforms structurally to exactly one Optical Role (`source`,
  `element`, `propagation`, `combination`, `detection`). Each role package
  presents its small structural Protocol, while one private role contract is
  the semantic authority used by both those public Protocol adapters and
  runtime validation. Independently maintained static and runtime signature
  tables are excluded. Every Component declares one immutable role identity
  without inheriting a universal base.
- When exported for Element, Propagation, Combination, or Detection, a paired
  Function receives the complete role-input Physical Value block followed by
  the physical parameters owned by its Component. Removing that input block
  yields the Component construction signature. This rule covers single-input
  and multi-input action roles without a special case.
- `forward` is never called directly and contains one delegation to the same
  physical implementation as the paired Function. There is no duplicate
  role-verb method, universal input payload, or forced common arity. Assembly
  Check evaluates `forward` on isolated `meta` copies, so the paired
  calculation, shape, dtype, and real execution cannot drift.
- There is no universal Component base class and no inheritance family. Roles
  are physical navigation only; they own no runtime state.
- Current Component results are the closed Physical Value set `OpticalField`,
  `Intensity`, and `RayBundle`. An arbitrary tensor or untyped payload is
  never a Component result or Named Output. `RayBundle` is the geometric-ray
  Physical Value: it carries three-dimensional per-ray position, direction,
  power, Optical Path, and finite status, and reuses Spectrum and Medium
  metadata. It does not carry complex amplitude, Wave coherence, Polarization
  Representation, Source Lineage, or Spatial Grid; a Ray-producing Source
  authors ray position from explicit pose, never from a transverse field
  sample.

### Assembly

- The Source role accepts both Wave-producing and Ray-producing call shapes
  through the same private role authority. The call shape
  `(SpatialGrid) -> OpticalField` continues to own Plane Wave identity, and
  the added call shape `(SpatialGrid) -> RayBundle` owns collimated ray
  launch. Combination and Detection are unchanged: a Ray Bundle is not a
  Wave input, and the Wave-oriented Coherent and Incoherent Combination
  contracts remain the only mixing semantics.
- `Assembly` is the one canonical typed optical structure, authored in native
  Python with the three-step grammar `include`, `connect`, and `expose`.
  - `include` validates exactly one Optical Role and registers the Component
    under a unique stable semantic name. Invalid modules fail immediately with
    `AssemblyError`; implementation exceptions never leak from Assembly Check.
  - `connect` declares Physical Value flow and names ports only when the
    connection is ambiguous.
  - `expose` assigns a user-facing name to a final Physical Value. Assembly
    retains that authored exposure, while populated Named Outputs exist only
    as the result of Workstation Run.
- `freeze()` first runs Assembly Check, then permanently locks topology.
  After freeze, `include`, `connect`, and `expose` raise; Parameters and
  Buffers remain discoverable through `named_parameters()` and
  `named_buffers()`. Structural change requires a new Assembly.
- `check()` succeeds with `None` or raises one `AssemblyError` that reports
  all discovered topology and optical-compatibility defects in physical
  reading order.
- Stable Component names anchor parameter paths, error paths, independent
  random streams, connections, exposures, and frozen execution facts. Those
  facts never retain a Component object or Python `id`; replay resolves the
  current Module from the registered name. Deep copies and same-version
  serialized copies therefore rebuild correct instance relationships without
  repair hooks. Included modules cannot be replaced or deleted outside the
  authoring grammar, and a name already held by Assembly or PyTorch state is
  rejected before registration changes. There is no public Graph, Node,
  Builder, or port-reference wrapper; no implicit registration; no string-path
  connection schema.
- Topology validation, isolated-meta Check, and Workstation meta/real execution
  consume one private frozen fact and one private replay implementation.
  Compatibility aggregation remains private and does not expand the authoring
  interface; Assembly owns no memory traversal or estimate.

### Direct calls versus Assembly

Direct Function or Component calls in physical reading order are the primary
composition form for simple calculations. A hosted linear system uses one
module-level calculation with one Component call per physical line. Paired
Functions, where exported, serve stateless one-off use; Components serve state,
training, reuse, and Assembly membership. A frozen Assembly is the recommended
complete optical structure for branched, merged, or multi-output paths, while a
legal linear Assembly remains supported. All paired forms share the same
Physical Values and physical implementation. Assembly admits Wave-only,
Ray-only, and mixed independent Wave/Ray subgraphs in one frozen topology
(see `0007-mixed-independent-wave-ray-assembly.md`); each Source anchors its
own spatial grid as a Source-side sampling anchor, and Optical Field,
Intensity, and Ray Bundle are all exposed through the same authoring grammar.
Direct Wave-to-Ray and Ray-to-Wave connections remain illegal; no converter
is provided.

### Optical path and coherent carrier

This subsection records how the decision interacts with the Optical Path
Reference; the current term, including its autograd behaviour, is owned by
`CONTEXT.md`.

- The decision admitted an Optical Path Modulation that consumes an Optical
  Path Profile in SI metres: its spatial variation contributes
  `exp(i 2π optical_path_variation / wavelength)` without re-multiplying by
  the Propagation Medium, and its uniform baseline advances the per-spectrum
  Optical Path Reference rather than duplicating that carrier in the envelope.
- The decision excluded inferring geometric thickness, material dispersion, or
  surrounding-medium contrast from the field. A future material-thickness
  Element was left to own its conversion to wavelength-resolved optical path.
- The decision rejected "unequal references break coherence" as a failure
  mode. An ordered Coherent Combination was defined to take its first input
  reference as the output reference and to restore every other input's
  relative carrier before applying its complex mixing law.
- The decision preserved autograd through the factored uniform carrier. It
  separated structural immutability of the reference container — the
  per-spectrum length tuple is fixed once authored and the container never
  mutates in place — from autograd detachment. The decision did not require
  tensorizing every fixed scalar: a fixed length that has never been
  represented by a Tensor may remain a Python float. Once Tensor arithmetic
  begins, the decision chose one device-local `float64` accumulator for fixed
  Buffer-derived and trainable lengths alike and forbade collapse back to a
  Python float. This prevents a separately represented short adjustment from
  being rounded away on a long common path merely because the Field uses
  `COMPLEX64`. The trainable branch also retains its graph through the factored
  carrier, including the Aplanatic axial contribution. The decision recorded
  that this carrier gradient is observable only once coherent alignment
  re-enters the relative carrier phase in a complex mixing law; an isolated
  single field carries only a global phase, so its intensity need not show a
  nonzero gradient.

## Consequences

- Simple calculations need no runtime, catalog, or graph framework.
- Complete paths are checked before any real field is allocated (Assembly
  Check via isolated Meta Inference), then checked again against an explicit
  device and Precision (Workstation Check).
- Trainable values remain optimizable while topology is frozen, so an SLM,
  phase map, or focal length can be optimized inside a fixed structure.
- Equal- and unequal-arm interferometers share one Combination interface;
  reference differences change phase rather than topology validity.
- Diagnostics are hard and ordered: one `AssemblyError` lists every defect in
  physical order, replacing the legacy diagnostic hierarchy.

## Superseded history

Historical ADRs 0015, 0019, 0021, 0022, 0023, 0032, 0033, 0036, 0037, 0039,
0056, 0058, 0061, 0063, 0067, 0068, 0089, 0159, 0160, 0162, 0165, 0224, and
0226 built the graph/operator/contract framework. Their lessons are recorded
in `docs/history.md`.
