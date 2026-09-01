# 01 — Let authority remember what it has proved

Type: implementation

Status: resolved (2026-07-29)

Blocked by: nothing.

## Outcome

The Rust authority performs one complete audit before it trusts a workspace,
then reuses that exact proof on the stable common path. Its public Interface
remains one `Authority` with `check`, `view`, `fetch`, and `decide`.

## Scope

1. Start with a failing public-seam regression that demonstrates repeated
   stable `view` or `decide` work walking historical rows.
2. Record a new ADR for the separation between explicit full audit and the
   verified common path.
3. Give each open Authority one private verified state containing the durable
   workspace generation, current revision, and replayed view established by a
   successful complete audit.
4. Make open and explicit `check` perform the existing complete recovery and
   integrity audit before remembering any state.
5. Let stable `view` and `decide` compare a cheap durable identity with the
   remembered generation and reuse the verified view only while they agree.
6. Force one complete re-audit after another Authority, another process,
   database replacement, head change, or durable generation change.
7. After a successful local atomic commit, advance the verified revision and
   view together. Rejection, stale revision, lock failure, and commit failure
   must not advance them.
8. Preserve `fetch` as exact object verification. Do not make the verified
   state a substitute for content-hash checking.
9. Keep the frozen ledger schema, protocol bytes, proposal meanings, finding
   meanings, recovery semantics, and Python extension surface unchanged.
10. Move the largest scale diagnostic out of a production Interface module
    when private test access can do so without weakening the seam.

## Acceptance

- Opening an Authority performs a complete audit and answers from the audited
  view.
- Explicit `check` always performs another complete audit.
- Repeated stable `view` and `decide` perform no historical-row scan.
- A successful local decision updates durable truth and verified state as one
  logical transition.
- An external generation change invalidates the proof and triggers exactly
  one complete refresh before an answer or decision.
- A failed refresh returns no stale view and leaves the handle unverified.
- Restart reconstructs truth from durable storage rather than trusting
  process memory.
- Projection, event, marker, head, object, and database replacement faults
  still fail closed.
- Concurrent decisions at one revision still admit at most one winner.
- Canonical wire fixtures remain byte-stable.
- Rust contains no scientific, solver, material, phase, brief, or result
  meaning.
- The public native Interface remains exactly one class and four verbs.

## Focused tests

- count complete audits and historical-row reads across open, stable view,
  stable decide, explicit check, local commit, external commit, and restart;
- interrupt or fail each commit boundary and prove that remembered truth never
  outruns durable truth;
- replace or mutate each governed durable identity and prove one fail-closed
  refresh;
- race two Authority handles at one revision;
- fetch valid and corrupt objects before and after a verified-state refresh;
- exercise valid authority histories at 304, 1,504, and 3,004 events.

## Verification

- Rust formatting;
- Clippy on all targets with warnings denied;
- all Rust tests;
- release build;
- Python import smoke with the repository interpreter;
- focused architecture tests for the frozen native seam;
- source-manifest regeneration and verification;
- `git diff --check`.

Record the 304-, 1,504-, and 3,004-event release diagnostics. On the same
reference workstation, stable `view` at 3,004 events should be at least twenty
times faster than the recorded approximately 149-second baseline. Treat this
as a human diagnostic, not a cross-machine CI timeout.

## Documentation

The ADR must explain:

- why complete audit remains explicit and exact;
- why the stable common path may reuse a verified proof;
- what invalidates that proof;
- why a persistent projection tree is deferred;
- why no protocol or storage migration is required.

## Stop and report

Stop before implementation widens a public verb, alters canonical bytes,
changes the ledger schema, weakens content verification, introduces science,
or requires a data migration.

## Do not add

Do not add a Merkle or Patricia tree, content-addressed projection, delta
ledger, background integrity service, second authority class, diagnostic
public verb, compatibility protocol, version name, or benchmark framework.

## Resolution

Commit `f3efe39` introduced one private verified authority state while
preserving the four public verbs, wire bytes, storage, and explicit complete
audit. The integrated baseline remained green through `ca90c27`.
