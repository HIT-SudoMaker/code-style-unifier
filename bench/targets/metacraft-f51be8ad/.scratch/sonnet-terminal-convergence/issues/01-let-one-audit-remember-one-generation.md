# Let one audit remember one generation

Type: implementation

Status: resolved (2026-07-29)

Blocked by: nothing.

## Outcome

One Rust writer lifetime establishes one verified authority state. No
interleaving writer can bind an audited old view to a newly observed
generation, and no observation failure leaves stale proof available.

## Scope

1. Add a deterministic failing regression that interleaves two Authority
   handles between audit and generation capture.
2. Hold the existing workspace writer across complete audit, generation
   capture, and verified-state replacement for open, refresh, and explicit
   check.
3. Keep the writer held across the already-atomic local decision path.
4. Make generation observation return an exact failure. Do not discard file
   metadata errors through `ok()` or preserve old verified state after an
   error.
5. Forget verified state on any failed audit, failed generation observation,
   lock failure, or commit failure.
6. Preserve the measured stable-view common path without scanning historical
   rows or hashing the complete database.
7. Replace implementation-history comments with invariant language.
8. Amend ADR 0012 so its guarantee matches the accepted threat model:
   cooperative writers and observable durable changes invalidate proof;
   metadata-preserving adversarial raw-byte tamper belongs to explicit check,
   not stable view.

## Acceptance

- An external writer cannot commit between audit and the generation paired
  with that audit.
- Stable view returns only a state established by one audit or one verified
  local commit.
- A generation observation failure returns no stale view and leaves the
  Authority unverified.
- Explicit check always performs complete audit.
- Stable view at 3,004 events retains at least the prior twenty-times
  improvement over the historical baseline.
- Canonical authority bytes, ledger format, storage layout, extension surface,
  four verbs, and error strings remain unchanged.
- Rust contains no scientific meaning.

## Focused tests

- deterministic two-handle audit/capture interleaving;
- metadata observation failure;
- audit failure after a previously verified state;
- local commit success and failure;
- external commit followed by exactly one refresh;
- 304-, 1,504-, and 3,004-event release diagnostics;
- canonical interface and wire fixtures.

## Verification

- `cargo fmt --check`;
- `cargo clippy --all-targets -- -D warnings`;
- `cargo test --all-targets`;
- release scale diagnostics;
- Python extension import smoke with the repository interpreter;
- source-manifest regeneration and verification;
- touched-file CSU;
- fixed-range `git diff --check`.

After this ticket, production Rust is frozen.

## Stop and report

Stop before adding a public verb, a second Authority, a persistent cache
service, a database hash on each view, a storage migration, new error wording,
or any scientific Rust type.

## Do not add

Do not add Merkle storage, a background integrity worker, a benchmark
framework, a public verified-state value, versioned code names, or compatibility
logic.

## Resolution

Audit, generation capture, and verified-state replacement now share one writer
lifetime. Generation observation failure forgets the private proof, and the
scale diagnostic is split into independently runnable event counts.

Release diagnostics on the reference workstation:

| Events | Open audit | Explicit check | Stable view | 16 stable views |
| ---: | ---: | ---: | ---: | ---: |
| 304 | 1.660 s | 1.574 s | 0.873 ms | 12.53 ms |
| 1,504 | 36.60 s | 36.20 s | 2.608 ms | 34.76 ms |
| 3,004 | 155.81 s | 148.96 s | 8.524 ms | 72.88 ms |

Every stable view performed zero complete audits and read zero historical rows.
At 3,004 events it remained roughly 18,000 times faster than the explicit
complete audit.
