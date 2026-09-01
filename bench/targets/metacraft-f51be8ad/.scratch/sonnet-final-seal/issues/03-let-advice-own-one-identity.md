# Let advice own one identity

Type: implementation

Status: resolved (2026-07-29)

Blocked by:
[Let one current decision resolve contention](02-let-one-current-decision-resolve-contention.md).

## Outcome

Generic available science keeps one advice sequence. Period and height advice
derive one exact identity from their canonical documents, while Authority
admission and scientific adoption remain separate operations.

## Scope

1. Keep `AvailableScience.advice` as the only advice container.
2. Remove `period_advice_reference` and `height_advice_reference` from
   `AvailableScience`, compilation functions, conduct, and local composition.
3. Keep `PeriodAdvice`, `HeightAdvice`, and `DesignAdvice` value shapes
   unchanged.
4. Derive a period or height advice reference only from its canonical document
   through `reference_for`.
5. Keep provider-created period and height advice outside
   `AvailableScience` until Authority admission succeeds.
6. Verify the reference returned by admission equals the canonical document
   reference, then store the unchanged advice record in
   `AvailableScience.advice`.
7. Leave `DesignAdvice` unchanged, unbound, and without a synthetic reference.
8. Let `compile_study` continue to receive one advice sequence.
9. Let `compile_metalens` derive the `period_choice` and `height_choice`
   consultation references from the matching advice records.
10. Reject duplicate or wrong-type period and height advice at their existing
    metalens seam.
11. Remove the parallel `advice_reference` argument from period and height
    choice operations; let each operation derive the advice identity from its
    canonical document.
12. Verify the derived reference against the ready task consultation before
    forming a choice.
13. Preserve `AdvisedPeriod` and `AdvisedHeight` as the exclusive indication
    that validated advice became a choice basis.
14. Update propagation, geometric, validation, conclusion, and replay paths to
    derive exact advice references where required.
15. Preserve the existing checkpoint schema and advice bytes.
16. Restore checkpoint period and height documents only after fetching their
    exact Authority references, then place the unchanged records in the one
    advice sequence.
17. Preserve `Study.canonical_bytes()` for the same scientific inputs.
18. Clarify identity, admission, and adoption in `CONTEXT.md` and `SCIENCE.md`.
19. Remove the retired reference fields without aliases or compatibility
    properties.

## Acceptance

- `AvailableScience` contains one advice field and no aim-specific advice
  reference field.
- No `AdviceFact`, `AdmittedAdvice`, or second advice container exists.
- No advice dataclass gains an admission field or admission-state method.
- `DesignAdvice` remains ordinary unbound advice.
- One period or height advice document always derives the same exact
  `Reference`.
- Local consultation admits the advice before exposing it as available
  science.
- A mismatch between the admission-returned and derived reference is rejected.
- Period advice cannot satisfy `height_choice`, and height advice cannot
  satisfy `period_choice`.
- Existing period and height consultation still compile deterministically.
- Study advice retains the same underlying immutable records.
- Ready task identities retain the same exact consultation references.
- `PeriodChoice` and `HeightChoice` retain the same advice-backed basis.
- Checkpoint advice bytes remain unchanged.
- Study canonical bytes remain unchanged.
- Existing checkpoints replay into the same advice values without a second
  decoder shape.
- No compatibility alias for removed fields exists.
- Rust is untouched.

## Focused verification

Run only focused tests or exact nodes covering:

- exact period- and height-advice reference derivation;
- admission-returned versus derived reference validation;
- unchanged canonical advice and Study bytes;
- ordinary `DesignAdvice`;
- duplicate and wrong-type consultation rejection;
- period and height choice basis;
- compile and conduct with Authority-recorded advice;
- checkpoint advice-byte equality;
- checkpoint replay;
- frontier successor validation;
- the generic-science public surface.

Also run:

- local Pyright for touched Python scope;
- CSU for touched production files;
- `git diff --check`;
- `git diff -- rust`.

Do not run the complete science suite, complete architecture suite, Adviser,
Lumerical, canonical briefs, or Rust tests.

## Stop and report

Stop if canonical document identity differs from the Authority body reference,
if checkpoint advice bytes, Study bytes, or task identities would change, if a
valid metalens consultation cannot be expressed by its concrete advice type,
or if replay would require a registry or second checkpoint format.

## Do not add

Do not add `AdviceFact`, `AdmittedAdvice`, a second advice container, a
compatibility property, generic advice registry, schema registry, dynamic
decoder, checkpoint version, migration, advice admission field, advice
admission-state method, synthetic reference for ordinary advice, public advice
framework, workflow container, new aim, or Rust change.
