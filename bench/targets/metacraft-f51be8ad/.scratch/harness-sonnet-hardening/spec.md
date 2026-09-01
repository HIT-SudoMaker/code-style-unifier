# Harness-native Sonnet hardening

Status: stable planning contract (2026-08-09; implementation requires explicit
owner approval)

Decision source: [Choose one bounded hardening movement](issues/08-choose-one-bounded-hardening-movement.md)

This specification authorizes no code, test, canonical-document, retained-
artifact, or live-harness change by itself. Each implementation ticket remains
`ready-for-agent` until the owner explicitly approves implementation against
this exact specification.

## Context

ADR 0021 has already cut MetaCraft over from embedded model transport to one
provider-free consultation contract, one resumable `conduct` lifecycle, one
local command Adapter, and one canonical skill consumed by Codex and Claude
Code. The deterministic implementation is sealed. The retained closed-book
campaign is also honest: eight sessions were started once, all confinement
audits passed after a zero-rerun correction chain, and none reached advice.

The post-seal review found four bounded maintenance defects without finding a
new scientific requirement:

1. `PeriodAdvice` and `HeightAdvice` repeat one closed-record invariant, and
   their public test matrices have drifted.
2. broad `ValueError` catches can misclassify request formation, advice
   construction, and implementation faults as caller-owned invalid answers;
3. `MetalensEvidence.recompile` trusts retained Study advice more than fresh
   conduct does, instead of proving its admitted bytes and current validity;
4. acceptance support redispatches the same Codex/Claude distinction through
   strings and retains two completed correction writers as live mutation
   paths.

These are trust, ownership, depth, and deletion defects. They do not justify a
new public concept, schema, lifecycle, transport, harness registry, or support
claim.

## Problem

Fixing each symptom independently would leave two roads. Fresh answers could
use stricter rules than replay; period and height could continue to drift;
historical correction code could remain an alternate writer beside fresh-run
sealing; and a generic profile registry could recreate provider abstraction in
tests. A broad final refactor would be equally unsafe because it would mix
scientific validation, Authority proof, external CLI dialects, retained
provenance, documentation, and optional live evidence in one context.

The movement therefore needs one frozen destination and small vertical slices.
Every slice must end at an observable Interface, retain the owning fault, and
delete its superseded road. The movement must close deterministically even if
neither real harness is available or usable.

## Principle

One question has one acceptance path, one retained fact has one proof path, and
one external convention has one acceptance-only owner.

The production cadence is:

```text
public period/height shell
  -> private closed-record mechanics
    -> question-owned answer validation
      -> typed caller fault or direct owner fault
        -> Authority-backed replay of the same rules
          -> compilation
```

The acceptance cadence is:

```text
concrete profile preflight/prepare/observe
  -> shared fixed matrix
    -> shared audit/redaction/inspection/classification
      -> blind manifest
        -> post-hoc reports
          -> final seal
```

The two cadences meet only through the already installed command and retained
application-root facts. Acceptance code is not production architecture, and
acceptance artifacts are not scientific evidence.

## Architecture

### Frozen public contract

The implementation must not change:

- installed root exports: `Authority`, `compile_study`, and `conduct`;
- the `conduct(brief, *, application_root, evidence_adapter=None,
  consultation_answer=None)` Interface or its closed outcomes;
- the Authority constructor and `check`, `view`, `fetch`, and `decide` verbs;
- any canonical brief, consultation request, consultation answer, period
  advice, or height advice schema identifier, key, ordering, or byte encoding;
- `PeriodAdvice`, `HeightAdvice`, `PeriodRecommendation`,
  `HeightRecommendation`, `ConsultationRequired`, or
  `ConsultationAnswerRejected` as public/domain-owned values;
- the four public rejection reasons `not_required`, `duplicate`, `stale`, and
  `invalid`, including duplicate-before-stale precedence;
- period-before-height ordering, request candidates, scientific grounds,
  phase-envelope asymmetry, choice behavior, benchmark truth, solver behavior,
  evidence meaning, or Result meaning;
- one `StudyFrontier`, one application root, one conduct lifecycle, one
  canonical skill, and the exact local command grammar; or
- Codex and Claude Code as the only current acceptance targets, without making
  a support, parity, or usability claim.

`CONTEXT.md` and ADR 0021 remain unchanged. No compatibility reader, alias,
dual writer, stored request, mutable pending state, replay entry point, public
generic advice, production harness Adapter, or third-harness extension seam is
permitted.

### Private closed-advice Interface

Add exactly one private production Module:

```text
src/metacraft/science/metalens/_closed_advice.py
```

It is imported only by `period_advice.py` and `height_advice.py`, imports
neither shell, and is absent from every package export. Its internal Interface
is limited to these four responsibilities:

```python
validate_recommendation_fields(
    quantity: int,
    reason: str,
    decisive_ground_identities: tuple[str, ...],
    external_claim_identities: tuple[str, ...],
) -> None

validate_advice_fields(
    brief_identity: str,
    request_identity: str,
    grounds: tuple[ConsultationGround, ...],
    conclusion: RecommendationFields | EvidenceRequired,
    external_claims: tuple[ExternalClaim, ...],
) -> None

restore_advice_fields(
    document: Document,
    *,
    exact_keys: frozenset[str],
    recommendation_key: str,
) -> RestoredAdviceFields

require_exact_document_bytes(actual: Document, expected: Document) -> None
```

`RecommendationFields` and `RestoredAdviceFields`, if named as private frozen
values, carry only the common structural fields and never cross either public
shell. They contain no schema identifier, question kind, period/height policy,
envelope rule, candidate rule, or configurable callback.

The shared mechanics require positive non-boolean integral quantities,
nonblank identities/reasons, nonempty unique grounds and decisive grounds,
unique external claims, decisive-ground closure, recommendation-to-claim
closure, no claims on `EvidenceRequired`, strict exact-key and indexed mapping
restoration, closed conclusion alternatives, and exact final document bytes.

The period and height shells continue to own schema checks, exact outer keys,
`period_nm` versus `height_nm`, domain-specific constructors, stable outward
reasons, and public document formation. Height alone owns
`envelope_reference`; consultation formation/acceptance alone owns envelope
presence, forecast decisiveness, ruled-out heights, geometric prohibition,
period ceilings, and candidate legality. Private structural failure is
translated by the shell to its existing period- or height-specific reason.

### Typed consultation fault and error ownership

Move `InvalidMetalensConsultationAnswer` to
`science/metalens/consultation.py`. It remains private, carries a closed
`QuestionKind`, and is the only internal value generic conduct may translate
to `ConsultationAnswerRejected("invalid")`.

Period and height acceptance follow one order:

1. form the expected request and compare its canonical bytes;
2. inside the sole caller-fault scope, run shared answer closure and explicit
   question-owned rules over caller-controlled answer contents;
3. outside that scope, resolve the validated candidate and construct the
   public recommendation and advice.

Request formation, stale internal request, domain/envelope restoration,
candidate conversion after validation, advice construction, wrong runtime
type, Authority, storage, concurrency, and replay faults propagate directly.
`accept_metalens_consultation` catches no `ValueError`. Generic conduct catches
exactly `InvalidMetalensConsultationAnswer`. Command document decoding remains
`answer_document_invalid` and never reaches this typed seam.

### Authority-backed replay

`MetalensEvidence.recompile` remains the sole Interface. Before
`compile_metalens` receives retained period or height advice, it must:

1. strictly restore the sole retained item of each kind and reject duplicates;
2. derive its advice document reference, fetch exact bytes through the existing
   `AuthoritySession`, and require equality with the Study subtree;
3. restore the current admitted period/height domain and, for propagation
   height only, the current phase envelope;
4. form the request for every member of the closed `ResearchMode` enum and
   require exactly one identity match, without assuming a default;
5. reconstruct the exact `ConsultationAnswer`, reverse-mapping a recommendation
   value to its canonical candidate and preserving reason, decisive grounds,
   external claims, or `EvidenceRequired`;
6. pass the answer through the same question-owned acceptance function used by
   fresh conduct; and
7. require regenerated advice bytes to equal the retained admitted bytes and
   pass only the regenerated value to compilation.

Replay performs no mutation, network access, harness detection, compatibility
repair, or fresh consultation. Current rules govern replay. Stable direct
reasons distinguish period/height request staleness and replay mismatch. A
checkpoint codec may add `study_frontier_invalid` only by chaining the direct
cause. A replay fault never becomes `ConsultationAnswerRejected`, advice
absence, or a new request.

### Correction deletion and immutable provenance

The active runner retains exactly:

```text
tests/harness_acceptance_runner.py --preflight
tests/harness_acceptance_runner.py --run --evidence-root <absent-directory>
```

Delete `--correct-audits`, `--correct-retained-evidence`, both correction
writers, their correction-only capsule helpers, and their now-unused imports.
Add no verify, repair, amendment, migration, force, overwrite, or compatibility
mode. The existing `acceptance/07` tree remains byte-identical.

`tests/acceptance/test_retained_harness_evidence.py` becomes the read-only
owner of original -> audit-corrected -> retained-evidence-corrected provenance.
It verifies every manifest/correction digest, every old/new run identity,
current artifact bytes, both zero-rerun declarations, confinement and redaction
facts, honest failure positions, and bounded post-hoc claims. It writes no
artifact and opens no harness.

### Two concrete acceptance profiles

Acceptance support contains the closed composition:

```python
HarnessAcceptanceProfile = CodexAcceptanceProfile | ClaudeAcceptanceProfile

ACCEPTANCE_PROFILES = (
    CodexAcceptanceProfile(),
    ClaudeAcceptanceProfile(),
)
```

Each frozen concrete profile exposes a literal `name` and exactly
`preflight(capture)`, `prepare(request)`, and `observe(transcript)`. The shared
values are `HarnessPreflight`, `HarnessInvocation`, `PreparedHarnessRun`, and
`HarnessObservation`; `CapsuleRequest` is in-memory only.

Each profile owns its executable/version/help contract, required flags,
authentication environment names, native capsule overlay, argv/stdin, strict
native JSONL event decoding, access extraction, outer command grammar, and
final explanation. Both materialize byte-identical canonical skill bytes.
The runner iterates the tuple and never redispatches by profile name.

The shared runner owns blind fixtures, prepared application roots, the fixed
matrix, execution, confinement policy, answer-name policy, redaction parity,
scientific inspection, classification, hashing, manifests, post-hoc reports,
and claims. `RecordedHarnessExecution` is test-only; there is no production
profile, Protocol, registry, discovery mechanism, plugin, or callback recipe.

### Nonblocking campaign implementation

The runner always plans two profiles by four blind slots in fixed slot/profile
order. It calls both profile preflights once before root creation. The shared
launcher plus profile results yield 0, 4, or 8 eligible cells. It then claims
one explicitly supplied absent root and starts each eligible cell at most once.
An unavailable profile receives four `not_started_preflight` plan entries and
no synthetic per-cell artifact. A started nonzero, timed-out, incomplete,
audit-rejected, or unfavorable cell is terminal and is never retried.

Every sealed campaign has `preflight.json`, eight plan entries, artifacts only
for started cells, accepted canonical answer copies only when present,
`blind-manifest.json`, four slot reports plus `post-hoc/matrix.md`, and
`sealed-manifest.json`. It records planned, eligible, and actually started
counts separately and `session_rerun_count: 0`.

Classification remains orthogonal:

- profile availability: `available` or `unavailable_preflight`;
- attempt: `not_started_preflight`, `completed`, `failed`, or `timed_out`;
- started-cell audit: `accepted` or `rejected`;
- started-cell inspection: `completed` or `failed`;
- accepted inspected consultation: one of the eight positions frozen by
  Ticket 06, from `process_failed_before_advice` through
  `consultation_cadence_complete`.

Recorded executions prove both-available, Codex-only, Claude-only, and neither-
available campaigns without opening a real harness. A real campaign is a
separate owner-authorized evidence action after deterministic closure. Its
success is neither required nor sufficient for this movement's seal.

### Documentation and ratchets

Implementation updates `DESIGN.md`, `SCIENCE.md`, and `DEVELOPMENT.md` beside
the slice that changes their owned behavior. `CONTEXT.md` and ADR 0021 receive
no edit. Final integration must leave the canonical prose stating current-rule
Authority-backed replay, narrow typed fault ownership, private closed-record
sharing, the fixed two-profile acceptance composition, and nonblocking partial
campaign semantics.

Architecture tests add only three shape guards:

1. `_closed_advice.py` joins `_CONSULTATION_CONTRACT_PATHS`, imports neither
   shell, is unexported, and has no production importer beyond the two shells;
2. `ACCEPTANCE_PROFILES` is exactly Codex then Claude with unique literal names;
3. production defines/imports no acceptance profile, harness-name dispatch,
   or harness Adapter.

The existing local-Markdown-link ratchet must also batch its read-only
`git check-ignore` candidate arguments below the Windows command-line limit.
This is a portability repair to the existing check, not a fourth architecture
guard: it preserves the same tracked/untracked, in-repository, nonignored link
semantics and must make the canonical pytest entry pass without a proxy.

Replay order, catch scope, advice closure, transcript dialects, and campaign
counting are behavioral contracts, not source-text tests. Existing installed-
root, Authority, DAG, science ownership, no-provider, schema, no-string-
classification, one-frontier, and canonical-skill ratchets remain unchanged.

## Trade-off

One private structural Module adds a small internal vocabulary, but removes two
full invariant edit sites while keeping public scientific meaning visible.
Current-rule replay may reject advice produced under superseded rules; that is
safer than silently compiling unproved retained state and avoids a migration
road. Two concrete acceptance profiles duplicate a little orchestration, but
keep real external conventions cohesive and avoid a speculative extension
framework. Removing repair writers makes historical corrections intentionally
non-repeatable as mutations; their exact immutable chain remains independently
verifiable.

The optional campaign may seal zero sessions or unfavorable observations. That
limits claims but prevents availability and authentication from becoming a
release gate or rerun-until-green policy.

## Conclusion

The bounded destination has one production validation path and one fresh
acceptance path. Public science and Authority contracts stay fixed; private
closed-advice mechanics deepen, caller faults become typed, replay proves
admitted advice under current rules, historical correction authority
disappears, and two real harness dialects meet one shared evidence lifecycle.

The movement stops when Tickets 09-16 are implemented and deterministically
sealed with no second road. A live campaign outcome, additional harness,
general-purpose framework, compatibility layer, Native execution, or further
aesthetic refactoring is not a closure condition.

## Exact test contract

- Public period/height advice matrix: construction, canonical round trip,
  frozen bytes/references for recommendation and `EvidenceRequired`, all
  malformed structural mutations, domain-specific reasons, and height
  envelope-reference presence/absence.
- Consultation matrix: four public reasons and precedence, period/height
  caller closure, height forecast/ruled-out rules, direct stale request and
  envelope faults, sentinel construction/Authority/storage faults, and command
  decode ownership.
- Replay matrix: period/height by recommendation/`EvidenceRequired`, admitted
  byte proof, all research modes, duplicate/stale/mismatch/direct-fault cases,
  no mutation, and no public rejection translation.
- Provenance matrix: complete immutable amendment chain plus retired CLI mode
  rejection and a before/after whole-tree digest equality check.
- Profile matrix: exact native preparation, real recorded event dialects,
  fail-closed mutations, normalized audit/redaction parity, and absence of
  string redispatch.
- Campaign matrix: four availability combinations, fixed plan, exact starts,
  every terminal class without retry, artifacts/manifests/hashes, partial
  reports, absent-root enforcement, and rejection of reuse/repair modes.
- Integration: focused Interfaces, full non-live deterministic suite, Pyright,
  architecture suite, CSU, the canonical Markdown-link pytest ratchet without
  `WinError 206` or a proxy, domain naming, and `git diff --check`; report exact
  counts and intentional exclusions.

## Exclusions

- No real Codex or Claude Code session in implementation or sealing tickets.
- No Lumerical, delivery, canary, integration, Native, paid, network, or solver
  execution; no claim from an excluded or skipped test.
- No Rust or Authority change, application-root migration, benchmark edit,
  scientific threshold, candidate, ground, choice, evidence, or Result change.
- No edits to retained `acceptance/07` artifacts, map, or `.scratch/INDEX.md` as
  part of this specification's implementation.
- No provider transport, credential channel, MCP, plugin, registry, Protocol,
  generic advice/choice framework, third harness, or production test support.
- No compatibility wrapper, dual schema, forwarding path, repair writer,
  mutable pending state, second conduct/replay entry, or exception-text
  classifier.

## Stop condition

Stop after the dependency graph is complete, all frozen contracts and deletion
inventories are proved, the deterministic final seal records exact results and
scope, and no named High/Medium defect or second execution road remains. A
failure reopens its owning ticket; the seal performs no semantic repair. “More
Sonnet” or a possible live usability improvement is not a reopening condition.
