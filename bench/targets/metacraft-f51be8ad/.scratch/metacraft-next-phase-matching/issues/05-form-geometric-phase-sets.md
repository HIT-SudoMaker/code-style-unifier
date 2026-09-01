# 05 — Form geometric phase sets

**What to build:** A researcher can form 8-, 12-, and 16-level geometric phase
sets from one selected anisotropic cell by analytic rotation, without repeating
the native simulation for each orientation.

**Blocked by:** 04 — Choose one geometric height and cell.

**Status:** wontfix

**Superseded by:** [Metalens Sonnet convergence](../../metalens-sonnet-convergence/spec.md).

- [x] Every geometric phase set contains exactly one cell identity and exactly
  8, 12, or 16 distinct orientation states.
- [x] Target phases are uniformly spaced over one full turn, while physical
  orientations are normalized over the half-turn symmetry of the anisotropic
  cell.
- [x] Each orientation is derived from the target phase, selected cell's base
  converted phase, incident handedness, and exact admitted rotation convention.
- [x] Converted and retained complex responses remain distinct in every state;
  the converted channel receives the geometric phase and the retained channel
  preserves its qualified leakage response.
- [x] No solver session, engine process, permit, or orientation sweep is created
  while phase states are formed.
- [x] Each state records its cell identity, integer orientation index, physical
  rotation, target phase, realized response, convention reference, and source
  evidence.
- [x] Stable state identity uses canonical typed values and never hashes raw
  floating-point rotation or phase.
- [x] Identical admitted inputs reproduce identical states regardless of Jones
  library input order.
- [x] The public result contains separate 8-, 12-, and 16-level phase sets and
  introduces no automatic winner.

## Comments

2026-07-24: Implemented as analytic half-turn rotations from one admitted cell.
No orientation-specific solver work is created; converted and retained
responses remain distinct in all three quantizations.
