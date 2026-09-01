# 31 — Honor the propagation atom

**Type:** implementation (spec phase 5)

**Status:** wontfix

**Superseded by:** [Metalens Sonnet convergence tickets 01 and 03](../../metalens-sonnet-convergence/spec.md#tickets).

**Blocked by:** ticket 22.

**What to build:** Carry the propagation atom declared by the brief through
the compiled route, height choice, candidate plan, Lumerical construction,
exact construction readback, response evidence, and phase library. The
current shapes are `circular pillar`, with one diameter, and `square pillar`,
with one width. No intermediate module may silently replace either shape
with the other. The physical period continues to come only from the admitted
height domain or height choice.

The two shapes share one propagation-response contract and one phase-set
law. Product-specific construction stays inside the Lumerical Adapter;
science sees typed fabrication cells and never native commands.

**Acceptance:**

- Public compiler tests prove that each declared shape reaches the bound task
  unchanged.
- Fake-session Adapter tests build and read back one circular and one square
  cell through the public construction seam.
- Evidence and phase-library tests retain the shape name and its natural
  dimension (`diameter_nm` or `width_nm`) without a generic geometry bag.
- A separately marked live test reads back one cell of each shape; it is
  written but not enabled by the normal suite.
- Architecture tests forbid compiler ceilings and native Lumerical commands
  from entering the science modules.
- Touched files leave `csu check` with zero hard violations.

Decisions: tickets 19, 22, 29; spec phase 5.
