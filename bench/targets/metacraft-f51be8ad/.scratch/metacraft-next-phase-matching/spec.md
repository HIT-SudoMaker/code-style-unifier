# Scientific phase matching

Status: superseded by ../metalens-sonnet-convergence/spec.md

## Problem Statement

MetaCraft can already construct qualified Lumerical periodic cells, gather
traceable responses, control local solver capacity, and propagate a scalar
field. Its present scientific result path does not yet express the design that
the researcher approved.

The current compiler carries every allowed atom height into the lateral cell
domain instead of choosing one height first. Propagation phase is matched
independently at every aperture site instead of forming reusable 8-, 12-, and
16-level phase sets. Geometric phase rotates one selected anisotropic cell, but
does not yet expose the same quantized phase-set contract. Candidate names lose
the typed fabrication geometry needed by a researcher, and focus evaluation
observes only the nominal focal plane instead of the focal region.

These gaps also leave soft seams. A mixed-height library can reach matching, a
deterministic fixture can look like native scientific evidence, floating-point
values can leak into identity and lookup, and a route-specific aperture shape
would make future pointwise large-na matching unnecessarily disruptive.

The large-model adviser has an important but deliberately limited role. It
should use the exact brief, compiled height domain, and scientific experience
to recommend one suitable height. It must never turn its own recommendation
into user fact, evidence, solver work, authority state, or an unchecked
scientific choice.

## Solution

MetaCraft will compile each current route through five scientific meanings:
height, cells, states, aperture, and focus.

The compiler first derives a finite route-specific height domain. The
provider-neutral adviser receives the exact brief and immutable domain, then
uses scientific experience to return exactly one height recommendation with
its reasoning and exact input identity. The recommendation remains advice and
contains no claimed solver evidence.

A pure height-selection policy adopts the recommended height only when it is
present in the compiled domain, consistent with the route and exact brief, and
capable of producing a non-empty fabrication domain. An unavailable,
malformed, stale, or out-of-domain recommendation leaves height unresolved.
The adviser cannot invoke a solver, create a task, propose an object to
authority, or mutate a study. Python validates and proposes the resulting
height choice; Rust only admits or rejects the exact record without
interpreting its scientific meaning. Lumerical begins only after that exact
choice and scans lateral geometry at one height.

Once admitted, the `HeightChoice` is fixed. The fabrication domain is
recomputed from that chosen height and the approved aspect limit, then rounded upward to the
route's lateral grid. A detailed cell library may contain many lateral
geometries but exactly one height, one route, one period, one material binding,
one phase reference, and one native evidence closure.

Propagation phase jointly selects distinct geometries for uniformly spaced
phase states. Geometric phase selects one anisotropic cell and produces its
phase states analytically by rotation; it does not run one FDTD solve per
orientation. The current low-na capability returns separate 8-, 12-, and
16-level designs without silently choosing a winner.

`Aperture` is the stable seam between matching and field evaluation. It
contains a typed cell table, a state table, and a two-dimensional map of
stable state identities. A quantized design annotates each state with a phase
level. The state identity, rather than the phase level, is the aperture's
primary reference, so a future pointwise matcher may assign an independent
state at every site without changing the aperture or fabrication contract.

Matching uses normalized integer keys and deterministic content identity.
Dimensions are represented as integer nanometres, quantized phases as integer
levels, and rotations as deterministic integer indices. Persisted identity
does not use Python's process-randomized hash or raw floating-point keys.
Quantized aperture assignment uses vectorized array lookup. A future pointwise
matcher may use a hash index to retrieve a small candidate set before exact
scientific scoring.

The matched complex aperture field is evaluated with the qualified scalar
angular-spectrum implementation. Focus search first surveys the axial interval
from 0.8 to 1.2 times the expected focal length, then refines around the main
focus. Each design returns expected and found focus, focal shift, x and y
half-maximum widths, depth of focus, transmitted fraction, focused fraction,
incident-normalized focus efficiency, peak intensity, and whether the focus
and half-maximum crossings were bracketed. The current focal-power bucket uses
the declared Airy radius, 0.61 times wavelength divided by numerical aperture.

The final design package contains a fabrication cell table, an optical state
table, a labelled aperture table, a focus result, and their exact admitted
evidence closure. Existing native monitor-placement and workstation-capacity
results remain valid implementation evidence. They do not count as a cell
library, `Aperture`, or focus result.

Rust remains unchanged.

## User Stories

1. As a metasurface researcher, I want the adviser to recommend an atom height
   from my exact brief, compiled domain, and scientific experience, so that
   model intelligence is applied to a genuine scientific choice.
2. As a metasurface researcher, I want a model recommendation to remain advice,
   so that it cannot silently become scientific fact or workspace truth.
3. As a metasurface researcher, I want an invalid or unavailable recommendation
   to leave the study unresolved, so that MetaCraft never invents a fallback
   height.
4. As a metasurface researcher, I want the chosen height to cite its brief,
   advice, domain, and route, so that I can reconstruct why it was selected.
5. As a metasurface researcher, I want propagation and geometric phase to
   choose heights independently, so that one mechanism cannot borrow the
   other's physical assumptions.
6. As a fabrication engineer, I want the lateral fabrication domain to be
   derived after height selection, so that aspect-ratio limits describe the
   actual design rather than the tallest allowed candidate.
7. As a fabrication engineer, I want every selected cell to name its shape,
   material, period, width, length, diameter, and height as applicable, so that
   it can be manufactured without parsing an artifact name.
8. As a propagation-phase researcher, I want each quantized phase state to use
   a distinct qualified geometry, so that collapsed phase states cannot pass as
   a complete phase set.
9. As a geometric-phase researcher, I want one qualified anisotropic cell to
   generate all phase states by rotation, so that redundant angle sweeps do not
   consume solver time.
10. As a geometric-phase researcher, I want converted and retained circular
    channels to remain distinct, so that useful focusing and polarization
    leakage cannot be confused.
11. As a researcher, I want separate 8-, 12-, and 16-level design results, so
    that I can compare fabrication burden and optical performance explicitly.
12. As a researcher, I want a phase set to retain target phase, realized phase,
    useful power, leakage power, geometry, rotation, and source evidence, so
    that every phase state is scientifically explainable.
13. As a researcher, I want the aperture to reference stable state identities,
    so that its labels remain meaningful for both quantized and future
    pointwise designs.
14. As a researcher, I want matching to use deterministic tie-breaking, so that
    identical admitted inputs always reproduce the same design.
15. As a workstation user, I want phase assignment to use vectorized lookup and
    indexed candidates, so that matching does not become the bottleneck after
    an expensive sweep.
16. As a workstation user, I want repeated scientific keys to reuse indexed
    results, so that future pointwise matching can avoid redundant searches.
17. As a researcher, I want ASM to consume the realized complex aperture rather
    than an ideal phase mask, so that measured amplitude and phase errors reach
    the focus result.
18. As a researcher, I want focus searched from 0.8 to 1.2 times the expected
    focal length, so that focal shift is observed rather than assumed away.
19. As a researcher, I want a coarse survey followed by local refinement, so
    that the wider focal interval does not require an unnecessarily dense scan.
20. As a researcher, I want x and y focal widths reported separately, so that
    anisotropy is not hidden inside one number.
21. As a researcher, I want depth of focus derived from bracketed axial
    half-maximum crossings, so that a truncated scan cannot claim a complete
    depth.
22. As a researcher, I want transmission, focused fraction, and focus
    efficiency reported separately, so that loss and concentration are not
    conflated.
23. As a fabrication engineer, I want a cell table, state table, and labelled
    aperture table, so that repeated structures remain compact and every site
    can be reconstructed.
24. As a reviewer, I want native observations and deterministic fixtures
    labelled unambiguously, so that test evidence cannot be presented as a live
    scientific result.
25. As a future large-na researcher, I want pointwise matching to produce the
    same `Aperture` contract, so that matching can evolve without changing
    Rust or the fabrication package.
26. As a maintainer, I want scientific matching and focus evaluation to remain
    Python-only changes, so that the frozen Rust authority remains small and
    stable.

## Implementation Decisions

- The highest test seam is one route result: an exact study, advice record,
  admitted evidence closure, and explicit quantization enter; one immutable
  design result leaves.
- `HeightDomain`, `HeightAdvice`, and `HeightChoice` are different meanings.
  Their representations are not interchangeable. A height domain contains no
  solver observation.
- Height advice is provider-neutral. Provider URL, model, request identity,
  response identity, availability, and validation outcome remain traceable,
  while provider branding does not name the public module.
- The adviser receives only the exact brief and immutable compiled height
  domain needed for the recommendation.
- The standard adoption policy accepts exactly one recommendation only when it
  passes every deterministic validation rule. It never ranks, repairs, rounds,
  substitutes, or guesses a recommendation.
- A `HeightChoice` is route-specific and brief-specific. It precedes solver
  binding and the detailed lateral library.
- The scientific order is height domain, height advice, height choice, cell
  library, phase set, aperture, focal scan, and result. `HeightAdvice` is a
  consultation input to height choice, not evidence and not a proof obligation.
  No current route creates a multi-height solver task.
- No detailed lateral sweep task exists while `HeightChoice` remains
  unresolved.
- The minimum feature is the chosen height divided by the aspect limit,
  rounded upward to the route's lateral grid. The maximum feature is the period
  minus that minimum feature.
- A detailed cell library rejects mixed heights, mixed routes, mixed periods,
  mixed material bindings, mixed phase references, duplicate geometries,
  non-finite responses, and incomplete evidence closure.
- The first propagation cell family is the circular pillar and the first
  geometric cell family is the rectangular fin. Typed fabrication geometry
  permits later square pillars and elliptical pillars without widening Rust.
- A phase state binds one cell, one orientation, one target phase, one realized
  complex response, and exact source evidence.
- Propagation phase constructs uniformly spaced phase states and jointly chooses
  distinct fabricable cells. It fails closed when the library cannot provide
  the requested number of distinct states.
- Geometric phase chooses one cell from converted and retained Jones evidence,
  then derives all orientations from base converted phase, handedness, and the
  admitted rotation convention. No per-orientation FDTD task exists.
- The only current quantizations are 8, 12, and 16 levels. They produce three
  comparable results; no implicit winner or unapproved optical threshold is
  introduced.
- An `Aperture` contains cells, states, occupied sites, a state-identity
  map, spacing, radius, and exact evidence references. Phase level is optional
  metadata rather than the map's identity.
- Fabrication identity is deterministic from canonical typed values.
  In-memory indexes use normalized integer tuples. Raw floating-point phase,
  dimensions, and rotations are not persisted lookup keys.
- Quantized assignment computes the level map as an array operation and obtains
  state identities through array lookup. It does not score the complete library
  separately at every aperture site.
- `Aperture` is independent of its evaluator. The current evaluator
  forms one scalar complex field; future vector evaluation may use the same
  physical placements and richer response evidence.
- Focus search uses an explicit focal window with lower ratio 0.8 and upper
  ratio 1.2. It performs a broad survey and a deterministic refinement around
  the main focus.
- A focus result is incomplete when the main peak or required half-maximum
  crossing touches the axial window boundary. It reports that condition rather
  than extrapolating.
- The x and y half-maximum widths are measured at the found focal plane. Depth
  of focus is the contiguous axial half-maximum interval around the found
  focus.
- Transmitted fraction is transmitted power divided by incident aperture power.
  Focused fraction is focal-bucket power divided by transmitted power. Focus
  efficiency is focal-bucket power divided by incident aperture power.
- The current focal bucket is a disk of radius 0.61 times wavelength divided by
  numerical aperture and is recorded with the result.
- A design package writes one cell table, one state table, one aperture table,
  and one focus document for each quantization.
- Native Lumerical observations preserve the already qualified grating frame,
  100 nm reflection and transmission offsets, mesh accuracy four, construction
  read-back, execution evidence, and bounded workstation placement.
- Existing monitor-sensitivity and capacity experiments qualify only those
  implementation facts. They cannot satisfy height, phase-set, aperture, or
  focus obligations.
- Deterministic adapters remain valid test implementations and record that they
  are non-native. A production conclusion cannot mislabel their observations as
  native evidence.
- The Rust source and authority protocol do not change.

## Testing Decisions

- Tests exercise the route-result interface and assert observable design
  results rather than private matching steps.
- Compiler tests prove that advice alone cannot select a height, malformed or
  stale advice leaves height unresolved, and identical exact inputs reproduce
  identical studies.
- Height tests prove route and binding separation, single-height libraries,
  `HeightChoice` fabrication bounds, grid rounding, and rejection of an empty
  fabrication domain.
- Propagation tests prove exactly N distinct cells for N phase states, uniform
  target phases, deterministic joint selection, stable state identity, and
  failure on collapsed or insufficient libraries.
- Geometric tests prove exactly one selected cell, N distinct analytic
  orientations, correct handedness and sign convention, and absence of
  per-orientation solver work.
- Aperture tests prove that quantized layouts use state identities and that the
  same public shape can represent a pointwise fixture without requiring a
  phase-level field.
- Performance tests prove that aperture assignment does not call full-library
  scoring once per site and that output is invariant under candidate input
  order.
- Field tests retain the existing plane-wave and grid-refinement qualifications
  for the scalar angular-spectrum operator.
- Focus tests use analytic or deterministic focal fields to prove axial
  bracketing, refinement, found focus, focal shift, x and y widths, depth of
  focus, and all three power ratios.
- Result tests prove that each 8-, 12-, and 16-level design carries its complete
  evidence closure and fabrication tables.
- Adapter tests retain construction read-back, native execution labelling,
  capacity freshness, and partial-observation reuse.
- Live Lumerical height and lateral sweeps remain opt-in. Their artifacts must
  be labelled native and cannot be replaced by deterministic fixture claims.
- The final suite asserts that Rust source and its public protocol are
  unchanged.

## Out of Scope

- Implementing large-na pointwise matching.
- Vector angular spectrum, Debye or Richards-Wolf propagation, and full-device
  FDTD.
- Optimizers, inverse design, genetic algorithms, simulated annealing, and
  holographic sequence optimization.
- Multi-wavelength achromatic design.
- Square propagation pillars and elliptical geometric pillars in the first
  tracer implementation.
- CST or COMSOL adapters, templates, license checks, execution, or native
  materials.
- Automatically choosing one of the 8-, 12-, and 16-level results.
- Changing or widening the Rust authority protocol.

## Further Notes

The earlier implementation remains useful below the corrected seams: the
Lumerical grating construction, complex response extraction, polarization
convention, scalar propagator, authority closure, and bounded workstation
execution are retained.

The current live experiment used a 400 nm wavelength, 660 nm period, 600 nm
circular pillar, 100 nm grating-plane offsets, and mesh accuracy four. It
validated construction and sensitivity, not height selection, phase coverage,
quantized matching, or focal performance.

This specification supersedes earlier claims that continuous per-site matching
and a single nominal focal plane complete the low-na propagation and geometric
results. Implementation tickets remain subject to researcher review before
they become an implementation frontier.
