# Field semantics and Sonnet language

Status: superseded by ../metalens-sonnet-convergence/spec.md

This specification remains the audit record for the component-field and
language-convergence effort. It follows
[ADR 0006](../../docs/adr/0006-represent-fields-by-components-not-approximations.md)
and the accepted vocabulary in `CONTEXT.md`.

## Problem

The current low-na result path works numerically, but its public language no
longer states what the code does:

- `propagate_scalar_field` only forms an aperture-plane array;
- `evaluate_focus` reconstructs that array and combines propagation with
  evaluation;
- result interpretation reconstructs parts of the same evidence again;
- the field has no component basis, medium, frame, or incident-condition
  provenance;
- `PhaseMethod`, `CellPolicy`, `HeightDomain.route`, response names, and
  workstation names contradict the canonical domain vocabulary;
- shorthand such as `kx`, `ky`, `kz`, `na`, and bare `x`/`y` result fields
  breaks the Sonnet standard.

Adding `Scalar` or `Vector` prefixes would preserve the wrong abstraction and
multiply every downstream type.

## Outcome

MetaCraft has one component-based Field Module and one coherent production
language. The current propagation-phase and geometric-phase metalens proofs
run through:

`aperture -> field -> focal region -> focus -> result`

with:

`form -> propagate -> evaluate -> conclude`

Rust remains byte-for-byte untouched.

## Field contract

One `Field` is a single-wavelength sampled fact containing:

- a sampled surface and coordinate frame;
- a locally uniform propagation medium;
- a closed component basis;
- immutable electric component arrays;
- optional immutable magnetic component arrays;
- exact source references.

The current implementation exposes plane surfaces and two transverse bases:
linear and circular. Cartesian and sphere-tangent bases are recorded by ADR
0006 but enter the closed union only with their first real method. This effort
adds no large-na operator, Debye--Wolf operator, optimizer, or
multi-wavelength workflow.

The component structure is the vector fact. There is no `is_vector` flag and
no global propagated-field polarization label. `MetalensBrief` and
`MetalensDesign` use `incident_polarization`; PB handedness components are
physical field components, while `converted` and `retained` remain
route-owned interpretations.

Every in-memory array is finite, shape-aligned, C-contiguous, read-only, and
complex128. A field manifest records its surface, frame, medium, basis,
component roles, shape, dtype, units, source references, and exact binary
component references.

Each component is stored in C order as deterministic raw little-endian
complex128 bytes with media type `application/vnd.metacraft.ndarray`. The
manifest is the claim-closing evidence; component objects are immutable
records referenced by that manifest. Existing Authority verbs and proposal
protocol are sufficient.

## Scientific language

`ControlStrategy` is independent of aperture regime and scientific `Method`.
Current values are `propagation phase` and `geometric phase`.

`ApertureRegime` is an independent resolved design fact with current values
`low na` and `large na`. The compiled route remains a claim--method graph and
uses one stable lowercase compound identity:

- `metalens.low_na.propagation_phase`;
- `metalens.low_na.geometric_phase`;
- `metalens.large_na.propagation_phase`.

`HeightDomain.route`, `HeightChoice.route`, material binding, evidence schema,
and result closure all name that compiled route. Rules that need the strategy
or regime read `control_strategy` or `aperture_regime` explicitly. Large-na
geometric phase remains unsupported and must not fall back.

`CellPolicy` is removed:

- `sampling_ceiling_nm` is a derived metalens-design fact;
- finite height candidates and fabrication ranges belong to `HeightDomain`;
- substrate thickness, mesh accuracy, simulation time, and grating-plane
  offsets belong to the qualified Lumerical template.

The sampling ceiling remains the hard period boundary. The evidence-derived
order ceiling is diagnostic: a selected period above it yields a non-blocking
`higher orders possible` caution, not a refusal or a smaller period. That
caution survives the height domain, study, solver run manifest, and result.

The generic `science/model.py` is separated only where doing so exposes the
existing mental order: brief values live in `science/brief.py`; compiled
design, proof, task, and study values live in `science/study.py`. No registry,
plugin, or generic workflow layer is introduced.

## Field operations

### Form

`form_aperture_field` consumes an admitted Aperture and its exact incident
condition.

- Propagation phase forms a transverse-linear field.
- Geometric phase forms a circular-basis field and preserves both handedness
  components.

It does not propagate.

### Propagate

`propagate_field` consumes admitted field evidence and one compiled focal
region request. The task's binding selects the qualified realization. The
current realization applies angular spectrum independently to compatible
transverse components, prepares each spectrum once, and surveys `0.8f` to
`1.2f` with local refinement.

It returns focal-region evidence, not focus metrics. Padding, Fourier,
evanescent, batching, and convergence conventions belong to realization
provenance.

### Evaluate

`evaluate_focus` consumes focal-region evidence. It never invokes a
propagation implementation.

It records `x_half_maximum`, `y_half_maximum`, `depth_of_focus`, expected and
found distance, focal shift, separate power measures, component observations,
convergence, and explicit completeness.

### Conclude

Route interpretation consumes admitted phase, aperture, field, focal-region,
and focus evidence. It does not rebuild arrays or rerun field calculations.

## Sonnet naming constitution

1. One domain concept has one canonical noun.
2. Types are nouns and operations are verbs that disclose their work.
3. Public interfaces and canonical schemas use natural language.
4. Paired names keep the same word order.
5. A Boolean reads as one proposition and never combines provenance facts.
6. Product-native language is translated at the Adapter boundary.
7. Units and established technology nouns remain concise; local scientific
   shorthand is expanded.
8. Public-schema renames are atomic; unrelated aesthetic churn is forbidden.

Examples include `wave_number_x`, `numerical_aperture`, `position_x_m`,
`electric_field_x`, `x_half_maximum`, `output_y_from_input_x`,
`minimum_fit_frequency_hz`, and `real_part`.

Axis values (`"x"`, `"y"`, `"z"`), unit suffixes, external API spellings,
and established nouns such as FDTD, FFT, CZT, NUMA, LLM, JSON, and URL are
not expanded. Production imports use `numpy`, not the local alias `np`.

## Confirmed TDD seams

Tests exercise behavior only through these accepted seams:

- `compile_study` for pure scientific compilation;
- `form_aperture_field`, `propagate_field`, and `evaluate_focus` for the
  Field Module;
- `conduct` for admitted end-to-end scientific evidence and replay;
- Lumerical qualification, construction, and dispatch interfaces at the
  external-product boundary;
- workstation `plan` and launch interfaces for local placement;
- package and dependency architecture tests for vocabulary and Rust
  immutability.

Internal FFT preparation, decoder helpers, compiler passes, and route caches
are not independent test seams.

## Verification

Every ticket uses one red--green vertical slice before adding the next.
Expected values come from existing independent fixtures or explicit worked
examples, never by recomputing the implementation formula inside the test.

Every ticket must:

- run its focused tests and the affected standard-brief tests;
- leave touched files with zero CSU hard violations;
- keep the Authority constructor and `check`, `view`, `fetch`, `decide`
  unchanged;
- keep `git diff -- rust` empty;
- preserve live Lumerical tests as explicitly opt-in;
- retain no compatibility alias after its schema migration closes.

## Tickets

1. Speak control strategy throughout the compiler.
2. Form and propagate one component field.
3. Carry geometric-phase handedness through the same field proof.
4. Translate Lumerical construction and evidence language.
5. Converge local language and ratchet the architecture.

Tickets 02 and 04 depend on 01. Ticket 03 depends on 02. Ticket 05 follows all
others.

## Out of scope

- Rust changes;
- large-na numerical implementation;
- Debye--Wolf implementation;
- optimization;
- achromatic or multi-wavelength execution;
- CST, COMSOL, GUI, plugin, registry, or dynamic method discovery;
- compatibility shims for evidence created before this new baseline;
- repo-wide translation of prose merely to satisfy a style counter.
