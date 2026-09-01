# 0005 — Derive the cell period from the zeroth-order condition

Status: superseded by [ADR 0009](0009-keep-g0-only-metalens-proofs-in-the-zeroth-order-domain.md)

## Context

The 355 nm propagation sweep ran at a 630 nm period — the Nyquist sampling
bound `lambda/(2*NA)` — and produced evidence in the multi-order regime: nine
propagating transmitted orders, with zeroth-order power as low as 0.37%. The
phase library had recorded one Fourier coefficient of a multi-order field. The
compiled period rule lacked the diffraction bound entirely, and a pure
compiler cannot supply it: the bound needs a refractive index, which is
evidence.

No primary source states one canonical rule. The zeroth-order-grating
condition `P/lambda <= 1 / [max(n_i, n_t) + n_i * sin(theta)]` (Delacroix et
al., Proc. SPIE 7731, 77314W (2010)) binds both media at normal incidence;
Ansys states only the Nyquist condition; metalens practice judges both sides
(Arbabi et al., Nat. Nanotechnol. 10, 937 (2015)) or treats substrate-side
leakage as conservative loss (Byrnes et al., Opt. Express 24, 5110 (2016)).
No primary source argues the substrate condition may be dropped. The
literature facts, derivation, assumptions, and applicability limits behind
this decision are preserved in the Research Record
[Zeroth-order period rule](../research/2026-07-26-zeroth-order-period-rule.md).
That record establishes scientific grounds; this ADR alone owns the accepted
system decision.

## Decision

The physical cell period is bounded by two ceilings and floored to 10 nm:

`period_nm = floor_10nm( min( sampling ceiling, order ceiling ) )`

- The **sampling ceiling** is the Nyquist bound `lambda / (2 * NA)`. It is
  the demoted meaning of `CellPolicy.period_nm` and stays in the compiler.
- The **order ceiling** is `lambda / (n_sub + NA)` — the real-space form of
  the light-cone criterion `G >= k + k0`, evaluated with the solver-native
  substrate index at the brief wavelength, the whole-aperture numerical
  aperture, and the denser bounding medium. It suppresses every nonzero
  propagating order in both bounding media under the lens's worst-case local
  deflection. It lives in evidence: the height domain derives and retains it,
  citing the index sample it used.

This rule is **derived, not cited**. Future readers must not treat
`lambda/(n_sub + NA)` as a literature-standard formula; it follows from the
light-cone criterion plus the conservative choice to keep the substrate
condition, and this ADR is its provenance.

The enforced state is the `order regime` value `zeroth order`; the violated
state is `multi order`. The term "single order" is avoided — it collides with
published usage (single-order transmission gratings, J. Opt. Soc. Am. A 33,
1641 (2016)). The term "admissible period" is avoided — it collides with the
authority language `admit`/`admitted`/`admission`.

## Consequences

At the standard briefs the order ceiling binds (355 nm -> 200 nm,
400 nm -> 220 nm) and the Nyquist bound is nearly toothless. Every current
standard brief then refuses on candidate count before phase span is ever
examined; which constant may honestly move is a separate decision
([the counting wall](../../.scratch/order-regime-and-phase-envelope/issues/14-the-counting-wall.md)).
Zeroth-order operation is a validity floor for the periodic-transmission
phase library, not an efficiency guarantee. An empty domain at the order
ceiling is the finding `zeroth_order_domain_empty`, which names the ceiling,
the index sample, and the per-height candidate counts, so a human can act on
the refusal.
