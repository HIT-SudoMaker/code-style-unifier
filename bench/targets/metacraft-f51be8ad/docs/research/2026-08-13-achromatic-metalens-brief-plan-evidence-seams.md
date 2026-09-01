---
record_type: research_record
date: 2026-08-13
status: research_finding
authority_level: none
current_capability: false
---

# Continuous-achromatic metalens: Brief, plan, and evidence seams

## Research question

For MetaCraft's next continuous-achromatic metalens effort, which facts belong
to user/aim intent, which belong to design and bounded planning, and which are
periodic-response evidence? Should the existing aim-owned `MetalensBrief` be
changed, inherited, replaced, or left intact?

This record uses the repository's accepted ADRs and current source as the
first-party architecture contract, and the original Wang--Tsai papers as the
primary scientific sources. It makes no implementation decision and changes
no current capability.

## Verdict

The user's concern is correct. MetaCraft's current architecture deliberately
separates four meanings:

```text
aim-owned Brief
    -> resolved Design and compiled Study
    -> bounded CellStudyPlan
    -> PeriodicResponse observation and admitted evidence
```

A continuous-achromatic extension must preserve this separation. In
particular, the spectral sweep grid, candidate geometries, response channels,
work count, phase-unwrapping procedure, and selected compensation elements are
not user facts and must not be added to a Brief merely because the new proof
needs them.

The least disruptive and most faithful type decision is:

1. **Leave the existing `MetalensBrief` canonical contract untouched.** It is
   the exact input identity of the four established monochromatic cases, and
   application resumption requires byte-identical brief content.
2. **Do not subclass `MetalensBrief`.** Inheritance would wrongly inherit its
   required scalar `wavelength_nm`, single-wavelength validation, and current
   control-strategy assumptions.
3. **Add a sibling aim-owned brief under `science.metalens/` only when the new
   proof is specified.** A name such as `ContinuousBandMetalensBrief` states an
   operating-condition category, not a paper or implementation. It should
   derive directly from the shared `Brief`, carry `aim="metalens"`, and be
   compiled by the metalens aim module.
4. **Let aim selection choose the aim-owned intake family before canonical
   brief construction.** This is a harness/intake interaction, not a new
   Authority state or a new public lifecycle. The durable scientific language
   remains `brief -> study -> result`, with `aim` retained inside the completed
   brief as its discriminator and immutable user fact.

This preserves the current four cases without turning continuous achromatism
into a new top-level aim, a new lifecycle, or a hard-coded workflow.

## 1. What the repository already decided

### 1.1 Aim owns its Brief language

The shared [`Brief`](../../src/metacraft/science/brief.py) contains only common
facts: wording, aim, objectives, budget, and omissions. The concrete
[`MetalensBrief`](../../src/metacraft/science/metalens/brief.py) lives under the
metalens aim and adds wavelength, focal, polarization, atom, substrate,
fabrication, and optional explicit-choice facts. The generic
[`compile_study`](../../src/metacraft/science/compile.py) checks both the
declared aim and the aim-owned concrete type before delegating to
`compile_metalens`.

This is the implemented form of [ADR 0010](../adr/0010-let-each-aim-own-its-scientific-language.md):
one public `brief -> study -> result` lifecycle, while each real aim owns its
scientific language. `Aperture`, `FocalRegion`, and `Focus` are metalens
language, not universal workflow stages.

Therefore the correct interaction is conceptually:

```text
user selects aim: metalens
    -> metalens-owned intake asks which metalens objective/operating category
    -> it constructs one exact aim-owned Brief subtype
    -> generic compile_study delegates to metalens science
```

It should not become a generic Brief containing optional focus, spectrum,
resonance, absorption, BIC, and hologram fields. That would reverse ADR 0010.

### 1.2 Brief, planning, sweep, and evidence are already separate

The separation remembered by the user is explicit in the accepted design:

- [`SCIENCE.md`](../../SCIENCE.md) defines Brief as preserved user wording,
  conditions, constraints, preferences, and honest omissions; it defines
  Design as resolved intent that stops before route, proof, numerical method,
  solver, capacity, and task structure.
- [ADR 0002](../adr/0002-compile-studies-from-evidence.md) rejects a fixed
  workflow and makes the pure compiler compose a Study from the Brief,
  admitted evidence, methods, and qualified capabilities.
- [ADR 0004](../adr/0004-compile-proofs-from-claims-and-methods.md) keeps aim
  and objectives in the Brief, but puts route and proof in the Study. A method
  establishes one claim; it does not own an end-to-end process.
- [ADR 0024](../adr/0024-let-one-cell-study-own-bounded-response-work.md) places
  exact height, candidate geometry, response channels, work count, cautions,
  and provenance in one immutable `CellStudyPlan` after period choice. The
  downstream periodic request must project that plan verbatim rather than
  reconstructing a grid.
- [`PeriodicResponse`](../../src/metacraft/science/periodic_response.py) is the
  route-neutral observation seam. Its context exposes qualified response
  abilities and its `observe` method returns typed observed responses or a
  typed unavailability; it does not interpret the user's focal objective.

The existing four-case implementation is consequently evidence that these
are distinct domains, not merely convenient file divisions.

## 2. Fact ownership for continuous achromatism

### 2.1 User and aim intent: belongs in the new aim-owned Brief

The following are user-declared scientific intent or honest omissions:

| Fact | Why it belongs to the Brief |
| --- | --- |
| `aim = metalens` | Selects the aim-owned scientific language. |
| Objective: fixed-focus operation over a continuous wavelength interval | This is the requested outcome, not a numerical method. |
| Band lower and upper wavelength | Operating conditions that define the claim. |
| Focal length and numerical aperture, or an explicitly declared aperture fact | Physical requirements of the requested lens. |
| Incident polarization | Input operating condition. |
| Material family, substrate family, atom-family and fabrication constraints, when explicitly supplied | User constraints; omitted choices remain omissions. |
| Acceptance criteria explicitly owned by the user | For example allowed focal shift, efficiency floor, or spot-width variation; a Method must not invent these. |
| Budget and preferences | Bound compilation and later planning without selecting solver work inside the Brief. |
| Explicitly required or forbidden physical mechanism, if the user states one | A constraint on applicable Methods, not a solver or route selection. |

The original Wang--Tsai 2017 paper defines the requested optical outcome as
one fixed focal length over a continuous interval. Its ideal phase is
`-2*pi*(sqrt(R^2+f^2)-f)/lambda`, so band, focal length, and aperture coordinate
define the target family. The article demonstrates the principle over
1200--1680 nm, but those paper values are not MetaCraft user facts unless the
user explicitly chooses them ([Wang et al. 2017, phase requirement and Eqs.
1--4](https://www.nature.com/articles/s41467-017-00166-7#Sec3)).

### 2.2 Resolved design and bounded planning: does not belong in the Brief

The compiler and metalens planning Modules should derive or resolve:

| Planned fact | Owner |
| --- | --- |
| Applicable achromatic claim--method proof | Compiled Study route/proof. |
| Material coverage and admissible response mechanism | Resolved Design plus qualified capability/evidence. |
| Reference wavelength and any aperture-wide spectral phase offset | Achromatic target/assignment Method. |
| Design wavelengths, holdout wavelengths, and convergence refinements | Spectral cell-study plan and validation plan. |
| Period and height domains and their selected choices | Existing evidence-governed period/height planning pattern. |
| Candidate `(length, width)` geometries, orientation rules, response bases/channels, and exact work count | A new bounded spectral `CellStudyPlan` variant. |
| Phase unwrapping, continuity rule, interpolation model, objective weighting, and deterministic tie-breaks | Versioned Method contract. |
| Site-wise selection of one geometry and orientation shared by every wavelength | Achromatic aperture-assignment Method output. |
| Per-wavelength propagation coordinates and batching/chunking | Bound field-formation/propagation task construction. |

Wang et al. separate the lens phase into a wavelength-independent basic phase
and a wavelength-dependent compensation term linear in `1/lambda`; they also
allow a wavelength-dependent global phase shift that does not change focusing.
Those decompositions and the chosen compensation range are design freedoms,
not part of the user's fixed-focus statement ([Wang et al. 2017, Eqs. 2--4
and accompanying text](https://www.nature.com/articles/s41467-017-00166-7#Sec3)).

The 2018 transmissive realization then chooses a specific GaN IRUE library,
height, lattice, and geometry/orientation assignment to implement that
principle. These are one implementation's design decisions, not mandatory
fields of a general continuous-band metalens Brief ([Wang et al. 2018,
publisher record and Supplementary Information](https://www.nature.com/articles/s41565-017-0052-4)).

### 2.3 Periodic-response evidence: never a Brief or a plan

Execution must observe and Authority must retain, per candidate and
wavelength:

- the complete requested complex response channels, preferably the full
  linear-basis Jones response when PB conversion is part of the selected
  Method;
- useful, converted, retained, and leakage power under explicitly defined
  channel conventions;
- exact wavelength, material binding, cell geometry, period, height, input
  basis, phase-reference planes, and coordinate conventions;
- native/recorded execution origin, solver status, numerical closure,
  warnings, and exact provenance;
- raw complex values before phase unwrapping or spectral fitting;
- separately identified design and holdout observations.

The plan requests these facts; it cannot contain their values. A fitted phase
slope, continuity qualification, or interpolated response is derived evidence
that cites the raw observations; it is not retroactively a planning fact.

This matches the paper's physical requirement. Continuous achromatism depends
on the same unit element exhibiting a smooth phase response over the band,
not on stitching independently selected monochromatic structures. Wang et al.
explicitly reject merely broadband-unchanged elements as insufficient and
design integrated-resonant responses with smooth behavior against
`1/lambda` ([Wang et al. 2017, integrated-resonant unit elements](https://www.nature.com/articles/s41467-017-00166-7#Sec4)).

## 3. Type alternatives

### A. Mutate the existing `MetalensBrief`

**Reject for the next slice.** Replacing `wavelength_nm` with a tagged spectral
intent could eventually produce one elegant metalens intake type, but it
changes the canonical document of every existing case. Current `conduct`
resumes an application root only for byte-identical brief content, so this is
a schema migration rather than a local feature. It also risks placing spectral
planning details in the user contract.

### B. Subclass `MetalensBrief`

**Reject.** The base already semantically requires one scalar wavelength and
validates a current propagation/PB strategy. A continuous-band subclass would
either carry contradictory fields or weaken inherited invariants. This is
inheritance for transport reuse rather than domain truth.

### C. Replace `MetalensBrief`

**Reject.** Replacement would retire four working brief identities and create
no scientific benefit. The current type remains truthful for the established
single-wavelength proof family.

### D. Leave it untouched and add a sibling metalens Brief

**Recommend.** A `ContinuousBandMetalensBrief(Brief)` can carry only continuous-
band user facts and remain owned by `science.metalens/`. Generic dispatch still
checks `aim == "metalens"`; the metalens compiler then resolves the correct
objective relationship from the concrete aim-owned Brief. Shared value types
such as polarization, material intent, atom intent, aperture intent, and
fabrication constraints may be reused without subclassing the monochromatic
Brief.

The sibling is justified by the deletion test: deleting it would force
mutually exclusive scalar-wavelength and continuous-band invariants into one
shallow optional-field document. By contrast, deleting a speculative generic
`SpectralAimBrief`, `WorkflowKind`, or public route selector would concentrate
no complexity; those abstractions should not be added.

## 4. Recommended compilation shape

```text
Aim selection (harness interaction)
    metalens
      |-- existing MetalensBrief
      |     scalar wavelength + current focus intent
      |     -> existing four monochromatic proofs unchanged
      |
      `-- ContinuousBandMetalensBrief
            band + fixed-focus intent + user constraints/criteria
            -> resolve ContinuousBandMetalensDesign
            -> compile one applicable achromatic proof
            -> resolve period/height and bounded spectral CellStudyPlan
            -> observe atomic broadband PeriodicResponse evidence
            -> assign one physical aperture across the band
            -> form/propagate one exact Field per wavelength
            -> conclude one continuous-band focus Result
```

This is still scientific-process compilation. The compiler selects and records
the claim--method proof from user facts, admitted evidence, and qualified
capabilities. It does not ask the user to preassemble a workflow, and it does
not move the compiler's selected sampling/sweep work into the Brief.

## 5. Consequences for the Wayfinder map

The next architecture map should not start with "change `MetalensBrief`". Its
first decision should instead be:

> Define the closed user-fact contract of a sibling continuous-band metalens
> Brief, while freezing the existing monochromatic Brief and preserving aim-
> owned dispatch.

Only after that decision can the map sharpen the downstream questions:

1. the continuous-band metalens Design and terminal claim;
2. the achromatic claim--method proof and applicability/refusal rules;
3. a bounded spectral cell-study plan that preserves ADR 0024;
4. broadband periodic-response evidence and qualification;
5. one physical aperture with exact single-wavelength Fields;
6. continuous-band result and holdout semantics.

Future hologram, quasi-BIC, frequency-selective, absorber, CST, and COMSOL work
is outside this decision. None is needed to justify or shape this aim-owned
metalens extension.

## Primary sources

- MetaCraft [`CONTEXT.md`](../../CONTEXT.md), [`SCIENCE.md`](../../SCIENCE.md),
  [ADR 0002](../adr/0002-compile-studies-from-evidence.md),
  [ADR 0004](../adr/0004-compile-proofs-from-claims-and-methods.md),
  [ADR 0010](../adr/0010-let-each-aim-own-its-scientific-language.md), and
  [ADR 0024](../adr/0024-let-one-cell-study-own-bounded-response-work.md).
- MetaCraft source:
  [`Brief`](../../src/metacraft/science/brief.py),
  [`compile_study`](../../src/metacraft/science/compile.py),
  [`MetalensBrief`](../../src/metacraft/science/metalens/brief.py),
  [`MetalensDesign`](../../src/metacraft/science/metalens/design.py),
  [`compile_metalens`](../../src/metacraft/science/metalens/compiler.py),
  [`resolve_metalens_relationship`](../../src/metacraft/science/metalens/relationship.py),
  [`CellStudyPlan`](../../src/metacraft/science/metalens/cell_study.py), and
  [`PeriodicResponse`](../../src/metacraft/science/periodic_response.py).
- S. Wang et al., "Broadband achromatic optical metasurface devices,"
  *Nature Communications* 8, 187 (2017),
  [DOI 10.1038/s41467-017-00166-7](https://doi.org/10.1038/s41467-017-00166-7).
- S. Wang et al., "A broadband achromatic metalens in the visible,"
  *Nature Nanotechnology* 13, 227--232 (2018),
  [DOI 10.1038/s41565-017-0052-4](https://doi.org/10.1038/s41565-017-0052-4).

