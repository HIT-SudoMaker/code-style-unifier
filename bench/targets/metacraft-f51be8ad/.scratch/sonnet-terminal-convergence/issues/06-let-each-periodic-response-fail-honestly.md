# Let each periodic response fail honestly

Type: implementation

Status: resolved (2026-07-29)

Blocked by:
[Let field evidence hide its storage](04-let-field-evidence-hide-its-storage.md)
and
[Let one frontier return one science](05-let-one-frontier-return-one-science.md).

## Outcome

Periodic transmission and polarization qualifications prove only their own
observations. Expected product absence remains exact data; implementation
drift is never disguised as an unavailable capability.

## Scope

1. Add failing fake-product tests that distinguish scientific failure,
   expected native absence, malformed output, and programming error.
2. Keep the two canonical capabilities:
   - `periodic_transmission_response`;
   - `periodic_polarization_response`.
3. Run independent fixtures and preserve sibling cleanup even when one fails.
4. Require exactly two distinct polarization input bases and validate both
   output relationships.
5. Let scientific non-finite, insufficient, or non-establishing output return
   capability false.
6. Remove broad exception-to-false and exception-to-Finding translations.
7. Translate only product-owned external failures at the native adapter seam
   into the existing typed outcomes.
8. Before a Study exists, surface exact typed preflight absence rather than
   returning opaque `None`.
9. During an existing branch, admit one diagnostic document, attach its
   reference to the Finding, and return an honest waiting Study for expected
   product loss.
10. Preserve exact closure of sessions, workers, permits, and lanes.
11. Reject duplicate binding capabilities and repair the corresponding
    architecture ratchet with an exact importer allowlist.

## Acceptance

- One polarization basis cannot establish polarization capability.
- Transmission and polarization capability outcomes remain independent.
- `KeyError`, invariant `RuntimeError`, malformed internal shape, and protocol
  drift reach the caller.
- Expected product absence preserves its exact typed reason.
- A branch-level expected absence has one admitted diagnostic reference.
- No conduct code classifies exception strings.
- Every session, permit, worker, and lane closes on success and failure.
- No live solver starts during tests.

## Focused tests

- fake transmission success/failure;
- fake x/y polarization success and missing/duplicate basis;
- non-finite response;
- typed product absence before and during Study;
- injected programming and invariant failures;
- sibling fixture attempt and cleanup;
- duplicate capability binding;
- exact typed-outcome import ratchet.

## Verification

- focused fake-solver, qualification, application, conduct, and architecture
  tests;
- Pyright;
- touched-file CSU;
- production Rust diff is empty;
- fixed-range `git diff --check`.

## Stop and report

Stop before enabling a live marker, changing physical thresholds or templates,
renaming capabilities, adding retries, or touching Rust.

## Do not add

Do not add a new exception hierarchy, string classifier, fallback capability,
solver registry, health service, retry database, compatibility alias, or live
fixture execution.

## Resolution

Periodic qualification now attempts transmission and polarization as
independent siblings, closes their shared work life on every outcome, and
requires exactly the `x` and `y` input bases before polarization can be
established. Finite but non-establishing science returns capability false;
malformed output, invariant failure, and programming drift raise after sibling
attempt and cleanup.

The native Adapter preserves explicit product startup and channel absence as
`LumericalUnavailable`. Dispatch forms `LumericalObservationFailed` only when
every gathered leaf is that typed absence; mixed or implementation failures
remain direct. Preflight no longer converts absence to `None`. A live branch
admits one exact diagnostic, attaches its reference to one capability Finding,
and recompiles as an honest waiting Study.

Bindings reject duplicate capabilities, and the architecture ratchet names
the exact importers of both typed outcomes. Verification completed with 146
focused fake-product, qualification, dispatch, application, conduct,
lifecycle, compiler, and architecture tests; project Pyright at zero errors
and warnings; ten touched production files at zero blocking CSU findings; an
empty production Rust diff; and a clean fixed-range diff check. No live solver
or scientific template was changed.

Review closure hardens the remaining runtime seams without widening the
design. Native workers now speak exactly one of three non-overlapping
envelopes: success, typed unavailability, or implementation failure. Startup
EOF and operating-system channel loss retain `LumericalUnavailable`; missing
license utilities and exhausted seats retain their exact product-owned
reasons. Session and startup cleanup attempt every owned resource, preserve
the primary outcome, and attach secondary failures as diagnostics.

`PeriodicResponseProof` now accepts exact booleans only, and qualification
requires that exact value rather than a look-alike. The importer ratchet
freezes source module, symbol, and importer together and rejects qualified
module access. Compact regressions cover these review findings; no new
exception family, template, threshold, live execution, or Rust change was
introduced. Review-closure verification passed 136 focused tests, project
Pyright with zero errors and warnings, and CSU with zero hard violations in
each touched production file; the production Rust diff remains empty.
