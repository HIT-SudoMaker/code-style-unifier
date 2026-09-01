# 02 — Form propagation phase sets

**What to build:** A researcher can gather one fixed-height propagation cell
library and form traceable 8-, 12-, and 16-level phase sets whose states use
distinct manufacturable geometries and deterministic fast matching.

**Blocked by:** 01 — Adopt one propagation height recommendation.

**Status:** wontfix

**Superseded by:** [Metalens Sonnet convergence](../../metalens-sonnet-convergence/spec.md).

- [x] The detailed lateral sweep accepts one admitted `HeightChoice` and never
  expands across the original height domain.
- [x] Every cell retains typed shape, material, period, height, and lateral
  dimensions in addition to its natural artifact name.
- [x] A propagation cell library rejects mixed heights, routes, periods,
  material bindings, phase references, duplicate geometries, non-finite
  responses, invalid construction, and incomplete evidence closure.
- [x] The current circular-pillar library retains complex transmission, useful
  power, leakage power, realized phase, solver status, warnings, native
  execution evidence, and exact observation references.
- [x] The matcher constructs uniform 8-, 12-, and 16-level target phases and
  jointly selects exactly that many distinct fabricable cells for each phase
  set.
- [x] A requested phase set fails closed when the admitted library cannot
  provide enough distinct states or adequate phase coverage under the explicit
  selection policy.
- [x] Every selected state records target phase, realized phase, circular phase
  error, complex response, useful power, leakage power, cell identity, source
  evidence, loss, and deterministic tie-break.
- [x] Cell and state identities are derived from canonical typed values;
  persisted identity never uses raw floating-point keys or Python's
  process-randomized hash.
- [x] Matching indexes use normalized integer dimensions and phase keys, and
  candidate input order cannot change the selected phase set.
- [x] The public result contains three separate phase sets and does not
  implicitly rank 8, 12, or 16 levels as the winner.

## Comments

2026-07-24: Implemented and hardened. The 8-, 12-, and 16-level sets remain
separate per-quantization studies. Canonical integer identities, exact
Authority references, deterministic matching, and failure boundaries are
covered by the complete suite.
