# 06 - Make the compiled scientific path observable

Status: ready-for-agent

Assignee: unassigned

Label: `ready-for-agent`

Blocked by:

- [05 - Let spectral qualification own one verdict](05-let-spectral-qualification-own-one-verdict.md)
- [11 - Restore one achromatic closure in one place](11-restore-one-achromatic-closure-in-one-place.md)

Parent: [Publication freeze](../spec.md)

## Work

Deepen the existing read-only run projection so a reader can inspect exact
references for Brief, Design assessment, Route/Proof, ready/completed Tasks,
admitted Evidence, qualification, fixed aperture, Result, and typed stop.

The projection remains a view of Authority truth and never becomes recovery
state. Preserve provider-free advice semantics: an unanswered consultation
projects `advice == []` and `ConsultationRequired`; only validated, admitted
advice retained in the Study may appear later. Advice remains untrusted and is
not scientific evidence.

Keep `src/metacraft/advice/` and `tests/advice/` absent from tracked source. Do
not read or package their local `__pycache__` residue.

## Acceptance

- One completed continuous run and every typed stop produce stable,
  content-addressed projections with exact Authority references.
- Projection deletion or corruption cannot affect conduct, resume, conclude, or
  replay.
- Missing advice stays empty and waiting; a stale or invented answer cannot
  appear in the projection or mutate Authority.
- Tests assert through the projection Interface and public conduct/replay seams,
  not private compiler functions.
- Architecture ratchets reject restoration of the retired provider-owned advice
  package and any projection-as-recovery import.

## Non-goals

No dashboard, mutable workflow state, event bus, provider transport, or second
application root.
