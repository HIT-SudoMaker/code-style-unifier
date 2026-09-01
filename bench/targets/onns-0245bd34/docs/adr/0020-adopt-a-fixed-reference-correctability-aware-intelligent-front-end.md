---
status: accepted
---

# Adopt a fixed-reference, correctability-aware intelligent optical front end

The active Restoration candidate is an **intelligent optical front end**, not
a post-detection restoration network and not a conventional wavefront sensor
with a renamed controller. Its claim-facing behaviour is the closed sequence

```text
measure -> infer -> predict -> decide -> correct -> verify
```

The mechanical delay arm remains fixed during an episode. Its delivered
arm-relative phase is calibrated and tracked as a nuisance state; it is not
assumed to remain exactly zero. Required phase-shifting diversity is applied as
a global piston on the processing-arm phase SLM and is counted in the SLM-state,
settling, photon, camera-read, and wall-clock budgets.

The primary science observation keeps the coherent reference present. The
controlled quantity is therefore the **relative optical transfer** produced by
the interference of the fixed reference arm and the phase-controlled processing
arm. A reference-blocked acquisition is retained only as a structural ablation
that asks whether the advantage came from coherent transfer steering; it is not
the default claim-facing endpoint.

The physical model defines the hardware-feasible correction set and its ideal
reachable envelope. A measurement-conditioned estimator infers either a
posterior over correction-relevant state or a posterior directly over useful
delivered actions. A correctability predictor estimates the benefit, harm, and
uncertainty of each admissible action relative to a preregistered safe action.
The decision policy then chooses exactly one of:

- `correct`: load a supported correction and acquire a causally later frame;
- `probe`: spend one additional information-bearing measurement when its
  expected decision value exceeds its complete cost;
- `abstain`: retain the safe action when correction is unsupported or harmful.

Learning may amortize inference, model hardware residuals, calibrate uncertainty,
or choose probes. It may not receive simulated aberration truth at evaluation,
replace the detector output with a restored digital image, or expand the
phase-only hardware-feasible action set by declaration. Until prospective
calibration is demonstrated, the output is called a **correctability estimate**,
not a certificate.

The default sensing protocol is `4 + 1`: four quadrature phase-shifted
calibration observations followed by one prospective science observation.
The bounded adaptive protocol is at most `8 + 1`: at most eight calibration
observations followed by one later science observation. The additional four
states must be chosen for correction-relevant information, not added as an
unexplained fixed sequence.

The initially defensible aberration scope is differential aberration carried by
the processing arm after the beams split. Common-path specimen aberration is not
automatically identifiable from a self-reference interferometer because object
and pupil phase can share a gauge. Any broader claim requires an independent
reference, a validated guide feature, another diversity axis, or a direct
identifiability proof.

This decision supersedes the reference-blocked primary science endpoint in the
July research design and the use of `self-verifying` as the leading method name.
It does not supersede the prospective-frame, delivered-action, complete-budget,
or abstention requirements. Those requirements become stricter under the
intelligent-front-end claim.

## Evidence gate

The architecture is a candidate until all of the following are shown:

1. the relative-transfer model and four-step demodulation agree with simulation
   and controlled bench measurements;
2. useful delivered actions are identifiable without exposing aberration truth
   to the policy;
3. a correction improves a newly acquired raw reference-on science frame over
   safe, sham, opposite-sign, fixed-mask, and digital baselines;
4. the correctability estimate is calibrated under specimen, SNR, aberration,
   registration, LUT, and drift shifts;
5. `probe` and `abstain` improve the benefit--risk--cost frontier over always
   correcting and over the strongest fixed probe codebook;
6. reference-off ablation supports the claimed interferometric mechanism.
