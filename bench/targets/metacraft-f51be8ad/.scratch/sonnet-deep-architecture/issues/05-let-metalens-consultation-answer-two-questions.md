# 05 — Let metalens consultation answer two questions

Type: implementation

Status: resolved (2026-07-31)

Blocked by: ticket 02.

## Outcome

One metalens-owned `MetalensConsultation` interface asks exactly:

```python
recommend_period(...)
recommend_height(...)
```

The OpenAI-compatible production Adapter and one
`RecordedMetalensConsultation` satisfy that same interface. Period and height
advice remain immutable, untrusted scientific inputs.

## Problem

The two scientific questions currently live as a Protocol inside the local
application implementation. The production adviser also combines wording
review, design suggestions, period recommendation, and height recommendation.
Tests use an all-purpose fake that fabricates all four concerns.

Replay can restore durable advice records, but there is no deliberate recorded
Adapter at the same seam as production consultation. The conduct caller
therefore knows a private application type rather than an aim-owned interface.

## Scope

1. Add `science/metalens/consultation.py`.
2. Define `MetalensConsultation` with exactly `recommend_period` and
   `recommend_height`.
3. Keep period before height in both vocabulary and use:
   - period consumes one exact `MetalensBrief` and admitted `PeriodDomain`;
   - height consumes one exact `MetalensBrief`, admitted `HeightDomain`, and
     the exact propagation `PhaseEnvelope` when required.
4. Make the OpenAI-compatible period/height implementation satisfy this
   interface structurally; do not inherit from the Protocol.
5. Add `RecordedMetalensConsultation` using exact previously recorded
   `PeriodAdvice` and `HeightAdvice`.
6. Select recorded advice only by exact brief identity, domain reference, and,
   for height, exact envelope reference or exact absence.
7. Return the original immutable recorded advice. Do not rewrite provider,
   endpoint, model, prompt, response, status, failure, recommendation,
   identities, or durable `synthetic` value.
8. Keep configuration absence, transport failure, and invalid provider JSON
   represented by the existing durable advice status and exact failure.
9. Split wording review and design suggestion fixtures from the period/height
   recorded Adapter. Remove period/height behavior from the all-purpose test
   fake.
10. Replace the private local `Adviser` Protocol and its re-export. Do not
    retain an alias.
11. Keep Authority admission, conduct, result comparison, product choice, and
    end-to-end lifecycle outside this interface.

Primary production files:

- `src/metacraft/science/metalens/consultation.py`;
- `src/metacraft/science/metalens/period_advice.py`;
- `src/metacraft/science/metalens/height_advice.py`;
- `src/metacraft/advice/adviser.py`;
- `src/metacraft/advice/__init__.py`;
- `src/metacraft/_local/application.py`;
- `src/metacraft/_local/replay.py`;
- `src/metacraft/local.py`.

Primary focused tests:

- `tests/advice/test_metalens_consultation.py`;
- `tests/advice/test_adviser.py`;
- `tests/science/test_period_height_domain.py`;
- `tests/science/test_height_choice.py`;
- `tests/science/test_branch_checkpoint.py`.

Delete without aliases:

- `_local.application.Adviser`;
- the `Adviser` export from local composition;
- period and height methods on the all-purpose `FakeAdviser`;
- conduct tests that assert a private fake call shape.

Use purpose-named wording and design fixtures where those concerns still need
tests.

## Typed error contract

Production provider outcomes are durable values:

- `AdviceStatus.RECEIVED`;
- `AdviceStatus.INVALID`;
- `AdviceStatus.UNAVAILABLE`.

Missing provider configuration, transport failure, and malformed provider
response do not raise. They return an exact advice value with status and
failure.

The following remain direct faults:

- an unadmitted domain;
- brief/domain identity mismatch;
- propagation height consultation without its exact phase envelope;
- phase envelope/domain mismatch;
- an envelope supplied for geometric phase;
- malformed durable advice;
- duplicate or inconsistent recorded advice.

Absence of an exact recorded answer is a typed consultation-unavailable value
used by lifecycle code. The recorded Adapter must not fabricate an
`UNAVAILABLE` advice document.

No caller parses a failure string to choose control flow.

## TDD seam

Run the same contract table against the production Adapter with an injected
transport and the recorded Adapter:

- exact period grounds return one `PeriodAdvice`;
- exact propagation height grounds retain the envelope reference;
- geometric height grounds reject an envelope;
- unconfigured, transport-failed, and parse-failed production calls return
  durable typed advice;
- the recorded Adapter makes zero transport calls;
- the recorded Adapter returns byte-identical advice;
- foreign brief, foreign domain, incorrect envelope, and duplicate records
  fail directly;
- unavailable and invalid recorded advice replay exactly;
- a received recommendation remains untrusted and still requires
  deterministic period or height validation before choice.

Tests cross `MetalensConsultation`, not provider-private request or parser
implementation.

## Acceptance

- Conduct-facing code knows only `MetalensConsultation`.
- That interface contains exactly two methods.
- Production and recorded Adapters satisfy the same interface.
- Recorded consultation performs no network call and no Authority mutation.
- Period advice cannot choose height; height advice cannot rewrite period.
- Advice records preserve their canonical bytes.
- Wording review and design suggestion do not enter this interface.
- No generic adviser registry, provider hierarchy, or plugin mechanism
  appears.
- No compatibility alias remains.
- Rust is unchanged.

## Verification

Use the required project interpreter:

```powershell
$projectPython = 'C:\Users\Administrator\miniforge3\envs\research_env\python.exe'

& $projectPython -m pytest `
  tests/advice/test_metalens_consultation.py `
  tests/advice/test_adviser.py `
  tests/science/test_period_height_domain.py `
  tests/science/test_height_choice.py `
  tests/science/test_branch_checkpoint.py

& $projectPython -m pyright

rg -n "class Adviser|_local\.application import .*Adviser|FakeAdviser.*recommend_(period|height)" src tests
git diff --exit-code -- rust
git diff --check
```

The search may mention retired spellings only in explicit absence assertions;
it must return no production use.

## Stop and report

Stop before implementation if the interface needs a third question, requires
Authority mutation, changes durable advice bytes, turns advice into a period
or height choice, or needs a provider registry.

## Do not add

Do not add a generic consultation operation, dynamic provider discovery,
plugin mechanism, mutable advice cache, fabricated recorded advice, result
comparison, product selection, compatibility alias, record migration, or
workflow interface.

## Comments

Resolved with one metalens-owned `MetalensConsultation` Protocol containing
exactly `recommend_period` followed by `recommend_height`. The production
OpenAI-compatible Adapter satisfies it structurally, while
`RecordedMetalensConsultation` uses immutable exact Reference-key indices and
returns the original durable advice object and bytes. Missing exact records
are typed unavailable and leave the Study waiting.

Period and height grounds now require self-matching admitted domains;
propagation height also requires the exact self-matching envelope and
domain-reference pairing, while geometric height forbids an envelope.
Checkpoint replay constructs the recorded Adapter from the same
`AuthoritySession`, performs no external call or mutation, and verifies each
advice's exact structured admission closure. Plain records, reversed grounds,
duplicate keys, ambiguous proposals, malformed records, and forged references
fail directly.

The private local `Adviser` Protocol and all-purpose fake were removed without
aliases; wording, design, and metalens consultation fixtures now have separate
owners. The implementing agent passed 74 focused tests plus four result-replay
tests. Independent verification passed 83 affected tests and Pyright with zero
findings. The retired-seam search, Rust diff, and `git diff --check` were
clean.
