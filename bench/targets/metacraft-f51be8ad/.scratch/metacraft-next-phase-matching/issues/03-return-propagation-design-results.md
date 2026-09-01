# 03 — Return propagation design results

**What to build:** A researcher can turn each propagation phase set into a
labelled low-na metalens, evaluate its realized complex field across the focal
region, and receive one fabrication-ready result for each quantization.

**Blocked by:** 02 — Form propagation phase sets.

**Status:** wontfix

**Superseded by:** [Metalens Sonnet convergence](../../metalens-sonnet-convergence/spec.md).

- [x] Each 8-, 12-, and 16-level phase set produces a separate `Aperture`
  containing a typed cell table, state table, occupied sites, spacing, radius,
  and two-dimensional state-identity map.
- [x] The state-identity map is the aperture's primary label; phase level is
  quantized-design metadata and is not required by the aperture contract.
- [x] Quantized aperture assignment is vectorized and does not score the full
  cell library independently at every occupied site.
- [x] The scalar aperture field uses every selected state's realized complex
  response rather than an ideal unit-amplitude phase mask.
- [x] The qualified angular-spectrum evaluator surveys 0.8 to 1.2 times the
  expected focal length and then deterministically refines around the principal
  focus.
- [x] Each focus result reports expected focus, found focus, focal shift, x and
  y half-maximum widths, depth of focus, peak intensity, and axial bracketing.
- [x] Each focus result separately reports transmitted fraction, focused
  fraction, and incident-normalized focus efficiency using the declared Airy
  radius.
- [x] A peak or required half-maximum crossing at the focal-window edge produces
  an explicit incomplete result rather than an extrapolated width or depth.
- [x] Each design package contains a fabrication cell table, optical state
  table, labelled aperture table, focus result, and complete admitted evidence
  closure.
- [x] The three design results remain comparable and separate; no unapproved
  rule automatically chooses one quantization.

## Comments

2026-07-24: Implemented with exact `aperture -> field -> focus` evidence.
The standard 400 nm, na 0.3 brief now uses a 30 um focal length so the declared
0.8f-to-1.2f window can bracket the complete focus without relaxing the gate.
