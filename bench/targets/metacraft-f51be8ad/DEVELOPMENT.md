# Development

## Layout

```text
rust/                 authority, workspace, Python binding
src/metacraft/        installed Python science and product Adapters
examples/             external benchmark cases and opt-in inspection tools
docs/research/        durable research records
docs/adr/             system-wide decisions
.scratch/             current and historical specifications and tickets
reference/            local source material, never generated output
```

Generated application roots, Native projects, binaries, caches, wheels, and
Cargo targets do not belong in source control.

`.scratch/INDEX.md` is non-normative navigation. It identifies the current
implementation road, sealed baseline, preserved human decisions, and
historical feature chain. Each specification, issue, and decision header
remains the sole authority for its own status.

## Sonnet naming

- Use one domain term for one concept and one owner for one transition.
- Name classes with exact nouns and operations with clear verb phrases.
- Prefix Boolean names with `is`, `has`, `can`, or `should` when that states a
  complete positive proposition.
- Follow Python `snake_case` / `PascalCase`; preserve established units and
  exact native product strings only at their boundary.
- Prefer scientific names such as `numerical_aperture`, `wave_number_x`,
  `benchmark_case`, `application_root`, and `project_execution` over broad
  `data`, `info`, `manager`, `helper`, `utils`, abbreviations, or ticket names.
- Do not add numbered production modules, compatibility aliases, forwarding
  paths, schema migrations, speculative generics, or pass-through wrappers.

CSU is the lower bound. Code must also read in domain order and pass the
deletion test: removing a retained Module must otherwise scatter real policy
across at least two callers.

## Dependency and API gates

The runtime import graph must remain acyclic without an allowlist. Production
never imports `examples`; shared values never import an aim; `workstation`
never imports a solver. The installed root remains lazy and exports exactly
`Authority`, `compile_study`, and `conduct`. The Authority Interface remains
its constructor plus `check`, `view`, `fetch`, and `decide`.

`metacraft.field` continues to export exactly its six shared vocabulary names.
Raw rectilinear geometry and uniform reference-surface formation live behind
specialized Field submodules; consumers import those exact Interfaces rather
than widening the root or adding a generic conversion utility.

`conduct` compiles before storage access and accepts `application_root`, an
optional aim-specific `evidence_adapter`, and at most one exact
`consultation_answer`. The first call atomically claims a fresh root; later
calls resume only the byte-identical checkpointed brief. Foreign and partial
roots fail without repair. Pending requests and completed Results restore
before any Adapter opens. Tests classify caller answer faults only through
`ConsultationAnswerRejected`, never exception text. Period and height first
re-form the exact current request, then translate only shared answer-closure
and explicit question-rule failures through one typed metalens fault carrying
the exact question kind. Generic conduct is the sole owner of translation to
public `invalid`; request/domain/envelope formation, candidate and advice
construction, Authority, storage, concurrency, wrong-runtime-type, and
implementation faults propagate directly. Behavioral tests inject sentinel
faults through these Interfaces rather than ratcheting catch source text.
Checkpoint restoration exercises current-rule advice replay only through
`MetalensEvidence.recompile`. Tests must admit the exact advice and current
domain/envelope documents, cover every period/height, recommendation/evidence-
required, and closed-book/source-grounded combination, and assert Authority's
view is unchanged. Stable request-stale and replay-mismatch faults remain
direct; `StudyFrontier.from_document` may add only `study_frontier_invalid`
with that direct fault as its cause. Tests do not call replay helpers or infer
failure kinds from exception text.
An answer cannot claim a missing application root. Tests also force the narrow
post-advice frontier conflict and require a direct storage fault with the exact
current projection, frontier reference, and frontier bytes unchanged. Because
Authority admits one Proposal per transaction, an already admitted immutable
advice record may remain non-current after that fault; do not relabel it as a
caller-stale rejection or add mutable pending state to conceal it.

Expected scientific outcomes cross public seams as typed values. Tests must
reject exception-message, prefix, or source-text classification in conduct,
compiler, consultation, and scientific choice paths. Source inspection is reserved
for architectural dependency, import-cost, naming, and forbidden-boundary
ratchets; behavior tests use public or explicitly owned Interfaces.

## Local conduct command

The installed command is one structured Adapter over the same conduct life:

```text
metacraft conduct --brief BRIEF.json --application-root RUN \
    --material-library MATERIALS.toml \
    [--lumerical-environment LUMERICAL.env] [--answer ANSWER.json]
```

The canonical brief and required material library are always validated. The
optional answer is one canonical consultation-answer document. Only an
explicit Lumerical environment composes `LumericalMetalensEvidence`; omitting
it passes no evidence Adapter and permits conduct to stop honestly at its next
waiting boundary. The command never searches a project, inherits Lumerical
configuration, or creates a fake capability.

Every typed outcome exits `0` and writes one schema-first canonical JSON object
as explicit UTF-8 bytes to stdout without a trailing newline; terminal encoding
cannot rewrite or reject scientific text. Option names are exact and every
singleton option may appear only once. Malformed command or noncanonical
document input and typed `ConsultationAnswerRejected` faults exit `2`, leave
stdout empty, and write one UTF-8 `metacraft.command.input_failure` object to
stderr. Authority, storage, and implementation exceptions remain uncaught
nonzero failures; the Adapter does not translate them into input or scientific
outcomes. `encode_conduct_outcome` is the byte contract shared by direct Python
verification and the installed command; it creates no second lifecycle.

## Harness skill discovery

`skills/metacraft-design/SKILL.md` is the one behavior source for the opening
consultation cadence. Codex reads the project router at
`.agents/skills/metacraft-design/SKILL.md`; Claude Code reads the byte-identical
router at `.claude/skills/metacraft-design/SKILL.md`. Each router only redirects
to the canonical skill. Keep scientific policy, command schemas, solver rules,
and harness-specific tool instructions out of both routers.

No provider credential, web client, plugin manifest, MCP server, session hook,
or user-global configuration is installed by MetaCraft. Harnesses invoke the
same local `metacraft conduct` command and provide answers as canonical files.
Acceptance tests represent the two native CLI dialects with exactly two frozen
concrete profiles in fixed Codex-then-Claude order. A profile owns only its
preflight, native capsule preparation and invocation, and transcript
observation. The shared acceptance runner retains case order, execution,
confinement, redaction, inspection, classification, artifact sealing, and
bounded reports; there is no profile discovery, registry, or production
harness Interface.

A fresh campaign collects both profile preflights before claiming one absent
evidence root, then retains all eight entries of the fixed two-profile by
four-slot matrix. Eligibility is exactly zero, four, or eight cells, while the
started count records actual process crossings rather than planned work. Each
eligible cell crosses the process boundary at most once; unavailable profiles
consume their profile-level opportunity without synthetic session artifacts.
Completed, failed, and timed-out processes are final observations: the runner
does not retry, resume, repair, substitute, or turn confinement and inspection
results into an overall pass. Availability, attempt, audit, inspection, and
consultation position remain orthogonal. The blind manifest distinguishes
planned, eligible, and started counts and is sealed before the five post-hoc
reports; the final manifest hashes that blind boundary and those reports.

The retained closed-book acceptance record is under
`.scratch/harness-native-consultation/acceptance/07`. Its 2026-08-09 run used
four fresh Codex and four fresh Claude Code sessions with no reruns. All eight
transcripts passed the corrected confinement audit, but none produced advice:
Codex could not execute the capsule-local installed command under its workspace
policy, while Claude Code authentication had expired before tool use. The
original seal, deterministic audit-correction record, and amended seal are all
retained; this is an honest failed usability check, not a product or scientific
pass.

Those retained correction records are immutable history, not executable
repair authority. The active runner exposes only fresh preflight and fresh run
modes; a read-only verifier proves the original-to-amended identity chain and
writes no artifact. A later real campaign is a separate owner-authorized,
nonblocking evidence action. Its absence, unavailable profiles, or unfavorable
outcomes cannot block deterministic closure, and success would not establish
product support, scientific performance, or an overall pass.

## Product and Native gates

Product callers never supply worker counts, sessions, lanes, process handles,
or affinity. A product Adapter owns qualification, capacity evidence,
`WorkExecution`, native project construction, observation, artifacts, and
cleanup; it borrows process placement from `workstation`. Test observations
record `native = false` and cannot satisfy Native acceptance.

Reference-surface observation preserves the product's finite, strictly
increasing horizontal and vertical coordinates. The session and Adapter must
not require uniform spacing, interpolate, resample, or silently substitute a
fallback. Uniform formation is one Field-owned batch operation: all input
surfaces share one selected target grid, all outputs pass separate Python
numerical qualification, or the call raises without returning a partial
batch.

The fixed formation contract is `periodic_rectilinear_bilinear_v1`: one 24 by
24 half-open target grid, periodic bilinear interpolation, at most 256 inputs,
no extrapolation or normalization, and diagnostic limits of `0.0081` raw
round-trip relative L2, `0.0093` normalized maximum error, and `0.0006`
relative power-proxy change from 20 by 20 to 24 by 24. A caller cannot tune
these values or request a fallback.

The 24 by 24 target is a resource gate as well as a numerical gate. The
superseded 64 by 64 candidate crossed the qualified 1 GiB high-NA vector-field
guard; the final target passed all five delivery tests across the four cases.

The Adapter persists the existing `ProjectExecution` after solve completion
and before observation. If observation faults, propagate that fault unchanged;
do not add a failure record, sidecar, exception taxonomy, or classifier. Tests
must prove an execution-only directory cannot construct a `WorkRecord`,
receipt, admitted evidence, recovery authority, or lifecycle transition.

Tickets 08.6 and 08.7 are resolved. Their shared deterministic closure passed
1,223 non-live tests with 6 deselected and 0 skipped, 105 architecture tests,
Pyright with zero findings, and CSU with zero blocking findings.

`.env.lumerical` is Lumerical-owned configuration. Fixed lane and memory
invariants remain code. Harness acceptance, Lumerical qualification, delivery, and
canary tests are opt-in and separately marked. A deterministic ticket must not
claim a skipped or unavailable Native test.

Periodic `simulation time` is likewise not configuration. The Lumerical
Adapter derives ADR 0025's ordinary and extended maxima from each immutable
construction, records native status and autoshutoff evidence, and permits no
third automatic solve. Tests that exercise an extension must retain both
attempts and the resulting closure or refusal under the candidate run.

Finding control flow is type-driven: `UNAVAILABLE` may retry at its declared
task seam, while `REFUSAL` may not. Tests must not classify `Finding.needs`
text by prefix, splitting, or substring.

Use only:

```text
C:\Users\Administrator\miniforge3\envs\research_env\python.exe
```

## Release verification

Run focused tests through each changed Interface, then:

```powershell
$projectPython = 'C:\Users\Administrator\miniforge3\envs\research_env\python.exe'

& $projectPython -m pytest -q --tb=short -p no:cacheprovider `
  -m "not integration and not lumerical_live and not lumerical_delivery and not lumerical_canary"
& $projectPython -m pyright
.\csu\bin\csu.exe check src\metacraft --format json `
  --output .csu\report.json --no-history
& $projectPython -m pytest -q -p no:cacheprovider `
  tests/architecture/test_runtime_import_dag.py `
  tests/architecture/test_scientific_boundary.py `
  tests/architecture/test_sonnet_ratchets.py `
  tests/architecture/test_domain_naming.py
git diff --check
```

When a ticket freezes Rust, also diff it against that ticket's fixed point.
Never run a Native solve, alter Rust, clean unrelated work, commit, or publish
without the corresponding owner authorization.
