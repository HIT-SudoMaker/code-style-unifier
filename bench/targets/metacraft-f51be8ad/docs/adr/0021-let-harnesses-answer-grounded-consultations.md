# 0021 - Let harnesses answer grounded consultations

Status: accepted

Implementation status: implemented (2026-08-09)

Under this accepted destination, MetaCraft no longer initiates language-model
or web requests. It forms one
content-addressed consultation request from an exact brief and admitted
scientific grounds; an external agent harness reasons, researches when the
request permits it, and returns one answer; MetaCraft validates that answer
before recording provider-free advice. This replaces the embedded
OpenAI-compatible client because model transport was obscuring the scientific
seam and preventing Codex or Claude Code from using their own tools.

The one behavior source is a canonical MetaCraft skill and the one execution
seam is a local structured command. Codex and Claude Code are the current
acceptance targets. Reasonix and Pi are future compatibility candidates,
not current acceptance targets, and receive no dedicated Adapter, prompt copy,
or support claim. MCP, plugin runtimes, provider registries, model selection,
endpoint configuration, retries, and API credentials remain outside the
architecture until a measured need establishes another real Adapter.

For closed-book acceptance, Claude Code receives capsule-confined Read and
Write plus only the exact `metacraft` Bash command. Write exists solely to
materialize canonical answer JSON. Acceptance audits every Read/Write path and
every Bash argv before the blind record is sealed; this narrow executability
allowance does not add a product Adapter, filesystem authority, or second
behavior source.

MetaCraft owns exact questions, legal candidates, grounds identifiers,
research mode, answer schema, validation, advice admission, and deterministic
choice. A harness owns natural-language interpretation, user clarification,
external research, and conservative reasoning. External sources and advice
remain untrusted and never become Authority evidence. Benchmark consultations
are closed-book; production consultations may be source-grounded and must
retain source locators.

A consultation ground is one closed, request-owned proposition with an identity,
statement, source identity, and epistemic kind: fact, constraint, forecast, or
caution. A fact may project an exact brief declaration or admitted scientific
domain; its kind never promotes a forecast or caution into evidence or a
verdict. External claims supplied by a harness remain separate: they may explain
a recommendation but never replace, mutate, or become a ground.

The brief opening is deliberately asymmetric. A harness may propose an
interpretation or ask whether a user meant a canonical material family, but
MetaCraft accepts only explicit user facts and honest omissions through its
deterministic brief validation. The broad `DesignAdvice` and provider-shaped
`WordingReview` do not survive as alternative sources of brief truth.

An asynchronous harness answer requires the same application root to cross a
process boundary. The first conduct call still claims one fresh root; later
calls may resume only a complete MetaCraft root whose canonical brief identity
matches exactly. The current consultation request is derived from the admitted
Study frontier rather than stored as a second mutable state. A stale answer,
invented ground, illegal candidate, malformed document, foreign root, or brief
mismatch raises directly. Missing advice returns the exact request; an accepted
`evidence required` answer leaves an honest waiting Study and never reaches the
planner.

An answer is resume-only: when its application root is absent, conduct rejects
it before claiming storage. Authority transactions admit one Proposal, so
advice admission and frontier replacement cannot be one public atomic action.
The application-root lock makes replacement loss exceptional; if it still
occurs, it remains a direct storage/concurrency fault. No current frontier or
evidence advances, while the immutable non-current advice record may remain as
an auditable orphan and an exact retry remains safe.

This decision supersedes ADR 0002's configured-LLM-adviser consequence and ADR
0018's embedded-adviser error table, active consultation callback, and absolute
no-reopen clause. It also supersedes only ADR 0003's clause reserving `.env`
for LLM/API credentials; ADR 0003's product-owned `.env.lumerical` and every
solver-gating decision remain in force. It preserves ADR 0018's single
`conduct` lifecycle, exact application-root ownership, three installed Python
entries, immutable Study,
Authority admission, error discipline, and stop rule. It preserves ADR 0011's
period-before-height order and every scientific, solver, evidence, benchmark,
and dependency decision not named here.

Until the implementation tickets close, the current `CONTEXT.md`, `DESIGN.md`,
`SCIENCE.md`, `DEVELOPMENT.md`, and production code remain the description of
implemented behavior. Each semantic ticket updates its owning canonical
documents in the same change as code and tests; the final seal verifies that
agreement rather than rewriting it after the fact.

The deterministic implementation seal is recorded in the
[closure record](../../.scratch/harness-native-consultation/closure.md).
Closed-book usability remains honestly unproved: all eight retained Codex and
Claude Code sessions stopped before advice, so this implementation status is
not a harness-success, Native, or scientific-performance claim.

The supporting facts and rejected framework choices are recorded in the
[harness-agent tooling Research Record](../research/2026-08-08-harness-agent-tooling-reference.md).
