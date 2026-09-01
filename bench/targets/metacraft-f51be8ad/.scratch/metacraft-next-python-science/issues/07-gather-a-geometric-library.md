# 07 — Gather a geometric library

**What to build:** The standard geometric study can gather an anisotropic rectangular-fin library with complete Jones evidence and derived converted and retained circular channels, reusing the bounded runner without borrowing propagation evidence.

**Blocked by:** 02 — Compile the standard studies; 04 — Qualify Lumerical; 05 — Gather a propagation library.

**Status:** wontfix

**Superseded by:** [Four-brief delivery ticket 06](../../four-brief-metalens-delivery/issues/06-let-rectangle-and-ellipse-share-one-geometric-proof.md).

- [x] The template enforces `length > width`, aspect limit, accepted spans, and the 20 nm compact grid.
- [x] Each geometry performs x and y linear inputs sequentially under one permit.
- [x] Handedness, time convention, Jones basis, channel order, propagation direction, and orientation sign are explicit.
- [x] Raw linear channels and derived `circular.converted` and `circular.retained` values are retained.
- [x] The public matching projection is `phase.value`, `power.useful`, and `power.leakage`.
- [x] Geometric and propagation evidence are structurally unable to satisfy one another's proof.
