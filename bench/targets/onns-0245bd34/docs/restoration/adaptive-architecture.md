# Adaptive Measurement architecture

- Status: active implementation plan
- Scope: programmable coherent-image simulation and later bench deployment
- Scientific state: deterministic truth-blind episode, distinct Oracle Ladder,
  calibrated reachability, and canonical evidence implemented; calibrated
  uncertainty, distribution evidence, matched comparison, and physical transfer
  remain open

## Context

Fixed Measurement and Adaptive Measurement are teammates because they use the
same 638 nm, 100 mm focal-length, reference-on interferometer and the same
512 by 512 Computational Fourier-Phase Grid. They are not symmetric
experiments. Their matched amplitude-replay track loads the same
data-pipeline-degraded image on SLM1. Fixed learns a specimen-independent phase
from target-visible paired data; Adaptive must choose a scene-conditioned
delivered action without clean-target access. A separate Adaptive coherent
mechanism track first uses the existing processing-arm phase SLM as a calibrated
differential-aberration emulator. A pre-split common pupil operator remains a
later microscope-transfer stress test; neither is native-microscope evidence.

## Problem

Three concerns must not be collapsed:

1. `data` prepares and degrades the SLM1 scene but does not manufacture an
   Adaptive camera observation;
2. the physical bench delivers phase and acquires intensity without exposing
   the hidden clean target to the policy;
3. the episode Module owns sensing, inference, trial, Action Echo,
   admission/reversion, budget accounting, and the later raw science frame.

In the matched amplitude-replay track, moving the archived disk/noise
degradation downstream would no longer represent the physical replay. In the
first coherent mechanism track, a persistent phase is added on the
processing-arm SLM and labelled as a same-device differential-aberration
emulator. A later pre-split operator is required to stress transfer to a
common-path coherent microscope. The contracts must not be merged. If the
clean target reaches either estimator, the result is an oracle rather than an
Adaptive policy. If global phase-shifting piston is merged into the spatial
phase action, piston-gauge normalization destroys the four-step observation.

## Principle

Share physics, separate evidence. Keep one deep episode Interface and one
physical-bench seam. The spatial correction and global
measurement piston are distinct parts of one command. Simulation truth belongs
to validation and evaluation, never to policy history.

## Architecture

The sibling packages follow the same reading rhythm without forcing false
symmetry:

```text
restoration/
  input_protocol.py               shared source, 256-to-512 preparation, encoding
  degradation.py                  shared SLM1 degradation profiles
  optical_bench/                  shared physical source of truth
  phase_control.py                spatial action + calibrated piston + delivery
  observations.py                causal detector records
  pupil_aberrations.py            evaluator and validation states
  evidence.py                     shared immutable evidence operations

  fixed_measurement/
    experiment.py                 run_fixed_measurement
    protocol/                     target-visible four-role plan
    optics/                       fixed learned frontend
    learning/                     backend and offline optimization
    evidence/                     sealed archive

  adaptive_measurement/
    episode.py                    causal state machine and only external runner
    protocol/                     policy-visible request and immutable policy
    inputs/                       SLM1 replay scenes from the data pipeline
    reachability/                 inference, projection, benefit, locked Echo
    sensing/                      internal quadrature and modal-fit implementations
    adapters/                     current simulated bench Adapter
    evidence.py                   write-once episode record and event ledger
    validation/                   Oracle Ladder and readiness gates

  studies/
    differential_correction.py   claim-facing B0/B1/B2/B3 study
```

Only directories with working responsibilities exist. `episode.py` is now
implemented. `control/`, `decision/`, and the physical bench Adapter are
created only when their first independently cohesive behaviour exists; empty
architectural placeholders are not accepted.

The target external Interface is:

```python
run_adaptive_episode(request, bench) -> AdaptiveEpisodeRecord
```

`bench` is the real seam. A simulation Adapter and a future ASI585MM plus SLM
Adapter satisfy the same Interface and return commanded phase, delivered phase,
delivered piston, raw intensity, timing, and hardware metadata in one causal
observation. Phase delivery remains an internal seam of each Adapter rather
than a second concern exposed to every episode caller.

The target Episode Interface does not require a known complex input field.
Controlled replay supplies its SLM1 command (D) through the replay Adapter;
future native input supplies only the information its own Adapter can lawfully
observe. Clean targets, hidden aberrations, evaluator B0/B3, and simulator field
truth remain outside both modes.

### Implemented architecture gates

The current implementation closes the first four architecture debts:

1. the Episode request contains real displayed replay intensity, never a known
   complex field, bench configuration, pupil, clean target, or hidden phase;
2. the simulated Adapter binds acquisition and one calibrated reachability
   Module to the same calibration identity;
3. the Episode record preserves the locked prediction, raw frames, commands,
   delivered states, policy snapshot, decisions, dose, timing, trial, revert,
   and later science in one write-once artifact;
4. O1 uses an arbitrary complex transfer, O2 an ideal reference-assisted
   continuous phase, and O3 a calibrated delivered phase-only search.

The remaining software debt is empirical rather than another speculative
abstraction: calibrate uncertainty and utility on a held-out distribution, then
bind the matched comparison to canonical records. The physical debt is a
measured ASI585MM/SLM Adapter, followed by one independently calibrated passive
aberrator only if the same-device and oracle gates pass. No empty physical
Adapter or compatibility layer is kept in advance.

The matched-comparison specification is approved, but its code is deliberately
absent until sealed Fixed records and canonical Adaptive episode records can be
consumed directly. Arbitrary in-process actor callbacks and synthetic timing
ledgers are not accepted as an information boundary.

The target episode state machine is:

```text
4 pre-action observations
        |
        v
infer candidate, delivered residual, deterministic mechanism benefit
        |
        +---- abstain -------------------------------+
        |
        v
lock prediction -> deliver trial -> 4 Action Echo observations
                                      |
                                      v
                                admit / revert
                                      |
                                      v
                         later raw reference-on science frame
```

Nine observations are the standard amplitude-replay and known-amplitude-target
mechanism budget. They are not yet an arbitrary-complex-specimen guarantee.
Two fully demodulated spatial probes, a complete four-frame Echo, and a science
frame require at least thirteen observations unless a stronger object or
reference constraint is independently validated. An Action Trial is an SLM
state transition, not an extra camera frame.

## Data flow

Fixed and Adaptive share the frozen ordered data stages but stop at different
causal points:

```text
Fixed:
load -> prepare -> perturb -> encode degraded replay -> target-visible training

Adaptive:
load -> prepare -> perturb -> zero-phase intensity encode -> degraded SLM1 scene
     -> explicit degradation posterior + reference-on bench posterior
     -> delivered action / abstention -> later raw science

Adaptive coherent mechanism:
load -> prepare -> degraded amplitude replay -> hidden processing-arm phase
     -> spatially informative reference-on observations
     -> pupil/action posterior -> delivered action / abstention -> raw science
```

The first Adaptive scene family is FMD averaged microscopy imagery prepared and
centre-padded to 512 by 512 and degraded before SLM1 encoding. Resolution
targets remain calibration controls, not substitutes for the extended-scene
result. The replay controller may read the actual SLM1 command (D), because
the hardware already knows what it displayed, together with causal camera
observations. It may not receive the simulator's derived complex field as a
universal Episode invariant, nor read the clean target, degradation truth,
random seed, hidden pupil phase, evaluator state, or episode-later metrics.

Fixed and Adaptive now consume the same source seed, split manifest, scene ID,
preparation geometry, degradation seed, profile, and encoding contract. The
canonical matched suite evaluates the same validation scene at `light`,
`medium`, and `heavy`. It does not add detector shot or read noise after the
interferometer; those effects belong to a separate robustness axis because the
Fixed archive did not include them.

## Evaluation contract

The prospective cross-line image standard is the centred 256 by 256 active
image support, not the zero-padded 512 by 512 canvas. Adaptive replay therefore
matches the complete Fixed input pipeline: automatic input normalization,
bilinear resize to 256 by 256, no edge taper, centred padding to 512 by 512,
shared perturbation profile, and intensity encoding. The encoded SLM1 field is
the degraded input; no second downstream degradation is added.

Three states remain separate: the SLM1 degraded input measures data degradation,
the pre-action zero-phase camera frame measures the uncorrected optical path,
and the prospective science frame measures the delivered correction. All three
are scored against the same clean prepared target on the active support. The
target is evaluator-only: it may establish performance after the episode, but
it cannot enter estimation, reachability, decision, or Action Echo. A direct
corrected-to-degraded distance is not a restoration metric because doing
nothing would minimize it.

The sealed Fixed archive reports full-canvas, fixed-dataset-level clamped
metrics. Its artifacts and identities stay unchanged. Adaptive therefore emits
both the primary active-support metrics and a separately named
`fixed_aligned_*` family that reproduces that historical normalization and
512-by-512 canvas. A claim-facing figure should recompute both lines on the
active support when raw Fixed outputs are available; otherwise it must use the
aligned family and label the historical metric boundary explicitly.

## Observation model

For spatial action \(u\) and global piston \(c_t\), the camera observes

\[
I_t(\mathbf x)=|r(\mathbf x)+e^{ic_t}p_u(\mathbf x)|^2+n_t.
\]

Four delivered piston states estimate the image-plane cross term through a
general linear demodulator rather than assuming perfect commanded quadrature.
This makes response error, quantization, and drift explicit in the design
matrix. The current observation simulator includes Poisson noise, read noise,
phase quantization, response gain, drift, and local crosstalk. Its four-step
contract holds the calibrated spatial delivery fixed while changing the global
piston. Physical deployment must validate that separability; otherwise the
demodulator must consume the actual pixel-wise phase of every step rather than
pretend that each frame differs by one scalar.

The same-SLM2 mechanism emulator composes hidden phase, policy action, and
piston before one physical delivery operation. The episode sees only its
action-space differential view; the complete composite command and delivered
phase are evaluator-only evidence. Thus nonideal LUT, response, quantization,
and crosstalk act on the same phase state that reaches propagation without
leaking the injected aberration into the policy.

Quadrature sensing is not itself an image-restoration objective. Under the
claim-facing replay protocol, blur and Poisson noise are already embedded in
the zero-phase amplitude displayed by SLM1 and no differential downstream
aberration is added. Four intensity observations can identify a coherent cross
term, but they cannot determine which unknown clean image produced that
amplitude. Classical phase conjugation must therefore be retained as a
falsification baseline, not presented as the Adaptive restoration algorithm.
Action Echo verifies whether a trial produced its locked optical change; it
does not add clean-image information or certify restoration benefit.

## Trade-off

SLM1 replay gives controlled degraded extended scenes, repeatable clean targets
for evaluator metrics, and direct reuse of the frozen data pipeline. It does
not constitute a native-specimen microscopy demonstration or correction of an
independent downstream aberrator. Claims about chromatic aberration, multiple
scattering, depolarization, common-path specimen phase, or live real-time AO
remain out of scope.

The full 512 by 512 phase is the delivered action space, not a claim that nine
frames identify 262,144 independent unknowns. Effective inference dimension
must be limited by pupil support, scene excitation, calibrated spatial
bandwidth, priors, and uncertainty; low-order modes initialize and diagnose but
do not define the final action.

## Conclusion

Fixed asks what a target-visible, specimen-independent optical transform can
learn. Adaptive asks what a finite observation history justifies delivering
now. Their topology rhymes; their evidence does not. The software gates now
close at one calibrated episode and one distinct Oracle Ladder. The next
scientific gate is the held-out same-device distribution study. One
independently calibrated processing-pupil passive aberrator is unlocked only
after that gate passes; a pre-split common-path or native-microscope claim
requires a separate future contract.
