# 04 — Compose one fixed continuous aperture

**What to build:** Compile one qualified geometry-controlled Jones response and one analytical PB orientation into a single immutable aperture. The Jones tensor is reconstructed from two linear-basis observations of the same unrotated geometry rather than treated as a second device. A researcher can inspect how the selected geometry supplies relative delay and intrinsic phase, how orientation supplies PB phase, and how their sum realizes the target reference phase on one physical Lattice.

**Blocked by:** 01 — Resolve one authoritative physical Lattice; 03 — Let one qualification decide candidate or refusal.

**Status:** resolved (2026-08-15)

- [x] Every occupied site selects exactly one eligible geometry against required relative delay using recorded deterministic tie-breaks.
- [x] Every occupied site derives exactly one physical orientation from the admitted circular-polarization convention after geometry selection.
- [x] Geometry and orientation maps are immutable and identical for every design, validation, and post-freeze verification wavelength.
- [x] The realized reference phase reconstructs from the geometry-controlled phase plus PB phase to canonical cyclic tolerance.
- [x] Required delay, selected delay, and delay error remain inspectable at every occupied site.
- [x] Neighbor dimension jumps and transition classes are retained as immutable aperture diagnostics without changing deterministic delay assignment.
- [x] The aperture exposes the union of every assigned geometry and the PB-only baseline geometry so that bounded blind-verification work can be projected only after the layout freezes.
- [x] Changing the polarization handedness changes the admitted PB sign rather than applying a universal sign.
- [x] A non-candidate qualification, foreign Lattice, or cross-linked spectral library cannot produce an aperture.
- [x] Candidate formation and aperture assignment create no rotation-specific periodic solver work; bounded post-freeze validation remains a separate publication check.

Resolved 2026-08-15: the Sonnet/conduct path now freezes one qualified geometry and one handed PB orientation per authoritative Lattice site. The canonical aperture records deterministic selection policy, per-site delay/phase evidence, immutable adjacency transition diagnostics, and the assigned-plus-baseline geometry union without projecting rotation-specific periodic work.
