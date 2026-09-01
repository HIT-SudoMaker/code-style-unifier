# Let one native record speak once

Type: implementation

Status: resolved (2026-07-29)

Blocked by: none.

## Outcome

Lumerical execution records decode through one owner, native session-open
failure crosses the Adapter seam with one stable reason, and one dead sweep
helper is deleted.

## Scope

1. Make `PropagationObservation.from_mapping` restore its nested execution
   value through `ExecutionRecord.from_mapping`.
2. Make `GeometricBasisObservation.from_mapping` do the same.
3. Preserve each observation's candidate identity, scientific response,
   canonical whole-document round trip, and existing error ownership.
4. Convert a caught native `LumApiError` during `open_engine` into
   `LumericalUnavailable("native_product_unavailable")`.
5. Preserve the original native exception only through exception chaining.
6. Ensure the local diagnostic receives only the stable reason.
7. Delete the unused `_complex_mapping` implementation.
8. Add no new public export or compatibility path.

## Acceptance

- There is exactly one production decoder for an execution-record mapping.
- Both propagation and geometric restoration reject every malformed execution
  mapping that `ExecutionRecord.from_mapping` rejects.
- Malformed nested execution records remain chained beneath the existing
  propagation- or geometric-artifact error instead of leaking a raw decoder
  error.
- Candidate and basis identity mismatches retain their existing specific
  errors.
- A native product error message never becomes
  `LumericalUnavailable.reason`.
- The chained cause still retains the original native exception.
- New local diagnostics record `native_product_unavailable`.
- Existing canonical absence reasons keep their meaning.
- `_complex_mapping` no longer exists.
- Rust is untouched.

## Focused verification

Run only focused tests or exact nodes covering:

- `ExecutionRecord.from_mapping`;
- propagation observation restoration;
- geometric basis observation restoration;
- native product launch failure;
- local typed-absence diagnostic translation;
- the relevant Sonnet architecture assertion for the retired helper.

Also run:

- local Pyright for touched Python scope;
- CSU for touched production files;
- `git diff --check`;
- `git diff -- rust`.

Do not run a native engine, complete solver suite, complete architecture suite,
or complete Python suite.

## Stop and report

Stop if a production execution mapping legitimately contains fields not owned
by `ExecutionRecord`, if native product errors require more than one stable
scientific reason, or if exact observation round trips would change.

## Do not add

Do not add an error hierarchy, native-message classifier, legacy reason,
execution-record alias, second decoder, product registry, live test, or Rust
change.
