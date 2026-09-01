# Sonnet deep architecture closure report

Date: 2026-08-05

Status: Sonnet-sealed

## Checkpoints

- Architecture fixed point: `40f2127`.
- Implementation commit: `eb6db2f`.
- Closure commit: recorded by commit history immediately after this report.

The implementation commit is the immutable checkpoint containing the complete
Tickets 06 through 09 implementation and deterministic repairs. This report,
Ticket 10's resolved status, and the matching map/spec state form the
non-production closure delta. The second checkpoint is deliberately identified
by repository history rather than by a self-referential hash embedded in its
own contents.

## Python seal

- Complete non-live suite: **1,245 passed, 6 deselected, 0 skipped**.
- Focused seam verification: **194 passed**.
- Architecture verification: **106 passed**.
- Pyright: **0 errors, 0 warnings, 0 information**.
- CSU: **4,473 total findings, 0 blocking findings**.
- Both independent reviews reported **no blocking finding**.

The verified architecture surface includes the exact installed root and Field
interfaces, cheap imports, canonical Study and Result restoration, the
create-only conduct seam, one Authority revision policy, one work life, one
periodic-response seam, external benchmark ownership, runtime import DAG,
deleted-lifecycle ratchets, strict schema identities, and production's absence
of an `examples` dependency.

## Frozen Rust authority

- Diff from fixed point `40f2127`: empty.
- `cargo fmt --check`: passed.
- strict `cargo clippy`: passed.
- Cargo tests: **18 passed, 3 ignored**.
- Rust architecture tests: **3 passed**.
- Authority interface tests: **17 passed**.
- Committed Rust source-manifest ratchet: **1 passed**.

The Rust source, protocol values, persisted authority meaning, and the four
Authority verbs `check`, `view`, `fetch`, and `decide` remain unchanged.

## Release artifact

- Wheel: `metacraft-0.0.0-cp312-cp312-win_amd64.whl`.
- Size: **1,737,468 bytes**.
- SHA-256:
  `28a8558f43a17685d2dc53fb5cdbdca27ffca2270e4e09f2c4d9931cce8a68f4`.
- Inventory: **105 entries**.
- Native extensions: exactly
  `metacraft/_authority.cp312-win_amd64.pyd`.

The inventory contains no examples, tests, `.scratch`, generated cache, or
build-tree content. An isolated target install loaded
`metacraft/__init__.py` and `metacraft/_authority.cp312-win_amd64.pyd` from the
installed target. The Authority smoke created one fresh workspace, verified
the root revision, admitted and fetched one canonical document through the
four-verb Interface, and passed integrity checks before and after the write.

## Native evidence carried from Ticket 09

- Receipt SHA-256:
  `5bf6e2170b82f077cfd313ed28c4c9268f773a1e857a4b92a838fbdd68b05416`.
- Solve count: **3 qualification + 0 recovery + 2 candidate = 5**.
- Native inventory: **38/38** entries accounted for in recovery inventory.
- Uniform formation: **24 by 24** for both retained candidate surfaces.
- Recovery execution: **zero**.

Ticket 10 verified only the tracked, redacted receipt. It did not reopen the
Ticket 09 application root and ran no Adviser, product discovery, Native solve,
or artifact recovery.

## Repository disposition

At report-writing time the closure delta contains exactly this report plus the
Ticket 10, map, and specification status records under
`.scratch/sonnet-deep-architecture/`. It contains no production, test, Rust,
wheel, generated artifact, or Native-receipt change. `git diff --check` passes,
and the immediately following closure commit in repository history is the
clean second checkpoint required by the two-point seal.

## Conclusion

ADR 0018 and ADR 0019 now agree with the implementation, deterministic gates,
release artifact, and bounded Native evidence. No production, test, or Rust
repair belongs to this seal. The architecture is **Sonnet-sealed**: one name
at the door, one Study in the middle, one Authority admitting, and benchmark
cases comparing from outside.
