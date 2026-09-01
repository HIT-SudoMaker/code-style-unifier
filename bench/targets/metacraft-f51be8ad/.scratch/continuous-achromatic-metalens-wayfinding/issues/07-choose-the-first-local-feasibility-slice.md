# Choose the first local feasibility slice

Status: resolved (2026-08-14)

Assignee: Codex

Label: `wayfinder:grilling`

Blocked by: [Draw the paper-to-local material adaptation line](03-draw-the-paper-to-local-material-adaptation-line.md), [Keep spectral work out of the Brief](05-keep-spectral-work-out-of-the-brief.md)

Parent: [Find the continuous-achromatic metalens compilation road](../map.md)

## Question

Which exact continuous band, focal length, numerical aperture or aperture,
reviewed local material family, substrate, fabrication bounds, polarization
channel and user-owned acceptance targets define the first modest positive
case without silently importing Chen's device as MetaCraft's design?

## Resolution

Use a Chen-2018-inspired local adaptation with a `470--590 nm` design band,
`530 nm` reference, circular input/cross-circular output, Siefke TiO2 on Palik
glass, a `600 nm`-high primitive rectangular fin in the existing square cell,
and locally order-safe period selection. The positive target is `R=10 um`,
`F=49 um`, `NA≈0.2`, requiring `3.369 fs`; the neighboring stress target is
`R=12.5 um`, `F=49 um`, requiring `5.234 fs`.

The Method, not the Brief, owns the paper-inspired wavelength grid, reference
wavelength, PB convention, phase fitting, holdout, and qualification rules.
The Plan owns the local period, height, geometry grid, and work count. A
single-rectangle refusal is a valid result and does not refute Chen's compound
library.

## Evidence

- [Local material feasibility](../../../docs/research/2026-08-14-local-tio2-glass-achromatic-feasibility.md)
- [Experiment result](../../../docs/research/2026-08-14-achromatic-experiment-result.md)
- Native material samples cover all five design and four holdout wavelengths.
- A partial real `530 nm` screen completed four geometries: two exceeded the
  normalized 5% conversion gate, two did not, and a fifth exposed the typed
  numerical-closure work still required before integration.
