# Sonnet performance and reliability convergence

Status: superseded by ../sonnet-terminal-convergence/spec.md

Tickets 01–05 were resolved on local `main` at `ca90c27`. The live delivery
ticket remains `ready-for-human` and requires explicit approval.

## Context

MetaCraft already has the right architecture. Rust owns generic workspace
truth through four verbs. Python owns scientific interpretation, compilation,
execution, and evaluation. AI supplies reviewable advice. The current low-NA
metalens science compiles propagation-phase and geometric-phase proofs without
placing either route in Rust.

The complete non-live suite is green, yet the closure audit found a small set
of deep contract defects behind that green baseline:

- high-frequency authority reads and decisions repeatedly re-audit cumulative
  ledger history;
- the Python authority Adapter coerces malformed wire values instead of
  rejecting them exactly;
- a multi-branch propagation frontier can be reduced to the newest single
  branch after a later checkpoint;
- one periodic transmission fixture currently qualifies a capability used by
  both propagation and geometric science;
- expected external unavailability still crosses seams as classified strings;
- a few shared meanings, architecture ratchets, dead paths, and planning
  records remain incompletely closed.

This effort repairs those defects without replacing the architecture that
already works.

## Problem Statement

As a MetaCraft researcher, I need a long-running local sweep to remain fast,
replayable, and scientifically exact as its authority ledger grows. I must be
able to trust that Rust has not weakened integrity for speed, that Python has
not guessed malformed protocol values, that all delivered propagation
quantizations survive interruption together, and that a solver capability is
issued only for the response actually verified.

The current implementation does not yet provide that assurance. A ledger of a
few thousand events makes one authority view take minutes. A malformed
Authority view can cross the Python seam through string and integer coercion.
The complete 8/12/16 frontier is stored after formation but can later be
overwritten by a single-branch checkpoint. Lumerical qualification proves only
periodic transmission while exposing a shared capability that also admits
Jones work. Expected absence is sometimes distinguished from implementation
failure by parsing exception text.

The user does not want another architecture. The user wants the existing one
to become swift under load, hard at its seams, and quiet in its concepts.

## Principles

1. **Audit the history; reuse the proof.** `check` remains a complete
   historical audit. Stable high-frequency operations reuse an exact verified
   authority state and re-audit whenever durable storage changes outside that
   proof.
2. **Complete knowledge owns complete persistence.** The Module that can see
   the whole branch frontier owns its checkpoint. A branch operation returns
   facts; it never persists a partial world as the whole.
3. **One capability, one proof.** Periodic transmission and periodic
   polarization response are distinct scientific abilities. Neither fixture
   qualifies the other.
4. **Expected absence is data; corruption is a fault.** Product
   unavailability becomes a typed Adapter outcome and then a scientific
   Finding. Malformed protocol, impossible lifecycle state, and implementation
   drift fail directly.
5. **Share mechanics, preserve meaning.** Field storage mechanics and the
   common metalens proof tail are each implemented once. Propagation and
   geometric response evidence remain scientifically distinct.
6. **Small interfaces, deep implementations.** No public verb, generic
   workflow, registry, status machine, compatibility shim, or speculative
   extension appears.

## Solution

The convergence keeps the current public mental orders:

```text
authority: check -> view -> fetch -> decide
science:   brief -> advice -> design -> study -> task -> evidence -> result
```

Rust gains one private verified-state implementation. Opening an Authority
performs the existing full audit and records the exact workspace generation,
revision, and replayed view. Stable `view` and `decide` reuse that proof.
Another Authority, an external process, a replaced database, or another
durable generation change invalidates it and causes one full re-audit.
Explicit `check` always performs the complete audit. No ledger schema,
protocol byte, public method, or scientific meaning changes.

The Python authority Adapter becomes an exact decoder. It accepts only the
schema, primitive types, references, timestamps, non-empty names, revisions,
and permit state relationships Rust can emit. It does not repair, stringify,
round, or otherwise normalize malformed wire values.

`conduct` becomes the sole owner of the private complete branch frontier. It
advances branches in deterministic order and atomically records the complete
delivered frontier after each transition. Formation diagnostics travel with
every later checkpoint. A waiting call returns the first canonical honest
waiting Study while retaining all siblings. Results are returned only when
every delivered branch has a complete admitted conclusion. Result admissions
remain idempotent through the existing four authority verbs; after an
interrupted conclusion pass, replay combines already admitted results with
the retained frontier and admits only the missing conclusions.

Lumerical qualification exposes two route-neutral capabilities:

```text
periodic_transmission_response
periodic_polarization_response
```

The propagation-phase method requires the former. The geometric-phase method
requires the latter. One product qualification passage may exercise both, but
each capability is issued only when its own fixture succeeds. Periodic
transmission observes its finite complex transmission. Periodic polarization
observes both independent input bases needed to establish one Jones response.
A product binding may therefore support either capability or both.

At the solver Adapter seam, expected qualification and execution failures are
narrow typed values or exceptions carrying exact facts. The local application
translates them into admitted diagnostics and typed Findings. `conduct` neither
imports a Lumerical error type nor parses text. Invariant failures continue to
raise directly.

Finally, the codebase removes the remaining duplicated proof and storage
mechanics, deletes the orphaned geometric decoder, makes architecture tests
recognize their exact allowed private imports, validates shared branch
bindings on replay, and reconciles active planning records with Git.

## Architecture

### Authority Module

The public Interface remains:

```text
Authority(workspace)
check()
view()
fetch(reference)
decide(proposal, at=revision)
```

Its private state has two meaningful forms:

```text
unverified
verified(generation, revision, view)
```

A verified state may arise only from:

- one successful complete audit; or
- one successful atomic commit performed from the currently verified head.

The hidden operational order is:

```text
open:   recover -> audit -> remember
check:  audit -> remember -> report
view:   observe -> compare -> refresh if changed -> answer
decide: normalize -> compare -> refresh if changed
        -> guard -> commit -> remember -> answer
```

Rejection, stale revision, lock failure, or commit failure cannot advance the
verified state. A failed audit returns no stale view and leaves the state
unverified.

### Python Authority Adapter

The Adapter remains the sole importer of the private native extension. It
translates exact Python values to the frozen native Interface and exact native
wire values back to typed Python facts.

Reference decoding validates:

- exact field set;
- string content and metadata hashes in the accepted hash form;
- non-empty media type;
- non-boolean, non-negative integer byte length.

Authority view decoding validates:

- the exact Authority view schema;
- exact revision type and non-empty value;
- ordered entry containers of the expected type;
- exact Current and Decision shapes and meanings;
- non-empty Current keys and permit scopes;
- valid RFC3339 permit expiry;
- valid open and closed permit relationships;
- consumed permits with their exact receipt references;
- revoked or expired permits without fabricated receipts.

No mapping compatibility property or fallback decoder is added.

### Conduct and Frontier

The frontier is private application knowledge, not a public workflow state or
new domain value. It contains every delivered branch's available science and
the formation report that created the family.

The application operation Interface returns one immutable branch outcome. It
does not admit checkpoints. `conduct`, which sees siblings, pending work,
complete studies, and existing results, replaces the advanced branch inside
the full frontier and records one new checkpoint.

The checkpoint uses one direct shape:

```text
brief identity
formation report
ordered delivered branches
```

Ordering is deterministic and uses scientific branch identity, including
phase-set level order where applicable. The decoder validates that all
restored branches share the capabilities and bindings that define their common
application context.

The previous partial checkpoint shape is not read. Its admitted evidence and
solver artifacts remain immutable and may be recovered by ordinary
recompilation.

### Periodic Response Qualification

Product discovery retains the existing order:

```text
configured -> found -> versioned -> licensed -> qualified -> available
```

The first four stages construct no scientific geometry. The qualified stage
performs the response fixtures through the same native dialect and session
implementation used by production work:

- periodic transmission: one propagation construction, engine execution, and
  finite complex-transmission observation;
- periodic polarization: two geometric constructions or inputs representing
  the independent bases, engine execution, and finite polarization response.

Each successful response produces its own qualification fact. Availability
still requires fresh positive license and workstation capacity. Material
sampling remains task-scoped and separate from product qualification.

The science relationships bind:

```text
propagation phase -> periodic_transmission_response
geometric phase   -> periodic_polarization_response
```

The Lumerical Adapter does not import or interpret either control strategy. It
knows only the response it can establish.

### Error Flow

Error ownership follows the seam:

```text
native diagnostic
  -> product-owned typed failure
  -> local admitted diagnostic and Finding
  -> honest waiting Study
```

Expected product or capacity absence never resembles an internal defect.
Malformed Rust protocol, impossible checkpoint state, method/operation drift,
and invalid scientific evidence remain direct faults. There is no broad
exception hierarchy and no common solver error framework.

### Sonnet Closure

The common metalens tail is declared once while accepting its
strategy-specific aperture prerequisite. Field component-reference encoding,
storage descriptor construction, validation, fetching, and restoration have
one private field-owned implementation. `Field` and `FocalRegion` retain
separate schemas and scientific meaning.

Architecture ratchets name every allowed private importer exactly. Tests do
not claim a seam is closed while omitting a relative-import level. Dead
decoders and their exclusively orphaned helpers are deleted rather than
deprecated.

## User Stories

1. As a researcher, I want a long sweep to keep admitting evidence as its
   ledger grows, so that authority overhead does not dominate solver time.
2. As a researcher, I want opening a workspace to verify its complete history,
   so that a fast session begins from proven truth.
3. As a researcher, I want explicit `check` to remain a complete audit, so that
   performance never weakens the integrity gate.
4. As a researcher, I want stable `view` calls to avoid historical replay, so
   that inspecting current truth remains responsive.
5. As a researcher, I want stable `decide` calls to avoid historical replay,
   so that permit and receipt admission scales with current state rather than
   total history.
6. As a maintainer, I want any external workspace generation change to
   invalidate the private proof, so that another process cannot leave this
   Authority serving stale state.
7. As a maintainer, I want restart to perform another full audit, so that no
   in-memory assumption survives process death.
8. As a maintainer, I want the public four authority verbs and protocol bytes
   unchanged, so that Python science and published code retain a stable seam.
9. As a maintainer, I want malformed Authority views rejected exactly, so that
   protocol drift cannot masquerade as valid Python facts.
10. As a maintainer, I want permit lifecycle combinations validated at the
    Adapter seam, so that impossible open, consumed, revoked, or expired
    states cannot enter science.
11. As a propagation-phase researcher, I want 8-, 12-, and 16-state branches
    retained together, so that an interruption cannot erase sibling work.
12. As a propagation-phase researcher, I want an explicitly refused
    quantization to remain a formation diagnostic rather than a fabricated
    branch.
13. As a researcher, I want all reachable branches advanced before a waiting
    Study is returned, so that one waiting branch does not prevent independent
    siblings from gathering reusable evidence.
14. As a researcher, I want completed branch conclusions recovered
    idempotently after interruption, so that partial conclusion admission does
    not become a partial public result.
15. As a caller, I want the existing `Study | tuple[Result, ...]` public shape
    preserved, so that frontier reliability does not create a public workflow
    container.
16. As a propagation-phase researcher, I want periodic transmission qualified
    by an executed transmission fixture, so that my solver binding cites the
    response it actually needs.
17. As a geometric-phase researcher, I want periodic polarization qualified by
    both independent input bases, so that a Jones response is never inferred
    from propagation evidence.
18. As a researcher, I want one response capability to remain usable when the
    other fixture fails, so that unrelated scientific routes do not block one
    another.
19. As a compiler maintainer, I want capability names to describe physical
    responses rather than metalens strategies, so that solver qualification
    remains route-neutral.
20. As a caller, I want expected solver unavailability to return an honest
    waiting Study, so that absence is not presented as a crash.
21. As a maintainer, I want internal implementation faults to remain direct
    failures, so that defensive error handling does not conceal defects.
22. As a field maintainer, I want component storage rules implemented once, so
    that Field and FocalRegion cannot drift in byte, dtype, shape, media, or
    reference treatment.
23. As a science maintainer, I want the shared metalens proof tail declared
    once, so that propagation and geometric proofs rhyme without duplicating
    their common end.
24. As a reviewer, I want architecture ratchets to recognize every intended
    private importer, so that passing tests make truthful claims.
25. As a reviewer, I want dead decoding paths removed, so that old evidence
    interpretations cannot mislead future agents.
26. As a release owner, I want every ticket verified through the highest stable
    seam, so that tests survive internal refactoring.
27. As a release owner, I want one complete non-live baseline after focused
    tickets pass, so that repeated full-suite runs do not slow implementation.
28. As a release owner, I want live delivery to require explicit human flags,
    so that architecture repair never launches expensive or licensed work.
29. As a future maintainer, I want one active spec and one live-delivery ticket,
    so that an agent cannot mistake historical instructions for current work.
30. As a future scientific author, I want the resulting code to read in a
    balanced natural order, so that reliability is visible in the design
    rather than hidden in commentary.

## Implementation Decisions

1. The overall architecture is preserved. This is a convergence, not a package
   rewrite.
2. Rust changes before Python. The verified authority state is the only
   authorized production Rust change in this effort.
3. The Rust public Interface, protocol schemas, canonical bytes, relation
   meanings, and database schema remain unchanged.
4. The verified state is private authority proof, not a generic cache. It
   contains no science and has no public controls.
5. The current workspace generation is observed through durable storage facts
   sufficient to detect another legitimate writer, replacement, or mutation.
   A detected difference causes complete audit rather than suffix guessing.
6. The implementation uses one reducer for admission and complete replay.
   Stable commits update the verified view only after atomic commit succeeds.
7. The Python Adapter performs strict decoding without `str` or `int`
   coercion of protocol primitives.
8. `conduct` owns complete frontier persistence. Branch operations become
   checkpoint-free fact transformations.
9. Result-family completeness is evaluated against the delivered frontier.
   Existing admitted conclusions are recovered and only missing conclusions
   are proposed.
10. Checkpoint replacement is direct. No compatibility alias, legacy reader,
    migration registry, or checkpoint version name is introduced.
11. `periodic_full_wave_response` is retired. The two accepted capability names
    are exactly `periodic_transmission_response` and
    `periodic_polarization_response`.
12. Capability qualification is independent. One product binding may produce
    one or both corresponding scientific bindings.
13. The solver Adapter remains route-neutral. Control strategies remain in
    metalens science.
14. Expected cross-seam failures are typed only where a caller classifies
    them. Local validation continues to use direct, narrow faults.
15. No new generic Result, Failure, Solver, Workflow, Advice, Field, or
    capability framework is introduced.
16. One new ADR records why explicit full audit and a verified common path are
    separate. Canonical science documentation records the two response
    capabilities and their fixture requirements.
17. The superseded closure remains historical evidence. This specification is
    the sole active implementation road and owns the new live-delivery gate.

## Testing Decisions

### Authority seam

Tests use the public Rust Authority Interface. Test-only structural counters
may observe audit and historical-row access, but production callers receive no
new diagnostic verb.

The tests prove:

- opening and explicit check perform complete audit;
- repeated stable view and decide perform no historical scan;
- a successful local commit updates the verified revision and view together;
- rejection and commit failure do not update verified state;
- another Authority commit invalidates the first handle's proof;
- restart rebuilds truth from durable history;
- projection, event, head, marker, and database replacement faults fail
  closed;
- concurrency still admits at most one decision at one revision.

Release diagnostics repeat the 304-, 1,504-, and 3,004-event exercises. On the
same reference workstation, stable 3,004-event view should improve by at least
twenty times over the recorded approximately 149-second baseline. This is a
recorded human diagnostic, not a cross-machine CI timeout.

### Python authority seam

Tests call `AuthorityView.from_mapping` and the public Python Authority. They
cover every nested value and reject:

- wrong schema;
- wrong primitive types;
- boolean integers;
- malformed or empty hashes and names;
- negative sizes;
- invalid timestamps;
- impossible permit state, close-reason, and receipt combinations;
- unknown or missing keys.

Golden valid mappings produced by Rust continue to round-trip unchanged.

### Conduct seam

Tests call public `conduct` with fake admitted science and a real local
authority workspace. They exercise:

- three delivered propagation branches across several later advances;
- two delivered branches plus one explicit formation refusal;
- interruption after each branch checkpoint;
- interruption during result conclusion admission;
- replay with some conclusions already admitted;
- deterministic first waiting Study;
- complete Result tuple only after delivered coverage is complete;
- geometric phase as one branch with no quantized phase-set fiction.

Tests assert on returned Studies, Results, admitted references, and replayed
behavior, not private queue implementation.

### Qualification and dispatch seam

Production and fake probes cross the same qualification Interface. Focused
tests demonstrate:

- discovery and license stages construct no scientific geometry;
- propagation success issues only periodic transmission capability;
- two-basis polarization success issues only periodic polarization capability;
- either capability can exist without the other;
- both successes produce both bindings under one product identity;
- expected qualification failure is typed;
- expected capacity or execution failure closes every permit and becomes an
  honest waiting Study;
- no caller supplies sessions, lanes, CPU sets, memory limits, or worker
  counts.

Live tests are written or updated where necessary but remain deselected.

### Sonnet architecture seam

Tests use public document interfaces for Field and FocalRegion. Architecture
ratchets assert exact dependency direction, allowed private importers, retired
capability names, one common proof-tail declaration, no string-classified
expected failures, no dead geometric decoder, and no scientific or versioned
language in Rust.

Focused tests run during each ticket. The complete non-live suite, Pyright,
CSU checks for touched production files, Rust source diff audit, and link
validation run once in the closure ticket.

## Trade-offs

- The selected Rust design removes repeated full-history work from the common
  path but does not change the fact that the current view itself grows with
  decisions and permits.
- Opening, restarting, explicit check, and an external writer change still pay
  the existing complete-audit cost. That cost is intentional and visible.
- Several independent Authority handles that alternate writes frequently will
  trigger frequent re-audits. The current one-coordinator model is optimized;
  a multi-writer incremental-prefix design is not invented.
- A persistent content-addressed projection tree could offer stronger
  asymptotic storage behavior, but would require a database migration and a
  substantial Rust rewrite. It is deliberately deferred.
- Route-neutral response capability names are slightly less visually tied to
  metalens strategies. That separation is intentional: solver ability and
  scientific use must not collapse into one term.
- Results may be durably admitted one at a time during a conclusion pass, but
  the public return remains family-complete. This preserves the four authority
  verbs without presenting partial completion.
- Direct checkpoint replacement declines compatibility complexity. Original
  immutable evidence remains recoverable, but the flawed partial checkpoint
  representation is not trusted.

## Out of Scope

- New authority verbs, protocol versions, database schemas, ledger
  migrations, projection trees, signatures, remote trust anchors, or a
  background integrity service.
- New science, aims, objectives, control strategies, large-NA methods,
  optimizers, or inverse-design methods.
- Changes to phase matching, 8/12/16 definitions, geometric orientation,
  materials, period or height policy, Torch implementation, focus metrics,
  workstation topology, or Lumerical native geometry.
- A solver-neutral Adapter hierarchy, CST, COMSOL, RCWA, GUI, or product
  registry.
- Compatibility aliases for retired capability names or checkpoint shapes.
- Running a real adviser, native solver smoke, full sweep, or four-brief live
  delivery during implementation tickets.

## Further Notes

Implementation should proceed one ticket and one commit at a time. A ticket
must stop rather than widen scope when its public seam cannot satisfy the
accepted contract.

The Sonnet test is qualitative but concrete:

```text
one fact, one owner;
one promise, one proof;
common paths light;
integrity paths exact.
```

## Conclusion

The convergence leaves MetaCraft recognizably itself. Rust remains small and
generic; Python remains scientific and adaptable; Lumerical remains a
product-specific Adapter; `conduct` remains the single brief-first
application operation.

The change is not another architecture. It is the moment the existing
architecture learns to keep its promises under interruption, malformed input,
partial product capability, and a long experimental history.
