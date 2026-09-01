# Metalens Sonnet convergence

Status: superseded by ../authority-and-science-sonnet-closure/spec.md
(2026-07-29). The Rust-first authority-and-science convergence replaced this
effort as the active implementation road. This file and its `issues/` are kept
as historical evidence of the prior plan; they no longer describe active work.

This specification is the sole implementation entry for the current Python
architecture convergence. It follows
[ADR 0010](../../docs/adr/0010-let-each-aim-own-its-scientific-language.md)
and preserves the four canonical delivery briefs from the superseded
four-brief specification as final integration fixtures.

The decision chain is explicit:

- aim-local ownership and content-addressed routes follow
  [ADR 0010](../../docs/adr/0010-let-each-aim-own-its-scientific-language.md);
- component Field meaning follows
  [ADR 0006](../../docs/adr/0006-represent-fields-by-components-not-approximations.md);
- the current G0-only period limit follows
  [ADR 0009](../../docs/adr/0009-keep-g0-only-metalens-proofs-in-the-zeroth-order-domain.md);
- period and height ownership follows
  [ADR 0011](../../docs/adr/0011-let-period-choice-precede-height.md);
- external product qualification follows
  [ADR 0003](../../docs/adr/0003-gate-external-solvers-with-local-facts.md).

## Problem

The current Python implementation contains strong scientific Modules, but
several historical layers now disagree with the accepted architecture:

- dotted propagation/geometric route names repeat facts already resolved by
  the metalens design;
- metalens-only aperture, height, focus, and regime language sits in global
  science or Field packages;
- speculative future-aim and large-na proof graphs look implemented when no
  method exists;
- evidence schemas are synthesized from route strings instead of being owned
  by the scientific values they encode;
- evidence is related to a broad route rather than the exact bound task that
  produced it;
- period and height choices do not form one explicit, paired scientific
  order;
- provider-side advice records point the science compiler outward;
- aperture sampling, target phase, propagation preparation, focus evaluation,
  and conclusion repeat knowledge across strategy-specific callers;
- the Lumerical caller can see execution and session machinery that belongs
  inside the product Adapter;
- run directories expose low-level writes while sweep code reconstructs the
  standard work record;
- `conclude` still performs retained-channel evaluation instead of consuming
  complete admitted evidence.

These are architectural debts, not permission to tune the physics, rewrite
Rust, or force the four live briefs to succeed.

## Outcome

MetaCraft keeps one lifecycle and lets each scientific aim own its language:

```text
brief identifies intent
design resolves intent
route composes claims
proof identifies meaning
task binds execution
evidence answers task
result closes study
```

The scientific verse remains:

```text
aim declares
route composes
method establishes
realization executes
evidence closes
result concludes
```

Rust remains byte-for-byte unchanged. Python becomes easier to extend because
large-na metalens, holography, quasi-BIC, and frequency-selective work can add
real methods later without inheriting the current low-na focus sequence.

## Ownership

### Shared science

The shared compiler language contains `Brief`, `Design`, `Claim`, `Method`,
`Route`, `Proof`, `Task`, `Study`, `Evidence`, and `ResultClosure`.
`Aim` retains the canonical values `metalens`, `frequency selective surface`,
`holographic metasurface`, and `quasi-bic metasurface`.

An aim without an implemented terminal proof returns `AimUnavailable`. An
implemented aim whose objectives have no applicable method returns
`MethodUnavailable`. Neither refusal creates a fake `Study`, `Proof`, or
`Finding`.

### Metalens science

`science/metalens/` owns:

- `MetalensBrief` and its atom, aperture, and fabrication intent;
- `MetalensDesign`;
- `ControlStrategy`;
- `ApertureRegime`;
- metalens material binding;
- `PeriodDomain → PeriodChoice`;
- `HeightDomain → HeightChoice`;
- phase envelope;
- `Aperture`, `FocalRegion`, `FocusSurvey`, `Focus`, and `Leakage`;
- propagation-phase response, finite phase matching, and phase sets;
- geometric-phase Jones response, cell choice, and orientations;
- metalens proof relationships and strategy-specific Result values.

`ApertureRegime` is a fact on `MetalensDesign`, not a field on generic
`Design`, `Aim`, or another metasurface. `Aperture`, `FocalRegion`, and
`Focus` are local to the metalens focus objective. Sharing them between
propagation phase and geometric phase proves metalens-local reuse only.

`science/routes/` is retired. A strategy is not a route package.

### Field science

`field/` owns the cross-aim `Field` value, its exact component evidence, and
the qualified angular-spectrum realization. It owns no universal workflow
stage and does not export metalens aperture or focus values.

The angular-spectrum implementation is one deep Module. Its small Interface
hides observation, qualification, spectrum preparation, memory budgeting,
component propagation, axial survey, and local refinement. Callers never
import its private preparation or budgeting functions.

### Advice

Pure consultation values live with the scientific questions they answer.
`WordingReview` and `DesignAdvice` live with brief and design science;
`PeriodAdvice` and `HeightAdvice` live under metalens science. The provider
Adapter depends inward on those values.

One private consultation lifecycle may serve `review_wording`,
`recommend_design`, `recommend_period`, and `recommend_height`; no generic
Advice framework, prompt object hierarchy, or provider registry is
introduced.

### External execution

Authority, Runner, Workstation, and solver Adapters remain system
infrastructure. They do not interpret phase, focus, or material physics.

The Lumerical Adapter owns:

```text
work identifies
permit admits
lane places
session opens
execution solves
observation records
receipt closes
```

Its final vocabulary is `InstallationProbe`, `WorkstationExecution`,
`SessionPool`, `SessionLease`, `WorkRecord`, `RunStore`, and `RunDirectory`.
`work_identity`, `session_identity`, and `lane_identity` are distinct facts.
There is no public `SessionFactory`, caller-supplied execution object, worker
count, or dormant `DirectEngine`.

## Scientific identity

### Route and proof

`Route` is a canonical content-addressed value containing the selected aim,
objectives, claims, methods, and applicability choices. It has no hand-written
name such as `metalens.low_na.propagation_phase`.

`Proof` expands the selected route into its exact prerequisite and evidence
topology. `proof_identity` is the canonical digest of that meaning. A
separately persisted `route_identity` is forbidden because it carries no
additional closure fact.

### Task and evidence

`task_identity` binds:

- `proof_identity`;
- the exact target claim and method;
- immutable brief and resolved-design inputs;
- prerequisite evidence references;
- exact consultations and choices consumed by the task;
- the selected binding and capacity scope when its method requires them.

Candidate or polarization-basis sub-work derives a separate `work_identity`
from `task_identity` plus the exact candidate input. `EvidenceFact` cites the
exact `task_identity`; solver work records additionally cite
`work_identity`. Evidence from another brief, design, choice, binding, or
prerequisite set cannot close the task.

### Schemas

Scientific value Modules own stable schema identifiers. A method declares the
schema of the value it establishes; the compiler copies and validates that
identifier. It never manufactures a schema from a route string.

Required examples include:

- `metacraft.science.field`;
- `metacraft.science.metalens.material_binding`;
- `metacraft.science.metalens.period_domain`;
- `metacraft.science.metalens.period_choice`;
- `metacraft.science.metalens.height_domain`;
- `metacraft.science.metalens.height_choice`;
- `metacraft.science.metalens.aperture`;
- `metacraft.science.metalens.focal_region`;
- `metacraft.science.metalens.focus`;
- `metacraft.science.metalens.result`.

Strategy-specific scientific records may own additional stable schemas.
Schema ownership is local; a central schema registry is forbidden.

## Metalens scientific order

### Period and height

The paired order is:

```text
material binding
→ period domain
→ period advice
→ period choice
→ height domain
→ phase envelope
→ height advice
→ height choice
```

`PeriodDomain` owns the exact sampling ceiling, order ceiling, strict 10 nm
period limit, fabrication constraints, and applicable period rules.
`PeriodChoice` accepts one explicit brief period or one exact recommendation
without flooring, clamping, or repair.

`HeightDomain` is derived only after `PeriodChoice`. It owns the finite height
candidates and lateral candidate arithmetic for the selected shape and
dimension step. The propagation-phase envelope is computed only where
applicable. `HeightChoice` accepts one explicit or advised height unchanged.

Advice recommends. Pure science validates. Only admitted choices permit a
solver sweep.

### Aperture, field, and focus

The common metalens tail is:

```text
assign_aperture
→ form_field
→ propagate_field
→ evaluate_focus
→ conclude
```

`Aperture` owns the circular lattice, occupied mask, target phase, stable
state placement, and vectorized identity lookup. Propagation phase supplies a
finite quantized assignment. Geometric phase supplies one admitted cell and
continuous orientations. A future pointwise method may supply a different
assignment without replacing the Aperture contract.

`Field` records component meaning. The bound realization propagates one
declared component group, searches its axial response once, and retains every
component on the matching transverse plane. `FocalRegion` owns that declared
group and records the exact metalens focal observation over `0.8f` to `1.2f`.

`evaluate_focus` accepts that aligned observation without propagating or
searching again and performs all remaining evaluation exactly once:

- a complete bracket produces `Focus`;
- an incomplete or unbracketed observation produces `FocusSurvey` plus a
  typed `Finding`;
- geometric retained-channel assessment may additionally produce `Leakage`.

Only complete `Focus` evidence closes the focus claim. `FocusSurvey` is an
admitted diagnostic, never disguised as Focus evidence. `conclude` validates
references and forms a Result; it performs no propagation, reconstruction,
power integration, focus search, or leakage calculation.

### Result and replay

`PropagationResult` and `GeometricResult` remain distinct scientific values
because their fabrication outputs differ. Both use the single document
schema `metacraft.science.metalens.result`.

The Result document contains only:

- the scientific conclusion;
- the exact fabrication output;
- admitted evaluation references;
- the exact closure reference;
- its origin and replay provenance.

Aim, objectives, control strategy, aperture regime, and proof meaning are read
from the cited closure; the Result does not copy them into a second authority.

Replay reconstructs the same Result from admitted authority objects without
calling an adviser, Lumerical, or Torch. CUDA workspaces, FFT spectra, and
other temporary numerical buffers are not authority artifacts.

## Lumerical work life

`InstallationProbe` truthfully owns installation, version, license,
solver-native material sampling, and capacity observation. Its Interface
declares every operation production dispatch uses.

`WorkstationExecution` is the sole production execution path. `SessionPool`
uses one private `open_session` operation and yields a `SessionLease`; this
test seam is internal and is not exported by `lumerical_fdtd`.

`WorkRecord` owns the standard artifact set and canonical manifest.
`RunDirectory` enforces safe paths and idempotent writes behind domain
operations for construction, execution, observation, logs, and native project
files. Sweep code does not hand-assemble that set.

The public Lumerical caller supplies only the configured workspace and
product configuration and receives dispatch. Execution, sessions, lanes,
license capacity, and worker counts remain hidden.

The existing physical policy remains unchanged: four distinct physical cores,
no SMT siblings, one locality cell, and a 16 GiB process-tree limit per lane.

## Sonnet constitution

1. One concept has one canonical noun.
2. Types are nouns; operations are verbs.
3. Paired responsibilities keep paired word order.
4. Public names use natural scientific language.
5. Mathematical shorthand stays inside equations and narrow local scopes.
6. Product-native language is translated at the Adapter seam.
7. `_local` means execution locality only.
8. New abstraction must pass the deletion test, reduce caller knowledge, and
   improve locality.
9. A deep Module may keep private test seams; test machinery never enlarges
   its public Interface.
10. No compatibility alias, generic base class, plugin registry, universal
    codec, manager, handler, processor, or shallow forwarding layer is added.

Accurate short nouns such as `Aim`, `Brief`, `Study`, `Route`, `Proof`,
`Task`, `Field`, `Cell`, `Aperture`, `Lane`, `Binding`, and `Result` remain
short. This is a responsibility audit, not a mechanical long-name rewrite.

## Verification order

Full brief execution is deliberately last.

### Ticket gate

Every implementation ticket must run:

- its focused behavior tests through the Module Interface;
- architecture tests affected by its seam;
- Pyright;
- CSU on touched files with zero hard violations;
- `git diff -- rust`, which must remain empty.

Old tests that observe retired shallow Modules are replaced, not layered.
No test imports another test-case file or asserts private implementation
spelling.

### Wave gate

The remaining waves are fixed:

1. ticket 05A: ownership, reference, and test-hygiene repair after tickets
   01–05;
2. tickets 06–07: Field and focus, then Lumerical work life through its fake
   native seam;
3. ticket 08: Result, replay, and retirement of the old route package;
4. ticket 09: documentation, architecture ratchets, and the full non-live
   suite.

After each wave, run only its related non-live integration slice. Do not run
all four canonical briefs merely to validate a local refactor.

### Final gate

After all implementation tickets:

1. run the complete non-live suite;
2. run one explicitly enabled live Adviser check with one incomplete wording
   and one complete canonical brief;
3. run one explicitly enabled, bounded native Lumerical smoke;
4. only with explicit human approval, run the four canonical live briefs;
5. replay every completed or waiting outcome without repeated advice, solver
   work, or propagation.

A scientifically unresolved brief remains unchanged and returns a replayable
waiting Study with exact diagnostics. Tests never tune a brief, widen a
method, fabricate evidence, or manufacture a Result.

## Canonical final fixtures

| fixture | control strategy | shape | wavelength | na | focal length | incidence | material pair | dimension step |
| --- | --- | --- | ---: | ---: | ---: | --- | --- | ---: |
| Johansen-inspired | propagation phase | circular pillar | 940 nm | 0.16 | 200 µm | x-linear | amorphous silicon on silica | 10 nm |
| Pi-inspired | propagation phase | square pillar | 1550 nm | 0.30 | 200 µm | x-linear | amorphous silicon on silica | 10 nm |
| Khorasaninejad-inspired | geometric phase | rectangular fin | 532 nm | 0.30 | 100 µm | right-circular | titanium dioxide on silica | 20 nm |
| Yang-inspired | geometric phase | elliptical pillar | 1550 nm | 0.32 | 30 µm | right-circular | silicon on silica | 100 nm |

All four use solver-native Lumerical FDTD materials, an aspect limit of 8,
one local-workstation budget, and explicitly omit large-na evaluation,
multiwavelength operation, and optimization. They omit cell period, atom
height, and lateral dimensions. Advice may recommend; deterministic science
alone admits or rejects. The two propagation fixtures target separate 8-,
12-, and 16-state Results. Each geometric fixture targets one
continuous-orientation Result.

## Delivery discipline

Before implementation, create one reviewed checkpoint commit of the current
accepted baseline. Do not recreate `.git`, rewrite history, or include secret
environment files.

One implementation agent handles one ticket per commit in numerical order. A
ticket may not silently absorb a later ticket. It must stop and report when:

- satisfying the ticket would change Rust;
- the specification conflicts with an admitted ADR;
- a compatibility shim appears necessary;
- a test can pass only by changing brief physics or numerical policy;
- a new registry, generic framework, or public test seam appears necessary;
- a live solver run is incomplete, unavailable, or scientifically
  unresolved.

The report must name the exact conflict and preserve all useful diagnostics
and artifacts.

## Tickets

1. [Let metalens own its intent](issues/01-let-metalens-own-its-intent.md).
2. [Let proof identify meaning and task identify work](issues/02-let-proof-identify-meaning-and-task-identify-work.md).
3. [Let period choose before height](issues/03-let-period-choose-before-height.md).
4. [Let one adviser answer grounded questions](issues/04-let-one-adviser-answer-grounded-questions.md).
5. [Let aperture arrange one metalens field](issues/05-let-aperture-arrange-one-metalens-field.md).
5A. [Let each fact have one owner](issues/05a-let-each-fact-have-one-owner.md).
6. [Let field travel and focus speak once](issues/06-let-field-travel-and-focus-speak-once.md).
7. [Let Lumerical contain one work life](issues/07-let-lumerical-contain-one-work-life.md).
8. [Let Result close and replay exact evidence](issues/08-let-result-close-and-replay-exact-evidence.md).
9. [Ratchet the Sonnet architecture](issues/09-ratchet-the-sonnet-architecture.md).
10. [Run the canonical live delivery](issues/10-run-the-canonical-live-delivery.md).

Tickets 01–05 are implemented and committed; ticket 05A records their required
conformance repair. Tickets 05A–09 are `ready-for-agent`. Ticket 10 is
`ready-for-human` and may begin only after ticket 09 records a green non-live
baseline and the human explicitly enables live execution.

## Out of scope

- any Rust source, protocol, lifecycle, or version change;
- large-na numerical implementation;
- vector angular spectrum or Debye–Wolf implementation;
- optimization or achromatic execution;
- holographic, quasi-BIC, or frequency-selective proof implementation;
- CST, COMSOL, GUI, or a common solver framework;
- old schema migration or compatibility readers;
- changing the four canonical briefs to obtain a preferred result;
- repository-wide aesthetic renaming unrelated to an accepted responsibility.
