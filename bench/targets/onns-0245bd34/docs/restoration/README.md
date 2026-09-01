# Restoration documentation

This directory is the short entrance to the active Restoration programme. It
does not duplicate the long-form derivation or historical evidence.

## Active reading order

1. [`intelligent-front-end.md`](intelligent-front-end.md) — current manuscript
   argument, physical model, algorithm, claim boundary, and figure logic.
2. [`four-day-endgame.md`](four-day-endgame.md) — the bounded design and
   simulation closure plan.
3. [`../restoration-research-design.md`](../restoration-research-design.md) —
   canonical long-form theory, evidence ladder, and comparison policy.
4. [`../adr/0020-adopt-a-fixed-reference-correctability-aware-intelligent-front-end.md`](../adr/0020-adopt-a-fixed-reference-correctability-aware-intelligent-front-end.md)
   — the durable decision that resolves fixed-delay and reference-on operation.
5. [`../research/README.md`](../research/README.md) — active supporting research
   and superseded narrative provenance.

## Code ownership

The code architecture remains the one frozen by ADR-0019:

```text
data pipeline        flat optical layers
       \                  /
        shared restoration physics
          /              \
 fixed_measurement   adaptive_measurement
```

Shared Restoration owns stable physical and evidence Interfaces. Fixed and
Adaptive own their protocols, state transitions, orchestration, and claims.
The Fixed relocation is complete: its training, protocol, algorithm, and
evidence code is contained under `fixed_measurement`. The physical geometry,
Fourier relay, aperture, and coherent dual-arm propagation live only in
`optical_bench`; Fixed and Adaptive call its same public propagation operation.

## Protected assets

- `data/raw`, formal Fixed results, protocol assets, and registered worktrees
  are evidence, not cleanup targets.
- `refresh_workspace.py` is a local, ignored archival tool. It is retained
  unchanged and is not part of normal development or cleanup.
- Project Nature skills under `.agents` and their `.claude` junctions are
  intentional project tooling.
