---
record_type: research_record
date: 2026-08-09
status: research_finding
authority_level: none
current_capability: false
---

# Conservative metalens cell-study recommendation: finite guidance before solver evidence

## Question and boundary

This record asks how MetaCraft can reduce a designer's starting uncertainty without
pretending that a pre-solver rule has selected the optically correct metalens cell. It
is limited to monochromatic transmissive metalenses using either propagation phase or
local Pancharatnam--Berry (PB) geometric phase. Resonant/nonlocal, achromatic and inverse
design routes are outside this record.

The broader hard-gate/forecast/evidence distinction and phase-control physics are already
established in the
[phase-control brief judgment framework](2026-08-08-phase-control-brief-judgment-framework.md),
and the empirical PB height range is audited in the
[PB height primary-source study](2026-08-09-pb-metalens-height-primary-source-study.md).
This record does not repeat those surveys. Its additive question is narrower: what does a
**conservative recommendation** mean, how can its first lateral study be finite and
auditable, and which decisions belong to deterministic code rather than an agent harness?

This is research, not an ADR or an implementation claim. Existing decisions remain in
force, especially period-before-height ([ADR 0011](../adr/0011-let-period-choice-precede-height.md)),
sampling-versus-proof ownership ([ADR 0022](../adr/0022-let-sampling-bound-the-period-and-order-bound-the-proof.md)),
provider-free harness consultation ([ADR 0021](../adr/0021-let-harnesses-answer-grounded-consultations.md))
and distinct periodic response capabilities ([ADR 0013](../adr/0013-let-each-periodic-response-prove-itself.md)).

## Conclusion first

MetaCraft should recommend a **starting cell study**, not a final cell. The smallest
reliable architecture has six beats:

```text
bind facts
  -> enforce legality
  -> estimate route-specific phase burden
  -> form an exact bounded coverage study
  -> let the harness choose one non-dominated option
  -> let periodic response qualify or expand the study
```

The recommendation is conservative when it:

1. never relaxes a user constraint or hard physical/fabrication bound;
2. keeps order regime as visible proof context rather than a hidden period veto;
3. compares coherent `period + height + lateral study` options instead of independently
   choosing scalar dimensions that may not work together;
4. uses propagation and PB forecasts only to rank options;
5. states every exact candidate and solver task before execution; and
6. returns `evidence_required` when the supplied facts cannot distinguish the surviving
   options honestly.

This does not promise the best or even a qualifying cell. It gives an ordinary designer a
legal, physically argued and computationally finite first experiment whose failure has a
defined next step.

## Why no scalar height or period rule can own the answer

Four original experimental designs already span incompatible normalized geometries:

| route | primary design | wavelength / period / height | `height / wavelength` | geometry role |
| --- | --- | --- | ---: | --- |
| propagation | Arbabi et al. 2015 | `1550 / 800 / 940 nm` | `0.606` | circular-post diameter changes complex transmission phase |
| propagation | McClung et al. 2024 | `550 / 430 / 650 nm` | `1.182` | SiN post width forms a measured propagation-phase library |
| local PB | Yang et al. 2018 | `1550 / 1500 / 340 nm` | `0.219` | one fixed `1350 x 480 nm` ellipse rotates |
| local PB | Khorasaninejad et al. 2016 | `532 / 325 / 600 nm` | `1.128` | one fixed `250 x 95 nm` TiO2 fin rotates |

Sources: [Arbabi et al., *Nature Communications* 6, 7069 (2015), author
manuscript](https://arxiv.org/pdf/1410.8261),
[McClung et al., *Advanced Optical Materials* 12, 2301865 (2024), author
manuscript](https://arxiv.org/pdf/2312.13851),
[Yang et al., *Nature Communications* 9, 4607 (2018)](https://www.nature.com/articles/s41467-018-07056-6),
and [Khorasaninejad et al., *Science* 352, 1190--1194
(2016)](https://capasso.seas.harvard.edu/resource/2016khorasaninejadetal3pdf).

These are not random samples from one universal distribution. Material index, cross-section,
substrate, etch or fill process, phase mechanism and response target changed together. The
architectural inference is therefore that no universal `height / wavelength`, largest-period,
or lowest-aspect scalar score can determine the recommendation. A weighted sum would merely
hide product policy inside unexplained coefficients. Hard filtering followed by a small
non-dominated trade-off frontier is more honest.

## Three epistemic layers

### 1. Hard eligibility: code may reject an option

Hard checks are exact and owned by code:

- an explicit user period or height takes precedence and must remain exact;
- the period must stay strictly below the sampling ceiling owned by ADR 0022;
- dimensions must be positive, grid-aligned and contained by the chosen lattice;
- process-declared minimum feature, minimum edge gap, height/feature limit and, for a
  rotatable anisotropic cell, orientation-envelope clearance must hold;
- the chosen study must fit its declared solver-task extent.

The last item is an operational planning bound, not a claim that the optical aim is
physically impossible. Violating sampling or an explicit fabrication contract can close a
geometry as illegal; exceeding the execution extent must instead return a resource/planning
finding and let the user enlarge or stage the study.

Feature and gap constraints must remain distinct process facts. Khorasaninejad's TiO2 fins
were formed through an electron-beam resist mould and conformal ALD, whose article states that
the deposition must be at least half the fin width to fill without voids. That is not the same
constraint as top-down silicon dry etching. A generic `aspect_limit` cannot silently claim to
model both processes.

The order ceiling is not in this list. Official Ansys FDTD documentation distinguishes total
transmission from transmission into individual grating orders and provides order-resolved
projection for periodic structures
([periodic-structure methodology](https://optics.ansys.com/hc/en-us/articles/360041688154-Plasmonics-simulation-methodology)).
This supports ADR 0022's separation: a sampling-legal multi-order choice is a proof warning and
response obligation, not intrinsically an illegal geometry.

### 2. Soft forecast: code computes, harness interprets

For a waveguide-like propagation estimate, Ansys defines
`beta = k0 * effective_index`, and its metalens example explicitly relates larger post radius
to a larger effective index and optical path
([MODE effective-index definition](https://optics.ansys.com/hc/en-us/articles/360034396734-FDE-solver-analysis-Mode-List-and-Deck),
[metalens unit-cell example](https://optics.ansys.com/hc/en-us/articles/360042097313-Small-Scale-Metalens-Field-Propagation)).
The first-order phase-span burden is therefore

```text
required_effective_index_span ~= wavelength / height
```

for a full `2 pi` propagation-phase library. Code may compare this requirement with a rigorously
bounded or explicitly modelled effective-index span. A bulk-index contrast is at most an
optimistic envelope; it is not a periodic-cell observation.

For local PB, two orthogonal eigenchannels accumulating a phase difference over height give

```text
retardance ~= (2 pi / wavelength)
             * height
             * effective_birefringence

first-odd-half-wave burden:
required_effective_birefringence ~= wavelength / (2 * height)
```

The propagation-length relation follows directly from the official Ansys polarization-rotator
derivation
([Ansys polarization rotator](https://optics.ansys.com/hc/en-us/articles/360042799593-Polarization-rotator)).
Yang's original paper then supplies the actual PB channel condition: the same-handed term is
proportional to `t_o + t_e`, while the converted term is proportional to
`(t_o - t_e) exp(i 2 theta)`. Thus height can lower the required first-order modal
birefringence, but only the complex Jones response can establish conversion and leakage.

These two forecasts should have parallel structure but different names and formulas. Neither
may admit a cell, claim phase coverage or become solver evidence. Higher posts lower the
first-order index burden while worsening some fabrication margins and potentially changing
modal/resonant behaviour; that trade-off is exactly why a scalar height rule is inadequate.

### 3. Solver evidence: only response may qualify

The propagation route needs complex periodic transmission over the selected one-dimensional
geometry set and must demonstrate usable transmission plus phase coverage. The local PB route
needs both independent linear input bases for every selected anisotropic geometry, from which
conversion, leakage and retardance can be formed. Yang's equations show why one basis or an
ideal `2 theta` label cannot establish the Jones transformation.

Ansys's metalens workflow likewise chooses height from calculated phase and transmission maps,
not from effective path alone. It also warns that interpolation from a coarse radius database is
appropriate only while response is sufficiently smooth; resonant nonsmooth response requires
denser or direct sampling
([large-scale metalens workflow](https://optics.ansys.com/hc/en-us/articles/18254409091987-Large-Scale-Metalens-Ray-Propagation)).

## A bounded initial lateral study

### Why the current full grid is not a conservative start

Current code forms the complete lateral feature grid and then constructs every anisotropic pair
with `long_dimension > short_dimension`
([`periodic_request.py`](../../src/metacraft/science/metalens/periodic_request.py)).
For the current Yang-like `period=1500 nm`, `height=800 nm`, aspect limit `8` and `10 nm`
dimension step, the arithmetic range is `100--1400 nm`: 131 axis values, 8,515 unordered
anisotropic geometries and 17,030 two-basis solver tasks. The request contains no optical
evidence yet, so this exhaustive Cartesian expansion is neither a conservative recommendation
nor a workstation-aware first experiment.

### Recommended coverage rule

For each admitted period and candidate height, code should first enumerate the **legal discrete
lateral domain**. It then derives the number of geometries from one typed execution extent:

```text
available_geometry_count
  = floor(maximum_periodic_solver_tasks / response_tasks_per_geometry)

response_tasks_per_geometry
  = 1  for current normal-incidence propagation transmission
  = 2  for current local-PB x/y Jones response
```

Any declared wavelength or angle multiplicity also belongs in the exact multiplier. The plan
must expose both the selected geometry identities and final task count; downstream request code
may only project that plan and must not recreate a Cartesian product.

The initial selection should be deterministic space-filling coverage of the legal domain:

- for propagation's one-dimensional feature interval, retain legal range anchors and distribute
  the remaining points across the uncovered intervals;
- for PB's constrained two-dimensional `(short, long)` domain, normalize the two axes and add
  the legal point with the greatest distance from the already selected set until the extent is
  filled;
- preserve the grid values exactly, resolve distance ties canonically, and content-address the
  resulting ordered set;
- do not scan orientation as a third design dimension: orientation produces the later PB phase
  states, while the starting cell study establishes the unrotated two-basis Jones response.

If the execution extent cannot carry the route's required range anchors and response bases, code
must return a resource/planning finding rather than silently dropping an anchor or inventing a
smaller scientific minimum.

Maximin-distance designs were introduced specifically as site-selection designs over an arbitrary
set with a defined distance
([Johnson, Moore and Ylvisaker, *Journal of Statistical Planning and Inference* 26,
131--148 (1990)](https://doi.org/10.1016/0378-3758(90)90122-B)). Here the criterion has a
limited meaning: it covers a finite legal geometry space without assuming a response model. It
does **not** optimize transmission, phase, conversion or fabrication yield.

Latin-hypercube sampling is a defensible alternative for a hyperrectangle, but SciPy's first-party
documentation defines it through stratified marginals in `[0,1)^d` and notes that
`scramble=False` alone does not make it deterministic
([SciPy `LatinHypercube`](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.qmc.LatinHypercube.html)).
The current PB domain is a constrained, discrete triangle with grid deduplication. A direct
canonical maximin selection on the actual legal points is therefore the simpler product rule;
it avoids a random seed, constraint projection and duplicate-repair policy.

### Sequential expansion, not hidden optimization

An initial coverage study can miss a narrow resonance or a small high-conversion island. Its
honest outcomes are therefore:

```text
qualified response found
  -> form the appropriate evidence-backed cell/library

response suggests an unresolved interval or region
  -> issue one new bounded expansion study

no useful response and no justified expansion
  -> evidence_required / user decision
```

The NIST engineering-statistics handbook explicitly recommends a sequence of small experiments
over expecting one large experiment to answer every question
([NIST/SEMATECH DOE steps](https://www.itl.nist.gov/div898/handbook/pri/section1/pri14.htm)).
This supports immutable staged studies, not a mutable optimizer. Every expansion must cite the
previous response and add exact new points; it cannot silently change the original plan.

No primary physical source supplies a universal `16`, `32`, `64` or other solver-task ceiling.
The affordable count depends on solver method, mesh, material dispersion, wavelength/angle
multiplicity, hardware and license capacity. `workstation` as free text is therefore insufficient
for automatic planning. A numeric `maximum_periodic_solver_tasks` must be supplied by a user or
by a separately benchmarked execution profile. It is operational policy, not a metalens law,
and the harness must not invent it.

## Non-dominated options instead of an unexplained score

After hard filtering, code can remove an option only when another legal option is no worse in
every declared comparison dimension and strictly better in at least one. Shared comparison
grounds include sampling margin, fabrication margin, order/proof context and exact task count.
The route-specific ground is required effective-index span for propagation or required effective
birefringence for PB.

The surviving frontier expresses genuine trade-offs. One option may offer more lateral room but
enter a multi-order proof regime; another may lower the phase burden by increasing height but
tighten feature/gap fabrication. An agent harness can use the user's declared priorities and
source-grounded platform precedent to choose one option without creating new dimensions.

The number of alternatives shown to the harness must also be bounded, but research does not
justify a universal numeric prompt cap. If a frontier is too large, deterministic representative
selection may use the same normalized coverage principle. The configured option limit and its
provenance must remain visible application policy rather than a physical constant.

## Harness contract

### Code owns

- exact brief and material binding;
- period sampling legality and order-regime classification;
- explicit-constraint precedence;
- fabrication and orientation-clearance arithmetic;
- route-specific dimensionless forecast grounds;
- non-dominance and deterministic representative coverage;
- exact lateral candidates, response bases and solver-task count;
- option identities, answer validation and later evidence admission.

### The harness owns

- interpreting the supplied trade-offs in the user's domain language;
- using permitted first-party literature to recognize a relevant platform precedent;
- choosing one existing option identity or returning `evidence_required`;
- explaining the choice and its unresolved cautions briefly.

It does not calculate candidate grids, alter explicit constraints, invent material data, create a
new option, choose a task budget, or call a forecast evidence.

A sufficient prompt can remain short because the scientific detail travels as structured grounds:

```text
Choose one option_id as a conservative starting cell study, or return
evidence_required. All hard constraints are already enforced: do not alter
dimensions, budgets, or create a new option. Compare fabrication margin,
sampling/order context, exact solver cost, and the route-specific phase forecast.
Forecasts rank options but never prove a cell. Return the option_id, a concise
rationale, and unresolved cautions.
```

Propagation and PB do not need separate prompt systems. Their options carry different typed
forecast and response obligations, while this one grammatical contract remains stable. That is
the useful architectural symmetry: one consultation rhythm, two physical verses, one evidence
closure.

## Architectural consequence

Preserve `PeriodDomain -> PeriodChoice` because period owns independent sampling legality.
After the admitted period, replace a scalar height recommendation followed by an implicit full
geometry expansion with a deep cell-planning module:

```text
PeriodChoice
  -> CellStudyDomain
       common legality
       + PropagationPhaseForecast | LocalPbRetardanceForecast
       + finite non-dominated study options
  -> CellStudyPlan
       exact height
       + exact lateral candidates
       + exact response obligation
       + exact work count
  -> PeriodicResponse
  -> Cell / PhaseSet / OrientationSet
```

`compact`, `waveguide-like` and similar families may describe an option in prose but should not
be schema enums: the auditable quantities are `period/wavelength`, `height/wavelength`, required
index burden, fabrication margin, order regime and work count. Likewise, do not add a generic
planner registry, provider Adapter or optimization framework. One metalens-specific module can
hide the enumeration, forecast, Pareto filtering and coverage machinery behind a small immutable
interface.

The resulting promise is deliberately modest and useful:

> MetaCraft does not pre-solve the correct cell. It compiles a legal, coherent and finite first
> study, explains why it is a conservative starting point, and makes the solver evidence or the
> need for expansion impossible to hide.

## Primary-source list

1. Arbabi et al., “Subwavelength-thick lenses with high numerical apertures and large efficiency based on high-contrast transmitarrays,” *Nature Communications* 6, 7069 (2015), [DOI](https://doi.org/10.1038/ncomms8069), [author manuscript](https://arxiv.org/pdf/1410.8261).
2. McClung et al., “Visible Metalenses with High Focusing Efficiency Fabricated Using Nanoimprint Lithography,” *Advanced Optical Materials* 12, 2301865 (2024), [DOI](https://doi.org/10.1002/adom.202301865), [author manuscript](https://arxiv.org/pdf/2312.13851).
3. Yang et al., “Generalized Hartmann--Shack array of dielectric metalens sub-arrays for polarimetric beam profiling,” *Nature Communications* 9, 4607 (2018), [article](https://www.nature.com/articles/s41467-018-07056-6), [author manuscript](https://arxiv.org/pdf/1807.06907).
4. Khorasaninejad et al., “Metalenses at visible wavelengths: Diffraction-limited focusing and subwavelength resolution imaging,” *Science* 352, 1190--1194 (2016), [DOI](https://doi.org/10.1126/science.aaf6644), [author-hosted article](https://capasso.seas.harvard.edu/resource/2016khorasaninejadetal3pdf).
5. Johnson, Moore and Ylvisaker, “Minimax and maximin distance designs,” *Journal of Statistical Planning and Inference* 26, 131--148 (1990), [DOI](https://doi.org/10.1016/0378-3758(90)90122-B).
6. NIST/SEMATECH, “What are the steps of DOE,” [official handbook](https://www.itl.nist.gov/div898/handbook/pri/section1/pri14.htm).
7. Ansys Optics, [Small-Scale Metalens -- Field Propagation](https://optics.ansys.com/hc/en-us/articles/360042097313-Small-Scale-Metalens-Field-Propagation), [Large-Scale Metalens -- Ray Propagation](https://optics.ansys.com/hc/en-us/articles/18254409091987-Large-Scale-Metalens-Ray-Propagation), [FDE effective-index definition](https://optics.ansys.com/hc/en-us/articles/360034396734-FDE-solver-analysis-Mode-List-and-Deck), [Polarization Rotator](https://optics.ansys.com/hc/en-us/articles/360042799593-Polarization-rotator), and [periodic-structure methodology](https://optics.ansys.com/hc/en-us/articles/360041688154-Plasmonics-simulation-methodology).
8. SciPy, [`scipy.stats.qmc.LatinHypercube` first-party documentation](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.qmc.LatinHypercube.html).
