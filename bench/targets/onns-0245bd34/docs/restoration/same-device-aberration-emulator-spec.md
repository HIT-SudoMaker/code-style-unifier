# Same-device differential-aberration experiment specification

- Status: approved for implementation
- Scope: simulation, same-device SLM emulation, and rapid bench transfer
- Claim ceiling: calibrated differential-aberration emulator

## Decision

The first differential-aberration transfer experiment adds no lens, phase
plate, moving delay, third SLM, or native specimen. It retains the present
amplitude-replay bench:

```text
laser -> HDSLM80RA Plus (degraded amplitude D) -> beam splitter
                                                    |-> fixed reference arm --|
                                                    |                         |-> camera intensity
                                                    |-> V processing arm -----|
                                                        HDSLM80R phase SLM
```

The mechanical reference arm is calibrated near a nominal relative phase of
zero and remains fixed during an episode. Four-step phase diversity is supplied
by global piston on the processing-arm phase SLM.

The same processing SLM may emulate a hidden persistent differential aberration
and deliver the corrective action:

\[
\phi_{\mathrm{display},t}(\mathbf r)
=
\phi_{\mathrm{hidden}}(\mathbf r)
+
u_t(\mathbf r)
+
c_t.
\]

The evaluator owns `phi_hidden`; the policy sees only the allowed intensity
history, `D`, delivered pistons, calibration, and budget. This is valid evidence
for a calibrated same-device emulator, not evidence of an independent incoming
aberrator or native microscope correction.

This mechanism track runs alongside the minimum amplitude-replay restoration
gate; it does not replace that gate or rescue it if it fails.

## Degradation placement

Three phenomena remain physically and semantically separate:

1. Image blur and baked image noise are produced by the shared data pipeline
   before SLM1 and are encoded in `D`.
2. Zernike pupil aberration is a persistent processing-arm differential phase
   displayed by the phase SLM after the beam split.
3. Shot noise and camera read noise are sampled independently for every camera
   exposure.

Gaussian or disk blur must not be relabelled as an SLM2 pupil aberration.
Likewise, a displayed Zernike phase must not be reported as recovery of
pre-display information lost from `D`.

## Optical and coordinate contract

- Wavelength: 638 nm.
- Relay focal length: 100 mm.
- Computational action grid: 512 by 512.
- Input pitch used by the frozen Fourier model: 8 micrometres.
- Nominal Fourier-plane interval:
  `638 nm * 100 mm / (512 * 8 um) = 15.576171875 um`.
- Native 8-micrometre phase-SLM sampling: approximately 1.947 native pixels per
  theoretical Fourier cell.

The 15.576-micrometre value is an FFT-conjugate sampling interval, not a
geometric magnification. Native delivery therefore uses calibrated
physical-coordinate projection. Integer 2-by-2 replication is prohibited.

Before claim-bearing acquisition, record phase LUT identity, usable pupil,
flat phase, reference-relative phase, parity, rotation, scale, centre,
processing/reference registration, camera exposure, and SLM/camera timing.

## Episode Interface

The experiment uses the existing deep Adaptive Interface:

```python
run_adaptive_episode(request, bench) -> AdaptiveEpisodeRecord
```

The same-device physical bench is an Adapter at the existing bench seam. It
does not create a second episode Interface. Simulation and hardware Adapters
must emit the same commanded phase, delivered phase, delivered piston, raw
intensity, clock, and calibration provenance.

The episode hides the complete control sequence:

```text
4 pre observations
    -> estimate differential phase and uncertainty
    -> project onto the calibrated delivered reachable set
    -> predict benefit, harm, and residual
    -> trial or abstain
4 Action Echo observations
    -> admit or revert
1 later raw science observation
```

The camera provides intensity only. No policy operation may receive a simulated
complex field, clean target, injected Zernike coefficient, `B0`, or oracle
action.

## Decision contract

The policy answers two separate questions:

1. `can_correct`: are the observation conditioning, uncertainty, reachable
   projection, and delivery margin sufficient?
2. `should_correct`: is the lower confidence bound of predicted benefit
   positive after exposure, latency, and harm costs?

Allowed pre-trial decisions are `trial` and `abstain`; an information probe may
be added only if it remains inside a separately declared frame budget. Allowed
post-Echo decisions are `admit` and `revert`.

Echo verifies that the delivered optical change matches the locked prediction.
It does not use clean truth and does not by itself prove image restoration.

## Bounded aberration family

The first simulation suite is intentionally compact:

- defocus;
- astigmatism;
- coma;
- primary spherical aberration;
- one held-out mixed-Zernike family.

Use two preregistered RMS phase strengths and the same held-out scenes under
`light`, `medium`, and `heavy` baked degradation. Do not begin with a dense
coefficient scan. A low-SNR/calibration-drift stress set is added only to test
abstention and reversion.

The first bench subset uses one moderate RMS strength, defocus, astigmatism,
coma, and the held-out mixture. Spherical aberration and additional strengths
move to supplementary evidence only after the primary gate passes.

## Physical states

- `B0`: `D`, no injected differential aberration, no correction;
- `B1`: `D`, hidden persistent aberration, no correction;
- `B2`: `D`, the same hidden aberration, truth-blind Adaptive action;
- `B3`: `D`, the same hidden aberration, evaluator-only delivered-space
  oracle.

Every `B2` science frame is acquired prospectively after the decision and Echo.
It is never synthesized from `B0`, `B1`, or the injected truth.

## Success and kill gates

The simulation gate passes only if:

- held-out median `B2` versus `B1` aberration-removal gain is at least 6 dB;
- positive gain is retained across all three baked-degradation profiles;
- `B2` recovers a declared material fraction of delivered `B3` headroom;
- deliberately unsafe low-SNR or drift cases are not falsely admitted;
- both active-support and mechanism metrics are regenerated from evidence.

The bench gate passes only if:

- calibration replay establishes the commanded-to-delivered phase response and
  physical-coordinate projection;
- accepted `B2` trials improve a separately acquired later raw science frame;
- sham, opposite-phase, and equal-RMS controls do not reproduce the effect;
- every rejected trial is physically reverted before the later science frame;
- raw camera frames and timing ledgers are retained without replacing them by
  simulated or demodulated complex fields.

Stop or narrow the claim if the policy requires injected coefficients, if the
same-device projector cannot be calibrated, if Echo fails to predict the
delivered change, or if accepted actions have a material harmful-correction
rate.

## Claim boundary

Passing this specification supports a teacher-free, observation-conditioned,
same-device differential-aberration correction and admission-control claim on
controlled amplitude-replay scenes. It does not support correction of an
independent incoming aberrator, arbitrary unknown complex specimens,
fluorescence microscopy, multiple scattering, chromatic aberration, or general
adaptive-optics superiority.

Those limitations are deliberate. The experiment is the minimum reliable rung
before a later independent aberrator or native microscope Adapter is designed.
