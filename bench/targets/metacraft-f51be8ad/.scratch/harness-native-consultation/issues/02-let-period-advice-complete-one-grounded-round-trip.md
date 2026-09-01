# 02 - Let period advice complete one grounded round trip

**What to build:** Replace the period portion of the active adviser callback
with one content-addressed request, one closed answer, and one provider-free
PeriodAdvice record while leaving period-domain formation and deterministic
choice unchanged.

**Blocked by:** None - can start immediately.

**Status:** resolved (2026-08-09; Ticket 08 seal correction)

- [x] Introduce the smallest shared canonical consultation values needed by a
      period request and answer: question kind, research mode, grounds,
      candidates, exclusions, cautions, answer contract, request identity,
      Recommendation, and EvidenceRequired.
- [x] Define ConsultationGround as one closed request-owned proposition with
      identity, statement, source identity, and exact kind `fact`, `constraint`,
      `forecast`, or `caution`. Cover the kind by request identity; never let a
      forecast/caution become evidence or a verdict, and keep harness-supplied
      external claims separate.
- [x] Let metalens period science form the request from the exact brief and
      admitted PeriodDomain. It must contain no height candidate, provider,
      model, endpoint, harness name, or benchmark truth.
- [x] Require an answer to cite the exact request, one legal period when it
      recommends, a concise physical reason, and only supplied decisive ground
      identifiers. External claims are closed `{identity, statement, locator}`
      values using absolute HTTPS or `doi:` locators; the conclusion cites each
      consequential claim identity. Closed-book mode requires none. Validate
      structure and identity, not source truth.
- [x] Reject stale identities, invented grounds, illegal candidates, malformed
      conclusions, and non-finite or wrong-unit values before Authority
      mutation.
- [x] Cut PeriodAdvice once to a scientific conclusion plus exact grounds. No
      compatibility reader retains status, provider, endpoint, model, prompt,
      raw response, failure, or synthetic fields.
- [x] First deepen generic `Study` restoration to retain opaque structural
      advice without `AdviceStatus` or provider fields; keep metalens-owned
      restoration strict so this ticket remains green before HeightAdvice moves.
- [x] Use the exact document identifiers
      `metacraft.science.metalens.period_consultation_request`,
      `metacraft.science.consultation_answer`, and
      `metacraft.science.metalens.period_advice`; retire
      `metacraft.advice.period` without an alias.
- [x] Preserve explicit-period precedence, period-domain validation, order
      regime behavior, choice identity, and ADR 0011 ordering.
- [x] Prove that EvidenceRequired creates no PeriodChoice and reaches no height
      or planner work.
- [x] Update the period/advice portions of `CONTEXT.md`, `DESIGN.md`, and
      `SCIENCE.md` in the same change as code and tests; do not defer current
      truth to the final seal.

## Verification boundary

Test canonical request and answer bytes, strict rejection, advice admission
sources, replay, and existing period choice through public scientific
Interfaces. Use deterministic answers only; no HTTP, harness, solver, or paper
lookup belongs here.

## Comments

Implemented through the public request, answer, advice, Study restoration, and
period-choice seams. Verification: 105 focused science/advice tests passed; 42
advice tests passed with one existing live test deselected; 53 dependency and
scientific-boundary architecture tests passed; Pyright reported zero errors and
zero warnings. The wider numerical science suite was started but intentionally
left to the final seal because it exceeded this ticket's focused boundary.

Corrective review now binds request grounds to the complete canonical
`Reference`, re-derives the exact period request before recorded replay, and
rejects forged request identities or invented grounds. Domain/request errors
remain outside answer-error translation, and a public Authority view proves
invalid answers mutate nothing. The 130-test focused period/brief regression,
110 architecture tests, Pyright, and `git diff --check` pass; two failures in a
broader mixed run are confined to concurrent Ticket 03 ruled-out-height work.

Ticket 08's focused seal reopened this owner after
`test_typed_result_frame_accepts_all_four_current_contract_families` requested
the existing 400 nm low-geometric fixture period, but that quantity was absent
from the current legal PeriodDomain and fixture construction raised
`StopIteration`. Ticket 08 changed no period science or fixture value. The
period owner must decide whether the domain or the cross-family fixture is
stale, restore one legal contract, and rerun the focused seal before closure.

The owner diagnosis found no period-domain regression: `400 nm` was a
non-normative convenience value in a Result-frame shape test. The current
low-geometric domain closes at `250 nm`, while the two high-NA
reference-surface fixtures close at `240 nm`; changing those ceilings would
weaken the preserved physical contract. The frame fixture now derives each
admitted `PeriodDomain` and chooses the largest legal 10 nm-grid candidate not
above its preferred `400 nm` test value. Benchmark facts, period validation,
and production domain formation remain unchanged. The reopened frame
regression passes at its owning seam.

Ticket 08's first full deterministic seal attempt found three further stale
period fixture paths in `diagnostic_contract_results`; a fixed 250 nm request
is absent from the applicable legal PeriodDomain and reaches
`fixture_period_advice` as `StopIteration`. The seal attempt recorded 1339
passes, five failures, and five deselections. Ticket 08 changed no period rule
or fixture and retains that failed attempt for the closure record.

The three exact diagnostic regressions shared the same non-normative fixture
drift: high-propagation and high-geometric preferred `250 nm`, while each
admitted domain exposes `240 nm` as its largest legal candidate. A shared
fixture selector now forms the closed-book request from the admitted domain and
chooses the largest candidate at or below the caller's preference. Yun frame
and diagnostic fixtures therefore share one selection rule. Production
ceilings, benchmark references, and strict validation remain unchanged; the
three exact failures and focused diagnostic/domain/architecture gates pass.
The wider pointwise gate reaches two separate Ticket 03 height-fixture failures:
an explicit `600 nm` propagation height is now certified ruled out. Those paths
pass period selection and remain outside this period owner's correction.

Final Standards review aligned the direct `PeriodAdvice` contract with
`HeightAdvice`: recommendation reasons and cited identities are typed,
non-empty, and unique before use; ground and external-claim values are typed
before identity access; and `EvidenceRequired` rejects external claims.
Direct construction and document restoration now fail through stable
`ValueError` codes rather than leaking attribute errors. Period, height, and
strict-decoding regression tests pass at this corrected seam.
