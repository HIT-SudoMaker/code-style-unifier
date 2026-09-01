# 0004 — Compile proofs from claims and methods

Status: accepted

## Context

Phase, aperture, field propagation, and focus describe the current metalens slice but are not universal scientific stages. A large-na metalens may require vector recovery or optimization; a holographic metasurface concludes field reconstruction; a quasi-bic metasurface requires resonance, symmetry, radiation-channel, and quality-factor evidence; and a frequency selective surface concludes from scattering, loss, and spectral evidence. Making the current metalens sequence the architecture would recreate fixed workflows under new names.

## Decision

The public scientific language remains `brief → study → result`. Aim and objectives belong to the brief; route and proof belong to the study. Inside the pure Python compiler, an aim declares terminal claims and registered methods establish claims from prerequisite claims and evidence under explicit applicability conditions. The compiler resolves intent, composes a deterministic claim–method proof, binds ready needs late to qualified capabilities and realizations, and closes the proof only with Rust-admitted evidence.

A route is the compiled claim–method graph, not a package, executor, workflow, or solver selection. Aim modules may declare terminal claims and conclusion rules but may not own an end-to-end process. Method modules may establish one explicit scientific claim but may not own the brief-to-result lifecycle. The compiler exposes no public rule, graph, registry, plugin, reflection, dynamic-discovery, or AI-planning interface.

The current low-na metalens routes are golden proof relationships:

- propagation phase closes `focus ← scalar field ← aperture ← phase set ← fixed-height cell library ← periodic complex transmission ← material and height evidence`;
- geometric phase closes `focus ← converted and retained fields ← channel apertures ← analytic orientations ← one anisotropic cell ← Jones response and polarization convention ← material and height evidence`.

They share the compiler, runner, authority seam, phase-circle semantics, aperture contract, and qualified low-na field implementation. Their raw response, polarization, selection, channel, and acceptance evidence remain distinct.

## Consequences

Large na changes applicable methods while preserving the metalens focus claim. Holographic, quasi-bic, and frequency-selective aims add terminal claims and scientific methods without adding a second lifecycle or changing Rust. Capability, method, realization, binding, capacity, and permit remain separate meanings. Unsupported combinations stop with explicit findings; the compiler never falls back to a nearby workflow.

This decision refines [ADR 0002](0002-compile-studies-from-evidence.md) and is grounded in [the scientific compilation dimensions research](../research/2026-07-22-metasurface-scientific-compilation-dimensions.md). Its current implementation contract is [Metalens Sonnet convergence](../../.scratch/metalens-sonnet-convergence/spec.md).
