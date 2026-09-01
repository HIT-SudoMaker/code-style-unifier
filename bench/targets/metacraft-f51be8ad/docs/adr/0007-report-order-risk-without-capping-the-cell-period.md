# 0007 — Report order risk without capping the cell period

Status: superseded by ADR 0009

Amended by:
[ADR 0008 — Honor explicit cell constraints before advice](0008-honor-explicit-cell-constraints-before-advice.md).

## Context

ADR 0005 made the conservative substrate-side diffraction bound a universal
period selector. At the 355 nm and 400 nm standard briefs this reduced the
period from 630 nm and 660 nm to 200 nm and 220 nm. The resulting fabrication
domains were too narrow to exercise the intended cell-library search.

The two ceilings answer different questions. The sampling ceiling asks whether
the lattice can sample the target phase gradient. The order ceiling warns that
nonzero diffraction channels may be kinematically open. An open channel need
not carry significant power, and its existence does not make the selected G0
complex response undefined.

The primary-source evidence, derivation, numerical examples, and G0 limits are
preserved in the Research Record
[Grating-order warning and G0 evidence](../research/2026-07-27-grating-order-warning-and-g0-evidence.md).
That record supplies the scientific grounds; this ADR owns the system
decision.

## Decision

When a metalens brief leaves its cell period open, the current default is:

`period_nm = floor_10nm(sampling ceiling)`

ADR 0008 additionally permits an explicit smaller period. In both cases, the
sampling ceiling `lambda/(2*NA)` remains a hard applicability boundary for the
current locally periodic route.

The evidence-derived order ceiling `lambda/(n_sub+NA)` no longer selects the
period and never refuses compilation, height choice, sweep dispatch, or result
admission. It classifies the selected period:

- `zeroth order` when the period does not exceed the order ceiling;
- `multi order` when it does.

A `multi order` classification produces one non-blocking caution:

`higher orders possible`

Its explanation states that nonzero diffraction orders may propagate and that
the current aperture field uses only the declared solver-response channels.
The caution cites the material sample used to derive the order ceiling and is
preserved in the height-domain evidence, immutable study, solver run manifest,
and admitted result.

A caution is not a finding. It cannot make a task unready or prevent a complete
proof from reaching a result.

## Consequences

The 355 nm and 400 nm standard briefs again use 630 nm and 660 nm periods and
can exercise their intended fabrication sweeps. Both are honestly labelled
`multi order`.

G0 remains valid as a named complex response channel, but a G0-only aperture
field must not be described as the total transmitted field or, by itself, as
proof of total transmission or focusing efficiency. Future evidence may add
order-resolved power or near-field reconstruction without changing this
decision.

The sampling ceiling is an upper bound, not a universal claim that the largest
allowed period is always optimal. A future period-selection strategy may choose
a smaller period while preserving the same warning semantics.
