# State Installation and immutable hosting

**Status:** Accepted — Ticket 07 (`Establish State Installation`) and
Ticket 08 (`Make hosted ownership immutable`) are both implemented on the
`scientific-foundation-final-seal` branch. Ticket 08 retired hosted
exact-alias loading inside `_ownership.py` and the
`workstation_state_dict_alias_conflict` identity, and closed direct hosted
native loading on the root and every claimed submodule via the
registry-gated `_HostedStateLoadGuard`.

**Partial supersession of:** the hosted-load behaviour that
`0003-optics-numerics-workstation-boundary.md` did not constrain in its
Workstation Host Claim paragraph, and the state-registration language in
ADR-0001's Decision bullet. ADR-0001 and ADR-0003 remain the implemented
truth at baseline `92a69d9`; this ADR records the future contract only.

## Context

ADR-0003 admitted hosted exact-alias loading through ownership hooks and
treated direct `root.load_state_dict(...)` as an unsupported but unenforced
escape hatch. As a result, hosted storage identity can today change while an
ownership claim is live, a single-precision `state_dict` entry can be silently
cast into a `float64` slot, and there is no single full-tree owner that
validates dtype, shape, alias partition, or schema before any project state is
mutated. The final seal must split state installation from hosting and make
hosting immutable.

## Decision

`install_state(root, state_dict) -> None` is the only supported checkpoint
installation interface. It is strict (`strict=True`, `assign=False`) and
unhosted-only.

- The complete root must be unhosted.
- Missing, unexpected, malformed, meta, `float32`, and `complex64` entries
  fail; partial registered-storage views fail.
- Incoming values for a target exact-alias group must be equal.
- Validation covers aliases across sibling subtrees of a transparent root.
- Ordinary target shapes must match, while a Source-local capsule may approve
  and stage its explicitly defined variable-spectrum resize.
- Parameter identity is unchanged after success.
- Source payload/schema preparation is validated before resize or copy.
- Four exact Sources and Conic use one closed private planning route owned by
  `_state_installation`; every other product/external module uses default
  PyTorch persistence.
- External persistence overrides/hooks, lazy state, Tensor subclasses, cyclic
  registration, and swap-module native mode reject before mutation.
- The one native call is the unbound
  `torch.nn.Module.load_state_dict(..., strict=True, assign=False)`.

`install_state` lives at the existing execution seam. A cohesive private
`_state_installation` support module may hold the full-tree implementation and
depends on `_ownership` for the shared unhosted critical section. This is
private root support, not a fourth production seam. Optics and `_numerics`
never import it.

### Immutable hosting

While a root is hosted, the following identities are immutable: module-tree
composition, Parameter and Buffer identity, storage `_cdata`, offset, shape,
stride, dtype, device, view, and alias partition.

- Hosted `load_state_dict` on the root or any claimed submodule is forbidden.
  A dynamically installed ownership guard must be first in the load-prehook
  order and reject before project/user hooks, project state copy, or Source
  resize.
- Modules whose persistence override can bypass that guard are rejected at host
  preflight.
- Allowed while hosted: forward execution, autograd, optimizer or explicit
  in-place Parameter value updates, and explicitly supported in-place Buffer
  value evolution that preserves the claim fingerprint.

### Honest atomicity

Neither operation is universal ACID.

- Host: ownership/dtype/view/structure preflight occurs before placement;
  target allocations are staged before registered tensor rebinding; preflight
  or staging failure leaves no claim and no project registered-state mutation;
  inert hosted-load guards are installed before rebinding; successful
  rebinding completes before the immutable claim is recorded; failure never
  leaves a live claim.
- State Installation: product-owned errors occur before project-state
  mutation; external persistence overrides and hooks are rejected. Unexpected
  native/infrastructure failure may restore project-owned registered state,
  but no transactionality is claimed for arbitrary side effects outside the
  supported persistence contract.

## Why this is surprising

ADR-0003 deliberately tolerated hosted exact-alias loading as a convenience
and treated direct `load_state_dict` as a soft escape hatch. This ADR removes
that tolerance: the only safe installation path is unhosted plus
`install_state`, and hosted state loading is forbidden entirely. It is also
surprising because the project adds one real public lifecycle interface while
simultaneously deleting the decorative `Precision` selector, so the public
top-level name count does not grow.

## Rejected alternatives

- **Leaf-only dtype hooks.** Rejected: a final-child `float32` entry would be
  cast after an earlier sibling already mutated (`F03`).
- **Mutable lease or dual owners.** Rejected: any mutable hosting identity
  breaks the immutability invariant that lets `release` reuse the original
  claim rather than rescan a possibly-corrupted tree.
- **Monkey-patch `torch.nn.Module.load_state_dict`.** Rejected: unsupported
  escape hatch; the project does not pretend to override arbitrary user roots.
- **Universal public base class to make direct loading impossible.** Rejected:
  cannot control arbitrary user roots; adds a universal base the architecture
  forbids.
- **Transactionality claim for arbitrary user side effects.** Rejected: the
  contract owns product-recognised failure classes only.

## Important cost

One new public top-level function (`install_state`) is added. The cost is
offset by removing `Precision`, so the public top-level name count remains
exactly two. Implementers must also reject previously tolerated hosted-load
paths, which may surface previously hidden user errors as hard failures.

## Implementation status

Ticket 07 (`Establish State Installation`) is implemented: `install_state` is
public at the top level (`__all__ = ["Workstation", "install_state"]`), backed
by a private `_state_installation.py` that owns the closed
`_plan_state_installation -> _StateInstallationPlan` seam and the 14-step
critical-section order, delegating to the four Ticket-04 Source planners and
the Conic-owner `_validate_conic_state_installation`. The unhosted-only
contract is enforced by `_ownership._run_unhosted_state_installation`. The
Source leaf-load hooks (`_SourceStateLoadPreHook`) and their
`*_state_load_subject_invalid` / `*_named_physical_state_incomplete` identities
have been retired; cross-spectrum Source loads now go through `install_state`.

Ticket 08 (`Make hosted ownership immutable`) is implemented: hosted
exact-alias loading inside `_ownership.py` and the
`workstation_state_dict_alias_conflict` identity are retired. Hosted
`load_state_dict` on the root or any claimed submodule is closed entirely by
the zero-state registry-gated `_HostedStateLoadGuard`, which raises
`workstation_hosted_state_load_forbidden` before any project copy or Source
resize. `_AliasConsistencyLoadHook` was renamed to `_HostedStateLoadGuard`
(the existing zero-state, picklable, module-level hook was already the
implementation of the brief's "at most one inert guard per slot" in Ticket
07's `install_state`; only its behaviour changed from alias-conflict check on
the root to load rejection on every claimed module). Host preflight now
rejects modules that override or instance-shadow `load_state_dict` or
`_load_from_state_dict` with `workstation_host_persistence_unsupported`. The
immutable weak claim (`_ImmutableHostedRootClaim`) is activated only after
staging, rebinding, and post-placement identity-graph verification all
succeed; any post-rebind failure restores the frozen original registered
tensor graph and removes every inert guard. Alias consistency during legal
loading belongs only to `install_state`.

### PyTorch-version coupling: hosted-load guard ordering

The hosted-load guard (`_HostedStateLoadGuard`) must fire **before** any
project or external `_load_state_dict_pre_hook`, otherwise an external hook
could mutate project state before the guard rejects the load. PyTorch (2.12)
implements `_load_state_dict_pre_hooks` as an `OrderedDict` and fires hooks in
insertion order; `_install_hosted_state_load_guards` therefore registers the
guard and then calls `move_to_end(handle.id, last=False)` to move it to the
first position before every project/external hook. PyTorch also wraps each
registered pre-hook in `_WrappedHook`, so dedup and `install_state`'s "at
most one inert guard per slot" check unwrap via `getattr(hook, "hook", hook)`.

This ordering is a reviewed **PyTorch-version coupling**: it relies on
`_load_state_dict_pre_hooks` remaining an `OrderedDict` whose iteration order
is the pre-hook firing order, on `register_load_state_dict_pre_hook` returning
a `RemovableHandle` whose `.id` is the dict key, on `move_to_end` being
available, and on the module-first calling convention (`with_module=True` is
the only mode in 2.12). A future PyTorch that switches `_load_state_dict_pre_
hooks` to a non-`OrderedDict` mapping, changes the handle id contract, or
alters the calling convention would require revisiting this ordering
discipline.

## Consequences

- The execution state machine is
  `UNHOSTED --install_state--> UNHOSTED --host--> HOSTED --run--> HOSTED
  --release--> UNHOSTED`.
- `install_state` is the sole checkpoint authority; hosted Parameter values
  remain trainable but their registered identity, storage, view, dtype, and
  device remain fixed.
- The private ownership module exposes only the lifecycle operations needed by
  Workstation and State Installation.
