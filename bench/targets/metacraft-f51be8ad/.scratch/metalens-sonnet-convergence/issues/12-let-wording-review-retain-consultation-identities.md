# 12 — Let wording review retain consultation identities

Type: implementation

Status: resolved (2026-07-28)

Blocked by: ticket 10 live attempt one.

## Outcome

One `WordingReview` records the identities of the exact provider request and
response, matching the provenance already retained by design, period, and
height advice.

## Evidence

Ticket 10 requires provider, endpoint, model, request identity, response
identity, and outcome. The first live attempt could record the first three and
the outcome, but `WordingReview` exposes no request or response identity.

## What to build

- Add exact `request_identity` and optional `response_identity` fields to
  `WordingReview`.
- Derive them at the Adviser boundary from the exact request bytes and the
  UTF-8 bytes of the exact raw model response retained as `raw_response`. The
  provider HTTP envelope is already parsed by the private transport and is not
  part of the response identity.
- Retain an exact request identity for unavailable and invalid outcomes;
  response identity is absent only when no raw model response was received.
- Keep secrets and authorization headers outside both identities and records.
- Update fake advisers and focused wording tests through the public value.

## Acceptance

- Received, invalid, and unavailable wording reviews retain the correct
  identities.
- The live test can report identities without printing request bodies, raw
  responses, or API keys.
- No provider-specific type enters science.
- Pyright and focused advice tests pass; touched files have zero CSU hard
  violations.
- Rust is unchanged.

## Do not add

Do not add a generic telemetry framework, request registry, mutable trace
object, or secret-bearing log.

## Resolution

`WordingReview` now retains one required `request_identity` and one optional
`response_identity`. `OpenAICompatibleAdviser` derives them with the same
provider-neutral SHA-256 convention as period and height advice:

- the request identity hashes the exact request body bytes;
- the response identity hashes the exact `raw_response` UTF-8 bytes;
- an unavailable consultation without `raw_response` retains only the request
  identity.

Focused tests cover received, invalid, and unavailable outcomes. They also
prove that changing the API key does not change the request identity and that
the secret is absent from the hashed request body. The fake adviser exposes the
same public value without adding telemetry or provider-specific science.

## Verification

- focused advice and architecture:
  `66 passed, 1 deselected in 5.18s`;
- Pyright: `0 errors, 0 warnings, 0 informations`;
- CSU on `adviser.py` and `wording.py`: zero hard violations;
- `git diff -- rust`: empty;
- no `advice_live`, network, solver, or Torch execution was run.
