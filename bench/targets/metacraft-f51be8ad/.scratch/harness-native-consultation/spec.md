# Harness-native consultation

Status: resolved (2026-08-09; implementation sealed, usability not demonstrated)

Resolution note: the deterministic architecture and evidence retention are
sealed. The eight required clean sessions were executed once, but none reached
advice; the clean-session success criterion below remains failed evidence and
creates no Codex or Claude Code support claim.

## Context

MetaCraft's scientific architecture already keeps advice untrusted, validates
period and height against admitted grounds, chooses period before height, and
keeps benchmark truth outside production. Its remaining adviser package still
constructs prompts, calls an OpenAI-compatible chat-completions endpoint,
parses responses, classifies transport state, and writes provider-shaped
fields into durable advice. `conduct` calls that adviser synchronously while
holding one fresh application root.

The intended caller has changed. Codex and Claude Code can already clarify a
user request, research external sources, reason over supplied constraints, and
invoke local commands. MetaCraft should provide the exact scientific question
and police the answer rather than embed a second, weaker agent runtime.

The four canonical metalens benchmark cases—Yun, Yang, Arbabi, and
Khorasaninejad—supply a closed propagation/geometric by low/high-NA matrix for
testing that opening judgment without giving production science paper answers.

## Problem

Deleting the HTTP client immediately would break more than transport. Period
and height advice persist provider, endpoint, model, raw response, synthetic,
and received/unavailable/invalid state; broad design and wording advice exist
mainly to mirror provider calls; `MetalensConsultation` is an active callback;
and the create-only conduct contract cannot receive an answer after a harness
process returns.

Four harness-specific implementations would repeat the same mistake. Codex,
Claude Code, Reasonix, and Pi do not own four scientific policies. Only Codex
and Claude Code are installed locally, so treating the other two as verified
would also turn architectural aspiration into a false capability claim.

## Principle

The Sonnet cadence is:

```text
user wording clarifies
  -> brief validates
    -> grounds establish
      -> request asks
        -> harness reasons
          -> answer validates
            -> advice records
              -> choice proceeds
```

One meaning has one owner:

- the user owns declared facts and omissions;
- MetaCraft owns brief validity, scientific grounds, legal candidates,
  request identity, answer validation, advice admission, and choice;
- the agent harness owns clarification, optional research, and conservative
  reasoning;
- Authority owns durable admission;
- evidence alone closes claims.

The deletion test is decisive: deleting the harness must leave deterministic
request formation, answer validation, replay, compilation, and testing intact.
Deleting the old provider transport must remove configuration and network
complexity without scattering it elsewhere.

## Architecture

### One grounded consultation Module

The Module exposes values, not a model callback:

```python
ConsultationRequest
ConsultationAnswer
Recommendation | EvidenceRequired
```

The strict document identifiers are:

```text
metacraft.science.metalens.period_consultation_request
metacraft.science.metalens.height_consultation_request
metacraft.science.consultation_answer
metacraft.science.metalens.period_advice
metacraft.science.metalens.height_advice
```

A request carries one question kind, exact brief identity, admitted grounds
references, legal candidates, exclusions, cautions, research mode, response
contract, and a content identity derived from canonical bytes. Period and
height science each construct and validate their own request through the same
small Interface; the common layer owns only closed transport-independent
values and canonical encoding.

A `ConsultationGround` is one closed, request-owned proposition with identity,
statement, source identity, and exact kind `fact`, `constraint`, `forecast`, or
`caution`. A fact may project a brief declaration or admitted domain value; the
kind is covered by request identity and prevents a forecast or caution from
masquerading as evidence or a verdict. External source claims remain a separate
answer value. A harness may reason from supplied grounds but cannot invent,
replace, or mutate them.

An answer cites the request identity and returns exactly one conclusion. A
recommendation names one legal candidate, a concise reason, decisive ground
identifiers, and closed external claims shaped as `{identity, statement,
locator}`. A locator is either an absolute HTTPS URL or a `doi:` locator; the
conclusion cites external-claim identities, and a claim is consequential exactly
when cited. Closed-book answers require an empty external-claims collection.
Source-grounded validation checks shape, identity, and citation closure, not the
truth of a source. `EvidenceRequired` names the missing fact and why selection
would be unsafe. Invalid JSON, a stale request, invented grounds, an illegal
candidate, or forbidden source use raises before advice exists. Absence of an
answer is application waiting, not an advice status.

PeriodAdvice and HeightAdvice retain scientific identities and exact grounds
but lose provider, endpoint, model, prompt, raw-response, failure, status, and
synthetic fields. The broad DesignAdvice and provider-shaped WordingReview are
deleted. The harness may propose a canonical material interpretation, but the
user must confirm it before it enters a brief.

Before either aim-owned advice schema changes, generic Study restoration is
deepened to retain opaque structural advice documents without importing
`AdviceStatus` or provider fields. Aim-owned period and height restoration stays
strict. This keeps every migration ticket green instead of requiring the
generic compiler to understand metalens transport history.

### One resumable conduct life

The first call claims a fresh application root. A later call may resume only a
complete root whose admitted brief is byte-identical to the supplied brief.
The current consultation request is re-derived from the immutable Study
frontier; no pending-request database, mutable workflow state, or second
lifecycle is added. Repeating `conduct` without an answer returns identical
request bytes.

`conduct` no longer accepts an active `MetalensConsultation`. Its revised
Interface is:

```python
conduct(
    brief,
    *,
    application_root,
    evidence_adapter=None,
    consultation_answer=None,
) -> ConductOutcome
```

It accepts at most one answer to the exact current request, validates and
admits resulting advice, then advances until the next consultation, an
unrelated waiting fact, or completed Results. `ConsultationRequired`, carrying
one request and the complete waiting frontier, joins the closed ConductOutcome
values. A concurrent or repeated answer loses by exact Authority revision or
request identity rather than last-write-wins behavior.

An absent evidence Adapter means no executable external capability was supplied;
it is not a fake Adapter and does not become state. Conduct may still restore
pre-admitted material prerequisites and complete consultations, but when the
frontier first needs executable evidence it returns the honest WaitingStudies
outcome without opening a product. A supplied Adapter is opened exactly once,
and only at that genuinely ready evidence boundary.

### One local command Adapter

One `metacraft` command translates structured files and standard streams to the
conduct Interface. Its only operation is:

```text
metacraft conduct --brief BRIEF.json --application-root RUN \
    --material-library MATERIALS.toml \
    [--lumerical-environment LUMERICAL.env] [--answer ANSWER.json]
```

Every typed ConductOutcome, including InvalidBrief, UnsupportedAim,
ConsultationRequired, WaitingStudies, and CompletedResults, exits `0` and emits
exactly one canonical JSON object to stdout:

```json
{"schema":"metacraft.command.conduct_outcome","outcome":"...","value":{}}
```

`outcome` is exactly one of `invalid_brief`, `unsupported_aim`,
`consultation_required`, `waiting_studies`, or `completed_results`; `value` is
that outcome's closed canonical mapping.

Malformed CLI, brief, answer, or document input exits `2`, leaves stdout empty,
and emits one JSON diagnostic to stderr with schema
`metacraft.command.input_failure` and a stable reason, exactly
`{"schema":"metacraft.command.input_failure","reason":"..."}`. Unexpected Authority,
storage, or implementation exceptions remain uncaught nonzero failures; the
Adapter never relabels them as science. The explicit material-library and
optional Lumerical-environment paths reuse existing formats without inventing a
project manifest. The Adapter contains no scientific rule, prompt copy,
provider client, web client, agent loop, plugin runtime, or harness detection.
When the Lumerical environment path is absent, the command passes no evidence
Adapter; it does not manufacture a test fake or inspect an implicit project.

Every canonical brief key is present. An absent key is malformed input; a
nullable optional user fact plus its matching `omissions` entry is an honest
omission; a missing required scientific fact yields InvalidBrief and user
clarification. MetaCraft suggests only canonical material families allowed by
the material library. A harness may ask “did you mean X?”, but only explicit
user confirmation changes the brief; no alias or fuzzy-selection policy is
hardcoded.

### One shared skill

One canonical, model-invoked `skills/metacraft-design/SKILL.md` teaches the
opening cadence in short action language. Byte-identical native routers at
`.agents/skills/metacraft-design/SKILL.md` and
`.claude/skills/metacraft-design/SKILL.md` contain only discovery metadata and
an instruction to read `../../../skills/metacraft-design/SKILL.md`. They carry
no scientific policy.

The canonical skill asks the user only for unresolved facts, calls MetaCraft
for exact grounds, researches only when `source_grounded` permits it, prefers a
conservative legal recommendation, submits the answer, and stops honestly on
`evidence_required`.

The skill contains no numerical ceilings, material alias table, candidate
generation, answer schema copy, benchmark reference, solver policy, or
harness-specific tool names. Codex and Claude Code installation notes may
differ, but their scientific behavior source does not.

### Acceptance layers

Deterministic tests prove canonical request bytes, strict answer refusal,
resumption, advice replay, period-before-height, no planner on missing evidence,
and the absence of model transport. Closed-book benchmark tests expose only
each case's blind brief and admitted grounds.

Clean Codex and Claude Code sessions then exercise the same installed skill and
command. The complete four-case matrix is evaluated for mechanism-aware
reasoning, legal period and height choices, conservative evidence escalation,
and distance from the later-revealed published design. The benchmark checks
reasoning and traceability, not exact paper reproduction. No Native solver
sweep belongs to this feature.

Each harness case runs inside a temporary acceptance capsule outside the
repository. The capsule contains only the installed command, one native copy of
the canonical skill, the blind brief, reviewed material library, prepared
application root, and answer files. It contains no examples, documentation,
Research Records, reference clones, paper identity, published values, or
comparison contract. Only deterministic admitted material prerequisites are
preseeded; the production period choice then derives the height domain and phase
envelope. No executable solver configuration is present, so the case stops
before Native work after height advice.

Network and connectors are disabled by harness configuration, not merely by
instruction. Complete JSON or JSONL tool events are retained and the acceptance
check rejects a network/search call or any path outside the capsule. After the
blind answer is sealed, a human-readable post-hoc report lists the advice and
published design facts separately. It calls no benchmark Result comparison,
computes no signed delta, defines no threshold, and makes no Result claim.

The reviewed closed-book execution profiles are deliberately concrete. Codex
uses `codex exec --ephemeral --ignore-user-config --skip-git-repo-check -C
CAPSULE -s workspace-write -c 'web_search="disabled"' -c
'sandbox_workspace_write.network_access=false' --json`; no `--search` or
additional directory is permitted. Claude Code runs from the capsule with
`claude -p --no-session-persistence --no-chrome --setting-sources project
--strict-mcp-config --tools "Read,Write,Bash" --allowedTools
"Read,Write,Bash(metacraft *)" --disallowedTools "WebSearch,WebFetch"
--permission-mode dontAsk --output-format stream-json`; its project settings
contain no MCP server. Read and Write are confined to the acceptance capsule,
Write exists solely to materialize canonical answer JSON, and the audit records
every Read/Write path and every Bash argv before accepting a run. Each run
records the actual harness version and fails closed if its installed flags or
event format no longer match this profile.

Reasonix and Pi are mentioned only as future compatibility candidates. No
current test, manifest, Adapter, or support claim names them as working.

## Trade-off

The application root becomes strictly resumable for the same brief instead of
absolutely create-only. That costs a careful restoration and concurrency
contract, but it keeps one conduct lifecycle and makes a cross-process harness
possible without a mutable session server.

Removing provider metadata deliberately breaks old advice documents and
configured live-adviser tests. No compatibility reader, dual schema, alias, or
deprecation layer is retained because application roots are exact scientific
records, not long-lived provider accounts. Historical ADRs and planning
records remain readable as history.

A local command is less discoverable than an MCP server, but it is available
to both installed harnesses and keeps the Interface small. MCP may be proposed
later only after an actual caller cannot use the command or measured tool
discovery materially improves reliability.

## Conclusion

The destination is one contract, one command Adapter, one skill, and two real
harness checks. MetaCraft never calls a model; a harness never decides
scientific truth. The feature ends when the old provider road is absent, the
same root crosses consultation pauses safely, Codex and Claude Code use the
same behavior source, and all four blind cases return inspectable advice or an
honest evidence requirement.

## User stories

1. As a user, I want the harness to clarify ambiguous wording without silently
   inventing facts.
2. As a user, I want canonical material suggestions phrased as questions that
   require my confirmation.
3. As a designer, I want a conservative period recommendation over exact legal
   candidates.
4. As a designer, I want height considered only after one exact period choice.
5. As a designer, I want propagation and geometric phase to receive
   mechanism-appropriate grounds.
6. As a designer, I want an honest evidence requirement when supplied grounds
   cannot support a safe recommendation.
7. As a maintainer, I want identical grounds to produce identical request
   bytes.
8. As a maintainer, I want stale requests, invented grounds, and illegal
   candidates rejected before advice is recorded.
9. As a maintainer, I want missing or malformed harness output to remain an
   application fault or waiting state rather than fake advice.
10. As an Authority user, I want every accepted advice document admitted with
    exact scientific sources.
11. As a conduct caller, I want the same exact application root to resume after
    an external consultation pause.
12. As a conduct caller, I want foreign, partial, mismatched, concurrent, and
    stale resumptions rejected deterministically.
13. As a compiler maintainer, I want advice to remain structural and
    aim-owned without importing a harness or command Module.
14. As a repository maintainer, I want provider configuration, credentials,
    HTTP transport, and live-provider tests removed completely.
15. As an agent user, I want one concise skill that works in both Codex and
    Claude Code.
16. As a benchmark reviewer, I want closed-book runs unable to retrieve the
    withheld paper answers.
17. As a benchmark reviewer, I want all four cases judged by legal,
    traceable reasoning rather than exact agreement with the paper.
18. As a project owner, I want Reasonix and Pi described honestly as future
    candidates until local evidence exists.
19. As a project owner, I want the feature to stop without an MCP server,
    plugin framework, provider registry, or speculative harness abstraction.

## Implementation decisions

- `ConsultationRequest` and `ConsultationAnswer` are closed canonical values;
  dictionary-shaped internal protocols are forbidden.
- Request identity covers question kind, research mode, answer contract, brief
  identity, every ground reference, candidate, exclusion, and caution.
- Ground identifiers are stable within canonical request bytes and are the only
  identifiers an answer may cite.
- Research mode is exactly `closed_book` or `source_grounded`.
- Every source-grounded external claim has one identity, statement, and absolute
  HTTPS or `doi:` locator; only cited claim identities are consequential.
- Closed-book answers contain no external claims, and validation establishes
  document integrity rather than source truth.
- Recommendation and EvidenceRequired are distinct closed conclusions; neither
  is represented by nullable fields plus a status enum.
- Invalid submission creates no advice document and does not mutate Authority.
- Period and height advice schemas change once; the retired schemas receive no
  compatibility reader.
- The new strict schema identifiers are the five identifiers listed in the
  Architecture section; an implementation ticket may not invent alternatives.
- The current Study frontier remains the sole source from which a pending
  request is derived.
- A resumable root is admitted as MetaCraft-owned and bound to one exact brief;
  directory existence alone never grants resumption.
- `conduct` remains the sole scientific lifecycle and installed Python entry;
  the command Adapter only translates its structured Interface.
- The command writes machine JSON to stdout and diagnostics to stderr; secrets,
  prompts from external pages, and raw harness transcripts never enter science.
- Every brief key is present; an absent key is malformed, a declared nullable
  omission is honest, and a missing required scientific fact requests user
  correction. Validation never changes wording or accepts an inferred fact.
- The skill is the only behavioral instruction source and stays shorter than
  the scientific contract it invokes.
- The two harness routers are byte-identical and contain no behavior beyond
  loading the canonical skill.
- Codex and Claude Code use the same command and response schema. Their
  transcripts are evidence of usability, not scientific evidence.
- No benchmark case identity or published value enters a consultation request.
- Current physics, candidate formation, period choice, height choice, planner,
  solver, Authority, Result, and benchmark comparison rules remain unchanged.

## Testing decisions

- Test through the request, answer, conduct, command, and benchmark Interfaces;
  do not pin private function placement.
- Canonical round-trip and mutation tests cover every request and answer field.
- Rejection tests prove zero Authority mutation for stale identity, unknown
  ground, illegal candidate, wrong research mode, forbidden source, malformed
  JSON, brief mismatch, and duplicate submission.
- Resume tests cover same-brief success, repeated-conduct idempotence, foreign and
  partial roots, exact-root faults, and concurrent Authority revision.
- Period tests prove no height information leaks into the request. Height tests
  prove the exact adopted period and required propagation envelope are present.
- EvidenceRequired tests prove no period or height choice and no planner task is
  created from insufficient advice.
- Architecture tests reject production imports of command, skill, Codex,
  Claude, HTTP clients, provider configuration, and examples.
- Source checks reject `METACRAFT_LLM_*`, `OpenAICompatibleAdviser`, `LlmConfig`,
  `advice_live`, provider fields, and the retired advice schemas after cutover.
- Four closed-book benchmark cases run without Native solves or published
  answers from deterministic, explicitly fixture-labelled material
  prerequisites inside isolated acceptance capsules.
  Their accepted outcomes are legal recommendation or explicit
  EvidenceRequired, never a magic target value or completed scientific Result.
- Codex and Claude Code each complete the same four-case prompt set in clean
  sessions, producing eight retained transcripts. Differences are reported;
  they are not hidden by averaging or one harness substituting for the other.
- Transcript checks reject every network/search event and every filesystem read
  outside the acceptance capsule. Post-hoc reports compare context in prose
  without invoking the benchmark Result comparison contract.
- The deterministic suite, architecture suite, Pyright, Markdown links,
  canonical checks, source checks, and `git diff --check` form the final gate.

## Out of scope

- Native Lumerical execution, parameter sweeps, paper reproduction, or changing
  any solver template and physical rule.
- MCP, a plugin runtime, per-harness adapters, session hooks, a provider
  registry, a generic agent framework, or edits to user-global configuration.
- Claiming Reasonix or Pi support before they are installed and verified.
- Adding future metasurface aims, methods, optimizers, or scientific policy to
  the skill.
- Changing benchmark references, comparison permissions, target-near briefs,
  aspect limits, or published values.
- Rewriting historical Research Records, ADRs, closed tickets, or old
  application roots.
- General workspace cleanup unrelated to the provider-to-harness cutover.

## Stop rule

Stop when Tickets 01-08 are resolved, the provider path is absent, one request
contract drives both installed harnesses, the eight clean-session transcripts
and four-case evaluation are retained, and all deterministic gates pass. A new
change must identify a violated owner, Interface, dependency direction, state
transition, error contract, domain term, harness transcript, or benchmark
fact. “More Sonnet” alone does not reopen this feature.
