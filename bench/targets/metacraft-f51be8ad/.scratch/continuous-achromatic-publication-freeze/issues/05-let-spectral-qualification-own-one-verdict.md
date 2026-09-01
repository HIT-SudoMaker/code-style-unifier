# 05 - Let spectral qualification own one verdict

Status: ready-for-agent

Assignee: unassigned

Label: `ready-for-agent`

Blocked by: [04 - Freeze one traceable spectral study specification](04-freeze-the-traceable-spectral-study-specification.md)

Parent: [Publication freeze](../spec.md)

## Work

Make one versioned qualification profile and one
`SpectralLibraryQualification` the sole owners of reference screening,
full-band phase linearity, blind-holdout residual, converted/leakage power,
reference-phase coverage, relative-delay span, evidence completeness, eligible
geometry, candidate, and physical-refusal decisions.

Remove repeated threshold calculations from cell screen, qualification, and
aperture assignment. Assignment consumes the qualification's eligible geometry
set and verdict only. Preserve the distinction among missing evidence,
numerical incompletion, unavailable capability, and complete physical refusal.

Review and cite every provisional numeric threshold before freezing the profile.
Changing one threshold changes the profile identity and downstream evidence
closure.

## Acceptance

- Complete candidate, conversion refusal, linearity/holdout refusal,
  phase-coverage refusal, delay-span refusal, missing, and numerical-incomplete
  matrices close through the qualification Interface.
- Assignment contains no power, R-squared, residual, phase-gap, or delay-span
  constants and rejects any non-candidate qualification.
- Eligible geometry identities round-trip exactly and agree with their
  assessments.
- Tests prove that a TiO2 candidate and an explicit alternative are judged by
  the same profile.
- Threshold changes cannot leave screen, qualification, and assignment with
  divergent behavior.

## Non-goals

No learned scorer, weighted opaque merit function, or relaxation of a failed
Brief.
