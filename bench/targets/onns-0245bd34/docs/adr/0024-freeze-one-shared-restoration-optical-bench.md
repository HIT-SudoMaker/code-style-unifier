---
status: accepted
---

# Freeze one shared restoration optical bench

Fixed Measurement and Adaptive Measurement use the same physical instrument.
They differ in where observations come from, what information an algorithm may
use, how phase is selected, and how evidence is evaluated; they do not differ
in lenses, Fourier sampling, aperture, splitter, arm gains, reference phase, or
coherent recombination.

The `experiments/restoration/optical_bench` package is therefore the single
physical source of truth. Its public Interface consists of
`OpticalBenchConfig`, Fourier-grid mapping and resolution-budget operations,
and `propagate_interferometric_bench`. Fixed and Adaptive import that public
Interface only. Configuration, Fourier relay, high-level propagation, and the
low-level dual-arm kernel remain private implementation segments inside the
package.

The canonical configuration retains the sealed Fixed values: 638 nm
wavelength, 100 mm focal length, 512 by 512 computational input and Fourier
phase grids, 8 micrometre SLM sampling, a 1024 by 1024 active SLM2 window, equal
nominal power splitting, and reference-on coherent detection. The corresponding
Fourier-grid interval is 15.576171875 micrometres, or 1.947021484375 native
SLM2 pixels. Physical deployment therefore remains a calibrated coordinate
projection rather than integer pixel replication.

The frozen propagation model is `compact_fourier_4f_equivalent`: centered FFT,
Fourier-plane aperture and phase transfer, inverse FFT, then coherent arm
recombination. This is the ideal thin-lens 4f equivalent already used by the
sealed Fixed archive. It preserves the physical role and focal-length-dependent
aperture without claiming an uncalibrated element-by-element model of the
V-shaped relay. A future explicit lens-and-distance implementation must pass a
declared equivalence and hardware-calibration gate before it can replace this
model.

Fixed owns target-supervised data, trained specimen-independent phase, digital
backends, training, and its immutable 45-run evidence. Adaptive owns unknown
episode fields, causal observation history, phase delivery, probe and admission
policy, stopping, and prospective evidence. Neither protocol may reconstruct
or override the common optical topology locally.

The migration preserves the serialized configuration field set and historical
geometry hash. Native loading of all 45 Fixed runs is the archive gate. Unit
tests may override the computational resolution for bounded execution, but the
scientific default and experiment CLI remain 512 by 512.
