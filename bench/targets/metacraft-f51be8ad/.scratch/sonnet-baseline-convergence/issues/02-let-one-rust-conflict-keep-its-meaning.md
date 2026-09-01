# 02 — Let one Rust conflict keep its meaning until the boundary

**What to build:** One complete Rust vertical slice in which a ledger-head
conflict is created and carried as private semantic state, while callers
observe the exact established Authority contract.

**Blocked by:** 01 — Lock the Authority boundary before changing its interior.

**Status:** resolved (2026-07-30)

- [ ] The ledger-head conflict is represented semantically at the point where
      the workspace detects it.
- [ ] Authority control flow matches the semantic variant and no longer
      classifies this conflict with a string-prefix test.
- [ ] The existing public error or rejected-decision spelling is encoded only
      at the outer boundary and remains byte-for-byte unchanged.
- [ ] `is_finding()` and its accepted finding set remain unchanged.
- [ ] The public Authority type, four verb names, canonical protocol,
      persistence format, revision meaning, and replay behavior remain
      unchanged.
- [ ] The Rust source manifest is regenerated deliberately and its architecture
      verification passes.
- [ ] Rust formatting, strict linting, all Rust tests, a native release build,
      the Python extension import smoke test, and the ticket-01 characterization
      all pass.
- [ ] If this slice requires a broad error hierarchy or widespread conversion
      of string-returning APIs, work stops and records that failed assumption
      instead of widening scope.
