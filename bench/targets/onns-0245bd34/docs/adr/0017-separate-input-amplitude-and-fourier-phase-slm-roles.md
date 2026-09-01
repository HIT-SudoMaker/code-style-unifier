---
status: accepted
---

# Separate input-amplitude and Fourier-phase SLM roles

The physical dynamic bench uses two independent LCOS devices: an HDSLM80RA Plus before the beam split as the input-amplitude SLM, and an HDSLM80R Plus in the V-shaped 4f processing arm as the Fourier-phase SLM. A calibration episode holds the input SLM fixed while only the Fourier-phase SLM carries time-varying probes and the final correction; the two devices must retain separate response models and LUTs because treating the amplitude and phase roles as interchangeable would invalidate both the forward model and the dynamic experiment.
