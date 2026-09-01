# 14 — Prove the pre-brief-validation baseline

**What to build:** One tracked closure record demonstrating that code, external
examples, report ownership, and archives are ready for the next phase of brief
validation.

**Blocked by:** 11 — Seal the Sonnet naming contract; 13 — Archive report
history by exact identity.

**Status:** resolved (2026-07-30)

- [ ] The complete non-live Python suite passes with integration, adviser-live,
      Lumerical-live, and Lumerical-delivery markers explicitly excluded.
- [ ] Static type checking, architecture tests, the code sustainability audit,
      Rust formatting, strict Rust linting, all Rust tests, and the Rust source
      manifest pass.
- [ ] A native release package builds and an isolated smoke test imports the
      built Authority surface while confirming that concrete examples are not
      packaged.
- [ ] Canonical Authority fixtures and replay pass without protocol, schema,
      reference, or persisted-byte drift.
- [ ] All four external canonical briefs load offline in stable order and their
      expected canonical bytes and content identities are recorded.
- [ ] Report source inventory, Git LFS pointers and local objects, office
      package structure, archive hashes, and repository status all verify.
- [ ] The tracked closure record names the implementation commit, report
      commit, four brief identities, verification commands and outcomes, Rust
      manifest state, architecture assessment, and planned ref dispositions.
- [ ] The closure record explicitly hands the four external briefs and the
      still-separate grounding decisions to the next brief-validation phase.
- [ ] No live adviser call, Lumerical discovery, native solve, sweep, delivery,
      or canonical brief execution occurs.
