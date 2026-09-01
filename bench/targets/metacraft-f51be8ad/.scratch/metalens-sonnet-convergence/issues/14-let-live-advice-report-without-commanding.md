# 14 — Let live advice report without commanding

Type: bug fix

Status: resolved (2026-07-28)

Blocked by: ticket 10 live attempt two.

## Outcome

The live wording gate records one real provider outcome for each wording
without retrying until the Adviser agrees with an expected conclusion.
Deterministic typed-brief validation remains Python's responsibility.

## Evidence

On 2026-07-28, the same canonical Johansen wording and exact request identity
received two different valid provider responses:

- response one requested `aim` and `objective`;
- response two requested `aim`, `objective`, and `atom_shape`.

Both responses were received and valid, yet the live test failed because it
required `complete=True`. The test therefore treated untrusted, stochastic
advice as deterministic acceptance and retried in pursuit of a preferred
answer.

## What to repair

- Cross the configured Adviser seam exactly once for the canonical wording and
  exactly once for the intentionally incomplete wording.
- Require an honest immutable consultation record with provider, endpoint,
  model, request identity, response identity, status, and outcome.
- Record the canonical review's `complete` value and questions without using
  them to rewrite, reject, or complete the typed canonical brief.
- Keep deterministic compilation of the unchanged typed canonical brief in
  its own non-live seam.
- For the intentionally incomplete wording, verify that received advice asks
  at least one exact registered question and opens no downstream work.
- Do not retry a request merely to obtain the expected semantic answer.

## Acceptance

- Non-live tests prove one provider call per wording.
- A received but questioning review of a complete typed brief remains a valid
  recorded Adviser outcome.
- The incomplete wording either returns registered questions or records an
  honest unavailable/invalid provider outcome; it never fabricates completion.
- The targeted live test remains behind `METACRAFT_RUN_ADVICE_LIVE=1`.
- No canonical brief, prompt, required-fact vocabulary, or compiler rule is
  changed.
- Rust is unchanged.

## Resolution

The live wording gate now calls the configured Adviser exactly once for the
canonical Johansen wording and exactly once for the intentionally incomplete
wording. It records each returned `WordingReview` as received, invalid, or
unavailable without retrying toward an expected `complete` value.

The canonical review observes `complete` and registered questions only as
properties of the immutable consultation record. It neither controls nor
rewrites the typed brief. Compilation of the unchanged
`johansen_circle_brief()` is covered by a separate non-live test with no
Adviser outcome in its inputs.

The incomplete helper contains no downstream callback, compilation, solver, or
Torch operation. A received outcome must contain at least one registered
question; invalid and unavailable outcomes are retained unchanged. Counting
fakes prove one call per wording and preserve the canonical bytes.

## Verification

- final non-live wording slice:
  `5 passed, 1 deselected in 1.37s`;
- focused advice and architecture gate:
  `69 passed, 1 deselected in 4.87s`;
- Pyright: `0 errors, 0 warnings, 0 informations`;
- CSU on the touched test file: zero hard violations;
- production CSU: not applicable because no production file changed;
- `git diff --check`: empty;
- `git diff -- rust`: empty;
- no live, network, solver, Torch, or full non-live suite was run.
