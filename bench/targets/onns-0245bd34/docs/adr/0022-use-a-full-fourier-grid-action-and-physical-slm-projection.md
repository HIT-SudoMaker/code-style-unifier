---
status: accepted
---

# Use a full Fourier-grid action and physical SLM projection

Adaptive Measurement controls a full 512 by 512 phase action on the canonical
Computational Fourier-Phase Grid. Low-order modes may initialize, regularize,
or diagnose the optimization, but they do not replace the final action space.
The first action estimate is grounded in the measured interferometric state and
is refined through a differentiable PyTorch propagation and hardware model
before exact delivery and Action Echo audit.

Under the frozen 638 nm wavelength, 100 mm focal length, 512 input samples, and
8 micrometre input sampling, one Fourier-grid interval is 15.576171875
micrometres. This is 1.947021484375 native 8 micrometre SLM2 pixels per axis,
not an integer two-pixel replication. Deployment therefore uses physical
coordinates and measured registration; the theoretical 512-grid footprint is
7.975 mm, approximately 996.875 SLM2 pixels, embedded in the native SLM canvas.

Bounded simulation retains a 512 by 512 observation grid. The ASI585MM bench
Adapter later preserves each native intensity-only frame before calibrated
crop, registration, or resampling. Camera-to-analysis registration and
Fourier-grid-to-SLM deployment are different transformations and may not share
an index-only resize.
