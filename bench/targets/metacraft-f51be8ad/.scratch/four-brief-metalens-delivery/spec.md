# Four-brief low-na metalens delivery

Status: superseded by ../metalens-sonnet-convergence/spec.md

## Problem Statement

As a metasurface researcher, I need MetaCraft to turn four concise,
literature-inspired metalens briefs into real, replayable results. The current
worktree contains the necessary scientific pieces, but its planning records
still disagree on period validity, paper-provided geometry, geometric-phase
quantization, field propagation, and what counts as a completed experiment.
The partial Field migration also mistakes retained scalar applicability for a
NumPy implementation requirement, leaves production on unqualified
four-times padding while new Torch tests cannot collect, and makes oversized
tests recompute compiler, fake-solver, matching, propagation, and replay
behavior together. Those disagreements make a long Lumerical run expensive
without making the result trustworthy.

## Solution

Keep one public operation:

`conduct(brief) -> waiting Study | independent Results`

The compiler first obtains the exact material evidence needed to establish the
period limit. When the brief omits a period, one provider-neutral period
advice recommends only a cell period. Pure scientific rules validate it
unchanged, derive the height domain and, for propagation phase, the phase
envelope, and then request a separate height advice. The brief alone fixes its
dimension step. Neither consultation may change the control strategy or shape
family, and no cell sweep opens before both choices are valid.

The current G0-only proof requires:

`physical ceiling = min(sampling ceiling, order ceiling)`

The period limit is the greatest multiple of 10 nm strictly below that
ceiling. A selected period must lie on the 10 nm grid and must not exceed the
limit. The compiler never silently floors, clamps, or replaces advice.

Two propagation-phase briefs gather a complete real cell library and form
independent 8-, 12-, and 16-state phase sets from the same evidence. Two
geometric-phase briefs gather both linear-basis responses for every candidate,
select one anisotropic cell deterministically, and form the aperture by
continuous analytic rotation. They do not invent phase quantization or solve
each orientation.

One complete four-brief delivery therefore contains eight admitted Results:
three propagation Results for each propagation brief and one geometric Result
for each geometric brief. “Four briefs” never silently means “four Results.”

One Torch field realization propagates every completed aperture. Local
workstation observation selects CUDA when available and Torch CPU only when
CUDA is absent; the selected device must then qualify. A failed CUDA
qualification does not fall back silently. Selection occurs once: execution
restores the admitted realization from the task binding rather than observing
the device again. The realization retains complex128 arithmetic and
two-times padding. Focus evaluation uses an axial intensity curve over
`0.8f` to `1.2f`, the complex field at the found focus plane, incident and
transmitted power, and exact execution provenance. It does not retain a full
complex three-dimensional volume.

The four equal-status adapted reproductions are:

1. Johansen-inspired circular propagation phase: 940 nm, NA 0.16, focal
   length 200 µm, amorphous-silicon pillars on silica, x-linear incidence,
   10 nm dimension step.
2. Pi-inspired square propagation phase: 1550 nm, NA 0.30, focal length
   200 µm, amorphous-silicon pillars on silica, x-linear incidence, 10 nm
   dimension step.
3. Khorasaninejad-inspired rectangular geometric phase: 532 nm, NA 0.30,
   focal length 100 µm, titanium-dioxide nanofins on silica, right-circular
   incidence, 20 nm dimension step.
4. Yang-inspired elliptical geometric phase: 1550 nm, NA 0.32, focal length
   30 µm, silicon pillars on silica, right-circular incidence, 100 nm
   dimension step.

Each brief also declares aspect limit 8, Lumerical FDTD as its solver
preference, one local-workstation budget, and explicit omission of large-na,
multiwavelength, and optimization work. These are brief facts, not inherited
compiler defaults.

These briefs deliberately omit cell period, atom height, and lateral
dimensions. The cited papers define the design problem and comparison
context, not MetaCraft's answer.

## User Stories

1. As a researcher, I want to submit one brief to `conduct`, so that I do not
   have to assemble a workflow manually.
2. As a researcher, I want each brief to preserve its wavelength, numerical
   aperture, focal length, materials, control strategy, and shape family, so
   that advice cannot rewrite the experiment.
3. As a researcher, I want paper-inspired briefs to omit paper cell answers,
   so that MetaCraft demonstrates design rather than copying.
4. As a researcher, I want solver-native material indices sampled at the
   working wavelength, so that period validation uses actual evidence.
5. As a researcher, I want separate advice for period and height, so that each
   consultation answers one grounded scientific concern.
6. As a researcher, I want every recommendation retained with its rationale
   and source, so that the design is reviewable and replayable.
7. As a researcher, I want invalid or unavailable advice to return a waiting
   Study, so that the program never fabricates missing facts.
8. As a researcher, I want the period to obey both sampling and order limits,
   so that a G0-only aperture field remains scientifically complete.
9. As a researcher, I want the strict physical ceiling converted to a clear
   10 nm period limit, so that equality and rounding are deterministic.
10. As a researcher, I want rejected period advice reported without a solver
    launch, so that invalid sweeps cost no licence time.
11. As a researcher, I want propagation candidates swept in parallel under
    observed workstation and licence capacity, so that real libraries finish
    efficiently.
12. As a researcher, I want each external process bound to one four-core,
    no-SMT, locality-aware lane with its memory limit, so that workstation
    execution remains stable.
13. As a researcher, I want one propagation library reused for 8-, 12-, and
    16-state matching, so that quantization comparison adds no solver work.
14. As a researcher, I want phase distance to be cyclic at `0 == 2π`, so that
    cells near the wrap point are matched correctly.
15. As a researcher, I want every propagation phase set returned separately,
    so that no hidden winner erases scientific alternatives.
16. As a researcher, I want both x- and y-basis evidence for each geometric
    candidate, so that polarization conversion is established rather than
    assumed.
17. As a researcher, I want an interrupted geometric sweep to redo only the
    missing basis, so that admitted evidence is not wasted.
18. As a researcher, I want geometric candidates ranked deterministically by
    converted power and retained leakage, so that replay selects the same
    cell.
19. As a researcher, I want one selected geometric cell rotated analytically,
    so that PB phase does not trigger orientation-by-orientation solves.
20. As a researcher, I want the Yang sweep to honor its 100 nm dimension
    step, so that the live candidate count remains practical.
21. As a researcher, I want circle, square, rectangle, and ellipse to retain
    typed natural dimensions through evidence and fabrication output, so that
    geometry is never reconstructed from an untyped bag.
22. As a researcher, I want CUDA selected whenever it exists and Torch CPU
    selected only when it does not, so that execution policy is explicit.
23. As a researcher, I want the exact device, dtype, padding, numerical
    convention, and binding recorded, so that field evidence is reproducible.
24. As a researcher, I want focus searched across `0.8f` to `1.2f`, so that a
    shifted real focus is not mistaken for failure.
25. As a researcher, I want separate x/y half-maximum widths, depth of focus,
    transmission, and concentration results, so that fabrication review has
    useful evidence.
26. As a researcher, I want one ordered fabrication cell table and one full
    aperture identity map, so that the result can be manufactured without
    reverse engineering.
27. As a researcher, I want real Lumerical evidence for all four delivery
    briefs, so that deterministic fakes cannot be presented as completion.
28. As a researcher, I want exact authority replay to return the same result
    without repeating admitted scientific work, so that a run remains
    auditable.
29. As a maintainer, I want Rust authority and protocol bytes untouched, so
    that Python science can evolve without reopening the frozen core.
30. As a maintainer, I want one deep compiler seam, one solver Adapter, and
    one Field module, so that responsibility stays local and understandable.
31. As a maintainer, I want production propagation and its qualification to
    use the same exact realization facts, so that a configuration is never
    called qualified without being exercised.
32. As a maintainer, I want compiler, Adapter, matcher, Field, Result, and
    replay behavior tested at their own seams, so that one failure does not
    trigger every expensive scientific operation.
33. As a maintainer, I want obsolete shallow tests replaced when the deep
    Field interface is established, so that contradictory NumPy and Torch
    expectations cannot coexist.
34. As a researcher, I want the four-brief matrix to return exactly eight
    Results, so that propagation quantizations are not collapsed or confused
    with geometric rotation.
35. As a researcher, I want impossible candidate counts rejected before a
    sweep, so that licence time is not spent on a library that cannot form the
    requested result shape.
36. As a researcher, I want a missing dimension step requested during brief
    completion, so that fabrication resolution is never invented downstream.

## Implementation Decisions

- `conduct` remains the sole application interface and highest acceptance
  seam. It coordinates compile, gather, admit, and recompile; it does not
  interpret Lumerical output or perform field mathematics.
- Rust owns lifecycle truth, permits, receipts, and admission only. No Rust
  source, protocol, or state vocabulary changes in this effort.
- The pure compiler keeps propagation phase and geometric phase as compiled
  routes, not fixed workflows. It can later select other methods without
  changing `conduct`.
- Material evidence precedes advice because the order ceiling needs the exact
  substrate index at the brief wavelength.
- The current G0-only method accepts only periods below both ceilings. The
  compiled period limit is the greatest 10 nm multiple strictly below their
  minimum; an exact grid-aligned ceiling loses one full 10 nm step.
- Both physical ceilings remain exact decimal values in evidence. Only the
  separate period limit is grid-aligned; the order ceiling is never rounded
  first and then mistaken for the physical threshold.
- Period advice proposes the actual cell period and nothing else. Once that
  exact proposal is valid, the compiler derives the height domain and
  propagation-phase envelope; height advice then proposes one allowed height.
  Validation accepts each proposal unchanged or returns a typed finding.
- The existing adviser seam deepens through two explicit operations,
  `recommend_period` and `recommend_height`. Their records remain distinct and
  both reach Result provenance and replay. No second provider Adapter or
  generic choice framework is introduced.
- The height domain retains one discriminated period basis: explicit brief
  constraint or exact period advice. No synthetic advice and no separate
  mutable period state are introduced.
- Design retains scientific intent and the brief-derived sampling ceiling; it
  does not grow a provisional optional period. The height domain owns the
  validated cell period, exact order ceiling, period limit, basis, regime, and
  candidate counts. No `PeriodChoice` type or lifecycle position is added.
- Aperture extent and occupied-site validation wait for that height-domain
  period. Initial compilation never substitutes the sampling ceiling merely
  to construct an aperture early.
- The current height priors are explicit. The 532 nm visible brief considers
  500–800 nm in 50 nm steps. The 940 nm and 1550 nm infrared briefs consider
  `0.5 × wavelength` through `0.6 × wavelength`, rounded inward to 50 nm:
  500/550 nm at 940 nm and 800/850/900 nm at 1550 nm.
- The dimension step is an immutable brief fact and is used directly by the
  current candidate sweep. Neither advice nor the Adapter may coarsen it.
- A generated-geometry brief without a positive integer dimension step remains
  incomplete. Wording review requests the fact; no period-based 5/10/20 nm
  default survives. A fixed cited geometry need not invent a step.
- Public Python and canonical evidence use `dimension_step_nm` consistently.
  The older `lateral_step_nm` spelling is migrated atomically and receives no
  compatibility alias.
- Height validation uses exact route arithmetic before dispatch. Propagation
  phase needs at least sixteen distinct generated dimensions; geometric phase
  needs at least two distinct axis values for one anisotropic pair. Passing
  this check establishes no response, phase coverage, or efficiency claim.
- The four standard briefs fix the route and shape family but omit period,
  height, and lateral geometry. Shape identity is not advice.
- The public examples module exposes exactly
  `johansen_circle_brief`, `pi_square_brief`,
  `khorasaninejad_rectangle_brief`, and `yang_ellipse_brief`. The older
  400 nm and 355 nm tracers move to compact test support where still useful;
  they do not remain competing standard examples.
- The existing scientific `Cell` is the sole fabrication cell for all four
  shapes. Its typed geometry is `Circle`, `Square`, `Rectangle`, or `Ellipse`;
  Jones evidence wraps that same `Cell` instead of preserving the parallel
  `RectangularFin` model or adding an elliptical counterpart. Adapter
  candidates remain transient construction input and preserve the typed
  geometry until native construction.
- Shape values use lowercase natural language—`circular pillar`, `square
  pillar`, `rectangular fin`, and `elliptical pillar`. Underscored aliases do
  not survive in canonical evidence.
- Propagation phase performs one complete real sweep per brief, then forms
  independent 8-, 12-, and 16-state results with one shared cyclic matcher.
- Propagation matching computes cyclic losses over the finite library once,
  forms a stable state table, and realizes the full aperture through vectorized
  identity lookup. It never searches the cell library independently at every
  aperture site.
- Geometric phase performs one complete real candidate sweep at the declared
  dimension step. Every candidate has independent x- and y-basis work
  identities. Selection maximizes `converted power - retained power`; ties
  prefer greater converted power, then the smaller axis product, then the
  smaller long/major axis, then the smaller short/minor axis.
- Geometric evidence, choice, orientations, and Field channels use
  `converted` and `retained` consistently. Leakage remains a Result measure
  derived from the retained channel, not a second name for that channel.
- Geometric phase returns one result per brief. Aperture phase is the analytic
  rotation relation for the admitted polarization convention; it is
  continuous and requires no additional Lumerical solve.
- The geometric compiled claim is `orientations`, established directly from
  one cell choice and the target phase. The old 8/12/16
  `GeometricPhaseSet`, `phase_level`, and rotation-index/count model is
  removed; it is not retained beside the continuous relation.
- The Lumerical Adapter owns product discovery, licence and version checks,
  native templates, session reuse, geometry read-back, evidence parsing, and
  run manifests. It receives scientific material and geometry facts rather
  than choosing them.
- Each admitted lane opens one hidden Lumerical session and reuses it across
  its candidate wave. Candidate work does not reopen a GUI or product session;
  a failed process tree invalidates only that lane's unfinished work.
- The workstation owns the hidden session and its direct-engine descendants
  for the lane's complete lifetime: four physical cores, no SMT, local memory,
  and the shared 16 GiB lane limit apply to the whole process tree. Session
  reuse is not an unplaced exception and creates no GUI concept.
- Workstation dispatch observes physical cores, locality, memory, and current
  licence capacity. It opens as many independent four-core lanes as the
  tightest capacity permits; callers provide no worker count.
- With session reuse, Lumerical capacity records the native
  `lumerical_gui` and `lumerical_solve` feature limits separately and takes
  the minimum of both and workstation lanes. The Adapter does not infer one
  pool from the other or introduce a generic licence framework.
- Field keeps one public representation by electromagnetic components. Its
  single Torch implementation moves tensors to the bound device, uses
  complex128 and two-times padding, and does not expose CPU and CUDA as
  separate scientific methods.
- Real coordinate and wave-number tensors are explicitly float64; complex
  field and spectrum tensors are explicitly complex128. The implementation
  never relies on Torch's global default dtype.
- Numerical provenance uses provider-neutral mathematical language: negative
  forward exponent, inverse normalization by sample count, discarded
  evanescent terms, and two-times padding. NumPy-branded convention values are
  retired.
- Field provenance names Torch as the implementation and CUDA or CPU as the
  device. It does not call either one an engine, backend, algorithm choice, or
  separate scientific method.
- Workstation observation selects CUDA when available and Torch CPU only when
  CUDA is absent. Qualification applies to the selected device and exact
  realization facts. A qualification or execution failure never triggers a
  hidden device change.
- Composition observes the device once and admits that exact realization in
  the task binding. Execution restores the realization from that binding; it
  never calls device availability again. Failed qualification omits the
  binding and leaves `conduct` at an honest waiting Study instead of raising
  an application error.
- NumPy remains permitted for immutable authority-array representation,
  canonical serialization, and small non-propagating evaluations. Numerical
  FFT propagation is Torch-only.
- Each nonzero Field component prepares one source spectrum. An identically
  zero component remains explicitly present but triggers no FFT.
- Qualification records a safe working-memory budget for the selected device
  after retaining a reserve; it cannot promise a plane count before the
  aperture grid exists. Execution refreshes usable memory, takes no more than
  the qualified budget, and derives the actual axial batch from the real
  two-times-padded grid and explicit tensor sizes. The recorded batch is
  neither a caller option nor a test-imported constant. If one plane cannot
  fit, the study waits without changing device or padding.
- The Field migration is atomic: the production implementation, dependency,
  binding, qualification, provenance, and tests move together. There is no
  accepted intermediate state in which tests require an unrealized interface
  or qualification exercises different padding, dtype, device, or numerical
  conventions from execution.
- Qualification uses the exact production configuration to verify
  zero-distance reconstruction and an apodized Gaussian propagation and
  refinement case. It does not retain the old nonzero-distance finite
  plane-wave fixture through a hidden one-times-padding exception.
- The focal region stores the axial intensity curve, the complex best-focus
  plane, incident reference power, transmitted aperture power, binding, and
  execution provenance. Focus evaluation consumes that evidence without
  propagating again. The ambiguous existing `source_power` name is retired
  atomically rather than preserved as an alias.
- A Result is admitted only from a complete proof. Fake evidence supports
  deterministic tests; only native Lumerical evidence satisfies the four
  delivery experiments.
- Existing implementation that already satisfies these decisions is retained.
  This effort adds no registry, alternate lifecycle, compatibility framework,
  or aesthetic repository-wide rewrite.
- Existing Modules deepen in place. The compiler owns period rules, the Advice
  Adapter owns consultation, the Field Module owns Torch execution and
  qualification, and the workstation observes local facts. No period planner,
  device manager, backend registry, or CPU/CUDA type split is introduced.

## Testing Decisions

- `conduct(brief)` remains the highest composition seam, but daily tests use
  only two compact end-to-end tracers: one propagation phase and one geometric
  phase. The four canonical brief factories are tested for exact intent,
  compilation, and ready-task formation without repeatedly running ASM.
- Pure compiler tests cover material-first advice, invalid advice, missing
  advice, the separation of period and height consultations, strict ceiling
  arithmetic, 10 nm flooring, and the exact-grid edge case such as 850 nm
  becoming a maximum of 840 nm.
- Height-domain tests cover the exact propagation and geometric candidate
  minima and the four briefs' finite height priors without treating either
  count as scientific-response evidence.
- Route tests observe scientific behavior: cyclic propagation matching,
  independent 8/12/16 results, paired geometric bases, deterministic cell
  selection, analytic rotation, and missing-basis recovery.
- Adapter tests use a fake native engine to verify all four typed geometries,
  native material use, session reuse, manifests, and automatic dispatch
  without inspecting private implementation structure.
- Field tests verify numerical equivalence, two-times padding, bounded axial
  work, CUDA selection, CPU selection only without CUDA, failed-device
  qualification, and exact provenance through the realization interface.
  They do not lock private constants or source spelling.
- Existing NumPy-FFT expectations, imports of private batch constants,
  uncollectable forward tests, imports from other test-case files, and
  architecture assertions about private implementation spelling are replaced
  rather than layered beneath the new interface tests. Dedicated test-support
  modules remain allowed.
- Expensive propagation is performed once in a focused numerical test.
  Result, refusal, and replay tests consume compact recorded evidence instead
  of recomputing an entire focal region.
- No single acceptance test simultaneously owns compiler interpretation,
  fake-solver generation, all three phase sets, numerical propagation, Result
  formation, and replay. The public `conduct` matrix verifies composition
  while each scientific assertion remains at its smallest truthful seam.
- Live tests remain explicitly enabled and use the configured local
  Lumerical installation. Automated smoke tests stay bounded; delivery runs
  execute the full compiled sweeps and must return six propagation Results
  plus two geometric Results.
- The automated native tracer may launch at most fifteen direct-engine solves.
  This limit does not truncate a delivery sweep: full experiments are separate
  explicitly enabled runs governed only by admitted licence and workstation
  capacity.
- Verification includes focused tests, the public four-brief matrix,
  architecture checks, type checking, CSU on touched files, and an empty Rust
  diff.

## Out of Scope

- Rust changes.
- GUI work.
- CST or COMSOL implementations.
- Large-na execution, vector angular spectrum, or Debye--Wolf propagation.
- Achromatic, multiwavelength, holographic, quasi-BIC, or frequency-selective
  surface execution.
- Optimization or continuous pointwise large-na matching.
- Multi-order G0 reconstruction, order-resolved propagation, or near-field
  stitching.
- Exact paper reproduction or paper efficiency as a pass threshold.
- A fifth standard brief, a plugin system, a generic solver framework, or a
  second Field implementation.

## Further Notes

This specification is the current implementation authority for the
four-brief delivery. Earlier low-na planning remains historical evidence where
it agrees, but its fixed paper geometries, warning-only order rule,
geometric-phase quantization, NumPy FFT, and four-times padding are not current
decisions.

When this specification's implementation tickets are published, the fifteen
overlapping older `ready-for-agent` tickets are marked `wontfix` with a pointer
here. The four older executable specifications—`low-na-phase-route-closure`,
`metacraft-next-phase-matching`, `metacraft-next-python-science`, and
`scientific-process-compiler`—are marked superseded by this specification.
Historical files and `ready-for-human` verification records remain intact.
This is tracker hygiene, not an implementation ticket.

Implementation first establishes the production Torch Field realization,
then closes material evidence through period and height advice. A focused test
cleanup follows those stable interfaces. The Lumerical Adapter then establishes
one contained reusable session per lane before the propagation route admits
circle and square and the geometric route admits rectangle and ellipse. The
last ticket alone runs and replays the complete four-brief matrix. Every ticket
lands green before its successor starts.

## Verification

Tickets 01 through 07 reached `ready-for-human` on 2026-07-28. The default
non-live suite completed with 295 passed and 15 explicitly deselected checks;
Pyright reported no errors or warnings, and Rust retained an empty diff and
status.

The native four-brief delivery remains explicitly gated and was not run during
this implementation pass. Maintainer review established that a canonical brief
must remain unchanged when its proof cannot close: the honest outcome is a
replayable waiting Study with exact diagnostics, never parameter tuning or a
fabricated Result. Eight native Results remain the successful target rather
than a prerequisite for truthful reporting.

The supporting literature facts remain in the existing Research Records.
ADR 0009 owns the narrow system decision that the current G0-only proof must
remain in the zeroth-order domain.
