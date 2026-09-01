# One PyTorch optical core

**Status:** Accepted

**Partial supersession:** the `Precision` paragraph below is partially
superseded by `0005-fixed-double-scientific-core.md` (implemented by Ticket
02 of the final-seal initiative). The state-registration language in the
Decision bullet below is partially superseded by
`0006-state-installation-and-immutable-hosting.md` (implemented by Tickets
07 and 08 of the final-seal initiative). The rest of ADR-0001 remains in
force, and it remains the implemented truth at baseline `92a69d9`.

## Context

ChromatixNext must run on local Windows workstations on CPU and on whatever
single CUDA device is available, with ordinary PyTorch differentiation,
parameter discovery, and state loading as the user experience. Earlier
governance work (historical ADRs 0001, 0049, 0112) admitted a narrow internal
CUDA adapter seam and a four-strategy acceleration ladder with a separate
Qualification Envelope. That seam grew a second implementation surface, a
compile-success prerequisite, and an execution-strategy taxonomy that
obscured the physical reading order and duplicated scientific ownership.

The refactor collapses that surface. There is one authoritative calculation
owned by Components and one private locality for tensor kernels. A future
native implementation is still physically possible, but only as a complete,
independently qualified slice, never as a public selector that the first slice
must negotiate.

## Decision

PyTorch is the sole implementation of the optical core on CPU and CUDA.

- Every Optical Component is an ordinary `torch.nn.Module`. Component state
  follows PyTorch-native rules: a user-supplied `Parameter` stays the
  registered trainable Parameter; an ordinary tensor or number becomes a
  fixed Buffer; derived caches are non-persistent Buffers.
- Every substantive tensor calculation has exactly one PyTorch reference
  implementation, owned privately under `chromatix_next._numerics`.
  Optical equations, sampling rules, mask synthesis, reductions, and
  multi-value mixing are substantive kernels; Components delegate them to
  cohesive private modules. State registration, input validation, dtype/device
  alignment, and immutable Physical Value construction remain with their
  physical owner. The project does not create shallow one-line kernels merely
  to satisfy the seam. There is no public numerical framework, no
  Component-owned backend selection, no per-Component implementation hook,
  and no per-Component acceleration flag.
- CPU and ordinary CUDA are complete, supported execution paths. They are not
  fallback paths and not slow reference paths. The Workstation selects one
  explicitly; there is no automatic device discovery.
- No public native-acceleration selector exists. A second implementation is
  admitted only after a complete, useful Assembly slice has independently
  qualified native kernels for the affected Components. When admitted, its
  public choice must be explicit, scientifically equivalent, recorded in the
  Run Record, and free of silent partial fallback.
- Numerical caches depend only on fixed Buffers, complete Physical Value
  identity, device, and Precision. Anything that depends on a trainable
  Parameter is recomputed on every call so autograd remains complete. A generic
  cache without a production consumer is deleted rather than qualified in
  isolation.

`Precision` ∈ {`COMPLEX64`, `COMPLEX128`} is selected explicitly by the
Workstation and determines paired real/complex dtypes for a whole run. No
Component chooses or changes Precision; each Component is qualified for both
Precisions.

## Consequences

- One canonical calculation per Component; qualification is the four-layer
  Component Evidence (physical invariants, independent reference, gradient
  evidence per trainable claim, Precision consistency and any claimed native
  CUDA path).
- CPU and CUDA runs share identical declared physics and never silently
  substitute one another.
- The single implementation surface keeps the public reading order intact and
  avoids a parallel strategy taxonomy.
- A future native kernel arrives as a complete equivalent slice, not as a
  one-option selector or a hypothetical backend seam.

## Superseded history

Historical ADRs 0001, 0049, 0112, and 0113 built the acceleration seam and
strategy ladder. Their lessons are recorded in `docs/history.md`; this ADR
re-closes the seam they opened.
