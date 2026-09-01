# Decide whether two advice schemas share one private implementation

**Parent map:** [Harness-native Sonnet hardening](../map.md)

**Label:** `wayfinder:prototype`

**Status:** resolved (2026-08-09)

**Assignee:** Codex

**Blocked by:** none

## Question

Does the confirmed PeriodAdvice/HeightAdvice validation drift and high
structural repetition justify one private in-process implementation for closed
advice validation and document restoration, or would that reduce domain clarity
and recreate the rejected generic choice framework?

Compare at least three designs: retain duplication with a stronger behavioral
ratchet; share only strict mechanical decoding; or absorb common closure into a
deeper question-owned implementation. Preserve distinct schemas, conclusion
types, height envelope meaning, stable failure reasons, and public Interfaces.

## Resolution

Use one private, in-process closed-advice implementation beneath the existing
period- and height-owned Interfaces. Keep `PeriodRecommendation`,
`PeriodAdvice`, `HeightRecommendation`, and `HeightAdvice` as the only public
scientific values; keep both schema identifiers and every canonical field
byte-for-byte. Do not introduce a public `Advice[T]`, generic conclusion,
policy, registry, Adapter, base class, or choice framework.

The private implementation belongs inside `science.metalens`, below both
question modules and above only Authority document/reference primitives and
the existing consultation ground, external-claim, and `EvidenceRequired`
values. Period and height modules depend inward on it; it imports neither
module, so the dependency graph remains acyclic. Its responsibility is exactly
the shared closed-record mechanics:

1. require a positive non-boolean integer recommendation, a nonblank reason,
   nonempty unique decisive-ground identities, and unique external-claim
   identities;
2. require nonblank brief and request identities, typed nonempty unique
   grounds, typed unique external claims, decisive grounds contained in the
   retained grounds, exact recommendation-to-claim closure, and no external
   claims for `EvidenceRequired`;
3. strictly decode the common canonical fields, indexed `ground_001` and
   `claim_001` mappings, and the closed recommendation/evidence-required
   alternatives; and
4. prove exact document bytes after the public question-owned value is rebuilt.

The period and height shells continue to own all visible meaning. They name
`period_nm` versus `height_nm`, construct their distinct recommendation and
conclusion types, declare their exact outer field sets, expose the unchanged
methods, and translate one private structural-invalid signal into the existing
stable period- or height-specific reason. Schema mismatch remains checked and
reported by the public shell before shared restoration; exact-byte mismatch is
likewise reported as `period_advice_document_mismatch` or
`height_advice_document_mismatch`.

`HeightAdvice.envelope_reference` remains exclusively height-owned. The
height shell restores `Reference | None` and retains it in canonical bytes; the
private implementation may enforce the shell-supplied exact key set but must
not infer whether an envelope is required, forbidden, stale, or physically
decisive. Those propagation/geometric rules, the forecast-ground restriction,
and the ruled-out-height check stay in the existing height consultation
formation and acceptance path. Period ceilings and candidate legality stay in
the period path. Common closure therefore becomes local without turning two
scientific questions into one scientific choice.

### Designs compared

1. **Retain both copies and add a ratchet — rejected.** Each public Module
   remains locally readable, but the cutover already demonstrated the cost:
   the final strict-construction and malformed-document correction was added
   to the period tests while the corresponding height matrix was not. A test
   can detect the next divergence only after one copy changes; every common
   invariant still has two production edit sites. The deletion test offers no
   concentration of complexity.

2. **Share only `_text`, `_mapping`, `_text_list`, and indexed-map decoding —
   rejected.** This removes small mechanical lines while leaving recommendation
   validation, ground/claim closure, conclusion decoding, restoration order,
   and exact-byte proof duplicated. The resulting Module would be shallow:
   deleting it merely returns four trivial helpers to two files while the
   confirmed drift remains possible.

3. **One private closed-advice implementation with explicit period/height
   shells — accepted.** The present files are 284 and 296 lines and reach a
   normalized textual similarity of about `0.85`; their substantive commonality
   is one closed-record invariant, not coincidental spelling. This design gives
   that invariant one edit site while the two existing public Interfaces retain
   their domain language and failure ownership. It passes the deletion test:
   deleting the private implementation makes the full validation/restoration
   closure reappear in both question modules.

4. **A public generic advice hierarchy or configurable choice registry —
   rejected.** It maximizes syntactic reuse by making callers learn type
   parameters, profiles, optional envelope state, or registration. That moves
   physical differences into configuration, enlarges the Interface, and
   recreates the generic choice framework already excluded by the parent map.

### Test replacement

Test only through the unchanged public period and height Interfaces; do not
import the private implementation. Replace the period-only closure tests with
one parameterized public behavioral matrix covering both schemas:

- valid direct construction and exact document/canonical-value round trips;
- frozen pre-refactor canonical bytes or document references for one
  recommendation and one `EvidenceRequired` record per schema;
- non-integer, boolean, nonpositive, blank, duplicate, unknown-kind,
  missing-key, extra-key, malformed-index, wrong-reference, open-ground, and
  open-claim mutations;
- exact domain-specific recommendation, advice, schema-mismatch, and
  document-mismatch reasons; and
- `EvidenceRequired` rejecting every external-claim payload.

Keep period request/candidate/ceiling tests in the period consultation suite.
Keep envelope presence, forecast decisiveness, ruled-out height, and geometric
envelope prohibition tests in the height consultation suite. Add a height-only
round-trip pair for `envelope_reference=None` and an admitted reference. Delete
the four period-only direct/restore closure tests once the shared public matrix
proves both questions; do not layer private-code tests beneath it.

No Research Record or ADR is required for this private refactoring decision:
the evidence is repository-local, and ADR 0021, ADR 0011, the canonical domain
language, and the resolved replay decision remain unchanged. A later
implementation specification should name the private file and exact helper
shape without reopening this seam.

## Comments

- 2026-08-09: Compared the two production Modules and their focused tests.
  Both consultation suites pass (`40 passed`), but the implementations contain
  the same closed-record rules while only the period suite carries the final
  malformed-construction/restoration matrix. Resolve by sharing private
  closure mechanics, not public scientific meaning.
