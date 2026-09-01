# Let one language describe the hardened seams

**Parent map:** [Harness-native Sonnet hardening](../map.md)

**Label:** `wayfinder:grilling`

**Status:** resolved (2026-08-09)

**Assignee:** Codex

**Blocked by:** [Let replay prove the same consultation twice](01-let-replay-prove-the-same-consultation-twice.md), [Let consultation faults keep their owner](02-let-consultation-faults-keep-their-owner.md), [Decide whether two advice schemas share one private implementation](04-decide-whether-two-advice-schemas-share-one-private-implementation.md), [Let two real harness profiles meet one acceptance seam](05-let-two-real-harness-profiles-meet-one-acceptance-seam.md)

## Question

Which existing domain terms, module names, canonical documents, ADR clauses,
and architecture ratchets must change—or explicitly remain unchanged—so the
accepted replay, fault, advice-depth, and acceptance-profile decisions have one
owner and one language?

Add no glossary term for an implementation detail. Amend ADR 0021 only if the
accepted result is hard to reverse, surprising without context, and represents
a genuine trade-off rather than enforcement of its current contract.

## Resolution

Use the existing consultation vocabulary as the only public language. The four
accepted decisions deepen or enforce seams already named by `CONTEXT.md`,
`DESIGN.md`, `SCIENCE.md`, `DEVELOPMENT.md`, and ADR 0021; they do not create a
new domain concept, public Interface, schema, lifecycle, or external support
claim.

### Domain language

No glossary entry is added, renamed, or retired.

- Keep **consultation request**, **consultation answer**, **consultation
  required**, **consultation answer rejection**, **consultation ground**, and
  **advice** unchanged. In particular, `advice` remains immutable and
  untrusted, and `consultation answer rejection` remains only the narrow
  caller-input fault. Replay is the act of proving retained advice against
  current admitted grounds and current question rules; it is not another
  durable domain value deserving a glossary noun.
- Keep **period advice**, **height advice**, their distinct bases and choices,
  **phase envelope**, **study**, **reference**, **record**, **current**, and
  **conduct** unchanged. Shared closed-record mechanics do not make period and
  height one scientific choice, and acceptance profiles do not become product
  or science terms.
- Do not add `closed advice`, `recompile`, `question kind`, `acceptance
  profile`, `harness observation`, `recorded execution`, or `replay mismatch`
  to `CONTEXT.md`. They are private implementation, Interface, test-support,
  or stable-reason language rather than domain entities.
- Keep **Module**, **Interface**, **seam**, and **Adapter** as the codebase-design
  vocabulary used in implementation specifications and development text. Do
  not substitute `service`, `component`, or `API`, and do not call a seam a
  DDD boundary.

`CONTEXT.md` therefore needs no edit for this movement. Its current `advice`
definition already says the conclusion is untrusted and derived from one exact
request and validated answer; its current rejection definition already excludes
storage, Authority, and implementation faults. Replay mechanics and concrete
harness profiles would make those definitions less durable, not clearer.

### Module and type names

Keep all existing public and domain-owned names:

- `MetalensEvidence.recompile` remains the one replay Interface and
  `StudyFrontier` remains the complete waiting/checkpoint owner. Do not add a
  replay Module, policy, registry, callback, Adapter, stored request, or second
  conduct entry point.
- `PeriodAdvice`, `HeightAdvice`, `PeriodRecommendation`,
  `HeightRecommendation`, `ConsultationRequest`, `ConsultationAnswer`,
  `ConsultationRequired`, and `ConsultationAnswerRejected` remain unchanged.
  The period and height schema identifiers and canonical fields remain exact.
- `InvalidMetalensConsultationAnswer` keeps its name but moves from metalens
  conduct beside the period/height answer rules in
  `science.metalens.consultation`. The closed `QuestionKind` is its data;
  generic conduct remains the only translator to public `invalid`.
- Name the new private shared production module
  `science/metalens/_closed_advice.py`. It owns only the structural closure and
  strict restoration mechanics accepted by Ticket 04. The leading underscore
  is intentional: callers and tests continue through the two public
  question-owned advice Interfaces. It imports neither `period_advice` nor
  `height_advice` and introduces no public generic advice type.
- Keep `tests/harness_acceptance.py` as acceptance support and
  `tests/harness_acceptance_runner.py` as the one acceptance lifecycle owner;
  do not create production counterparts or rename either into a generic
  harness framework. Within that support, replace string-dispatched helper
  names with the exact Ticket 05 names: `CodexAcceptanceProfile`,
  `ClaudeAcceptanceProfile`, the closed `HarnessAcceptanceProfile` union,
  `ACCEPTANCE_PROFILES`, `HarnessPreflight`, `HarnessInvocation`,
  `PreparedHarnessRun`, and `HarnessObservation`. Keep
  `RecordedHarnessExecution` explicitly test-only.

### Canonical document clauses

The later implementation specification must update each owning canonical
document in the same change as code and tests. The required edits are narrow:

| Document | Required clause | Explicitly unchanged |
| --- | --- | --- |
| `DESIGN.md` | In State, data, and errors, say that metalens recompilation fetches retained advice through Authority, re-forms the exact current question, sends the reconstructed answer through the same question-owned acceptance rules, and compiles only byte-identical regenerated advice. State that period and height shells share one private closed-record implementation while retaining visible meaning and fault ownership. In the harness paragraph, place both concrete acceptance profiles under tests and keep preparation/observation profile-owned while the matrix, audit, redaction, inspection, seal, and report lifecycle stays shared. | Installed exports, `conduct` Interface, Authority verbs, one Study/frontier, period-before-height order, production's lack of harness detection/transport, and the dependency direction. |
| `SCIENCE.md` | In Advice, make the replay sentence explicit about current admitted bytes/current rules, exact request identity across the closed research-mode alternatives, reconstructed `Recommendation` or `EvidenceRequired`, and byte-identical regenerated advice. State that only caller-controlled answer-rule faults become a consultation answer rejection; formation, domain/envelope, advice construction, Authority, storage, and replay faults remain direct. | Both canonical advice schemas, all scientific grounds/candidates/choices, envelope asymmetry, research modes, provider-free meaning, and benchmark/solver truth. Do not describe `_closed_advice.py` or acceptance profile types here. |
| `DEVELOPMENT.md` | In Dependency and API gates, require the typed internal answer fault and sole generic-conduct translation, current-rule replay through `MetalensEvidence.recompile`, and public behavioral tests rather than exception-text or broad-catch tests. In Harness skill discovery, describe the fixed two-profile acceptance-only composition and the one shared matrix lifecycle; say explicitly that profiles are not a registry, plugin Interface, production Adapter, or third-harness promise. Update the retained-run wording only when a new live record actually exists. | Command grammar and exit contract, canonical skill/router contract, exact-once acceptance rule, nonblocking live status, Python interpreter, and release gates. |
| `CONTEXT.md` | No change. | All canonical terms and avoided distinctions above. |
| ADR 0021 | No amendment. | Entire accepted decision and implementation status. |

ADR 0021 already chooses provider-free grounded consultation, external
harnesses, one canonical behavior source, Codex and Claude Code as the current
acceptance targets, one `conduct` lifecycle, current-frontier request
derivation, direct storage/concurrency faults, and no speculative Adapter.
Replay closes a trust gap, the typed fault corrects catch scope, closed-advice
sharing is private refactoring, and profiles concentrate acceptance-only
variation. None adds a hard-to-reverse public decision that is surprising
without context and selected through a new real trade-off, so the three-part
ADR threshold is not met.

### Ratchets and behavioral verification

Change architecture ratchets only where the protected fact is architectural or
naming-shaped; keep scientific behavior in Interface tests.

1. Extend `_CONSULTATION_CONTRACT_PATHS` in
   `tests/architecture/test_sonnet_ratchets.py` to include the new private
   `_closed_advice.py`, so provider fields and generic HTTP/model transport
   cannot hide in the shared implementation.
2. Add one dependency/visibility ratchet proving `_closed_advice.py` imports
   neither period nor height advice Modules, is absent from package exports,
   and has no importer outside the two question-owned advice Modules. This
   protects the inward dependency and private seam without testing helper
   source shape.
3. Add one acceptance-architecture ratchet over the `tests/` support proving
   `ACCEPTANCE_PROFILES` is exactly Codex then Claude with unique literal
   names, production contains no acceptance-profile definition/import, and no
   production harness Adapter or harness-name dispatch appears. Keep the
   existing one-canonical-skill/two-equal-router ratchet unchanged.
4. Keep the installed-root, Authority, acyclic-import, science-owns-
   consultation, no-provider-road, canonical-schema-owner, no-string-
   classification, and single-study/frontier ratchets unchanged. They already
   protect the decisions at the appropriate architectural level.
5. Do not add source-text ratchets for the body of `recompile`, catch widths,
   replay order, advice field closure, profile event parsing, or the fixed 2x4
   lifecycle. Verify those through the public behavioral matrices required by
   Tickets 01, 02, 04, and 05. Tests assert types, structured reasons,
   canonical bytes, calls, and outcomes; they do not inspect exception text or
   private helpers.

This allocation leaves one language at every seam: the glossary names durable
science and authority concepts; canonical prose states contracts and ownership;
Module names state the exact code responsibility; architecture ratchets prevent
dependency and vocabulary backsliding; behavioral tests prove execution.

## Comments

- 2026-08-09: Resolved after reconciling the parent map, Tickets 01/02/04/05,
  the canonical glossary and design/science/development documents, ADR 0021,
  and the Sonnet architecture ratchets. No production or canonical document
  was changed by this planning ticket.
- Map gist: Keep the public consultation language and ADR 0021 unchanged;
  document replay and fault ownership in DESIGN/SCIENCE/DEVELOPMENT, name one
  private `_closed_advice` implementation and two acceptance-only profiles,
  and ratchet only their dependency, visibility, and no-provider boundaries.
