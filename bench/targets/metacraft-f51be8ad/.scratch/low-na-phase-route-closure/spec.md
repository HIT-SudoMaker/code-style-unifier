# Low-na phase route closure

Status: superseded by ../metalens-sonnet-convergence/spec.md

This specification remains the audit record for closing the current
low-na propagation-phase and geometric-phase metalens routes. It follows
[ADR 0008](../../docs/adr/0008-honor-explicit-cell-constraints-before-advice.md),
the accepted language in `CONTEXT.md`, and the primary-source records for
[infrared propagation phase](../../docs/research/2026-07-27-low-na-infrared-propagation-metalens-candidates.md)
and
[classic geometric phase](../../docs/research/2026-07-27-classic-pb-metalens-candidates.md).

Rust authority and protocol bytes remain untouched.

## Problem

The two low-na routes contain most of their scientific operations, but their
public closure is not yet trustworthy enough for the first literature-led
experiments:

- the physical period is still forced to equal the largest sampling-safe
  period, so a paper's smaller disclosed period cannot reach construction;
- every height still appears to require advice, even when the brief states a
  cited height;
- Lumerical qualification and templates are hard-coded to silicon nitride on
  silica;
- propagation phase supports circular and square pillars, while geometric
  phase supports only rectangular fins;
- a geometric candidate is recovered as one indivisible item, so a completed
  `x` response is lost when its `y` response is interrupted;
- callers can still pass a propagation convention through the Field
  Interface instead of letting the selected binding own the realization;
- an incomplete focus can be admitted as proof evidence and fail only while
  constructing the result;
- the live installation helper is unreachable after an earlier return, and a
  test named “two-cell” actually opens a long sweep;
- the standard examples remain visible-band development tracers rather than
  four independent, literature-led route contracts.

The existing cyclic `0 == 2π` phase distance, independent 8/12/16 phase sets,
analytic geometric-phase rotation, component Field, `0.8f–1.2f` focal
region, automatic workstation lanes, and Rust lifecycle are retained.

## Outcome

One unchanged public application operation:

`conduct(brief) -> waiting Study | independent Results`

accepts four independent literature-led briefs and exercises the same mental
order:

`brief -> design -> material binding -> height domain -> height choice`

`-> cell evidence -> phase set -> aperture -> field -> focal region`

`-> focus -> result`

Every advance establishes exactly one fact. Scientific rules remain in their
own Python Modules; `conduct` coordinates compilation, admission, and
recompilation without interpreting solver output or field mathematics.

## Four independent examples

All four examples are explicitly named `adapted reproduction`. A paper is a
constraint source and comparison target, not an oracle that can override
MetaCraft's evidence rules.

Each factory also states the same non-optical intent explicitly:

```text
aim                = metalens
objectives         = focus
solver preference = lumerical fdtd
budget             = one local workstation
omissions          = large na, multiwavelength, optimization
```

Shared construction may remove mechanical repetition, but these values remain
part of each fresh brief's canonical identity.

### Circular propagation phase

`johansen_2024_circular_propagation_brief`

```text
wavelength          = 940 nm
numerical aperture  = 0.16
focal length        = 200 µm
cell period         = 400 nm
atom height         = 500 nm
atom shape          = circular pillar
atom material       = amorphous silicon, solver native
substrate           = silica, solver native
incident condition  = x-linear
aspect limit        = 8
```

The 200 µm focal length is a compact MetaCraft adaptation. It produces about
162 cells across the physical diameter while preserving the paper's
constant-phase low-na method regime.

### Square propagation phase

`pi_2025_square_propagation_brief`

```text
wavelength          = 1550 nm
numerical aperture  = 0.30
focal length        = 200 µm
cell period         = 600 nm
atom height         = 800 nm
atom shape          = square pillar
atom material       = amorphous silicon, solver native
substrate           = silica, solver native
incident condition  = x-linear
aspect limit        = 8
```

This gives a physical diameter near 126 µm and about 210 cells across. The
paper's 110–440 nm width interval is a comparison range, not a hidden
acceptance answer.

### Rectangular geometric phase

`khorasaninejad_2016_rectangular_geometric_brief`

```text
wavelength          = 532 nm
numerical aperture  = 0.30
focal length        = 100 µm
cell period         = 325 nm
atom height         = 600 nm
atom shape          = rectangular nanofin
fixed geometry      = long side 250 nm, short side 95 nm
atom material       = titanium dioxide, solver native
substrate           = silica, solver native
incident condition  = right-circular
aspect limit        = 8
```

The whole lens is adapted from the paper's unsupported NA 0.8 device. The
cited nanofin remains an exact Jones-response anchor.

### Elliptical geometric phase

`yang_2018_elliptical_geometric_brief`

```text
wavelength          = 1550 nm
numerical aperture  = 0.32
focal length        = 30 µm
cell period         = 1500 nm
atom height         = 340 nm
atom shape          = elliptical pillar
fixed geometry      = major axis 1350 nm, minor axis 480 nm
atom material       = silicon, solver native
substrate           = silica, solver native
incident condition  = right-circular
aspect limit        = 8
```

The paper's square sub-lens footprint is represented by the current circular
aperture contract, so the result remains adapted. Its `multi order` caution
must survive unchanged.

Each function returns a fresh immutable `MetalensBrief`. Shared construction
may hide mechanical defaults, but no example inherits another example's
scientific values. Production shape values use natural lowercase phrases;
`rectangular_fin` and similar identifier spellings are removed.

## Explicit cell constraints

The brief may carry:

- `cell_period_nm`;
- `atom_height_nm`;
- `atom.fixed_geometry`, an optional typed constraint compatible with its
  declared shape.

Fixed geometry belongs to `AtomIntent`, beside shape and material, and is
preserved inside the design's atom intent. The brief and design do not grow a
second top-level geometry field.

The compiled design always carries one resolved `cell_period_nm`. It also
retains the exact sampling ceiling as a separate value:

```text
sampling ceiling = wavelength / (2 * numerical aperture)
default period   = floor_10nm(sampling ceiling)
```

An explicit integer period is compared with the unfloored ceiling. The
floored default is used only when the brief omits a period. Downstream code
does not infer either value from the other. The ceiling remains a `Decimal`
through canonical admission; binary floating point does not enter this
boundary.

The Compiler Module applies these rules:

1. The sampling ceiling remains the hard upper bound.
2. An explicit period within that bound becomes the proposed physical period.
3. Without one, the ADR 0007 sampling-ceiling default remains.
4. The admitted material sample determines the order ceiling and order
   regime; `higher orders possible` remains non-blocking.
5. An explicit height forms a singleton height domain after fabrication
   validation, even outside the route's default height prior, and is chosen
   without synthetic advice.
6. Without an explicit height, the current route-specific envelope, advice,
   and deterministic selection remain.
7. A fixed geometry must satisfy positive dimensions, period, aspect, and
   gap against the unrounded physical limit. It forms a singleton candidate
   plan. A generated-candidate step does not round or reject it.

Malformed facts such as non-positive or non-integral dimensions fail brief
validation. A well-formed constraint that is scientifically inapplicable,
such as a period above the sampling ceiling or a geometry outside a known
fabrication bound, leaves a typed refusal at the first affected proof claim
and dispatches no solver work.

For propagation phase, an explicit height still waits for the admitted phase
envelope and remains subject to its certified necessary-condition exclusions.
Model forecasts and LLM advice cannot veto or replace it.

One discriminated height basis records either a `brief constraint` or an
exact `height advice` reference. It is not expressed as a nullable advice
reference repeated through later values. Downstream Modules cite only the
admitted height choice; its structured source closure retains the domain and
basis. Results expose advice only when advice actually supplied that basis.

There is no `period choice` proof obligation and no alternate lifecycle.

## Solver-native material catalog

Installation qualification remains product-level: configured paths, product
identity, licence, resource, template mechanics, and capacity. It does not
bind scientific material roles or pre-sample a global material set.

The Lumerical Adapter owns one configured material catalogue.

Environment keys follow one family rule:

`LUMERICAL_MATERIAL_<CANONICAL_FAMILY>=<exact native product name>`

The suffix is the reversible boundary spelling of a natural lowercase material
family: split its canonical words, uppercase them, and join them with `_`.
Invalid word forms and decoding collisions are rejected. This encoding applies
only to the key; the exact native product value is never normalized.

The first examples require canonical families:

- `silica`;
- `silicon nitride` for retained development examples;
- `amorphous silicon`;
- `silicon`;
- `titanium dioxide`.

Configuration completeness concerns solver path, Python API, licence utility,
licence endpoint, runs directory, and positive freshness. It does not require
any material family.

When `material_binding` becomes ready, the dispatch requests exactly the
design's atom family, substrate family, and wavelength from the catalogue.
The Adapter proves those exact native names exist, samples them at that
wavelength, and returns the sample from which the scientific
`MaterialBinding` is admitted. A repeated family is sampled once and may fill
both roles. Missing mappings, absent native names, and out-of-band material
data remain distinct findings; they do not make product qualification itself
false.

The product binding is role-neutral and contains no `atom` or `substrate`
material map. Product execution fixtures use no scientific material family.

Templates receive atom and substrate native identities from the admitted
scientific material binding. They never read configuration, select a family,
contain paper-specific branches, or assume silicon nitride on silica.

The ignored `.env.lumerical` remains user-owned. Implementation updates only
the distributable example. Before any opt-in native evidence opens a session,
a configuration preflight reports the exact missing catalogue keys and stops;
it never guesses a native name or rewrites local configuration.

No CST, COMSOL, portable-material-to-native conversion, or dynamic plugin
registry enters this effort.

## Geometry and candidate evidence

Science owns one cell-geometry vocabulary:

- circle by `diameter_nm`;
- square by `width_nm`;
- rectangle by `long_side_nm` and `short_side_nm`;
- ellipse by `major_axis_nm` and `minor_axis_nm`.

Typed dimensions keep their unit suffix. Natural lowercase phrases belong to
shape values such as `rectangular nanofin`; values such as
`rectangular_fin` are not public domain language.

Propagation uses circle and square. Geometric phase uses:

- rectangular nanofin;
- elliptical pillar.

At the science Interface, one admitted `Cell` is the fabrication identity
shared by the response library, selected states, aperture, fabrication table,
and Result. A pre-evidence candidate is an internal plan, not a second public
Cell. The Lumerical Adapter may project the geometry into private
product-construction values, but it must reconstruct and compare the same
typed geometry on read-back.

Every Result publishes an ordered fabrication cell table with stable cell
identity, natural shape, typed dimensions, height, period, material families,
and source references. Its state table and full aperture identity map refer
back to those cells; a consumer never has to reconstruct fabrication facts
from solver artifacts.

For geometric phase, one candidate owns two independently recoverable basis
observations:

```text
candidate
  x response
  y response
```

If `x` is admitted and `y` is interrupted, replay reuses `x` and dispatches
only `y`. The candidate becomes complete only after both responses are
admitted under the same binding, height choice, construction, and
polarization convention. Each basis has its own permit work identity, receipt,
artifacts, and observation record. The aggregate Jones response is the only
claim-closing evidence; basis receipts do not become proof obligations. A
mixed or stale pair is rejected.

A fixed rectangular or elliptical geometry produces one candidate and two
basis solves. The generated coarse grid remains only for a general geometric
brief whose geometry is not fixed.

Cell selection continues to minimize converted-channel loss and
retained-channel leakage under deterministic tie-breaking. It introduces no
hard efficiency threshold. Once selected, every aperture orientation is
derived analytically; no orientation launches another solver run.

The public Lumerical sweep interface remains small. Internal propagation and
geometric implementations may be separated for locality, but no new caller
configuration, worker count, or product-independent “solver framework” is
introduced.

## Field and focus honesty

Callers express:

`form -> propagate -> evaluate`

The field binding owns the exact propagation realization and its convention.
`propagate_field` does not accept an optional algorithm or convention.
The local application verifies the ready task's binding before invoking the
concrete realization; no public propagation protocol or runtime string
registry is introduced. Realization provenance remains in focal-region
evidence.

The current angular-spectrum realization prepares one source spectrum per
component and propagates axial distances in bounded array batches. Coarse
survey and local refinement may remain two adaptive passes, but neither pass
uses a Python loop that launches one inverse transform per plane. The internal
batch bound prevents an unbounded distance-by-aperture allocation and is not a
public worker or algorithm option.

Focus evaluation stays within `0.8f–1.2f`. If the survey does not bracket the
focus and all required half-maximum crossings:

- retain the diagnostic observation as a record;
- do not admit it as claim-closing `focus` evidence;
- return a waiting Study with an `incomplete` finding whose need is
  `focus_incomplete` and which cites that diagnostic record;
- do not throw during result construction;
- do not expand the focal region automatically.

An externally reported `incomplete` finding is valid only for a known proof
claim and must cite at least one admitted diagnostic record. Unknown claims,
duplicate findings, and reference-free incomplete findings are rejected at
compilation.

Complete focus evidence is evaluated once and consumed by conclusion without
propagating or decoding it again.

## Conduct and replay

The highest acceptance seam is each example through `conduct`.

Deterministic external adapters provide complete replayable evidence for all
four examples. Tests require:

- separately admitted 8-, 12-, and 16-state results;
- cyclic phase matching at `0 == 2π`;
- no implicit winner when quantizations differ;
- a rectangular aperture assignment with stable cell and state identities;
- component Field formation and one bound propagation realization;
- complete or honestly waiting focus semantics;
- exact result provenance after authority reopen and replay.

If one or more propagation quantizations form, `conduct` returns only their
independent Results. Each Result carries the complete phase-set formation,
including explicit refusals for the quantizations that did not form. If none
form, `conduct` returns one waiting Study with the `phase_set` refusal.
`conduct` does not invent a mixed Result-and-Study return type and never
collapses quantizations into one answer.

Authority replay performance is measured at this seam before optimization.
If repeated Python-side fetch or decode work is material, immutable documents
may be memoized for one conduct call. No persistent cache, Rust change, or
protocol extension is allowed.

## Bounded native evidence

Live Lumerical tests remain opt-in through exactly two flags:

```text
METACRAFT_RUN_LUMERICAL_SMOKE=1
METACRAFT_RUN_LUMERICAL_SOLVE=1
```

The smoke layer proves installation, licence, requested materials,
construction, and read-back without claiming a scientific result.

The solve layer uses at most two deterministic candidates per geometry:

- a disclosed paper cell when available, otherwise a legal near-minimum
  candidate;
- one legal near-midpoint comparison candidate.

Propagation therefore needs four candidate solves. Geometric phase needs
`x/y` for both candidates in both geometries, adding eight candidate solves.
One product execution qualification currently needs three fixture launches.
The native test therefore has a hard ceiling of fifteen direct-engine
launches, counted at the Adapter seam; a future implementation may lower but
not exceed it. This tracer proves construction, automatic workstation
dispatch, artifact identity, and per-axis recovery. It is not presented as a
complete cell library or Result.

The live helper must execute its inspection and qualification path, and the
test description, candidate count, and assertion must agree. No GUI Module is
introduced; headless operation remains the default.

## Sonnet ratchet

This effort improves only Modules touched by the four route closures.

- One domain concept has one natural noun.
- Public types are nouns; operations are verbs that disclose their work.
- Paired names retain word order: `minimum_feature_nm` /
  `maximum_feature_nm`, `converted_power` / `retained_power`,
  `major_axis_nm` / `minor_axis_nm`.
- Product-native strings stop at the Adapter seam.
- One admitted science `Cell` crosses response, aperture, and Result seams;
  candidates and product constructions stay internal.
- A height choice has one discriminated basis; later values cite the choice
  instead of repeating nullable advice references.
- `conduct`, `compile_study`, Field operations, and the Lumerical Adapter
  remain the test surfaces.
- Internal helpers are not promoted into public Interfaces for testing.
- Large files are split only where propagation and geometric responsibilities
  genuinely vary; line count alone is not a reason to create shallow Modules.
- Touched files leave CSU with zero hard violations and Pyright with zero
  errors.
- Architecture tests forbid Rust changes, hard-coded material families,
  physical-period substitution from the sampling ceiling downstream,
  public propagation conventions, and underscore-shaped public shape
  values.

Unrelated aesthetic churn and repository-wide style rewrites are forbidden.

## Verification

Every implementation slice begins with a failing test at one accepted seam
and finishes with:

- focused science or Adapter tests;
- the four example compilation tests;
- affected `conduct` and authority-replay tests;
- architecture tests;
- Pyright;
- CSU on every touched file;
- `git diff -- rust` empty.

Native tests are never enabled implicitly. Their artifacts remain under the
configured `runs` directory with exact route, geometry, physical period,
height, binding, workstation lane, and work identity in the manifest.

## Tickets

Each ticket is one bounded implementation session and begins at an accepted
public seam:

1. [Honor one cited cell through conduct](issues/01-honor-one-cited-cell-through-conduct.md)
2. [Qualify only what one brief requests](issues/02-qualify-only-the-materials-a-brief-requests.md)
3. [Give square propagation an equal route](issues/03-give-square-propagation-an-equal-route.md)
4. [Recover one rectangular Jones cell by basis](issues/04-recover-one-rectangular-jones-cell-by-basis.md)
5. [Give the elliptical pillar the same geometric route](issues/05-give-the-elliptical-pillar-the-same-geometric-route.md)
6. [Let the binding propagate and let incomplete focus wait](issues/06-let-the-binding-propagate-and-let-incomplete-focus-wait.md)
7. [Run the four-example matrix at bounded native cost](issues/07-run-the-four-example-matrix-at-bounded-native-cost.md)
8. [Measure replay and ratchet the Sonnet seam](issues/08-measure-replay-and-ratchet-the-sonnet-seam.md)

The dependency waves are:

- wave 1: ticket 01;
- wave 2: tickets 02 and 06;
- wave 3: tickets 03 and 04;
- wave 4: ticket 05;
- wave 5: ticket 07;
- wave 6: ticket 08.

Parallel tickets share contracts, not implementation ownership. A later wave
starts only after the preceding contract is admitted and its focused tests
are green. Before tickets in one wave are delegated concurrently, their
touched files must be disjoint; otherwise they run serially without changing
the dependency graph.

Legacy tickets 31–33 under `order-regime-and-phase-envelope` are historical
inputs, not additional implementation authority for this effort. Ticket 08
closes their stale active status only after the replacement seam is green; it
does not delete their history.

## Out of scope

- Rust source or Authority protocol changes;
- exact-reproduction claims;
- large-na execution;
- vector angular spectrum or Debye--Wolf implementation;
- optimization, achromatic, or multi-wavelength design;
- continuous pointwise matching;
- variable center spacing or She 2018 large-area layout;
- paper-efficiency thresholds as acceptance answers;
- long native sweeps in automated acceptance;
- CST, COMSOL, GUI, plugin, or dynamic method discovery.
