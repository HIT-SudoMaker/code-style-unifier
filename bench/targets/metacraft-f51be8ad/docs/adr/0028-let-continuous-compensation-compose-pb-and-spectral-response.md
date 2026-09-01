# 0028 - Let continuous compensation compose PB and spectral response

Status: accepted

One continuous-band metalens Method couples a geometry-controlled complex spectral response to a wavelength-independent PB orientation. Geometry supplies the phase slope, higher-order residual, conversion, and leakage over the band; physical orientation supplies the reference-phase offset under the admitted polarization convention. The compiler therefore does not add a third control strategy, workflow, or solver Adapter: it retains one geometry and orientation per occupied aperture site, forms exact single-wavelength Fields and focal regions from that immutable layout, and concludes one achromatic focus only from the complete design-and-holdout family.

This preserves the existing propagation-phase and PB-phase proofs and the public `brief -> study -> result` lifecycle. It rejects the simpler alternatives of redesigning the aperture independently at each wavelength, writing `+/-2 theta` without deriving the sign from the polarization convention, or treating a qualified unit-cell library as a completed metalens.
