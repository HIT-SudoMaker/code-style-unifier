# 03 - Let height answer only after period

**What to build:** Extend the grounded consultation round trip to height while
preserving the exact period-before-height dependency and the different physics
of propagation and geometric phase.

**Blocked by:** 02 - Let period advice complete one grounded round trip.

**Status:** resolved (2026-08-09)

- [x] Form a height ConsultationRequest only from an admitted HeightDomain whose
      exact PeriodChoice is present. A propagation request also carries the
      exact admitted PhaseEnvelope; a geometric request forbids that envelope.
- [x] Present finite legal heights, fabrication constraints, lateral candidate
      counts, cautions, and forecast limitations without presenting an
      estimate as evidence or a verdict.
- [x] Reuse the closed ConsultationAnswer contract without adding a height-only
      status convention or callback method hierarchy.
- [x] Validate one recommended height against the exact domain, period,
      mechanism, envelope applicability, cited grounds, and research mode
      before forming HeightAdvice.
- [x] Cut HeightAdvice once to the provider-free scientific schema and remove
      every transport and synthetic field without an old-schema reader.
- [x] Use the exact document identifiers
      `metacraft.science.metalens.height_consultation_request`,
      `metacraft.science.consultation_answer`, and
      `metacraft.science.metalens.height_advice`; retire
      `metacraft.advice.height` without an alias.
- [x] Preserve propagation-phase envelope rules, geometric Jones-response
      requirements, aspect limit, dimension step, candidate formation, choice
      tie-break, planner input, and all existing evidence thresholds.
- [x] Prove EvidenceRequired leaves one honest waiting Study and cannot create
      HeightChoice, cell-library work, orientation work, or a planner task.
- [x] Update the height/advice portions of `CONTEXT.md`, `DESIGN.md`, and
      `SCIENCE.md` in the same change as code and tests.

## Verification boundary

Verify both control strategies through exact request bytes, answer validation,
advice documents, replay, and choice outcomes. Period advice tests remain
unchanged except for the shared provider-free contract. Run no harness,
network, Native solver, or benchmark comparison.

## Comments

Ticket 08's first full deterministic seal attempt found two pointwise
propagation fixtures that submit a fixed 600 nm height which the exact request
marks `height_consultation_candidate_ruled_out`. The failures surface from
`fixture_height_advice` as `height_consultation_answer_invalid`. Ticket 08
changed no height rule or fixture and retains the failed attempt for the
closure record.

Owner diagnosis confirmed that production rejection is correct: for the stale
`200 nm` propagation fixture, the exact HeightDomain contains only `600 nm`,
and its PhaseEnvelope rules that sole height out for all 8/12/16-level goals.
No alternate legal height exists, so validation was not relaxed. The shared
height fixture now chooses the nearest legal candidate that the exact envelope
does not rule out and carries that selected value through the remaining Result
DAG. The two replay/caution callers, which assert no period value, now use the
legal `240 nm` high-NA propagation fixture; their geometric branch retains
`200 nm`. Production physics, benchmark facts, and result intent are unchanged.
