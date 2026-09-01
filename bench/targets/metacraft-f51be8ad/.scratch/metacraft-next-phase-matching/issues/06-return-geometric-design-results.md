# 06 — Return geometric design results

**What to build:** A researcher can turn each geometric phase set into a
labelled low-na metalens, evaluate useful and leakage fields across the focal
region, and receive three fabrication-ready polarization-aware results.

**Blocked by:** 03 — Return propagation design results; 05 — Form geometric
phase sets.

**Status:** wontfix

**Superseded by:** [Metalens Sonnet convergence](../../metalens-sonnet-convergence/spec.md).

- [x] Geometric results use the same `Aperture` interface, state-identity
  map, focal window, focus result, and fabrication package established by the
  propagation route.
- [x] Every occupied site references one of the selected cell's analytic
  orientation states; no route-specific aperture label bypasses state identity.
- [x] Converted and retained aperture fields remain separate from assembly
  through propagation and result serialization.
- [x] The useful converted field is evaluated from 0.8 to 1.2 times the expected
  focus with deterministic refinement around its principal focus.
- [x] Converted-field results report expected and found focus, focal shift, x
  and y widths, depth of focus, transmission, focused fraction, focus
  efficiency, peak intensity, and bracketing.
- [x] Retained leakage is reported under an explicitly labelled leakage channel
  and is not presented as useful focusing efficiency.
- [x] Each fabrication package identifies the one selected cell, every phase
  state's rotation, and every aperture site's state identity.
- [x] Each 8-, 12-, and 16-level result cites the polarization convention,
  selected cell, phase set, `Aperture`, channel fields, focus result, and
  complete admitted evidence closure.
- [x] No angle-specific native simulation artifact is required or claimed by a
  geometric design result.
- [x] The three results remain separate and no unapproved rule chooses a
  preferred quantization.

## Comments

2026-07-24: Implemented through the shared aperture/focus contract. The combined
field evidence and result serialization retain both converted and retained
complex channels, while retained power is reported only as leakage.
