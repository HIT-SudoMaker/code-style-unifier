---
status: accepted
---

# Use four Fixed roles with explicit physical controls

The claim-bearing Fixed Measurement matrix uses four intention-revealing
roles: `trained_phase_frontend_only`, `digital_backend_only`,
`frozen_frontend_serial`, and `joint_frontend_serial`. These names identify the
trained component, the retained topology, and the optimization relationship
rather than merely naming the origin of an intermediate tensor.

`trained_phase_frontend_only` establishes the capability and limit of one
specimen-independent trained Fourier phase. `digital_backend_only` trains the
selected digital backend directly from the degraded observation and provides
the common digital reference. `frozen_frontend_serial` initializes its front
end from the seed-matched `trained_phase_frontend_only` checkpoint, freezes
that phase, and trains the same digital backend. It therefore isolates the
consequence of presenting an optically transformed representation to the
backend. `joint_frontend_serial` starts from the same frontend checkpoint and
optimizes the phase and the same backend together, testing whether offline
co-adaptation can recover the loss or expose a complementary gain.

The three digital-bearing roles use the same backend architecture, data split,
seed set, update budget, loss, and evaluation contract. Frozen and joint serial
also share the same seed-matched optical warm start. Joint optimization remains
Fixed Measurement because the resulting phase is frozen before evaluation and
does not depend on observations from the current specimen.

`reference_arm_only`, `zero_phase_processing_arm_only`, and
`trained_phase_processing_arm_only` are retained as evaluation-only branch
controls rather than promoted to training roles. An arm-only name always means
that the other arm is blocked. The zero-phase and trained-phase interference
outputs instead contain the coherent sum of the reference and corresponding
processing fields. This vocabulary prevents the complete frontend from being
mistaken for either constituent arm and provides the intensities required for
cross-term attribution. The historical capacity ladder and eleven-parameter
backend remain archive material but do not belong to the active claim matrix.
This separates physical capacity, digital reference, representation transfer,
co-adaptation, and mechanism attribution without flattening them into one
ambiguous experiment list.

The four roles form a 36-run primary matrix: three degradation profiles by
three seeds for each role. A separate nine-run capacity challenge reuses the
`digital_backend_only` role with NAFNet-M. It is not a fifth role and does not
expand the frozen or joint serial branches. Its narrow purpose is to test
whether a larger digital-only model can match or exceed the optical-plus-small-
digital combinations; this prevents digital capacity from being confused with
an optical-front-end effect. The complete Fixed archive therefore contains 45
runs: 36 primary runs plus nine capacity-challenge runs.

The Fixed scientific protocol is frozen at this boundary. Its canonical
record preserves, for every declared profile and seed, the exact role, data and
split identity, optical configuration, branch state, phase state, trainable
parameter boundary, initialization lineage, optimization trajectory,
checkpoint identity, per-sample measurements, aggregate metrics, and runtime
status. Native bench frames are immutable source observations. Simulated
observations remain bound to their dataset sample, random realization, phase
state, and reproducible configuration. Failed, reverted, non-finite, and
unfavourable runs are recorded explicitly rather than omitted or overwritten.
Figures and tables are regenerable views of these records and never replace
them.
