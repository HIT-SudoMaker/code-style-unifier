# 01 — Cross the authority boundary

**What to build:** A Python caller can store one typed record through the frozen Rust authority, fetch it by exact reference, and decode it without encountering raw protocol machinery or a second lifecycle.

**Blocked by:** None — can start immediately.

**Status:** wontfix

**Superseded by:** [Four-brief delivery specification](../../four-brief-metalens-delivery/spec.md).

- [x] The private native extension is imported by one adapter only.
- [x] Public `Authority` preserves the constructor and `check`, `view`, `fetch`, and `decide`.
- [x] One typed record round-trips through canonical bytes and an exact typed reference.
- [x] Malformed proposals, rejected decisions, and stale revisions remain explicit and are never retried or repaired locally.
- [x] Rust source and native protocol fixtures remain unchanged.
