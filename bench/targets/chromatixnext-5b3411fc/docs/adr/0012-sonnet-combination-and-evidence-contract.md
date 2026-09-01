# Sonnet Combination language and evidence contract

**Status:** Accepted — implemented present truth

## Context

ChromatixNext separates authored topology, optical policy, numerical support,
and Workstation execution. Before this decision landed, its two Wave
Combination actions did not speak with equal precision: `CoherentCombination`
combined two `OpticalField` values, while the action then named
`IncoherentCombination` only added two already-detected `Intensity` values. It
owned no random-field model, mutual coherence, or detector integration model.

The former generic `input_1` and `input_2` ports hid which Physical Value
crossed the interface. Optical Path Reference arithmetic was also divided
between a numerical owner and a single-consumer forwarding module. The atomic
migration recorded here has landed: the language is Physical-Value-specific,
the numerical owner is deep, and the failure boundaries are explicit.

## Problem

1. `IncoherentCombination` claims more physical knowledge than its inputs can
   establish. Two intensities do not prove that their underlying fields are
   mutually incoherent.
2. Numbered ports obscure whether an action consumes fields or intensities.
3. `POWER` and `RELATIVE` intensities carry different dimensional promises;
   accepting both is useful, but mixing them is not meaningful.
4. A cross-device tensor operation could leak a backend exception instead of
   failing at the Combination applicability boundary.
5. `_numerics/combination.py` was a shallow, single-consumer forwarding seam;
   the underlying Optical Path Reference algebra already has a natural owner.
6. Function/Optical Component and Wave/Ray pairs need a shared cognitive
   rhythm without being forced into physically false mirrored implementations.
7. Repeated tests can increase maintenance without adding an independent
   scientific failure mode.

## Principle

- Name an action for the Physical Value and transformation it actually owns.
- Validate applicability and placement before numerical mixing.
- Keep one physical fact under one owner, and deepen a real seam before adding
  another abstraction.
- Use natural semantic symmetry, not implementation mirroring.
- Preserve exact domain boundaries: Wave phase is not Ray power, and a
  Function equation is not an Assembly adapter.
- Retain minimum sufficient evidence: one decisive scientific witness per
  claim, plus only the integration evidence needed to prove a distinct seam.
- Prefer explicit rejection over automatic conversion, silent transport, or
  metadata inference.

## Architecture

### 1. Public Combination language

The implemented public contracts are:

```text
CoherentCombination(field_1, field_2) -> OpticalField
ports: `field_1` / `field_2`

IntensityCombination(intensity_1, intensity_2) -> Intensity
ports: `intensity_1` / `intensity_2`
```

The corresponding Functions use the same Physical Value nouns:
`coherent_combination(field_1, field_2)` and
`intensity_combination(intensity_1, intensity_2)`.

The migration from `IncoherentCombination` to `IntensityCombination` is
atomic. The old class, Function, module, exports, calls, ports, and stable
error identities leave the active API together. There is no alias, shim,
`__getattr__`, or compatibility period. The current inventory is twenty-four
Optical Component actions. Separately, the public directional surface contains
three state-only owners, three closed Terminal/diagonal enums, and two
Assembly-issued Encounter reference types.

### 2. Intensity Combination physics

Intensity Combination means that the caller has already chosen the observable
domain. It does not determine mutual incoherence. Addition is physically
applicable when the cross-coherence term is zero on the target statistical or
integration scale, or when the two inputs have been independently detected:

```text
<|E1 + E2|^2> = I1 + I2 + 2 Re <E1* E2>
<E1* E2> = 0  =>  I_total = I1 + I2
```

The action therefore adds compatible observables; it does not reconstruct or
invent phase, polarization, spectrum, medium, Source Lineage, or Optical Path
Reference.

Normalization is explicit:

- `POWER + POWER` is a physical W/m² sum.
- `RELATIVE + RELATIVE` is valid only when the caller has placed both inputs
  on one explicit common dimensionless scale.
- Any mixed normalization is rejected.
- There is no automatic conversion, no renormalization, and no metadata
  inference.

The two `Intensity.values` tensors must share one device. A mismatch fails
before addition with `intensity_combination_device_mismatch`.

### 3. Coherent Combination process

The implemented cognitive and execution order is frozen as:

```text
validate fields -> collect physical findings -> collect placement finding -> fail before numerical mixing -> choose field_1 reference -> express field_2 in that reference -> add envelopes -> transform field_1 outline
```

The existing nine physical coherence findings keep their order and ownership.
Device placement is checked after those physical findings as an execution
compatibility fact, not represented as a tenth coherence dimension. No path
may move an input implicitly: the rule is no silent `.to()`.

Choosing the first field as the destination reference is an ordered
representation policy, not a physical preference. Swapping the inputs may
change the returned envelope's reference representation, but re-expression in
one common reference must yield the same physical field and a gauge-equivalent
observable.

### 4. Stable failure identities

All compatibility failures continue to be carried by `AssemblyError`. The
active Combination placement identities are:

- `coherent_combination_device_mismatch`
- `intensity_combination_device_mismatch`

Intensity Combination identities migrate atomically:

```text
incoherent_combination_intensity_1_invalid -> intensity_combination_intensity_1_invalid
incoherent_combination_intensity_2_invalid -> intensity_combination_intensity_2_invalid
incoherent_combination_grid_mismatch -> intensity_combination_grid_mismatch
incoherent_combination_normalization_mismatch -> intensity_combination_normalization_mismatch
incoherent_combination_axis_mismatch -> intensity_combination_axis_mismatch
```

This is a deliberate contract migration; old identities are not aliases.

### 5. Optical Path Reference numerical owner

`_numerics/optical_path_reference.py` is the single numerical owner for
normalization, accumulation, reference re-expression, and reference-local
envelope addition. Its precise implemented interfaces include:

```python
express_envelope_in_optical_path_reference(
    *,
    envelope,
    wavelengths,
    source_reference_lengths,
    destination_reference_lengths,
)

sum_envelopes_in_optical_path_reference(
    *,
    destination_envelope,
    added_envelope,
    wavelengths,
    destination_reference_lengths,
    added_reference_lengths,
)
```

The module accepts numerical values, never `OpticalField`, and owns no
coherence policy, Source Lineage, Combination errors, or output outline. It
preserves cycles-only phase, device-local float64 reference arithmetic,
complex128 envelopes, gradients through Tensor references, and no input
mutation or device fallback. The migration deleted
`_numerics/combination.py`; no re-export or compatibility alias remains.

### 6. Natural symmetry and directional Terminals

Function owns equations and applicability. Optical Component owns registered
state, roles, and Assembly adaptation while delegating the equation to its
Function. This is natural semantic symmetry, not implementation mirroring.

Wave and Ray actions use comparable public intent and invariant language only
where their physics is comparable. They do not share a universal base class,
parameter name, state shape, or numerical algorithm merely for visual
symmetry.

**Superseded historical record:** before the directional cutover, reciprocal
Wave NBS/PBS actions exposed relative transmitted/reflected branch Ports. That
lumped splitter Interface was removed atomically; it is not current API truth.

Current directional Cube owners expose physical `CubeTerminal` sides only
through Assembly-issued finite `WaveEncounter` and `RayEncounter` references.
Wave owns the private complex Cube response and coherent contributor sum. Ray
has no coherent amplitude or inter-lane coherent sum and owns a distinct
real-power/polarization-projection law; this does not assert that Rays are
mutually incoherent. Neither account introduces numbered branches or a public
general N-port scattering vocabulary.

### 7. Evidence architecture

Evidence follows the data flow and keeps one decisive owner:

```text
Physical Values -> Sources -> Surface adapters -> Elements -> Propagations
-> Combinations -> Detection -> Assembly -> Workstation
-> State Installation / Ownership -> Numerical Support
-> Architecture / active documentation -> Examples / release
```

Function tests own equations, independent oracles, applicability errors,
gradients, and output invariants. Optical Component tests own registered
state, role/port contracts, meta parity where necessary, and one nominal
Function parity witness. Assembly tests own authored typed data flow,
branch/convergence, exposure, and Workstation replay, not duplicate equation
proofs. Architecture tests own dependency direction, public surface, unique
fact ownership, and forbidden seams. Examples own executable research
narrative and one principal observable, not a second validation framework.

No evidence is deleted until a claim map names the retained decisive witness
for every removed assertion. Test count, line count, and coverage percentage
are not scientific acceptance criteria.

## Trade-off

The atomic rename intentionally breaks the old Combination name, ports, and
error identities. That short-term migration cost buys a durable ubiquitous
language without a permanent compatibility layer.

`IntensityCombination` is less lexically parallel to
`CoherentCombination`, but more physically exact: one consumes observables,
the other consumes fields. The deeper Optical Path Reference module gains one
operation while a shallow forwarding seam disappears. Explicit device guards
add a small amount of policy code, but produce deterministic errors before
backend arithmetic and forbid hidden data movement.

This decision does not add partial coherence, detector integration, random
fields, Ray coherent mixing, a Wave/Ray converter, a public graph framework,
or a second runtime. It makes no feature, speed, memory, ecosystem, or
universal-accuracy claim.

## Conclusion

The implemented structure reads in physical order and closes in numerical order:

```text
field_1 + field_2
  -> coherent compatibility
  -> one Optical Path Reference
  -> complex-field combination

intensity_1 + intensity_2
  -> grid / normalization / axes compatibility
  -> real-observable combination
```

Names reveal values, checks precede mixing, and one deep owner closes the
reference algebra. The architecture is balanced without being mirrored,
compact without being hollow, and explicit without pretending to universal
scope.
