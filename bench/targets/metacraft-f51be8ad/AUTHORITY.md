# Authority

`rust/` is the sole Rust crate. It builds the private extension
`metacraft._authority` and exposes one class, `Authority`.

## Public surface

- `Authority(workspace)` opens an initialized workspace or creates one at a path that does not yet exist.
- `check()` verifies objects, ledger, projections, protocol identity, and schema hashes.
- `view()` returns the replayed authority state at one revision.
- `fetch(reference)` returns exact immutable bytes.
- `decide(proposal, at=revision)` admits or rejects one proposal at an exact revision.

JSON returned through Python is canonical text. Object bodies remain opaque bytes unless a generic registered structure is attached.

## Relations

- `record` retains immutable evidence.
- `current` names one current object and may supersede only its exact predecessor.
- `permit` reserves one unit beneath a current capacity.
- `receipt` consumes one open permit.
- `close` revokes or expires one open permit.

Open and closed are final authority meanings. Repeating an open permit is rejected as already open; repeating it after receipt or close is rejected as already closed. Rejection never advances the revision.

## Invariants

1. Proposals and structured JSON are canonical and contain no duplicate keys.
2. Every supplied reference resolves, is duplicate-free, and is exactly required—neither missing nor surplus.
3. Objects are immutable and content addressed.
4. One decision commits objects, event, ledger head, and projection atomically.
5. A stale revision cannot commit.
6. Stored projections must equal deterministic ledger replay.
7. Capacity cannot fall below its open permits.
8. A permit binds one current capacity, one scope, and one future expiry.
9. Admission and replay use one typed lifecycle reducer; wall-clock checks occur only at admission.
10. Rust contains no scientific aim, method, solver, material, optimizer, workflow, or AI policy.

The protocol identifier and schema hashes are generated from one source. Golden fixtures freeze externally visible bytes and findings.
