# 03 — Let vector plane fields earn their focus

**What to build:** Propagate an actual sampled electromagnetic plane field
through one separately qualified vector angular-spectrum method suitable for
high-na focal evaluation.

**Blocked by:** 02 — Let present angular spectrum prove only what it does.

**Status:** resolved (2026-07-30)

- [ ] Vector angular spectrum is a separate method and realization, not a
      boolean mode or renamed componentwise implementation.
- [ ] The method consumes a field with an explicit plane, coordinate frame,
      medium, component basis, wavelength, and source references.
- [ ] The realization reconstructs the longitudinal electric component from
      Maxwell transversality under the declared propagation convention.
- [ ] An oblique plane-wave fixture verifies wave-vector direction,
      transversality, phase advance, and longitudinal recovery.
- [ ] A bounded direct vector reference agrees in complex electric components,
      not intensity alone.
- [ ] Power is evaluated from the appropriate Poynting-vector quantity rather
      than one electric component.
- [ ] Evanescent handling, propagation direction, sampling bounds, and
      coordinate conventions are explicit qualification facts.
- [ ] All production calculations use Torch complex128 and remain on the
      selected CUDA or CPU device.
- [ ] The selected device qualifies and executes the same realization; no
      silent device or method fallback exists.
- [ ] The new method binds through the existing capability and study model
      without adding a workflow registry or changing Rust.
- [ ] Focused vector-field qualification and binding tests pass without a
      paper reproduction or live solver.
