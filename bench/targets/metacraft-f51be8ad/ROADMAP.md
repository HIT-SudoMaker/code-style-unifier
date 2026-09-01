# Roadmap

The current metalens slice supports propagation and geometric phase across
low and high numerical aperture. Low-NA routes use finite 8-, 12-, and
16-state realizations with componentwise angular-spectrum evaluation. High-NA
routes use pointwise assignment, sampled reference-surface evidence, qualified
vector angular-spectrum propagation, and direct-Debye ideal-field comparison.

The four external `MetalensBenchmarkCase` values span the propagation /
geometric by low- / high-NA two-by-two matrix. They are reviewed comparison
truth, not proof that every case has been executed.

## Next evidence

After the Sonnet seal, run all four cases through recorded Adapters and verify
the established `3 + 3 + 1 + 1` Result shape, deterministic
`select -> conduct -> compare` flow, and external benchmark-comparison
documents. This is a deterministic example-case proof; it adds no production
benchmark meaning.

Executing all four cases with Native Lumerical is separate future work. It
requires explicit approval of cost and scientific value and is not implied by
the five-solve Native qualification/receipt gate.

## Planned research, not current capability

1. bounded optimization for high-NA sitewise recovery;
2. holographic metasurface synthesis with optimizer-backed sequence matching;
3. frequency selective surface studies;
4. quasi-BIC metasurface studies with operating band, resonance mechanism,
   radiative channel, and quality-factor objectives;
5. additional external solver Adapters, including CST, only after a real
   installation and license contract exists.

These additions belong to Python and may add aim-owned scientific types,
compilers, evaluators, and product Adapters. They do not add Rust authority
concepts. Optimization enters only behind a route-specific proof obligation
with an objective and stopping evidence; it is never a universal workflow
layer or placeholder.

The roadmap reserves seams, not code. No future aim enum, empty Adapter,
generic solver Interface, optimizer framework, plugin registry, or
compatibility path is added before a concrete second implementation proves
the variation.
