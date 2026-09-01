# Sharpen the MetaCraft design skill

Status: ready-for-human

Resolution: implementation, static gates, installed-profile tests, and Harness
preflight are complete. Real Harness acceptance remains incomplete: the first
Codex session was confined to its capsule but its exploratory command shapes
failed the strict audit and its dynamically formed conduct command used the
wrong option names before execution policy rejected it. Claude was not started
because the fixed cadence is Codex then Claude. The reusable Skill now fixes the
installed-root launcher and option shape while accepting caller-supplied literal
paths; the smoke prompt binds that shape to its three exact capsule paths. The
authorized final run formed that exact command but local execution policy
rejected it before MetaCraft ran, so real Harness acceptance remains incomplete.

Blocked by: 06

Parent: [map](../map.md) · [specification](../spec.md)

## Outcome

The repository Skill teaches Codex and Claude one short, complete conduct
cadence derived from the proven journey. It is easy to follow without becoming
a second implementation of MetaCraft.

## Implementation

Rewrite `skills/metacraft-design/SKILL.md` around the exact typed outcomes of
the command Interface, following the repository `writing-for-agents` skill for
the edit and its review. Preserve the existing principles—canonical inputs,
request-owned grounds, conservative grounded recommendation, exact answer,
same application root, and honest stopping—but make every outcome map to one
unambiguous action:

- `consultation_required`: inspect the exact request, obtain or form one legal
  answer, then repeat the same command with that answer;
- `waiting_studies`: stop unless the named external capability or evidence fact
  has demonstrably changed;
- `completed_results`: stop and report exact Result references;
- invalid/unsupported input: ask only for the unresolved user fact;
- `evidence_required`, unavailable execution, or unexpected fault: stop and
  report the exact next fact or capability.

The Skill must forbid algorithm selection, root substitution, invented
materials/candidates, repeated unchanged waits, result inference from `runs/`,
and silent repair. Keep it concise enough to remain salient in a Harness
context; link to domain docs rather than copying scientific policy.

## Acceptance

- Codex and Claude profile tests execute the same cadence and differ only in
  external transcript dialect.
- Each available real Codex and Claude executable completes one
  recorded-evidence smoke journey with a fresh Harness session between typed
  transitions. Missing executable or authentication is an explicit incomplete
  acceptance gate, never replaced by a synthetic transcript.
- Mutations that switch root, answer the wrong request, retry unchanged
  WaitingStudies, select FFT/CZT/ASM/VASM, or continue after completion are
  rejected by acceptance evidence.
- The Skill contains no provider, model, endpoint, credential, generic agent
  framework, or production test support.
- The Skill says that a stale pre-cutover root is historical evidence and that
  a fresh root—not an invented migration—is required for the current schema.
- Canonical skill discovery/install tests and the four recorded journey tests
  pass through a clean installed root.
- Writing-for-agents review, architecture no-provider/no-second-lifecycle
  gates, Pyright where applicable, Markdown links and diff gates pass.

## Guardrails

Do not add another Skill per Harness, embed solver policy, or turn the Skill
into a long copy of CONTEXT, ADRs, or command help.

## Evidence

- The canonical Skill is one concise `Anchor -> Conduct -> Consult -> Resume ->
  Stop` cadence. The Codex and Claude routers remain byte-identical,
  discovery-only pointers.
- `tests.harness_acceptance_runner --preflight` observed Codex CLI `0.147.0`,
  Claude Code `2.1.226`, and the installed MetaCraft launcher as available.
- The fixed `--resumable-smoke` road composes Codex then Claude, prepares a
  fresh session for each typed transition, and reuses the Ticket 06 recorded
  receipt-boundary driver. It has no profile selector or production support.
- Every attempted session now retains redacted stdout and stderr, return code,
  timeout truth, confinement/cadence audit, and one precise terminal status.
  The final smoke manifest is sealed even when a session is incomplete;
  unexpected implementation faults still raise after sealing rather than being
  relabelled as acceptance.
- The profile and session enter the manifest as `attempted` before execution or
  semantic assertions. A wrong transition, changed brief, invalid retained
  evidence, or invalid terminal outcome changes the profile to
  `implementation_fault`, retains the attempted session evidence, seals the
  manifest, and then raises the original fault.
- The acceptance-local cadence audit compares observed commands with before and
  after Authority snapshots. Mutation tests reject a foreign application root,
  an answer for the wrong request, an unchanged `waiting_studies` retry, a
  realization selector, and conduct after `completed_results`.
- The retained redacted Codex transcript is
  [`../acceptance/07-retry/transcripts/codex-01.jsonl`](../acceptance/07-retry/transcripts/codex-01.jsonl)
  and its strict audit is
  [`../acceptance/07-retry/audits/codex-01.json`](../acceptance/07-retry/audits/codex-01.json).
  There were no outside-capsule paths or writes. The session emitted no typed
  conduct outcome, so it is incomplete rather than accepted.
- The observed failure led to one bounded correction. The reusable Skill fixes
  `.\\metacraft.exe conduct --brief <brief> --application-root
  <application-root> --material-library <material-library>` and requires
  caller-supplied literal paths. Only the smoke prompt binds that command to
  `blind-brief.json`, `prepared-application-root`, and
  `reviewed-materials.toml`.
- The authorized final gate is sealed at
  [`../acceptance/07-final-20260813/resumable-smoke.json`](../acceptance/07-final-20260813/resumable-smoke.json).
  Codex session 1 returned normally without timeout, formed the exact literal
  command, and produced no invalid command, outside-capsule path, or write. The
  local execution policy rejected that command before MetaCraft ran; five
  retained Harness error events therefore made the strict audit
  `incomplete_policy_or_harness`. Fixed ordering left Claude unstarted and the
  manifest records `prior_profile_incomplete`. The redacted transcript and audit
  are retained beside that manifest.
- Focused Harness campaign/profile/Skill gates: `25 passed`; clean installed cadence and
  retained-material gates: `9 passed`; command/cadence/material regression
  gates: `10 passed`. Pyright reports zero errors for both acceptance support
  modules; CSU and `git diff --check` pass.
