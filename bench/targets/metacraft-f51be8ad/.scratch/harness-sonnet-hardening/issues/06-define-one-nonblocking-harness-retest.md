# Define one non-blocking harness retest

**Parent map:** [Harness-native Sonnet hardening](../map.md)

**Label:** `wayfinder:grilling`

**Assignee:** Codex

**Status:** resolved (2026-08-09)

**Blocked by:** [Let two real harness profiles meet one acceptance seam](05-let-two-real-harness-profiles-meet-one-acceptance-seam.md)

## Question

What exact preflight, attempt count, partial-availability rule, confinement
policy, artifact inventory, and classification should govern one post-hardening
Codex/Claude Code retest so that it can add usability evidence without becoming
a release gate or a rerun-until-green loop?

The decision must say what happens when only one harness passes preflight,
whether a failed preflight consumes an attempt, how old and new evidence remain
distinct, and which outcomes may be claimed.

## Resolution

Run one bounded retest campaign through the closed acceptance-profile union
from Ticket 05. The campaign always plans the same two profiles across the
same four blind slots, but it starts a real session only for a profile whose
mandatory preflight is available:

```text
planned cells:          2 profiles x 4 blind slots = 8
eligible cells:         available profiles x 4 blind slots = 0, 4, or 8
started sessions:       actual external process starts, from 0 through eligible cells
session attempts/cell:  at most 1
session reruns:         0
```

The campaign is evidence, not a release gate. A complete cadence may add
bounded usability evidence; unavailable, failed, timed-out, incomplete, or
audit-rejected observations are equally terminal evidence for this campaign.
None prevents the hardening movement from closing, and none authorizes a
second attempt.

### Preflight and availability

The shared runner calls `CodexAcceptanceProfile.preflight` and
`ClaudeAcceptanceProfile.preflight` exactly once each before creating the
evidence root and before any paid or stateful harness session. It collects both
results even when the first profile is unavailable; one profile's failure must
not hide the other's facts.

Each profile continues to own its executable, version/help commands, and
required native flags. The shared runner owns the installed `metacraft.exe`
launcher prerequisite and the aggregate availability decision. An available
profile has a resolved executable, successful version and help captures, no
missing required flag, and the shared launcher available. A missing
executable, failed version/help capture, missing flag, or missing launcher is
recorded directly as preflight unavailability. It is not a transcript
violation, process result, scientific outcome, or inferred authentication
failure. Preflight must not open a consultation merely to probe credentials.

The standalone `--preflight` command remains a read-only diagnostic. It emits
facts for both concrete profiles, creates no evidence root, and consumes no
retest campaign. The mandatory preflight inside an explicitly authorized
`--run` is different: once evaluated, it consumes that profile's one campaign
opportunity even when unavailable. Its four planned cells become
`not_started_preflight`, its started-session count remains zero, and the same
campaign may not retry that profile after configuration, authentication, CLI,
or network conditions change.

This is the precise meaning of a failed preflight consuming an attempt: it
consumes the one profile-level matrix opportunity, not four fictitious harness
sessions. It therefore prevents preflight-until-green while keeping actual
external-session accounting true.

### Partial availability and exact once

After both preflights finish, the runner claims the supplied absent evidence
root exactly once. It writes both availability records and then follows the
fixed slot/profile order from Ticket 05:

- if both profiles are available, start all eight planned cells once;
- if only one is available, start that profile's four cells once and retain
  the other profile's four `not_started_preflight` plan entries;
- if neither is available, start no session and still seal the campaign as a
  zero-session availability record.

An unavailable profile is never substituted by the available profile, and a
missing cell never receives an empty transcript, synthetic process exit, or
synthetic scientific outcome. For an eligible cell, crossing the private
`ExecuteHarness` callable is the session start and consumes that cell's only
session attempt. Nonzero exit, timeout, incomplete cadence, rejected audit, or
unfavorable advice is final; the runner does not retry, resume, repair, amend,
or ask the profile to choose another case.

Setup collisions, missing canonical skill material, profile/parser
implementation faults, redaction/audit-parity faults, and sealing faults keep
the direct ownership assigned by Ticket 05. They are runner failures, not
external harness outcomes. A root left by such a fault is visibly unsealed,
must not support claims, and must never be resumed or reused. If any real
session already started, rerunning the campaign under another root would
violate this ticket rather than repair it.

### Fresh evidence lane

The command remains the Ticket 03 Interface:

```text
tests/harness_acceptance_runner.py --preflight
tests/harness_acceptance_runner.py --run --evidence-root <absent-directory>
```

There is no default to, overwrite of, amendment to, or compatibility path for
`.scratch/harness-native-consultation/acceptance/07/`. The retest root is a new
sibling lane supplied explicitly and absent at entry. Old and new manifests,
transcripts, outcomes, and reports remain independently named and hashed; the
new lane does not copy old artifacts or present before/after identities as one
continuous run.

### Confinement policy

Ticket 05's profiles normalize their native event dialects through
`observe`; one shared audit then applies the same policy to both profiles.
Confinement fails closed on any malformed, missing, unknown, case-changed, or
incomplete event shape; rejected tool or event; invalid outer command or
non-canonical `metacraft conduct` grammar; path outside the resolved capsule;
or write target other than `period-answer.json` or `height-answer.json`.

The runner audits the raw observation, redacts the transcript and stderr, asks
the same concrete profile to observe the redacted transcript, and requires
the retained audit decision and normalized violations to equal the raw audit.
It retains sanitized machine roots, authentication values, and session
identifiers only through placeholders. A confinement rejection is retained
without retry and outranks consultation progress for claims: process and
violation facts remain reportable, but answer, advice, choice, and cadence
content from that cell is not accepted evidence.

### Artifact inventory and counting contract

Every successfully sealed fresh lane contains:

- `preflight.json`, with one record for each literal profile name, captured
  version when available, missing flags or direct failure reason, shared
  launcher fact, availability, and the profile-level opportunity consumed;
- `transcripts/`, `stderr/`, `audits/`, and `outcomes/`, with one artifact of
  each applicable kind for every actually started session;
- `answers/`, containing only canonical period or height answer bytes copied
  from a started cell and named by run identity;
- eight manifest plan entries in fixed 2x4 order, including profile, blind
  slot, eligibility, `not_started_preflight` reason when applicable, and the
  started-session fact, without counterfeit per-cell files;
- `blind-manifest.json`, written before benchmark context is revealed, hashing
  the preflight record and every retained blind artifact and recording
  `planned_cell_count: 8`, `eligible_cell_count`, `started_session_count`,
  terminal process counts, and `session_rerun_count: 0`;
- `post-hoc/slot-01.md` through `slot-04.md` plus `post-hoc/matrix.md`, showing
  unavailable profiles explicitly and keeping reviewed published facts
  separate from sealed harness advice; and
- final `sealed-manifest.json`, hashing `blind-manifest.json` and all five
  post-hoc reports so the complete fresh lane can be verified read-only.

`planned_cell_count` must never be inferred from the number of outcomes, and
`started_session_count` must never be reported as eight merely because eight
cells were planned. A process that starts and then exits nonzero or times out
still counts as one started session. A preflight-unavailable cell, setup fault
before execution, or absent synthetic file does not.

The two-manifest layout preserves the current blind-before-reveal ordering
without leaving reports outside the final artifact inventory. Neither file is
an amendment or repair record: `blind-manifest.json` seals the blind facts
once, and `sealed-manifest.json` closes the immutable lane once after reports
are generated.

### Multi-axis classification

Do not collapse the campaign into `pass` or `fail`. Retain orthogonal axes so
availability, process behavior, confinement, inspection, and consultation
position cannot overwrite one another:

| Scope | Axis | Closed values |
| --- | --- | --- |
| Profile | `availability` | `available`, `unavailable_preflight` |
| Planned cell | `attempt` | `not_started_preflight`, `completed`, `failed`, `timed_out` |
| Started cell | `audit` | `accepted`, `rejected` |
| Started cell | `inspection` | `completed`, `failed` |
| Accepted, inspected cell | `consultation` | `process_failed_before_advice`, `process_failed_after_canonical_answer`, `process_failed_after_period_advice`, `process_failed_after_height_advice`, `incomplete_without_advice`, `advice_retained_through_period`, `advice_retained_through_height`, `consultation_cadence_complete` |

An unstarted cell has no audit, inspection, or consultation value. An
audit-rejected cell has process and audit values but no accepted consultation
classification. An inspection failure remains `inspection: failed`; it must
not degrade into `incomplete_without_advice`. A nonzero exit or timeout keeps
the deepest independently inspected canonical answer/advice position, while a
zero exit alone never means cadence complete. Campaign reporting gives counts
on these axes and per-profile/per-slot facts; it computes no winner, average,
threshold, or overall acceptance state.

### Allowed claims

The sealed lane may claim only what its own artifacts establish:

- which concrete profile and captured CLI version was available at that
  preflight, and why another profile was unavailable;
- eight planned cells versus the exact number of eligible and actually
  started sessions;
- each started process's exit/timeout fact, confinement result, inspection
  result, accepted canonical answers, retained advice/choices, and deepest
  consultation position;
- for a confined, inspected cell classified
  `consultation_cadence_complete`, that the named profile demonstrated the
  complete local consultation cadence for that blind slot under the sealed
  version, prompt, capsule, and grounds; and
- if all four cells for one profile meet that condition, the same bounded
  four-case usability statement for that profile, without generalizing beyond
  the matrix.

Preflight unavailability supports only an environment/profile-availability
claim, not a claim that the harness attempted and failed the consultation.
Confinement rejection supports violation and process claims only. An
incomplete or failed cell may be described at its honest failure position but
does not erase retained progress from another cell or profile.

The lane may not claim release readiness, a hardening success condition,
scientific correctness, physical performance, paper reproduction, solver or
`Result` qualification, agreement with published values, harness parity,
superiority, interchangeability, cross-version reliability, or a conclusion
about an unavailable profile. Post-hoc reports must not turn reviewed facts
into comparisons, deltas, thresholds, or a winner, and one profile's result
must never be averaged with or substituted for the other's.

### Test contract

Use Ticket 05's `RecordedHarnessExecution` Adapter, never a live harness, to
prove both-available, Codex-only, Claude-only, and neither-available campaigns.
Tests must assert the fixed eight-cell plan, 0/4/8 eligibility, exact started
counts, no execution for unavailable profiles, one execution per eligible
cell, no retry after every terminal class, no counterfeit artifacts, raw and
redacted audit parity, multi-axis classifications, both manifests and all
hashes, explicit partial post-hoc reporting, absent-root enforcement, and
rejection of reuse or repair modes. Retained `acceptance/07` verification
remains read-only and byte-identical.

## Comments

Ticket 05 supplies the concrete ownership needed to close this decision:
`CodexAcceptanceProfile` and `ClaudeAcceptanceProfile` own native preflight,
preparation, and observation, while the shared runner owns the matrix,
partial-availability policy, execution count, confinement, redaction,
inspection, classification, sealing, and claims. This ticket narrowly refines
Ticket 05's fail-closed preflight aggregation: direct profile failures are
still direct and both preflights still precede root creation, but one
unavailable profile no longer suppresses the available profile's bounded
four-cell evidence.

Repository evidence also explains why planned and started counts must be
separate. The current runner hard-codes eight runs, fails preflight globally,
and equates retained run count with completed loop records; the retained
`acceptance/07` lane contains eight started sessions even though none retained
advice. Those historical facts remain useful provenance but are not the
partial-availability contract for this fresh lane.

This ticket is a planning decision only. No real harness was run, and no
runner, profile, test, retained artifact, map, index, or other ticket was
changed while resolving it. Implementation must use recorded events for
verification and run `git diff --check`; the later live campaign requires
separate explicit authorization and must use an absent evidence root.

**Map gist:** Run one fresh, non-blocking 2x4 retest campaign with per-profile
preflight availability, exact-once eligible sessions, truthful planned versus
started counts, fail-closed confinement, fully sealed partial evidence, and
strictly bounded usability claims.
