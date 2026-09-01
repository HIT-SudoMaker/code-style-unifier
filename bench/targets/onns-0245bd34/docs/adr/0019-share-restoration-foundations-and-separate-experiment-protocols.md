---
status: accepted
---

# Share restoration foundations and separate experiment protocols

The `experiments/restoration` root owns only stable physical and evidence
semantics that are used by both research lines: phase commands, delivered
phase states, pupil aberrations, and independently identified optical
observations. `fixed_measurement` and `adaptive_measurement` own their own
protocols, state transitions, orchestration, and result trees.

The dependency direction is one way. Experiment-specific Modules may depend
on shared restoration Modules, `data`, and the flat optical primitives in
`layers`. Shared restoration Modules do not depend on either experiment
subpackage, and the two experiment subpackages do not import one another.
Adapters connect a protocol to the shared Interfaces without transferring
protocol-specific invariants into the root.

This decision supersedes the part of ADR-0018 that described the fixed and
adaptive implementations as entirely independent. Their evidence remains
independent, but their stable vocabulary and physical contracts are shared.
In particular, the fixed replay invariant that reconstructs a coherent field
from a degraded intensity remains Fixed-only and cannot become an Adaptive
input contract.

We reject a shared experiment assembler, training engine, policy, or universal
scene object. We do not reject the shared physical bench: ADR-0024 freezes that
bench as the common dependency beneath both protocols. This keeps optical
truth singular while causal and optimization semantics remain separate.

## Resolved state

The ownership migration is complete. Fixed training, optics, protocol, and
evidence code now lives under `fixed_measurement`; Adaptive code lives under
`adaptive_measurement`; and the root is restricted to the shared physical and
evidence allowlist. The former root compatibility exports and role-translation
path have been removed. Both protocols now call the public `optical_bench`
propagation operation while preserving their different input and decision
contracts. Low-level topology, Fourier mapping, and aperture construction are
hidden behind that Interface.
