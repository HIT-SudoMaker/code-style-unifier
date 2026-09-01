# Fixed-double scientific core

**Status:** Accepted (implemented by Ticket 02 of the final-seal initiative).

**Partial supersession of:** the `Precision` paragraph in
`0001-one-pytorch-optical-core.md`. With Ticket 02 landed, the public
`Precision` selector, every precision selector/field, and the four paraxial
ray-transfer `dtype`
parameters are removed; this ADR is now the implemented truth for numerical
dtype.

**Directional-inventory supersession:** the historical public-action counts
that followed this ADR through ADR-0008, ADR-0009, and ADR-0010 are superseded
by the implemented directional cutover. Current truth is twenty-four Optical
Component actions. Separately, the public directional surface contains three
state-only owners, three closed Terminal/diagonal enums, and two
Assembly-issued Encounter reference types. The fixed-double regime and the
rest of this ADR stay in force.

## Context

ADR-0001 selected paired real/complex dtypes through an explicit
`Precision ∈ {COMPLEX64, COMPLEX128}` selector chosen by the Workstation for a
whole run. That selector is the only public numerical branch in the system: a
single-precision input or checkpoint may today be silently widened, a
`torch.get_default_dtype()` change can alter constructed state, and old
single-precision evidence cannot qualify a sealed fixed-double product. The
final seal must collapse that branch.

## Decision

The sealed product is fixed double.

- Every public real floating quantity is `torch.float64`.
- Every public complex quantity is `torch.complex128`.
- Integer, boolean, and `uint8` status values retain their physical dtype.
- Python real/complex scalars materialize as `float64`/`complex128`.
- `torch.get_default_dtype()` never changes product behaviour.
- Explicit `float32`/`complex64` public inputs are rejected, never widened.
- User Parameters must already have the required dtype and retain identity.
- Old single-precision full-module state is rejected during host preflight.
- Old single-precision `state_dict` is rejected by `install_state` before
  project-state mutation.
- The dynamic tensor Optical Path Reference continues to use one device-local
  `float64` accumulator; this is not a second selector and does not widen all
  module state.
- `Run Record` carries no precision or decorative fixed-format field.

The public `Precision` selector is removed, not deprecated. There is no
precision argument, precision property, precision field in `RunRecord`,
compatibility alias, one-option numerical-format field, autocast mode, or
fallback.

## Why this is surprising

ChromatixNext publicly committed to supporting both `COMPLEX64` and
`COMPLEX128` as first-class execution regimes: ADR-0001 made `Precision` an
explicit Workstation choice, every Source carries a precision-resolution tail
segment, and existing Component Evidence is split across the two regimes. This
ADR deletes that public contract rather than narrowing it. It is also
surprising because the project simultaneously spends the memory budget to
remove a numerical branch that, on paper, CUDA could have kept serving.

## Rejected alternatives

- **Deprecate `Precision` and keep an internal one-option enum.** Rejected: a
  decorative field with one legal value violates one-fact-one-owner and leaves
  a public-facing name that no longer maps to a decision.
- **Silently promote `float32` inputs to `float64`.** Rejected: silent
  promotion hides a broken checkpoint or a user error and is the precise
  failure class (`F03`) this decision must close.
- **Keep both Precisions and pin `RunRecord` to one.** Rejected: it preserves
  the branch that lets single-precision state pass.
- **Tensorize every fixed scalar.** Rejected by ADR-0002 already; fixed
  authored lengths may remain Python floats until Tensor arithmetic begins.

## Important cost

Fixed double roughly doubles real and complex tensor memory and throughput on
frame-sized buffers, especially on CUDA. No performance-superiority claim is
made. The cost is paid deliberately to remove a numerical branch, strengthen
reproducibility, and make checkpoint dtype a hard preflight invariant rather
than a runtime negotiation.

## Implementation status

Implemented by Ticket 02 (`Cut the system to fixed double`). The public
`Precision` selector is removed, every Source precision argument and
`RunRecord.precision` field is gone, the four paraxial ray-transfer `dtype`
parameters are
removed, `_numerics/_dtypes.py` is deleted (its pair mapping became trivial
under one numerical regime), and `host()` runs a fixed-double preflight that
rejects any `float32`/`complex64` registered state before device movement.
Single-precision `state_dict` rejection is owned by Ticket 07 (`install_state`)
and remains out of scope here.

## Consequences

- One numerical regime; old two-Precision evidence cannot qualify the new
  contract and must be regenerated under fixed double (Tickets 11–13, 16).
- `_unit_phasor_from_cycles` (ADR-0003 phase work, Ticket 03) returns
  `complex128` only.
- **Amendment (2026-08, Ticket 10 of the final-seal initiative).** The prior
  hard `<22,304` production-line gate and the `final LOC > 14,000`
  independent-review trigger are superseded and removed from active
  governance. They are not replaced by another arbitrary numeric threshold,
  and no correctness, performance, or simplicity inference is made from LOC
  alone. The active production-growth rule is: deterministic production
  physical-line movement is measured and reported, and any net production-line
  increase requires an independent Depth/Leverage/Locality and deletion-test
  review; such an increase is not automatically a failure. The hard budgets
  that actually govern growth are two top-level public exports (`Workstation`
  and `install_state`), twenty-four public Optical Component actions, three
  directional owners, three closed enums, two Encounter references, three
  production seams (`workstation.py -> optics -> _numerics`), one dependency
  direction, no cycle, and no new public framework. Fixed double introduces
  no line-budget warning.
