# 04 — Let one adviser answer grounded questions

Type: implementation

Status: resolved (2026-07-28)

Blocked by: ticket 03.

## Outcome

Scientific consultation values point inward. One provider Adapter answers
named questions without becoming compiler authority.

## What to build

- Place `WordingReview` and `DesignAdvice` with shared brief/design science.
- Place `PeriodRecommendation`, `PeriodAdvice`, `HeightRecommendation`, and
  `HeightAdvice` under metalens science.
- Rename the broad design consultation from `Advice` to `DesignAdvice` and
  its operation to `recommend_design`; migrate atomically with no alias.
- Keep the provider-neutral operations `review_wording`,
  `recommend_design`, `recommend_period`, and `recommend_height`.
- Hide request construction, provider calls, response parsing, and common
  status handling behind one private consultation lifecycle.
- Make the OpenAI-compatible provider Adapter depend on scientific records;
  science compilation must not import the provider package or transport
  configuration.
- Preserve configured base URL, model, API key handling, prompt/response
  identity, raw response, rationale, and received/unavailable/invalid
  outcomes.
- Let compilation validate recommendations through ticket 03's pure Modules;
  provider output never chooses or closes evidence.
- Add a dependency test proving science does not depend outward on `advice`.

## TDD seam

Use one deterministic fake provider through the four named Adviser
operations. Verify a complete wording review, a missing-fact review, valid and
invalid design advice, grounded period advice, grounded height advice, and
provider unavailability. Run no live network call.

## Acceptance

- The provider package owns transport only; immutable scientific consultation
  records live inward.
- Every recommendation retains its exact question grounds and provenance.
- Period and height advice cannot be reused with another domain identity.
- The compiler can consume recorded advice without constructing an Adviser.
- Public names contain no provider brand such as DeepSeek.
- No generic prompt hierarchy, advice subclass tree, provider registry, or
  second lifecycle exists.
- Focused adviser, compiler, and dependency tests pass.
- Pyright reports zero errors; touched files have zero CSU hard violations.
- `git diff -- rust` is empty.

## Do not add

Do not add automatic retry policy, hidden defaults, provider selection by AI,
fallback advice, or a generic `AdviceManager`.
