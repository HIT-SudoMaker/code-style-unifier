# 03 — Let four blind briefs close at WaitingStudies

**Parent spec:** [Four-brief grounded baseline](../spec.md)

**Decision source:** [Let four briefs stop before periodic evidence](../../four-brief-grounding/decisions/08-let-four-briefs-stop-before-periodic-evidence.md)

**Status:** resolved (2026-08-09)

**Blocked by:** Ticket 02

## What to change

Deepen only the existing external acceptance inspector. Beside its current
period/height advice, selected values, current question, and canonical answer
facts, restore the admitted `MaterialBinding` through Authority and report:
material family, exact native name, sampled wavelength and optical constants,
provenance, binding/sample references, and source identities. Do not add a
production report, public schema, benchmark-specific conductor, or material
lookup path.

First add deterministic contract tests that drive every catalogue case through
the existing material -> period -> height cadence with canonical test-side
answers and finish at `WaitingStudies`. The fixtures may choose only candidates
present in each emitted request and must not import or inspect
`PublishedReference` while answering. They prove state, replay, and inspection;
they do not claim that a canned answer measures harness judgment.

Then create four clean brief-stage capsules using the current external harness
contract. Expose only the canonical brief, admitted material/domain evidence,
consultation request, and grounds. Do not expose the case reference, paper
period/height, or post-hoc comparison. Submit one source-grounded period answer
and then one source-grounded height answer per case; retain exact citations,
reasons, decisive grounds, answers, and Authority documents. No retry-until-
green loop is allowed. An invalid answer remains an observable failure to fix
at its owning contract, not a reason to bypass validation.

After all four capsules are sealed, write one post-hoc Markdown comparison that
shows the selected material, period, height, order regime, fabrication range,
cautions, and distance from source-reported period/height where those facts are
comparable. Paper proximity is diagnostic only. Explain large differences;
never silently adjust the blind answer to match a paper.

## Acceptance

For McClung, Yang, Arbabi, and Khorasaninejad independently:

- `outcome == WaitingStudies` and `current_question is None`;
- one exact material binding, one period advice/choice, and one height
  advice/choice are visible and Authority-restorable;
- both retained answer documents are canonical and request-linked;
- the period lies on the 10 nm grid strictly below the sampling ceiling;
- order regime and all multi-order cautions remain visible;
- the height belongs to its post-period fabrication domain;
- no periodic response, cell library, aperture, field, focus, Result, or paper-
  efficiency acceptance exists.

The inspection output must distinguish scientific completion of this phase
from downstream study readiness without inventing `CompletedBrief` or another
state type.

## Verification

Run focused inspector, command, conduct, consultation, replay, material, and
four-case tests. Reinspect every retained capsule read-only from a fresh
process. Record any harness/network dependency honestly; Lumerical execution is
forbidden.

## Stop condition

Stop at `WaitingStudies`. Do not open a periodic-response port, sweep a cell,
form an aperture, calculate a field, compare focusing efficiency, or add an AI
transport abstraction.

## Comments

- 2026-08-09: The deterministic contract slice is implemented. All four
  canonical briefs traverse emitted period and height candidates to
  `WaitingStudies`; their canonical answers, Authority replay, fresh-process
  inspection, exact registered material names, and explicitly non-physical
  fixture samples are covered by focused tests. This does not create retained
  scientific capsules or validate harness judgment. The ticket remains open
  for the one-shot live campaign and, in particular, a qualified physical
  material sample at McClung's 550 nm wavelength. No network, harness, or
  Lumerical session was run for this slice.
- 2026-08-09: Existing retained Authority evidence physically grounds the
  Yang/Arbabi 1550 nm and Khorasaninejad 532 nm material pairs. McClung lacks
  the corresponding 550 nm Luke-SiN/Palik-silica sample. Completing the live
  scientific capsule now requires owner authorization for one hidden,
  read-only material-verification activity with no project load, geometry,
  save, or solve; otherwise McClung must remain `evidence_required` and this
  ticket cannot honestly close under the approved specification.
- 2026-08-09: The owner approved exactly that bounded 550 nm read-only
  material-verification activity. It may inspect the two registered native
  materials and retain their evidence, but may not load a project, create
  geometry, save, sweep, or solve.
- 2026-08-09: The first authorized session completed all read-only material
  calls and closed normally, but its post-session retention failed before
  sample admission because required license fields were omitted from the
  operator configuration. The incomplete root is retained and explicitly
  unusable; no numerical material fact survived. An offline-guarded retry is
  now green and also includes the separately required 1550 nm silicon-dioxide
  registration for Yang. Running that combined retry requires renewed owner
  authorization.
- 2026-08-09: The Yang pair exposed a pre-existing `serde_jcs 0.1.0`
  prefix-key ordering defect at the Rust Authority boundary. A read-only
  differential over 688 retained objects and 1,209 JSON-bearing values found
  zero byte changes under the standards-correct replacement. Fixing the bug
  still requires an explicit narrow unfreeze of the Rust canonicalizer
  dependency; Python will not imitate the non-RFC ordering.
- 2026-08-09: The owner approved both bounded prerequisites: replace the
  defective Rust canonicalizer with a standards-correct implementation under
  regression and zero-difference corpus gates, then run one combined read-only
  material retry for McClung at 550 nm and Yang at 1550 nm under the existing
  zero project/geometry/save/sweep/solve boundary.
- 2026-08-09: The combined material activity succeeded exactly once, and all
  four retained receipts now replay byte-exactly into fresh acceptance
  Authorities. The approved Codex-only blind campaign then started exactly four
  sessions, one per neutral slot, with zero retries. Every session terminated
  before the first answer because the Codex execution policy rejected the
  bundled local `metacraft.exe`; all four capsules therefore remain honestly at
  `ConsultationRequired(period)` with physical material evidence intact, no
  answers, and no downstream evidence. The complete failed campaign is sealed
  under `../acceptance/03/`. Ticket acceptance is not met and requires human
  action on the harness execution policy before any separately authorized new
  campaign; the retained four attempts must not be overwritten or retried.
- 2026-08-09: A separately approved, single-variable Codex executable smoke
  made the non-interactive approval policy explicit as
  `--ask-for-approval never` while preserving `workspace-write`, disabled
  network access, the capsule cwd, one session, and zero retries. One
  pre-session launcher attempt first exposed and then regression-locked a
  relative `-C` path defect; it produced no `thread.started` event and is
  retained separately without being counted as a Codex session. The corrected
  smoke started exactly one Codex 0.146.0 session and attempted the exact
  capsule-local `metacraft.exe conduct` command once. The router still declined
  that command before process start with `blocked by policy`. This falsifies
  the missing-headless-approval hypothesis and confirms the remaining boundary
  is execution of a workspace-local Windows PE under the Codex
  `workspace-write` policy. The smoke is sealed under
  `../acceptance/03-executable-smoke-20260809-02/`; all 19 declared artifact
  hashes match. Do not run another session or the four-case campaign until the
  owner approves a different single-variable executable-placement experiment.
- 2026-08-09: The owner clarified that Codex and Claude Code are ordinary
  callers of the installed command, not nested processes that MetaCraft must
  launch and confine. The active Codex agent therefore followed the canonical
  skill and called installed `metacraft` directly against fresh copies of the
  four material-grounded application roots. All four reached `WaitingStudies`
  with two canonical answers, no current consultation, preserved multi-order
  cautions, and no downstream solve. The selected period/height pairs were
  McClung 430/650 nm, Yang 1500/800 nm, Arbabi 800/900 nm, and
  Khorasaninejad 320/600 nm. Fresh-process inspection passed. The retained
  result is `../acceptance/03-direct-codex/result.md`. Yang's 800 nm height is
  an explicit scientific-domain mismatch against the 340 nm reference because
  the emitted legal domain contains only 800, 850, and 900 nm; it is not a
  harness failure. This direct caller result supersedes the nested-harness
  acceptance interpretation for this ticket.
