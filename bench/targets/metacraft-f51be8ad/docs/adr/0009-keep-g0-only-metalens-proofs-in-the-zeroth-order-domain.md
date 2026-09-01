# 0009 — Keep G0-only metalens proofs in the zeroth-order domain

Status: accepted

Supersedes:
[ADR 0007 — Report order risk without capping the cell period](0007-report-order-risk-without-capping-the-cell-period.md).

Amends the period-selection clauses of
[ADR 0008 — Honor explicit cell constraints before advice](0008-honor-explicit-cell-constraints-before-advice.md).

Period-to-height sequencing refined by
[ADR 0011 — Let period choice precede height](0011-let-period-choice-precede-height.md).

## Context

The current low-na locally periodic metalens proofs form the complete aperture
field from the Lumerical G0 complex response. ADR 0007 allowed a multi-order
cell to continue with a caution, but G0 alone does not contain the other open
orders and therefore cannot support that complete-field claim. A future
order-resolved or near-field method may support the multi-order regime; the
current method does not.

## Decision

The current G0-only proof has one hard physical ceiling:

`physical ceiling = min(sampling ceiling, order ceiling)`

where the sampling ceiling is `wavelength / (2 * numerical aperture)` and the
order ceiling is `wavelength / (substrate index + numerical aperture)`. The
order expression remains a MetaCraft conservative derivation, not a universal
literature formula.

The compiled period limit is the greatest multiple of 10 nm strictly below
the physical ceiling. Thus 857 nm becomes 850 nm, while an exact 850 nm
ceiling becomes 840 nm. A brief constraint or design advice may select a
smaller 10 nm-aligned cell period, but it must not exceed this limit. The
compiler never rounds, clamps, or replaces a proposed period silently.

The order ceiling depends on the exact substrate index at the working
wavelength, so material evidence precedes period advice. Period advice
recommends only the period. After deterministic validation establishes that
period, the existing height domain and phase envelope may ground a separate
height advice. The brief alone owns its dimension step. Invalid or unavailable
advice leaves an honest waiting study and opens no cell sweep.

## Consequences

`multi order` remains useful language for a future method, but it is outside
the applicability of the current G0-only proof rather than a non-blocking
caution. This decision does not claim high transmission, complete phase
coverage, or local-periodic accuracy. Rust authority and its protocol remain
unchanged.
