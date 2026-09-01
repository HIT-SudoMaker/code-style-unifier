# Assembly topology closure contract

**Status:** Accepted — implemented present truth. This ADR is the governance
and truth record of the sonnet-assembly-topology-closure initiative. It adds
no optical capability, changes no public optical action, and changes no
optical equation. It freezes one durable architectural decision — the
canonical Assembly topology shape, the atomic authoring contract, the
Authored Exposure semantics, and the exposed-path reachability rule. The
production tickets (02 connect atomicity, 03 Authored Exposure convergence,
04 exposed-path closure) have landed and their decisive evidence is green
(see "Implementation status" below), so the contract below IS present truth.
The honest forward partial-supersession banners on ADR-0002 and ADR-0003
identified in the "Identified narrowing targets" section have been applied by
the active-truth convergence ticket; this ADR does not rewrite that earlier
ADR history.

## Context

ChromatixNext already expresses complete optical structures through one
`Assembly` authoring grammar and one frozen replay path. Its intended physical
shape is a typed, multi-source, acyclic optical structure: Sources begin Physical
Value flow, declared ordinary Component ports or physical Terminals branch it, declared multi-input actions
merge it, authored exposures name results, and the Workstation privately
replays the frozen facts. ADR-0002 closed `Assembly` as the one authored
topology and explicitly rejected a public Graph/Node/Builder framework;
ADR-0007 admitted mixed independent Wave/Ray subgraphs inside that one
Assembly. This initiative deepens that existing Assembly rather than replacing
it.

Three smaller contract gaps currently prevent the authoring experience from
reaching the same standard as the frozen execution path. First, a second
connection that reuses an occupied source output or destination input is
appended to authored state and is rejected only by a later Check or Freeze,
which leaves the Assembly in a permanently invalid authored state and breaks
the expectation that a rejected authoring operation has no effect. Second,
active domain truth describes an exposure as naming only a final Physical
Value, while current implementation and qualified scientific evidence also
allow a computed Physical Value to be exposed and then consumed by one
downstream action; that meaning is not yet stated consistently, and the same
Component-output port may currently receive several exposure names. Third,
Freeze requires at least one exposure but does not require every included
Component to contribute to an exposed result, so a disconnected Source or a
dead terminal branch can be frozen and replayed despite having no effect on
Named Outputs.

These are topology and authoring-contract defects only. No optical equation,
Physical Value invariant, action inventory, polarization law, numerical
admissibility budget, public root export, device rule, or Workstation lifecycle
is being reopened.

## Decision

### Canonical structure is a typed, acyclic, multi-source Assembly; a tree is only a reading projection

The canonical structure is a typed, acyclic, multi-source Assembly. Sources are
entries; ordinary Component ports create branches; declared multi-input actions
create multi-parent convergence; and independent Wave and Ray subgraphs create
multiple source entries inside one frozen Assembly. A tree is a valid local human
reading projection of one branch, but it is never a second persisted or
executable truth. No tree representation becomes persisted or executable.

Mutable authoring state (`include`, `connect`, `expose`) builds one
intentionally mutable construction surface. `Freeze` compiles that surface
into the existing immutable frozen facts. No persistent builder and no second
topology representation are added; the canonical executable topology is the
typed, immutable, multi-source directed acyclic structure that the existing
frozen-fact owner already records.

### Frozen researcher cognitive order

The researcher-facing cognitive order is frozen verbatim as:

```text
include -> connect -> expose -> check/freeze -> host -> run -> Named Outputs
```

Authoring begins cleanly (`include`), connections develop in physical order
(`connect`), exposure turns calculation into an experimentally named result
(`expose`), `check`/`freeze` resolve the structure into one truth, `host`
mounts it immutably, and `run` closes the path through one replay into Named
Outputs.

### Frozen validation order

The validation order is frozen verbatim as:

```text
author-operation atomicity
-> base topology closure
-> exposed-path reachability
-> immutable frozen facts
-> isolated meta replay and Memory Check
-> real replay and Named Outputs
```

Author-time feedback delegates to the same private topology predicates that
Check and Freeze use; no rule is implemented independently in the facade, and
author-time guards and Freeze-time backstops call the same predicates so early
feedback cannot drift from final validation. Exposed-path reachability is
computed only AFTER base topology validation has succeeded, so a structurally
invalid topology never produces a cascading dead-path error list.

### Explicit physical branching

One ordinary Component output port may have at most one downstream connection.
Ordinary branching requires declared multi-output Component ports. Directional
branching instead uses typed physical Terminals and finite Encounters. Optical
power is never copied by topology; it changes only under the owning physical
law.

### Explicit physical convergence

Each input port has exactly one producer. Only a declared multi-input action
(for example a Wave Combination or a reciprocal-scattering action whose role
contract declares multiple named inputs) may combine several upstream Physical
Values. Physical Values are never merged implicitly by topology.

### Atomic authoring operations

`connect` is atomic with respect to authoring state. It validates source and
destination membership, port tokens, declared ports, Physical Value
compatibility, source-output occupancy, and destination-input occupancy BEFORE
appending the connection. A rejected connection leaves the prior valid
authored state unchanged. Whole-topology Check and Freeze repeat the same
occupancy rule as a defensive invariant through the same private authority.

### Authored Exposure

An Authored Exposure is one non-consuming user-facing name for one computed
Physical Value output. It is explicitly NOT an Optical Role, NOT a splitter,
NOT a Detection, NOT a sensor, NOT a tap, and NOT a loss. Naming an exposure
does not consume or alter the Physical Value: it changes no power, phase,
polarization, direction, status, or Optical Path.

An Authored Exposure may name an output that also has one downstream
connection, so a differentiable intermediate state can be inspected without
pretending to add a physical splitter. One stable Component-output anchor may
have at most one exposure name; a second name for the same anchor fails before
exposure state changes. Distinct ordinary Component output ports remain
independently exposable, and authored exposure order remains the Named Outputs
order.

Detection remains the only Wave role that derives Intensity; an exposure
cannot be mistaken for a detector or sensor.

### Honest memory consequence of an intermediate exposure

An intermediate Authored Exposure — one that names a topologically intermediate
Physical Value — becomes a final Named Output and remains live through run
completion, even though it does not consume or alter the physics. A physically
non-consuming readout is therefore NOT a hidden zero-cost computation claim:
the conservative Memory Estimate must account for that retained lifetime. The
existing Workstation shared-storage deduplication evidence (that one Tensor
storage contributes only once when several Named Outputs alias it) survives
this contract, but it must migrate to a legal output-alias shape rather than
relying on two Authored Exposures for one Component-output anchor.

### Exposed-path reachability

Exposed-path reachability is reverse reachability from every Authored
Exposure through declared input connections. It is computed only AFTER base
topology validation (cycle, connection compatibility, declared-port,
input-presence, and input-cardinality checks) has succeeded. Every included
Component must belong to at least one exposed path before Freeze succeeds.

Reachability is Component-level, not ordinary output-port exhaustiveness: a
multi-output Component is retained when at least one output reaches an
exposure, and another unconnected, unexposed ordinary output port remains
legal. This rule is partially superseded for energized directional Terminal
outputs: each must be connected, exposed, or explicitly disposed by a Route
End. No terminal Component, sensor, retained-intermediate container, or new
Optical Role is introduced to absorb an ordinary unused port: invalid dead
subgraphs fail rather than being silently removed.

### Frozen stable topology error identities

The following exact stable topology error identities are frozen here. Later
tickets implement these verbatim strings; each is used consistently at author
time and at defensive whole-topology validation, with no second synonymous
identity and no leaked Python collection or assertion failure:

- `assembly_output_port_reused` — a second `connect` reuses an occupied source
  output port.
- `assembly_input_port_count_mismatch` — a second `connect` reuses an occupied
  destination input port.
- `assembly_expose_output_reused` — a second Authored Exposure names the same
  stable Component-output anchor.
- `assembly_component_not_on_exposed_path` — an included Component that
  reaches no Authored Exposure.

### Unchanged product boundary (preserved)

All of the following are preserved unchanged by this contract:

- All twenty-four public Optical Component actions, their public names, optical equations,
  polarization contracts, exact-preservation paths, binary64 admissibility
  budgets, stable physical errors, and CPU/CUDA equations.
- The two top-level public exports (`Workstation` and `install_state`).
- State Installation and immutable hosting; the existing lifecycle
  `construct -> freeze -> host -> run` is unchanged, topology remains
  immutable after Freeze while Parameters remain trainable, and this contract
  introduces no second runtime.
- The one-way dependency direction `workstation -> optics -> _numerics`; this
  contract creates no fourth seam.
- The one frozen-fact owner, one private replay implementation, deterministic
  topological order, release facts, exposure order, and copy/serialization
  behaviour.

### Identified narrowing targets (now narrowed by visible partial supersession)

This ADR does NOT rewrite earlier ADR history. It identifies the exact
existing statements in the active ADR chain whose "final Physical Value only"
and "no retained intermediate" wording required visible narrowing once the
Authored Exposure implementation became present truth. That narrowing has now
been applied by the active-truth convergence ticket as honest
partial-supersession banners on ADR-0002 and ADR-0003 (and by direct
narrowing of the active prose in `CONTEXT.md` and `architecture.md`, which are
active truth rather than historical record):

- **ADR-0002**, the Assembly subsection: "`expose` assigns a user-facing name
  to a final Physical Value. Assembly retains that authored exposure, while
  populated Named Outputs exist only as the result of Workstation Run." The
  "final Physical Value" qualifier has narrowed to "a computed Physical Value
  output", which may be topologically intermediate when that output also has
  one downstream connection. The "populated Named Outputs exist only as the
  result of Workstation Run" clause stays in force; the narrowing concerns
  only what may be named by `expose`.
- **ADR-0003**, the memory lifetime model: the single weak tensor-storage
  lifetime tracer enumerates "final Physical Values" as the retained
  run-result category that enters the model (alongside operator inputs and
  results, aliases, disposable temporaries, non-persistent caches, and
  autograd-saved storage). The implicit "no retained intermediate" reading —
  that only final Physical Values are retained as run results — has narrowed
  to also account for an intermediate Authored Exposure promoted to a Named
  Output and retained through run completion, so the conservative Memory
  Estimate follows the retained storage lifetime rather than treating the
  exposure as free.

The adjacent active-prose mirror of the ADR-0002 wording in `architecture.md`
("`expose` assigns a user-facing name to a final Physical Value.") was the
same narrowing target at the active-truth layer and has been converged by the
active-truth ticket. The older wording in ADR-0002 and ADR-0003 stays in place
under the new banners as the bannered frozen record, and this ADR-0011
carries the forward contract that reconciles it.

## Exclusions kept explicit

This decision adds no optical capability and no new public surface. The
following exclusions are kept explicit and adjacent; they are not implicit and
are not deferred to a later ADR:

- No cycles and no cavity/feedback solver; topology is acyclic.
- No nested Assembly execution and no subassembly runtime; one Assembly is
  not authored or replayed inside another.
- No public Graph, Tree, Node, Builder, port-reference wrapper, traversal
  interface, visualization interface, generic topology framework, or
  path-reference abstraction. This is consistent with ADR-0002's rejection of
  a public Optical Graph: this initiative deepens Assembly, it does not
  revive a public Graph.
- No Wave-to-Ray conversion and no Ray-to-Wave conversion; no converter.
- No second runtime and no parallel replay implementation; meta, memory, and
  real replay share the one existing frozen fact.
- No automatic insertion of splitters, Combinations, Beam Dumps, Detections,
  or exposures; no public path optimization, dead-code elimination, automatic
  pruning, or execution-time topology repair.
- No Beam Dump, terminal Component, sensor, retained-intermediate container,
  or new Optical Role.
- No requirement that every ordinary Component output port be connected or
  exposed; an unused ordinary port remains legal when its owning Component
  otherwise contributes to an exposed path. Energized directional Terminal
  outputs follow the stricter disposition rule above.
- No public interface alias, compatibility shim, migration period, or
  `strict=False` authoring mode.

## Why this is surprising

The durable decision is surprising on two surfaces. First, it explicitly
permits one non-consuming intermediate readout (an Authored Exposure on an
output that also has one downstream connection) while continuing to forbid any
implicit optical fan-out: naming a result is not splitting it. That trade-off
must be visible in the ADR chain because it narrows the older "final Physical
Value only" wording honestly rather than silently. Second, it tightens the
authoring contract (atomic `connect`, one exposure per anchor, exposed-path
reachability) while preserving the mutable-authoring intent: the authoring
surface remains intentionally mutable, and `Freeze` remains the one point that
compiles it into immutable truth. The tightening therefore does not create a
persistent builder or a second topology representation even though it makes
author-time rejection as strict as Freeze-time validation.

## Rejected alternatives

- **Revive a public Graph/Tree/Node/Builder framework.** Rejected: ADR-0002
  closed `Assembly` as the one authored topology and rejected the legacy
  public Optical Graph. The canonical structure is a private typed DAG owned
  by the existing frozen-fact module; a public graph abstraction is the
  failure mode this initiative exists to avoid.
- **A strict tree as the authoritative execution model.** Rejected: explicit
  splitting, multi-input convergence, and independent Wave/Ray subgraphs all
  make the real shape a multi-source DAG. A tree is only a local reading
  projection; persisting or executing a tree would create a second topology
  truth.
- **Treat exposure as a physical detector, sensor, tap, branch, or loss.**
  Rejected: an exposure is non-consuming and executes no Optical Role.
  Modeling it as a physical action would change power, phase, polarization, or
  Optical Path, which is exactly what "non-consuming" forbids.
- **Allow several exposure names on one Component-output anchor.** Rejected:
  that creates aliases for one physical fact inside Named Outputs. Distinct
  output ports remain independently exposable; one anchor gets at most one
  name.
- **Absorb an unused output port with a Beam Dump or terminal role.**
  Rejected: it invents a physical object to satisfy a topology rule. An unused
  port is legal when its owning Component otherwise contributes to an exposed
  path; dead subgraphs fail rather than being physically terminated.
- **Make exposed-path reachability a separate persistent structure.**
  Rejected: reachability is computed from the existing frozen facts after base
  topology validation. Persisting it would add a second topology
  representation.
- **A persistent builder that accumulates immutable topology during authoring.**
  Rejected: authoring state is intentionally mutable; `Freeze` is the one
  compile point. A persistent builder would split the authoring surface from
  the frozen facts.
- **A warning period, compatibility alias, or `strict=False` path for the new
  author-time guards.** Rejected: any of these leaves a partially invalid
  Assembly in the wild, which is the contract break this initiative removes.

## Important cost

- **Author-time strictness matches Freeze-time strictness.** Making `connect`
  and `expose` reject before state change costs implementation discipline:
  each author-time guard must delegate to the same predicate that the
  defensive whole-topology validation uses, and the two must not drift. The
  payoff is that a rejected authoring operation has no effect, so one authoring
  mistake never forces a rebuild of the complete optical path.
- **Intermediate exposures cost real memory.** Permitting an Authored
  Exposure on an intermediate output is physically free but numerically
  honest: the retained value must be counted in the conservative Memory
  Estimate. The cost is bounded by the deduplication rule that one Tensor
  storage contributes only once when several Named Outputs alias it.
- **One additional ADR.** ADR-0011 adds governance surface. Leaving the
  canonical DAG shape, the atomic authoring contract, the Authored Exposure
  semantics, and the exposed-path rule only in private code would be smaller
  in files and larger in ambiguity, because the older "final Physical Value
  only" wording would otherwise contradict the implemented intermediate
  exposure silently. The honest partial-supersession link now applied to
  ADR-0002 and ADR-0003 keeps the ADR chain from drifting apart.

## Implementation status

Implemented present truth. The production cutover has landed and its
decisive evidence is green:

- 02 makes `connect` atomic and freezes the `assembly_output_port_reused` and
  `assembly_input_port_count_mismatch` identities at both author time and
  defensive whole-topology validation.
- 03 converges Authored Exposure semantics (one name per stable
  Component-output anchor) and freezes the `assembly_expose_output_reused`
  identity; the former double-Exposure alias memory witness migrated to a
  legal Workstation output-alias shape that retains the shared-storage
  deduplication proof.
- 04 closes exposed-path reachability and freezes the
  `assembly_component_not_on_exposed_path` identity.
- 05 reran the existing Wave, polarized-Ray, mixed Assembly, lifecycle,
  gradient, and available CUDA evidence under the stricter topology and added
  independent no-drift verification.

The active-truth convergence ticket (06) applied the honest forward banners
to ADR-0002 and ADR-0003 identified above, narrowed the active prose in
`CONTEXT.md` and `architecture.md`, and transitioned this ADR-0011 from
`Accepted — implementation pending` to `Accepted — implemented present truth`.
This ADR remains scoped to authoring and topology: it claims no new optical
capability, cyclic solver, nested Assembly, public graph, sensor, or
performance advantage.

## Consequences

- The canonical Assembly topology is frozen as a typed, acyclic, multi-source
  DAG with atomic authoring, declared branching and convergence, one-name
  Authored Exposures, and exposed-path reachability. The production tickets can
  be reviewed against this single ADR rather than against shifting prose.
- A tree remains only a local reading projection; no second persisted or
  executable topology truth is introduced.
- The four stable topology error identities are frozen verbatim and bound to
  their owning defects; later tickets implement these exact strings at both
  author time and defensive whole-topology validation.
- The "final Physical Value only" and "no retained intermediate" wording in
  ADR-0002 and ADR-0003 is narrowed by visible partial-supersession banners
  applied by the active-truth convergence ticket; the older wording stays in
  place as the bannered frozen record, and ADR-0011 carries the forward
  contract that reconciles it.
- The active inventory (all twenty-four public Optical Component actions, the two top-level public
  exports, the three production seams, and the one-way dependency direction
  `workstation -> optics -> _numerics`) is unchanged; no new optical equation,
  public capability, dependency seam, fourth role package, public Graph
  abstraction, or second runtime is introduced.
