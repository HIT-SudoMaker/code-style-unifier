# Example-owned research workflows

**Status:** Accepted

## Context

The legacy architecture treated inverse problems, optimization, loss, and
iteration history as a project concern: it separated forward models from
optimization problems through governance types (historical ADR 0027), tracked
reconstruction coverage through a forty-obligation Ledger (0186), and bound
qualification, scenarios, and evidence to a product evidence role (0195,
0227). That made research workflow look like a second scientific subsystem
that the platform had to own.

The refactor moves every research workflow out of the installed package and
into Examples.

## Decision

- Optimization, loss, iteration history, and optimizer selection belong only
  to Examples. An Example chooses trainable values, defines an objective,
  applies an ordinary PyTorch optimizer, and records its own history around
  ordinary Optical Components or one Assembly.
- There is no project optimization framework, no default optimizer, no
  inverse-problem runtime, and no graph-owned loss. Shared optimization
  support may be extracted only after multiple real Examples establish the
  same durable need.
- Each Example is one source-distributed executable teaching case that asks
  one physical question through natural Optical Components or one Assembly,
  with paired English and Chinese documentation and exact scientific
  provenance.
- Examples are the only project form for teaching, experimental demonstration,
  optimization workflows, and capability display. They add no experiment
  runtime role. Example smoke tests run deliberately small forms of each
  published Example through its public entry; they do not duplicate Component
  Evidence.
- The canonical teaching distribution is the source distribution, not a second
  runtime package. Runtime wheels contain the production package and the
  Release Descriptor; they do not export Example symbols from
  `chromatix_next` or install a parallel Example API.

The product platform is the optical core plus the Workstation; the only
user-facing companion is the source-distributed Example suite.

## Consequences

- Inverse problems remain ordinary PyTorch workflows assembled from the
  optical core, not a second scientific subsystem.
- The installed package stays compact and free of research workflow coupling.
- Examples verify the public researcher path without becoming a second
  validation framework; scientific correctness stays in Component Evidence
  and ordinary tests.
- A future Benchmark may measure an unchanged Example as a thin repository
  tool, but it does not become a product role.

## Superseded history

Historical ADRs 0013, 0027, 0045, 0190, 0191, 0203, 0204, 0205, 0206, 0207,
0208, 0209, 0210, 0211, 0212, 0213, 0214, 0215, 0216, 0217, 0218, 0219,
0220, and 0227 built the Example and product-surface decisions inside the
legacy tree. Their lessons are recorded in `docs/history.md`.
