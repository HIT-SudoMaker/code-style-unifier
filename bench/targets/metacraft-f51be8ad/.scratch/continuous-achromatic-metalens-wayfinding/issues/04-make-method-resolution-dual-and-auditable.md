# Make method resolution dual and auditable

Status: resolved (2026-08-14)

Assignee: Codex

Label: `wayfinder:grilling`

Blocked by: none

Parent: [Find the continuous-achromatic metalens compilation road](../map.md)

## Question

What exact durable facts and tests prove both directions of scientific
compilation: that changing user intent changes the compiled proof as expected,
and that every selected or refused Method can be traced back to the exact
intent, applicability judgment, capability, binding, and evidence that caused
that outcome?

## Comments

### 2026-08-14 investigation

The proposed "achromatic operation key" is not one user-facing algorithm
selector.  The durable concepts are deliberately different at each boundary:

- the Brief preserves a continuous operating-spectrum objective and any
  user-owned mechanism requirement or prohibition;
- the metalens compiler resolves the Design before considering one closed set
  of aim-owned Methods;
- a durable Method assessment records why every considered Method is
  applicable, inapplicable, selected, or refused;
- the resulting Relationship, Route, and Proof own the chosen scientific
  topology; and
- private compiled Task methods remain execution keys hidden from the caller.

This is a dual trace: intent deterministically changes the proof, while every
terminal conclusion can be traversed back through the selected Method,
applicability assessment, exact Plan, capability and binding, admitted raw and
qualified evidence, and preserved Brief.

The current production order is the reverse of the intended ownership:
`compile_metalens` resolves a Relationship first and then copies the selected
Method capabilities into `MetalensDesign`.  It should eventually resolve the
user-owned Design first, assess Methods second, and compile the chosen proof
third.  This is a schema cutover, not an additive compatibility road.

A second prerequisite was found.  `CellStudyPlan` already names the bounded
planning seam accepted by ADR 0024, but current propagation-phase and
geometric-phase execution reconstruct their periodic-request grids directly.
Continuous-band work must not add a spectral planner beside that gap.  The
monochromatic production road should first become
`HeightChoice -> CellStudyPlan -> PeriodicWork`; a spectral plan may then
compose exact single-wavelength work identities without becoming another
lifecycle owner.

The first physical Method remains intentionally narrow: one square-period
realization, one primitive anisotropic rectangle, one immutable geometry and
orientation at every site across the band, PB orientation supplying the
reference-frequency phase intercept, and geometry supplying the spectral
slope and residual.  Complete qualified evidence may prove this Method
insufficient; missing evidence is `unavailable` or `incomplete`, never a
physics refusal.  A coupled two-fin Method is not compiled or selected unless
the primitive Method has first produced an evidence-backed refusal and the
user starts a newly applicable road.

Research record: [Achromatic intent-to-proof traceability](../../../docs/research/2026-08-14-achromatic-intent-to-proof-traceability.md).

### Open decision frontier

The remaining human decisions are the public spectrum language, how much of
the Method-candidate assessment is retained, the meaning of mechanism
constraints, the primitive-rectangle stopping rule, and whether the existing
`CellStudyPlan` production cutover is a mandatory predecessor to spectral
implementation.

## Resolution

Keep one `MetalensBrief` and replace its scalar operating wavelength through
one schema cutover with a closed operating-spectrum value: monochromatic or
continuous band.  Achromatism is not an aim, control strategy, workflow, or
execution key.  An optional mechanism constraint records only a user's
explicit requirement or prohibition; omission lets the metalens compiler
assess the implemented methods.

Resolve `MetalensDesign` from user facts before resolving a Relationship.  The
aim compiler must retain one compact, typed assessment for every implemented
candidate it actually considered: exact design identity, applicability
verdict, grounds, selected claim-method graph or typed refusal.  It does not
retain hypothetical future candidates, transcripts, or arbitrary rule traces,
and it exposes no registry or policy engine.  The compiled Route and Proof
remain the execution-independent scientific topology; private `Task.method`
values remain the only execution keys.

Forward mutation tests must prove that changes to spectrum, mechanism
constraint, NA, polarization, material or fabrication facts change the
assessment and proof when scientifically relevant.  Reverse closure tests
must prove that every selected method and terminal conclusion reaches the
exact Brief, Design, assessment, Plan, binding and evidence references that
caused it.  Missing evidence remains unavailable or incomplete; only complete
qualified evidence may support a physical refusal.

Before continuous-band work is introduced, the monochromatic production road
must use the existing `CellStudyPlan` as its sole bounded periodic-work owner.
Propagation-phase and geometric-phase execution may no longer reconstruct
independent request grids.  This predecessor prevents spectral work from
creating another planning lifecycle.
