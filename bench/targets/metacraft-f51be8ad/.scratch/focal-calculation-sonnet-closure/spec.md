# Focal calculation Sonnet closure

Status: ready-for-agent

Fixed point: `c46e663f1f6841830994de5e5198dae25b4d1082`

Decision: [ADR 0026](../../docs/adr/0026-let-propagation-and-aplanatic-reference-meet-in-comparison.md)

Research basis: [Flat exit field, vector ASM, and aplanatic Debye](../../docs/research/2026-08-11-flat-field-asm-aplanatic-debye-gap.md)

## Context

MetaCraft already has one public `conduct` Interface, an Authority-backed Study
frontier, component-based Fields, component propagation for current low-NA
routes, electromagnetic propagation for current pointwise high-NA routes, and
FFT/CZT implementations of one Richards--Wolf aplanatic method. Focus work is
scientifically present, but its final architecture is not yet closed: the
selected high-NA field is propagated again during evaluation, the aplanatic
field is calculated at geometric-focus coordinates and relabelled onto the
realized focus plane, the comparison classifies exception text, only CZT is
bound in production, and no multi-process Harness journey proves continuity
from consultation to terminal Result.

## Problem

Segment tests prove useful local facts but do not prove one uninterrupted
scientific life across independent Codex or Claude invocations. Numerical
Implementation names also leak into orchestration while physically different
roles risk being flattened into one generic solver Interface. Immediate
replacement of component propagation by electromagnetic propagation would be
premature: current low-NA PB Fields use a circular basis and converted/retained
power language that the VASM realization does not accept directly.

## Principle

Keep the outer Interface small and the inner roles explicit. `conduct` owns the
complete resumable life; compiled tasks and exact bindings choose realizations;
private formation Modules hide numerical preparation without hiding physical
meaning. A propagated Field and an aplanatic reference are different inputs and
meet only in comparison. FFT and CZT are two realizations of the same physical
method and must qualify independently and together. Scientific facts persist;
live sessions and numerical caches do not.

## Architecture

The target flow is:

```text
Codex or Claude
  -> metacraft-design skill
  -> conduct(byte-identical brief, same application root)
  -> Authority Study frontier
  -> compiled Task + exact Binding
  -> Field propagation -> admitted FocalRegion
  -> aplanatic-reference formation -> admitted reference Field
  -> numerical agreement + physical focal comparison
  -> Focus -> Result -> terminal replay
```

`FocalRegion` owns the selected complex Field samples, axial survey, and the
matching selected power plane. Evaluation reads it and never propagates again.
The aplanatic-reference Module prepares one pupil, forms the FFT natural-grid
reference, repeats those exact coordinates with CZT to establish numerical
agreement, and uses CZT on the exact comparison grid. No algorithm string,
registry, public factory, averaging, fallback, or second lifecycle is allowed.

The external Interface remains `conduct`. The calculation-formation seam is
private and aim-owned. Component propagation and electromagnetic propagation
remain separately qualified until the final parity ticket can judge replacement
readiness. That ticket records the decision but does not perform a conditional
migration inside the terminal seal. If replacement is justified, it produces a
separately reviewable successor proposal; otherwise it records the exact dual
applicability and closes this movement.

## Contracts

- Replace the present least-squares intensity scaling measure with unit-integral
  intensity comparison on one exact uniform grid. For observed and reference
  maps `I_o` and `I_r`, report
  `||I_o/sum(I_o) - I_r/sum(I_r)||_2 / ||I_r/sum(I_r)||_2` after rejecting
  nonfinite or nonpositive sums. Keep aligned complex-field disagreement and
  absolute Poynting power separate.
- Shape mismatch uses a typed fault or owner-local structural validation; no
  caller classifies exception text.
- The aplanatic axial coordinate is
  `found_focus_m - expected_focus_m`; its stored physical surface is the found
  focus plane. Geometric-focus coordinates must never be relabelled.
- FFT and CZT each retain independent analytic qualification. Joint
  matched-grid qualification additionally requires aligned complex error and
  unit-integral intensity error no greater than `1e-10` on the selected device,
  across the frozen low/high-NA, linear/circular, transverse center/off-axis,
  and negative/zero/positive axial-offset fixture matrix.
- `WaitingStudies` is a typed stop. A Harness may retry only after a named
  external capability or evidence fact changes.
- Repeated completed conduct returns the same Result references without opening
  an Adapter, rerunning native work, or repeating propagation.

The initiative is one deliberate schema cutover. Tickets 01, 02 and 04 first
freeze fixed-point document and Result witnesses, then replace the comparison,
focal-region and aplanatic-reference schemas without aliases, migration readers
or dual routes. Existing application roots remain immutable historical
evidence; they are not silently resumed under the new schemas. Qualification
and journey tests use fresh application roots, while explicit stale-schema
tests fail closed without modifying an old root.

## Verification architecture

Four test layers remain distinct and cumulative:

1. numerical qualification for propagation, FFT/CZT, device, dtype, sampling,
   and error limits;
2. scientific Interface tests for Field, FocalRegion, aplanatic reference,
   comparison, Focus, and Result;
3. multi-process application journeys using one application root through every
   typed pause to terminal replay;
4. Codex and Claude Harness acceptance through the same cadence, comparing
   Authority and Result facts rather than prose. Each available executable must
   complete one recorded-evidence smoke journey in fresh sessions; executable
   or authentication absence is an incomplete Harness gate, not a simulated
   pass.

All four recorded journeys are required: low-NA propagation, low-NA PB,
high-NA propagation, and high-NA PB. Native qualification uses two endpoint
cases, one propagation and one PB, with one low-NA and one high-NA endpoint
across the pair. Native absence must be reported, never counted as passing.

## Trade-off

The plan deliberately keeps two propagation realizations during the initiative.
This costs some temporary duplication but avoids corrupting PB basis and power
semantics for aesthetic uniformity. Conversely, it requires both FFT and CZT
for aplanatic binding, increasing local calculation cost in exchange for an
independent numerical consistency fact. Shared pupil preparation, prepared
VASM spectra, batching, and device residency recover performance behind private
seams without widening the Interface.

The schema cutover intentionally makes pre-initiative roots audit-only. This is
less convenient than a compatibility reader, but it preserves one current
contract and prevents old and new metric meanings from sharing one field name.

## Conclusion

The movement closes after eight vertical tickets. It does not continue merely
because another aesthetic refactor is imaginable. Ticket 08 records one of two
valid conclusions: replacement is justified and belongs to a separately
approved successor movement, or both qualified realizations remain with their
exact applicability. This movement does not conditionally rewrite propagation
inside its seal. Either conclusion is complete when the full verification
matrix, documentation truth, dependency direction, public surface, and
terminal replay are sealed.

## Exclusions

- No generic solver, provider, Harness engine, registry, selector, or fallback.
- No embedded AI transport, persisted live session, serialized CUDA tensor, or
  cache-as-authority.
- No averaging FFT and CZT results and no threshold on VASM-versus-aplanatic
  physical comparison.
- No change to user brief facts, materials, cell-study policy, periodic native
  time policy, benchmark truth, or Lumerical construction.
- No claim that low NA alone proves VASM replacement; PB basis, power, sampling,
  performance, and Result parity are all required.
- No in-ticket component-to-electromagnetic propagation migration and no
  compatibility reader for pre-cutover application roots.

## Stop condition

Stop when Tickets 01-08 are completed in dependency order, each required gate
is green, the four recorded journeys and both named Native endpoints are
reported exactly, ADR 0026 and active docs describe present truth, and Ticket 08
records the propagation decision without a compatibility road. A Native
endpoint that cannot run is an explicit incomplete gate, never a pass or a
reason to weaken the plan. A failed gate reopens its owning ticket; it does not
authorize broader refactoring.
