# Project baseline

- Status: active
- Established: 2026-07-26
- Last resolved: 2026-08-13

## Foundation

`data` and `layers` are frozen scientific building blocks.

- `data` advances sample meaning through
  `load -> prepare -> perturb -> encode`.
- `layers` exposes flat physical primitives: diffraction, lens, modulation,
  and detection.
- Experiments own composition, optical topology, control policy, and claims.
- `data/raw` is immutable and outside every cleanup operation.

This foundation does not depend on the success of any Restoration method.

## Fixed Measurement

Fixed Measurement is the sealed target-supervised route. It encodes an already
detected degraded image into an optical field, applies one
specimen-independent phase, and may connect the resulting interference
measurement to a digital restoration backend. Its claim-bearing matrix is:

1. `trained_phase_frontend_only`;
2. `digital_backend_only`;
3. `frozen_frontend_serial`;
4. `joint_frontend_serial`.

The 36-run primary matrix uses NAFNet-S for every digital-bearing role under
one data, seed, budget, loss, and evaluation contract. An additional nine-run
NAFNet-M digital-only capacity challenge tests whether a larger conventional
backend changes the conclusion without creating a fifth role. Both serial
roles start from the profile- and seed-matched trained frontend checkpoint.
Physical attribution records
`reference_arm_only`, `zero_phase_processing_arm_only`, and
`trained_phase_processing_arm_only` separately from the corresponding
reference-on interference outputs.

Matched studies did not establish an advantage over credible digital
neural-network baselines. The result rejects that fixed, specimen-independent
measurement architecture as the project's main contribution; it does not
reject coherent optical control. The archived route now serves three roles:

1. reproducible historical evidence;
2. a strong static optical baseline;
3. the capability--limitation bridge that motivates measurement-conditioned
   adaptation.

The reproducible record is:

- implementation: `experiments/restoration/fixed_measurement`;
- frozen protocol: `experiments/restoration/fixed_measurement/protocol_assets`;
- evidence: `results/restoration/fixed_measurement`;
- formal Interface: `experiments.restoration.fixed_measurement.run_fixed_measurement`;
- immutable optical record Interface:
  `experiments.restoration.fixed_measurement.record_fixed_optical_states`.

The formal archive contains 45 native studies: 36 primary studies and nine
NAFNet-M capacity-challenge studies. Existing weights were transferred without
retraining; all native study artifacts are covered by the archive integrity
gate. Runtime loading uses only the four scientific role directories and
performs no historical name translation. The archived FMD split and operating
point remain the data and geometry identities. Named optical-control records
and new figures may be regenerated from those inputs and native checkpoints;
regeneration is evaluation, not training. Historical source results remain
outside the runtime contract until the unified held-out evaluation is sealed.

## Adaptive Measurement

Adaptive Measurement is the active **correctability-aware intelligent optical
front end**. It is not a post-detection neural restoration method. Its
claim-facing sequence is:

1. keep the mechanical delay arm fixed and calibrate its effective phase;
2. acquire reference-on observations using declared processing-SLM phase
   states, including global piston diversity;
3. infer a correction-relevant state or useful delivered action from the
   measurement history alone;
4. predict prospective benefit, harm, uncertainty, and complete cost;
5. choose `correct`, acquire another information-bearing `probe`, or `abstain`;
6. load and settle a hardware-feasible phase-only action;
7. acquire a causally later raw reference-on science observation;
8. use reference-off acquisition only as a structural mechanism ablation.

Learning may amortize inference, model residual mismatch, calibrate risk, or
select probes. Simulated aberration truth is evaluator-only. A network-generated
image is not part of the method.

The default transparent protocol is `4 + 1`: four quadrature phase-shifted
calibration observations and one later science observation. The adaptive
ceiling is `8 + 1`: at most eight independently read calibration observations
and one later science observation. Frame count is only one coordinate of the
complete budget.

The current scope is local, quasi-static, narrowband coherent transmission or
phase imaging and initially targets processing-arm differential aberration.
Common-path specimen aberration, fluorescence, strong multiple scattering, and
fast live dynamics require different evidence and are not implied.

## Architecture

The dependency direction is:

```text
data pipeline        flat optical layers
       \                  /
        shared restoration physics
          /              \
 fixed_measurement   adaptive_measurement
```

Shared Restoration owns only stable physical and evidence Interfaces used by
both research lines: requested and delivered phase, pupil aberration semantics,
observation identity, and measurement-neutral value contracts. Fixed and
Adaptive own their protocols, state transitions, orchestration, and evidence.
Neither experiment subpackage imports the other; shared Restoration imports
neither experiment.

The target Adaptive deep Module exposes one episode Interface and accepts
simulation or bench acquisition and phase-delivery Adapters. Probe scheduling,
history, estimation, correctability, stopping, delivery, later acquisition,
and evidence capture remain hidden implementation. A new seam is introduced
only when at least two meaningful Adapters exist.

Fixed training, optics, protocol, and evidence code now resides entirely under
`fixed_measurement`. The former root compatibility quarantine has been
removed. Both research lines use the shared two-arm propagation contract;
neither imports the other's protocol implementation.

## Evidence gates

Adaptive Measurement advances only if:

1. the relative-transfer model and phase-shifting identity survive noise,
   drift, registration, and controlled bench validation;
2. a delivered phase-only oracle establishes material headroom;
3. a useful action is identifiable without policy access to aberration truth;
4. a newly acquired raw reference-on frame improves over safe, sham,
   opposite-sign, fixed-mask, AO, and digital comparators;
5. active probing beats the strongest fixed/Fisher codebook under matched
   photons, reads, SLM states, settling, computation, and wall time;
6. the correctability estimate remains calibrated under specimen, aberration,
   SNR, LUT, polarization, registration, and drift shifts;
7. abstention reduces harmful correction at nontrivial coverage;
8. held correction lasts long enough to amortize calibration;
9. reference-off ablation supports the interferometric mechanism.

Failure of headroom, identifiability, or prospective optical benefit kills the
route. Failure of the active-versus-fixed gate removes the adaptive-probing
claim. Failure of risk calibration removes the intelligent selective-action
claim. Until calibration passes, use `correctability estimate`, not
`correctability certificate`.

## Workspace

- Preserve `data/raw`, Fixed code, protocol assets, results, and dirty worktrees.
- Keep project Nature skills under `.agents` and their `.claude` junctions.
- Keep `refresh_workspace.py` unchanged as an ignored local archival tool; do
  not run it as routine cleanup.
- Delete only explicitly verified, reproducible cache state.
- Keep project prompts under `docs/prompts` and use `docs/restoration/README.md`
  as the current Restoration entrance.
- Keep root `CONTEXT.md` as the terminology ledger and colocated `README.md`
  files as Module Interfaces.
