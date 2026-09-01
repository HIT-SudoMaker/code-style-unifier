# Four-brief metalens qualification

Status: superseded by ../four-brief-grounding/map.md (decision handoff 2026-08-09)

This specification remains historical input. It must not be executed as the
current road because it retains Yun, the former Adviser vocabulary, the G0
hard period ceiling, and live cell/field work that the current four-brief
phase explicitly defers.

## Problem Statement

MetaCraft already has a stable brief-first lifecycle, a frozen Rust authority
core, low-na propagation and geometric science, one qualified Torch angular
spectrum realization, and replayable results. What it does not yet have is one
honest four-case standard that proves the architecture across both control
strategies and both numerical-aperture regimes.

The existing public examples are adapted low-na demonstrations. They do not
preserve the exact paper platforms needed for reproduction, geometric phase is
currently continuous where the agreed low-na comparison requires 8-, 12-, and
16-orientation results, and numerical aperture above 0.5 is refused before a
high-na method can establish its own applicability. The current componentwise
angular spectrum realization also cannot be renamed or presumed to be a
high-na vector method merely because it transports multiple components.

Response evidence and field propagation are separate scientific concerns. A
G0 complex coefficient may close the current zeroth-order method, but it cannot
claim a complete output field when other orders may propagate. Conversely, a
richer reference-surface field does not itself prove a high-na propagation
operator. Without keeping these axes distinct, the program either rejects
valid future methods, weakens ADR 0009, or hides missing physics behind one
large workflow.

The project therefore needs four canonical paper cases, paired low-na
assignments, pointwise high-na assignments, independently qualified field
methods, and a staged comparison path. It must preserve the existing
`brief -> study -> result` lifecycle, keep Rust unchanged, avoid a generic
workflow framework, and postpone expensive live solver work until every
smaller seam is trustworthy.

## Solution

Introduce one canonical four-case qualification matrix:

1. `yun_2025_low_na_propagation`
2. `yang_2018_low_na_geometric`
3. `arbabi_2015_high_na_propagation`
4. `khorasaninejad_2016_high_na_geometric`

Each case owns one blind brief, one immutable set of paper-locked facts, one
comparison contract, and one fidelity classification. The Adviser receives
only the blind brief. Paper facts never leak into its prompt and never become
authority merely because they were published. Adviser recommendations are
reported against the hidden paper facts; they do not overwrite the brief or
the reproduction contract.

The paper-locked path retains exact cited geometry only as fidelity and
comparison truth after blind advice returns. It does not feed that geometry to
the compiler. The program derives period and height from the blind brief and
admitted evidence; generated lateral geometry uses the brief's own dimension
step.

The low-na pair answers in matching measures:

- propagation phase forms separate 8-, 12-, and 16-state phase sets from one
  admitted cell library;
- geometric phase forms separate 8-, 12-, and 16-state orientation sets from
  one admitted anisotropic cell and one analytic orientation relation.

All six low-na outcomes are first-class results. Neither route chooses a hidden
winner. The two mechanisms share the requested counts but do not share a
generic quantizer: propagation discretizes cell identity, while geometric
phase discretizes physical orientation.

The high-na pair does not manufacture phase levels:

- propagation phase selects one admitted cell at each occupied site by cyclic
  phase distance, transmitted magnitude, and stable fabrication identity;
- geometric phase derives one analytic orientation at each occupied site from
  the admitted polarization convention.

High-na propagation uses normalized integer phase bins and vectorized Torch
identity lookup. It never uses exact floating-point dictionary keys or scans
the complete cell library once per site.

Method selection depends on the evidence and field contract, not on a stored
`low-na` or `high-na` route label. The current G0-only complete-field method
keeps the hard ADR 0009 zeroth-order boundary. A paper platform in the
multi-order regime can proceed only through a separately qualified
reference-surface response that retains the sampled complex field required for
aperture assembly. The resulting order regime and locally periodic limitation
remain visible through study, result, and replay.

The existing angular spectrum realization keeps its honest componentwise
meaning and is qualified against a direct scalar diffraction reference and
the low-na Airy limit. A separate vector angular spectrum method propagates an
actual sampled plane field while enforcing Maxwell transversality, recovering
the longitudinal electric component, and evaluating power through the
Poynting vector.

Richards--Wolf/Debye focusing is a separate physical method for an ideal
aplanatic pupil or reference sphere. Direct vector integration is its reference
realization. FFT and CZT are accelerated realizations of that same method,
accepted only after complex component parity with the direct reference. All
three realizations are implemented in Torch; the direct reference is not a
NumPy or SciPy escape hatch. They are not three workflow branches and not
three different physical claims.

All production numerical kernels use Torch with complex128 arithmetic.
Execution selects CUDA when available and Torch CPU only when CUDA is absent.
The selected device is part of the qualified binding; a failed CUDA
qualification never falls back silently. Angular-spectrum padding remains two
times, never four times. Large apertures and focal regions are evaluated by
bounded Torch chunks without retaining an unnecessary full complex
three-dimensional volume.

Validation proceeds in four deliberate movements:

1. brief reasoning and Adviser isolation;
2. independent field-method qualification;
3. aperture assignment, response evidence, and paper comparison with bounded
   deterministic fixtures;
4. real Lumerical sweeps and four-case delivery behind an explicit human gate.

The complete non-live matrix yields eight replayable results: three Yun
propagation results, three Yang geometric results, one Arbabi high-na
propagation result, and one Khorasaninejad high-na geometric result. Paper
efficiencies are comparison values, never hidden acceptance thresholds.

## User Stories

1. As a metasurface researcher, I want exactly four canonical metalens cases,
   so that the standard remains memorable and reviewable.
2. As a metasurface researcher, I want the cases to cover propagation and
   geometric phase at low and high numerical aperture, so that one matrix
   exposes both shared structure and real physical differences.
3. As a researcher, I want each case to retain one immutable blind brief, so
   that Adviser quality can be measured without leaking the paper answer.
4. As a researcher, I want each case to retain paper-locked facts separately,
   so that reproduction truth cannot be rewritten by advice.
5. As a researcher, I want each case to declare its fidelity classification,
   so that an adapted standard is never presented as an exact reproduction.
6. As a researcher, I want each case to declare its comparison contract, so
   that paper metrics are interpreted consistently.
7. As a researcher, I want a valid complete brief to compile into a reviewable
   study, so that I can inspect the proposed proof before scientific work.
8. As a researcher, I want an incomplete brief to name only its missing facts,
   so that no solver or field calculation starts prematurely.
9. As a researcher, I want Adviser output to remain untrusted advice, so that
   a fluent recommendation cannot silently become evidence.
10. As a researcher, I want Adviser recommendations compared with hidden paper
    values only after they are received, so that the evaluation remains blind.
11. As a researcher, I want a paper mismatch reported as a comparison outcome,
    so that a scientifically plausible alternative is not misclassified as a
    software fault.
12. As a researcher, I want exact cited geometry to remain exact, so that a
    general sweep grid does not deform a published device.
13. As a researcher, I want generated geometry to retain the brief's dimension
    step, so that fabrication resolution is never invented downstream.
14. As a researcher, I want Yun's conventional full-2π comparator isolated
    from its 4π/3 optimized design, so that two different devices are not
    spliced into one case.
15. As a researcher, I want Yun's 850 nm, NA 0.35, 0.5 mm diameter, 400 nm
    period, and 800 nm height retained, so that the low-na propagation case
    has a definite paper platform.
16. As a researcher, I want one Yun cell library reused for 8-, 12-, and
    16-state phase sets, so that quantization comparison adds no solver work.
17. As a researcher, I want cyclic phase distance to treat zero and one full
    turn as adjacent, so that phase-set matching remains correct at the seam.
18. As a researcher, I want all three Yun phase sets returned independently,
    so that no preferred quantization erases the alternatives.
19. As a researcher, I want Yang's 1550 nm, nominal NA 0.32, 30 µm focal
    length, and 22.5 µm square footprint retained, so that the low-na
    geometric case keeps its physical scale.
20. As a researcher, I want Yang's 1500 nm period, 340 nm height, and
    1350-by-480 nm elliptical silicon pillar retained, so that paper geometry
    is not reconstructed from an unrelated sweep.
21. As a researcher, I want the Yang case to select one circular-polarization
    sublens, so that it does not claim to reproduce the complete
    Hartmann--Shack array.
22. As a researcher, I want Yang's one admitted anisotropic cell to form 8-,
    12-, and 16-orientation sets, so that geometric and propagation comparison
    have equal fabrication measures.
23. As a researcher, I want geometric phase to respect the doubled
    phase-orientation relation and its handedness sign, so that orientation
    discretization preserves the declared polarization convention.
24. As a researcher, I want each Yang orientation set returned independently,
    so that discrete fabrication alternatives remain visible.
25. As a researcher, I want no orientation-by-orientation solver sweep, so
    that analytic rotation does not create fictitious work.
26. As a researcher, I want the high-na Arbabi case to preserve the 1550 nm
    amorphous-silicon HCTA platform, so that high-na propagation is grounded
    in an established design family.
27. As a researcher, I want the Arbabi standard to use the 800 nm hexagonal
    lattice, 940 nm post height, and 200--550 nm circular-post range, so that
    the pointwise selector operates on a definite library.
28. As a researcher, I want the compact Arbabi standard to use a 100 µm
    aperture, 25 µm focal distance, and derived NA of about 0.89, so that the
    selected high-na case is bounded but still physically demanding.
29. As a researcher, I want the Arbabi standard marked HCTA-derived rather
    than exact, so that plane-wave incidence is not confused with the paper's
    single-mode-fiber illumination.
30. As a researcher, I want high-na propagation to choose a cell at every
    occupied site without finite phase levels, so that spatial assignment is
    not confused with low-na phase quantization.
31. As a researcher, I want high-na selection to use stable cyclic integer
    bins and vectorized lookup, so that a large aperture does not become a
    Python-loop bottleneck.
32. As a researcher, I want transmitted magnitude to break equal phase losses,
    so that pointwise selection retains useful energy.
33. As a researcher, I want fabrication identity to break any remaining tie,
    so that selection is deterministic across input order and replay.
34. As a researcher, I want Khorasaninejad's 532 nm, NA 0.8, 240 µm diameter,
    and 90 µm focal length retained, so that high-na geometric phase has a
    clear benchmark.
35. As a researcher, I want its 325 nm period and 95-by-250-by-600 nm
    titanium-dioxide nanofin retained, so that the benchmark is not reduced to
    a generic rectangle.
36. As a researcher, I want one admitted high-na geometric cell rotated
    continuously at each site, so that no unnecessary finite phase set is
    imposed.
37. As a researcher, I want the current G0-only proof to retain its hard order
    ceiling, so that complete-field claims never omit propagating orders.
38. As a researcher, I want a multi-order case to request richer response
    evidence rather than weaken the ceiling, so that method applicability and
    evidence strength advance together.
39. As a researcher, I want a reference-surface response to retain sampled
    complex field, surface, basis, medium, and source identity, so that it can
    establish an actual aperture field.
40. As a researcher, I want the order regime and locally periodic limitation
    carried into the result, so that a complete computation does not hide a
    modeling caution.
41. As a researcher, I want a bounded small-aperture full-wave comparison, so
    that local response assembly has an explicit diagnostic against a stronger
    model.
42. As a researcher, I want the current angular spectrum method qualified
    against a direct scalar reference, so that its existing claim is proven
    without renaming it vector.
43. As a researcher, I want the low-na field checked against the Airy limit,
    so that sampling, sign, scaling, and focus location are independently
    visible.
44. As a researcher, I want vector angular spectrum to recover longitudinal
    field and satisfy transversality, so that high-na propagation respects
    Maxwell structure.
45. As a researcher, I want vector angular spectrum checked with an oblique
    plane wave and a direct vector reference, so that component coupling is
    qualified before a paper case uses it.
46. As a researcher, I want focal power evaluated through the Poynting vector,
    so that high-na efficiency is not inferred from one electric component.
47. As a researcher, I want direct Richards--Wolf/Debye integration to define
    one ideal-focus reference, so that accelerated realizations have a clear
    scientific truth.
48. As a researcher, I want FFT and CZT Debye realizations compared through
    complex Ex, Ey, and Ez fields, so that intensity agreement cannot hide
    phase or polarization errors.
49. As a researcher, I want FFT and CZT treated as realizations of one Debye
    method, so that the compiler does not confuse acceleration with physics.
50. As a researcher, I want actual sampled aperture fields propagated by
    vector angular spectrum and ideal aplanatic pupils evaluated by Debye, so
    that each operator receives the surface it understands.
51. As a workstation owner, I want every production field kernel implemented
    in Torch, so that CPU and CUDA share one numerical contract.
52. As a workstation owner, I want CUDA selected when available and CPU
    selected only when CUDA is absent, so that acceleration policy is
    deterministic.
53. As a workstation owner, I want a failed selected-device qualification to
    remain failed, so that execution never falls back silently.
54. As a workstation owner, I want complex128 and two-times angular-spectrum
    padding retained, so that precision and memory costs remain explicit.
55. As a workstation owner, I want aperture and focal calculations chunked
    under observed device capacity, so that million-site cases remain bounded.
56. As a researcher, I want focus searched over 0.8f through 1.2f, so that a
    shifted realized focus is not mistaken for absence.
57. As a researcher, I want separate x/y half-maximum widths, depth of focus,
    transmission, concentration, and complex-field error, so that spot shape
    and energy allocation are both visible.
58. As a researcher, I want paper efficiencies used as comparisons rather
    than pass thresholds, so that an adapted reproduction can return an honest
    result even when it performs differently.
59. As a researcher, I want the complete non-live matrix to return exactly
    eight results, so that low-na alternatives and high-na pointwise outcomes
    are counted without ambiguity.
60. As a researcher, I want each result to retain the case, response method,
    field method, assignment, evidence, and comparison identities, so that its
    meaning survives replay.
61. As a researcher, I want replay to restore all admitted results without
    Adviser, solver, or field execution, so that reproducibility is a property
    of evidence rather than a repeated experiment.
62. As a maintainer, I want `conduct` to remain the sole application operation,
    so that no paper case grows its own workflow.
63. As a maintainer, I want the compiler to remain pure, so that method choice
    never mutates authority or observes a workstation.
64. As a maintainer, I want response methods independent of field methods, so
    that richer cell evidence does not force one focus algorithm.
65. As a maintainer, I want paper cases to depend on public science contracts,
    so that examples never import local execution machinery.
66. As a maintainer, I want dependencies to flow from application to science
    contracts to realizations, never back into case definitions, so that
    runtime imports remain acyclic.
67. As a maintainer, I want public identifiers to use natural domain language,
    so that mathematical shorthand remains local to equations and kernels.
68. As a maintainer, I want expected absence to use existing typed findings
    and Adapter outcomes, so that this feature creates no broad exception
    hierarchy.
69. As a maintainer, I want malformed evidence and invariant violations to
    fail directly, so that defects are not disguised as scientific waiting.
70. As a maintainer, I want Rust authority and protocol bytes unchanged, so
    that this scientific extension cannot reopen the stable lifecycle core.
71. As a maintainer, I want focused tests at each scientific seam before the
    matrix test, so that failures remain local and cheap to diagnose.
72. As a maintainer, I want real Lumerical execution behind a human gate, so
    that licence time and solver artifacts are never consumed implicitly.
73. As a workstation owner, I want direct Debye, FFT-Debye, and CZT-Debye
    implemented entirely in Torch, so that qualification and production share
    one CPU/CUDA numerical contract without a NumPy or SciPy substitute.

## Implementation Decisions

- Rust is frozen for this effort. No authority state, protocol, event,
  manifest, binding machinery, or public Rust interface changes are allowed.
- `conduct` remains the only end-to-end application operation. It compiles,
  gathers ready evidence, proposes admission, recompiles, and returns an honest
  waiting study or independent results.
- The compiler remains pure. It selects claim methods from the resolved
  design, available evidence, qualifications, and bindings; it performs no
  filesystem, network, solver, Adviser, Torch, or authority work.
- The four canonical cases live at the examples boundary and depend only on
  public scientific values. A case contains a blind brief, paper facts,
  comparison contract, and fidelity. It is not a workflow or executor.
- Paper facts are immutable post-advice fidelity and comparison inputs, not
  authority, evidence, or compiler inputs. Exact reproduction inputs become
  scientific facts only through the existing document and admission path.
- The Adviser receives only the blind brief. Advice evaluation occurs after
  the response and cannot affect the original paper contract.
- Paper geometry is hidden fidelity and comparison truth revealed only after
  blind advice returns. It is never a compiled constraint. The program derives
  period and height from the blind brief and admitted evidence; generated
  lateral geometry uses only the fabrication step declared by that brief.
- The canonical Yun case is a quantized adapted reproduction of the
  conventional full-2π comparator: 850 nm wavelength, NA 0.35, 0.5 mm
  diameter, about 669.1 µm focal length, 400 nm period, 800 nm
  hydrogenated-amorphous-silicon circular posts, and fused silica substrate.
  The 4π/3 optimized device and its 500 nm height are excluded.
- The canonical Yang case is a quantized adapted reproduction of one
  circular-polarization sublens: 1550 nm wavelength, nominal NA 0.32, 30 µm
  focal length, 22.5 µm square footprint, 1500 nm period, 340 nm silicon
  elliptical pillars with 1350 nm major and 480 nm minor axes, and a silicon
  dioxide underlayer. It does not claim the complete six-sublens sensor.
- The canonical Arbabi case is an HCTA-derived high-na propagation standard:
  1550 nm wavelength, 100 µm circular aperture, 25 µm focal distance, derived
  NA of about 0.89, x-linear plane-wave incidence, 800 nm hexagonal period,
  940 nm
  hydrogenated-amorphous-silicon circular posts spanning 200--550 nm, and
  fused silica substrate. It is adapted because the paper's exact optimum
  phase uses single-mode-fiber illumination that the current brief does not
  express.
- The canonical Khorasaninejad case is the 532 nm high-na geometric device:
  NA 0.8, 240 µm circular aperture, 90 µm focal length, right-circular
  incidence, 325 nm spacing, and a 95-by-250-by-600 nm amorphous-titanium-
  dioxide rectangular nanofin on glass.
- Low-na propagation forms independent 8-, 12-, and 16-state `phase set`
  values from one library. State matching is cyclic and deterministic.
- Low-na geometric phase introduces an `orientation set` value paired with
  `phase set` in scale but not implementation. It contains one cell and 8,
  12, or 16 ordered physical orientations derived from one admitted continuous
  orientation relation.
- The low-na geometric aperture uses the selected orientation set directly.
  It does not solve orientations, invent a second cell library, or collapse the
  three sets into one preferred result.
- High-na propagation forms one pointwise aperture from the complete admitted
  cell library. It uses cyclic integer phase bins, vectorized Torch lookup,
  transmitted-magnitude tie-breaking, and stable fabrication-identity
  tie-breaking.
- High-na geometric phase forms one pointwise aperture from one admitted cell
  and its continuous orientation relation. It has no `phase set`,
  `orientation set`, quantization count, or optimizer.
- Aperture owns lattice coordinates, footprint mask, target phase, and state
  placement. It supports the existing circular footprint and the square
  footprint required by Yang without creating a generic surface hierarchy.
- A state may retain a constant complex response or a sampled
  reference-surface patch. Aperture field formation consumes the response
  form established by the selected method rather than pretending every state
  is one complex number.
- Response evidence and field propagation are orthogonal method axes.
  Numerical aperture may participate in applicability, but it does not name a
  fixed route or stored regime enum.
- ADR 0009 remains unchanged. The current G0-only complete-field method
  requires a period below the compiled period limit. It does not demote an
  order violation to a caution.
- A new route-neutral periodic reference-surface response may support
  multi-order cases. Its evidence retains the sampled complex field, surface,
  coordinate frame, medium, component basis, requested input basis, and exact
  source references. Its qualification does not imply a metalens strategy.
- Existing periodic transmission and periodic polarization capabilities
  remain independently qualified according to ADR 0013. The richer response
  is additive and receives its own fixture; no compatibility alias or shared
  “full-wave” capability is introduced.
- Locally periodic patch assembly retains an explicit caution and a bounded
  small-aperture full-wave comparison. The comparison reports complex-field
  and power differences; it is not disguised as whole-device FDTD.
- The current angular spectrum realization remains the componentwise method.
  Its public name does not gain a `scalar` prefix, and it does not claim
  Maxwell-vector qualification.
- Vector angular spectrum is a separate scientific method and qualified
  realization for an actual sampled plane field. It reconstructs the
  longitudinal component from transversality and propagates the declared
  component basis consistently.
- Direct Richards--Wolf/Debye integration establishes ideal aplanatic focal
  fields from a pupil or reference sphere. Its quadrature, component
  construction, batching, and reductions are implemented in Torch on the
  selected device. It does not consume an arbitrary sampled exit plane by
  pretending the surfaces are interchangeable.
- FFT and CZT are Torch realizations of the Debye method. Their transforms,
  chirps, coordinate construction, batching, and reductions remain on the
  selected Torch device. Their bindings retain sampling, window, coordinate
  convention, device, dtype, and source method.
- NumPy and SciPy are forbidden in the production Debye realizations. Small
  independent test oracles may use closed-form values or separately derived
  fixtures, but they may not become the implementation being qualified.
- All production field mathematics uses Torch and complex128. CUDA is selected
  when present; CPU is selected only when CUDA is absent. The same selected
  realization must qualify and execute.
- Angular-spectrum propagation retains two-times padding. Four-times padding
  is forbidden unless a future, separate qualification proves and requests
  it.
- Large apertures use Torch chunks for placement, spectrum preparation,
  propagation, and focal sampling. Capacity changes chunk size, never
  scientific meaning or result identity.
- Focal evaluation spans 0.8f through 1.2f and stores bounded focal-region
  evidence rather than a full complex volume. It reports found focus, x/y
  half-maximum widths, depth of focus, transmission, concentration, and
  method-appropriate field or power comparisons.
- Paper focusing efficiencies, spot sizes, and other metrics are labeled
  source comparisons. They do not become universal thresholds or suppress a
  complete but scientifically different result.
- Result identity includes the canonical case, paper-contract revision,
  response method, field method, assignment, and exact admitted evidence.
  Reordering input candidates or restarting a workspace cannot change it.
- The six low-na results and two high-na results are independent branches.
  One refusal or waiting branch cannot discard completed siblings.
- Replay restores admitted advice, paper comparison, response evidence,
  assignment, field evidence, and results without repeating any external or
  numerical work.
- Missing brief facts, unavailable methods, missing qualifications, and
  unavailable capacity use existing typed refusals, findings, and Adapter
  outcomes. This effort adds no common solver error base class.
- Malformed documents, mismatched references, non-finite fields, impossible
  component bases, and violated invariants raise directly. They are defects,
  not expected waiting states.
- Public names use canonical domain language. Mathematical shorthand is
  limited to equations and tightly local numerical kernels. No new `manager`,
  `helper`, `utils`, numbered workflow, route registry, generic science
  framework, or compatibility layer is introduced.
- Dependencies remain one-way: examples describe cases; science compiles and
  evaluates claims; realizations gather observations; the application binds
  them; authority admits immutable facts. Runtime imports must remain acyclic.

## Testing Decisions

- Tests assert observable scientific contracts and canonical documents, not
  private helper calls, loop structure, or incidental module layout.
- The highest application seam is `conduct`. It verifies incomplete-brief
  wording, blind advice isolation, immutable study compilation, sibling
  results, exact admission, and replay.
- Field methods require their own qualification seam because an end-to-end
  result cannot diagnose Fourier sign, normalization, transversality,
  longitudinal components, or Debye quadrature.
- Existing brief, standard-study, phase-set, aperture, angular-spectrum,
  focus, delivery-matrix, and replay tests are the prior art. New tests deepen
  those seams instead of introducing a parallel test harness.
- Case tests prove that exactly four canonical cases exist and that each
  contains one blind brief, exact paper facts, fidelity, and comparison
  contract.
- Blind-advice tests prove that paper period, height, and lateral dimensions
  are absent from the Adviser input and appear only in the later comparison.
- Low-na propagation tests reuse one deterministic library to form 8-, 12-,
  and 16-state phase sets across the zero/full-turn seam.
- Low-na geometric tests reuse one admitted cell and one orientation relation
  to form 8-, 12-, and 16-orientation sets with the correct handedness sign
  and no additional solver identities.
- Aperture tests prove circular and square footprint coordinates, masks,
  target phase, stable state placement, and document replay.
- High-na propagation tests compare vectorized pointwise selection with a
  small direct reference, including cyclic seam, power tie, identity tie,
  candidate-order independence, and absence of per-site library scanning.
- High-na geometric tests prove continuous pointwise orientation, one cell,
  no finite level map, and exact polarization convention.
- G0 tests retain the strict ADR 0009 boundary. Multi-order tests prove that
  only the qualified reference-surface method can proceed and that the order
  regime remains visible.
- Reference-surface response tests verify finite complex samples, exact
  surface and medium, component basis, source identity, orientation, and
  canonical round trip.
- Small-aperture assembly tests compare the locally periodic field with a
  bounded full-wave fixture and report differences without asserting paper
  success.
- Componentwise angular-spectrum qualification compares complex propagated
  fields with direct scalar Rayleigh--Sommerfeld evaluation and checks the
  Airy low-na limit.
- Vector angular-spectrum qualification uses oblique Maxwell plane waves,
  verifies transversality and longitudinal recovery, and compares complex
  components and Poynting power with a direct vector reference.
- Direct Debye tests use Richards--Wolf symmetry, on-axis component, parity,
  and coordinate-convention fixtures. They prove that the direct reference
  remains Torch-native on both supported device classes.
- FFT and CZT Debye tests compare complex Ex, Ey, and Ez against the direct
  Debye reference over matched coordinates before any timing claim. An
  architecture ratchet rejects NumPy or SciPy imports from all production
  Debye realizations.
- Device tests prove CUDA preference, CPU-only absence fallback, no silent
  failed-CUDA fallback, complex128 preservation, and the two-times padding
  contract.
- Bounded-memory tests use representative chunk boundaries and prove that
  chunk size changes neither complex field nor result identity.
- A non-live matrix test uses admitted deterministic response fixtures and
  returns exactly eight independently replayable results. It does not call
  Adviser, Lumerical, or a hidden fallback.
- Focused tests run after each implementation slice. The complete non-live
  suite runs once at integration, not as the first diagnostic for every local
  change.
- Live Lumerical tests remain deselected by default. The final live ticket
  requires explicit human approval, begins with one smoke response, stops for
  artifact review, and only then may open bounded sweeps.
- A live failure preserves all artifacts and opens a focused follow-up defect;
  it does not authorize editing thresholds, source, briefs, or scientific
  policy inside the delivery gate.

## Out of Scope

- Any Rust source, protocol, authority vocabulary, event, manifest, or binding
  machinery change.
- A generic workflow, public frontier framework, route registry, compatibility
  alias, or broad new exception hierarchy.
- Multiwavelength or achromatic metalenses.
- Limited-phase optimization, inverse design, topology optimization, genetic
  algorithms, simulated annealing, or any optimizer placeholder.
- Radial Hankel/Bessel specialization.
- NumPy- or SciPy-based direct, FFT, or CZT Debye production kernels.
- Whole-device FDTD for the 0.5 mm Yun lens or the complete high-na devices.
- Exact reproduction of Arbabi's single-mode-fiber incident field.
- Reproduction of Yang's complete six-sublens Hartmann--Shack sensor.
- Yun's 4π/3 optimized design.
- Khorasaninejad's 405 nm and 660 nm devices.
- Arbabi 2020 grating averaging as the default high-na route. It remains a
  stress and comparison reference only.
- Holographic, frequency-selective, quasi-BIC, absorber, CST, or COMSOL work.
- Automatic execution of the live four-case delivery. Live use remains a
  separate human-controlled gate.

## Further Notes

- This specification supersedes the case selection in the older four-brief
  delivery and early four-brief validation records. The current canonical
  selection is Yun 2025, Yang 2018, Arbabi 2015, and Khorasaninejad 2016.
- ADR 0009 remains authoritative for G0-only complete-field applicability.
  Multi-order support must strengthen the evidence method; it must not weaken
  the existing boundary.
- ADR 0013 remains authoritative for independent periodic transmission and
  periodic polarization qualification.
- Yun 2025 is a quantized adapted reproduction: the conventional full-2π
  platform is paper truth, while the 8-, 12-, and 16-state phase sets are
  MetaCraft results.
- Yang 2018 is also quantized and adapted: the fixed paper cell and square
  footprint are retained, while 8-, 12-, and 16-orientation sets are explicit
  fabrication comparisons rather than a claim about the paper's original
  continuous layout.
- Arbabi 2015 is deliberately HCTA-derived because the current brief cannot
  express the paper's complete fiber field. This limitation is a fidelity
  fact, not a reason to replace MetaCraft's native pointwise design chain.
- Khorasaninejad 2016 supplies the high-na geometric benchmark without
  requiring an orientation sweep.
- The architecture closes in four lines:

  `brief preserves intent; proof selects method`

  `response establishes surface; field advances light`

  `assignment follows physics; comparison keeps truth`

  `authority guards history; replay returns result`
