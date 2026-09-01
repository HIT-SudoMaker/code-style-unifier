# 07 — Publish three source-level showcases

**What to build:** Give users three small, comparable source-level demonstrations of propagation phase, PB phase, and continuous compensation phase through the same conduct and Result lifecycle. The continuous showcase visibly separates geometry-controlled phase, PB phase, and their realized composition without changing the frozen historical benchmark catalogue.

**Blocked by:** 05 — Close, replay, and inspect one continuous Result.

**Status:** resolved (2026-08-15)

- [x] The propagation showcase exposes target and realized phase, selected geometry, Field, focus, and Result.
- [x] The PB showcase exposes target and PB phase, physical orientation, converted Field, focus, and Result.
- [x] The continuous showcase exposes geometry-controlled phase, PB phase, realized phase, fixed geometry and orientation maps, spectral focus, and Result or typed stop.
- [x] All three showcases invoke the existing conduct lifecycle rather than private scientific helpers.
- [x] The continuous showcase states that PB orientation supplies no group delay and that both responses belong to the same anisotropic structure.
- [x] Existing propagation, PB, Result-byte, and four-case benchmark regressions remain unchanged.
- [x] The showcase output contains exact references and no machine-local paths, credentials, or runtime cache inputs.

## Comments

- 2026-08-15: Resolved with three public-conduct examples. A typed stop is
  returned unchanged when external evidence is unavailable; projection occurs
  only from an admitted Result and retains its explicit execution origin. The
  focused showcase and historical-catalogue matrix passed 15 tests, and the
  three example sources passed Pyright without importing test fixtures or
  private scientific helpers.
