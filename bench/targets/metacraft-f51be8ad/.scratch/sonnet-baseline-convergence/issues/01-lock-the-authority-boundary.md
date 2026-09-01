# 01 — Lock the Authority boundary before changing its interior

**What to build:** A public-seam characterization that fixes the observable
Authority contract before the private Rust experiment begins.

**Blocked by:** None — can start immediately.

**Status:** resolved (2026-07-30)

- [ ] Characterization covers `check`, `view`, `fetch`, and `decide` through
      the typed Python Authority surface.
- [ ] Admitted decisions, rejected decisions, revision mismatch, canonical
      JSON, exact references, public exception text, integrity findings, and
      replay are represented by external-behavior assertions.
- [ ] Tests use existing Authority and replay seams rather than exposing a new
      private Rust test API.
- [ ] The current public outputs are captured without changing production Rust,
      protocol schemas, persisted workspace bytes, or canonical fixtures.
- [ ] The focused Authority suites and complete non-live Python suite remain
      green with every external integration marker excluded.
- [ ] No live adviser, Lumerical, delivery, or canonical brief execution runs.
