# 06 — Archive the three competitor source sets

**What to build:** Create one lawful, durable manifest for Self-Evolving, MetaChat, and MetaDesigner so publication positioning can be reproduced without relying on transient links or runtime folders. The manifest distinguishes papers, supporting information, code, data, and weights and preserves existing user-provided sources.

**Blocked by:** None — can start immediately.

**Status:** resolved (2026-08-15)

- [x] Exactly three article identities are unambiguous and deduplicated by DOI or arXiv identity.
- [x] Every retained local artifact records source locator, version or access date, byte size, SHA-256, and license or redistribution status.
- [x] Every linked-only artifact states why it is not copied locally.
- [x] Papers, supporting information, code, data, and weights are separate manifest entries.
- [x] Existing user-provided references are preserved without destructive replacement.
- [x] Temporary downloads, runtime reports, bytecode caches, and run projections are excluded from the durable archive.
- [x] The manifest and deduplicated bibliography remain research context rather than scientific Authority.
