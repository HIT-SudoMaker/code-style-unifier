# 11 — Let live wording use one canonical brief

Type: bug fix

Status: resolved (2026-07-28)

Blocked by: ticket 10 live attempt one.

## Outcome

The live wording gate calls the configured Adviser with one genuinely complete
canonical brief and one intentionally incomplete wording. It never treats
typed fixture fields that were absent from the user's wording as stated facts.

## Evidence

On 2026-07-28, the configured provider reviewed
`long_focus_propagation_brief().wording` twice and returned
`status=received`, `complete=False`, and
`needs=("dimension_step_nm",)` both times. The typed fixture carried
`dimension_step_nm=10`, but its wording did not state that fact. The provider
and prompt were therefore consistent; the live test expectation was not.

Ticket 10 requires one complete *canonical* brief. The four canonical example
wordings already state their fabrication increment explicitly.

## What to repair

- Use one of the four canonical example briefs for the complete live wording
  path.
- Keep one intentionally incomplete wording and assert its exact missing facts.
- Prove that an incomplete wording opens no compilation, solver, or Torch work.
- Do not alter a canonical brief, the required-fact vocabulary, or the provider
  prompt merely to make a live response pass.

## Acceptance

- Non-live tests prove that the complete path selects a canonical example
  wording and that the incomplete path stops before downstream work.
- The targeted live test may run only with
  `METACRAFT_RUN_ADVICE_LIVE=1`.
- Provider failure remains an honest recorded outcome.
- Rust is unchanged.

## Resolution

The complete live wording case now uses `johansen_circle_brief()` unchanged.
The intentionally incomplete wording states every required fact except
`dimension_step_nm`, so its exact expected need is stable and reviewable.

The non-live wording gate uses an injected downstream callback. Its incomplete
case supplies a fail-fast callback representing compilation, solver work, and
Torch propagation; the callback is not reached. The live test remains guarded
by `METACRAFT_RUN_ADVICE_LIVE=1` and was not run during this repair.

## Verification

- focused advice and architecture:
  `66 passed, 1 deselected in 5.18s`;
- Pyright: `0 errors, 0 warnings, 0 informations`;
- CSU on the touched production files: zero hard violations;
- `git diff -- rust`: empty.
